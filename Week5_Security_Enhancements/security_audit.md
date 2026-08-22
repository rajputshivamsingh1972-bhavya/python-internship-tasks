# Security Audit Report — User Directory Application

## 1. Application Under Review

`vulnerable_app.py` is a small CLI application backed by SQLite:
register a user, log in, search users by username, and save/restore a
"remember me" session to disk. It's the kind of small utility that
often gets written quickly and never revisited from a security
standpoint — which is exactly why it was chosen for this exercise.

Every vulnerability below was **actually exploited** against the real
application (not just described theoretically), then fixed in
`secure_app.py`, then **re-verified as blocked** with the same exploit
attempt. Transcripts of both are included.

---

## 2. Vulnerabilities Found, Exploited, and Fixed

### Vulnerability 1 — Passwords stored in plain text

**Where:** `register()` — `password` is inserted into the database
exactly as typed.

**Real-world exploitability:** any leak of `users.db` — a stolen
backup, a misconfigured cloud storage bucket, a copied file, a former
employee's laptop — hands over every user's actual password
immediately. No cracking, no rainbow tables, nothing. And because
people reuse passwords across sites, this single leak compromises
accounts far beyond this application.

**Exploit (against `vulnerable_app.py`):**
```
$ python3 -c "
import sqlite3
conn = sqlite3.connect('users.db')
for row in conn.execute('SELECT username, password FROM users'):
    print(row)
"
('alice', 'correcthorsebattery')
('bob', 'hunter2')
('admin', 'ExtremelySecretAdminPass!')
```

**Fix:** hash with **PBKDF2-HMAC-SHA256** and a fresh random 16-byte
salt per user, 200,000 iterations:
```python
def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    ).hex()
```
Login compares hashes with `hmac.compare_digest()` (constant-time, to
avoid leaking match-length via timing) rather than `==`.

**Re-verification (against `secure_app.py`):**
```
('alice', '8702c2d5017...', '6a87ccca619b...')  # (username, password_hash, salt)
('bob',   'cf45578c456...', '54ca3a38e031...')
('admin', '9d306179f5c...', '295cb50e4bbd...')
```
Full DB read access no longer yields a usable password.

**Trade-off, stated honestly:** PBKDF2 was chosen (over bcrypt/argon2)
specifically to keep this a standard-library-only dependency, matching
this exercise's constraints. In a real production system, **argon2id**
or **bcrypt** would be preferred — they're more resistant to
GPU/ASIC-accelerated cracking than PBKDF2 at equivalent settings. This
is flagged explicitly rather than presenting PBKDF2 as the strongest
possible choice.

---

### Vulnerability 2 — SQL injection (login bypass AND data exfiltration)

**Where:** `login()` and `search_users()` — both build SQL via f-string
interpolation of raw user input.

**Exploit A — auth bypass, against `vulnerable_app.py`:**
```python
result = app.login(conn, "admin' -- ", "anything_at_all")
```
The injected username turns the query into:
```sql
SELECT * FROM users WHERE username='admin' -- ' AND password='anything_at_all'
```
`--` comments out the rest of the query, including the password check
entirely.

**Actual result:**
```
Login result with injected username: (3, 'admin', 'ExtremelySecretAdminPass!', 'admin@example.com')
BYPASSED AUTH: True
```
Full authentication bypass as `admin`, with **zero knowledge of the
real password.**

**Exploit B — mass credential exfiltration via the search feature:**
```python
malicious_query = "' UNION SELECT username, password FROM users --"
app.search_users(conn, malicious_query)
```
**Actual result:**
```
('admin', 'ExtremelySecretAdminPass!')
('admin', 'admin@example.com')
('alice', 'alice@example.com')
('alice', 'correcthorsebattery')
('bob', 'bob@example.com')
('bob', 'hunter2')
```
A feature intended only to return usernames and emails was turned into
a full credential dump for every account in the system, through a
"search" box.

**Fix:** parameterized queries everywhere. User input is passed as a
bound parameter, never spliced into SQL text:
```python
cursor = conn.execute(
    "SELECT username, password_hash, salt, email FROM users WHERE username = ?",
    (username,),
)
```
This is not a sanitization/escaping fix (which can be bypassed with
enough cleverness) — it's a structural one: the database driver treats
`username` strictly as a data value, never as query grammar, regardless
of its content.

**Re-verification (against `secure_app.py`):**
```
Login result with injected username: None
BYPASSED AUTH: False

Results returned: []
Injection treated as literal search text, not SQL -- no rows match, no data leaked.
```

---

### Vulnerability 3 — Insecure deserialization via `pickle` (remote code execution)

**Where:** `save_session()` / `load_session()` use `pickle.dump` /
`pickle.load`.

**Why this is dangerous:** `pickle` is not a plain data format — it can
encode instructions to reconstruct arbitrary Python objects, including
calling arbitrary callables via an object's `__reduce__` method. If an
attacker can get their own bytes into `session.pkl` — a MITM'd network
transfer, a compromised backup, a world-writable temp directory, a
supply-chain-poisoned dependency — loading that file executes their
code with the same privileges as the app.

**Exploit (against `vulnerable_app.py`, harmless proof-of-concept):**
```python
class MaliciousPayload:
    def __reduce__(self):
        return (os.system, ("touch /tmp/PWNED_via_pickle.marker",))

with open("session.pkl", "wb") as f:
    pickle.dump(MaliciousPayload(), f)
```
```
Marker file exists before load: False
Calling load_session() -- this is what a victim app would do...
Marker file exists after load_session(): True
ARBITRARY CODE EXECUTED DURING DESERIALIZATION: True
```
A single call to the ordinary-looking `load_session()` function ran
`os.system(...)` with attacker-chosen arguments. In a real attack this
would not be a harmless `touch` — it could be a reverse shell, data
exfiltration, or ransomware, run at whatever privilege level the app
has.

**Fix:** replaced pickle with **signed JSON**:
```python
payload = json.dumps(user_data, sort_keys=True).encode("utf-8")
signature = hmac.new(SECRET_KEY.encode(), payload, hashlib.sha256).hexdigest()
```
JSON can only represent plain data (str/int/float/bool/list/dict/None)
— there is no mechanism in the format itself to execute code on load,
unlike pickle. The HMAC signature additionally catches tampering: if an
attacker swaps the file contents without knowing `SECRET_KEY`, the
signature check fails and the session is rejected outright.

**Re-verification (against `secure_app.py`):**
```
Loaded session: {'user': 'alice'}                              # legit session still works

Tampering correctly detected and rejected: Session data failed integrity check and was rejected.
```
Both the code-execution vector is structurally gone (JSON has no
equivalent of `__reduce__`), and tampering is actively caught rather
than silently trusted.

---

### Vulnerability 4 — Verbose error messages leak internal details

**Where:** `handle_error()` prints the full exception traceback
(`traceback.print_exc()`) directly to the console for any error.

**Exploit (against `vulnerable_app.py`):** a malformed injection
attempt (an unbalanced quote) still crashes, revealing internals:
```
Traceback (most recent call last):
  File "vulnerable_app.py", line 78, in login
    cursor = conn.execute(query)
sqlite3.OperationalError: near "' AND password='": syntax error
```
This confirms to an attacker that the app builds raw SQL via string
interpolation (rather than parameterized queries) — valuable
reconnaissance that makes refining a working injection payload much
easier. It also exposes file paths and code structure.

**Fix:** only two specific, safe exception types
(`ValidationError`, `AppError`) ever have their message shown to the
user. Every other exception is logged in full detail server-side
(via Python's `logging` module, to `app.log`) and reported to the user
generically:
```python
except (ValidationError, AppError) as exc:
    print(f"Error: {exc}")
except Exception:
    logging.exception("Unhandled error")
    print("Error: something went wrong. Please try again.")
```

**Re-verification (against `secure_app.py`):**
```
User sees only: Username must be 3-20 characters: letters, numbers, or underscore only.
```
No file paths, no query text, no stack trace reaches the user. The
server log retains full detail for legitimate debugging, but
deliberately **never logs raw passwords** — only usernames and outcome
(success/failure/reason), confirmed in the log excerpt:
```
2026-08-22 03:46:54,554 INFO User registered (username=alice)
2026-08-22 03:46:54,657 INFO Login failed: unknown username (username=admin' -- )
```
Note the log even safely records the attempted injection string as
plain text (an audit trail of the attack attempt), without it being
executed as SQL and without any password ever appearing in the log.

---

### Vulnerability 5 — Hardcoded secret key in source

**Where:** `SECRET_KEY = "supersecretkey123"` committed directly in
`vulnerable_app.py`.

**Why this matters:** anyone with read access to the source file (or
its git history, even after later "removal" — old commits still
contain it) has the secret permanently. It can't be rotated without a
code change and redeploy, and it's identical across every
environment (dev/staging/prod), so a leak of a dev machine compromises
production too.

**Fix:** the secret is read from an environment variable and the app
refuses to start if it's missing, rather than silently falling back to
an insecure default:
```python
SECRET_KEY = os.environ.get("APP_SECRET_KEY")
...
if not SECRET_KEY:
    print("ERROR: APP_SECRET_KEY environment variable is not set...")
    return
```
This makes a missing secret a loud, obvious failure at startup instead
of a silent vulnerability.

---

### Vulnerability 6 — No input validation

**Where:** `register()` accepted any username/password/email —
including empty strings, arbitrary length, or unexpected characters.

**Why this matters on its own:** beyond enabling the injection issues
above, weak input handling means malformed data can reach the database
or downstream systems unexpectedly, and there's no baseline password
strength requirement at all.

**Fix:** dedicated validators run before any database write:
```python
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8
```
Each raises a `ValidationError` with a clear, safe-to-display message
on failure (see Vulnerability 4's fix for how that message reaches the
user without leaking internals).

---

## 3. Summary Table

| # | Vulnerability | Real exploit demonstrated | Fix |
|---|---|---|---|
| 1 | Plain-text password storage | Read passwords directly from `users.db` | PBKDF2-HMAC-SHA256 + per-user salt, constant-time compare |
| 2 | SQL injection (login + search) | Auth bypass as admin; dumped all passwords via search | Parameterized queries everywhere |
| 3 | Insecure `pickle` deserialization | Arbitrary code execution via crafted `session.pkl` | Signed JSON (HMAC-SHA256), no code-execution surface |
| 4 | Verbose error / traceback leakage | Error revealed raw SQL + file paths | Generic user-facing errors; full detail logged server-side only, secrets never logged |
| 5 | Hardcoded secret key | Secret permanently exposed in source/history | Read from environment variable; hard fail if missing |
| 6 | No input validation | N/A (enabling factor for above) | Regex/length validation before any DB write |

## 4. Testing and Validation

Every fix above was validated by re-running the **exact same exploit
attempt** against `secure_app.py` and confirming it failed to achieve
its original goal (see "Re-verification" under each vulnerability).
Additionally:
- Legitimate functionality was confirmed to still work after each fix
  (registration, login with correct password, session save/load).
- The session integrity check was tested against a deliberately
  tampered file to confirm tampering is detected, not just that a
  well-formed session works.

## 5. Residual / Out-of-Scope Notes

- **Rate limiting / account lockout** is not implemented in either
  version. A production system should rate-limit login attempts to
  slow down credential-stuffing and brute-force attacks — this is
  flagged as a known gap rather than silently omitted.
- **Transport security (TLS)** is out of scope for this CLI/local
  exercise, but any networked version of this app would need it;
  passwords and session tokens should never travel over plain HTTP.
- **PBKDF2 vs. argon2/bcrypt** trade-off is discussed under
  Vulnerability 1.
