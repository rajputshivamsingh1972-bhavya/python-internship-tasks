# Week 5 — Security Enhancements in Python Applications

## What this is

A small SQLite-backed user-directory CLI app, built in two versions:

- `vulnerable_app.py` — a realistic first draft with 6 real,
  deliberately-planted security vulnerabilities
- `secure_app.py` — the same functionality, fully hardened

Every vulnerability was **actually exploited** against the vulnerable
version (not just described), then fixed, then the same exploit was
**re-run against the secure version to confirm it's blocked.** Full
transcripts of both are in **`security_audit.md`** — start there.

## Files

```
vulnerable_app.py   - insecure baseline (SQL injection, plaintext passwords,
                       insecure pickle deserialization, verbose errors,
                       hardcoded secret, no input validation)
secure_app.py        - hardened version: parameterized queries, salted
                       password hashing, signed JSON sessions, generic
                       error messages, env-var secret, input validation
security_audit.md    - full audit: each vulnerability, its exploit,
                       the fix, and re-verification (the main report)
```

## How to reproduce

**Vulnerable version** (do not use outside this exercise):
```bash
python3 vulnerable_app.py
```

**Secure version** — requires a secret key set via environment variable:
```bash
export APP_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
python3 secure_app.py
```

To see the exploits and their fixes run directly, see the code blocks
in `security_audit.md` — every one of them is a real, copy-pasteable
Python snippet that was actually executed against these two files.

## Result

| Vulnerability | Status in `secure_app.py` |
|---|---|
| SQL injection (login bypass) | Blocked — parameterized queries |
| SQL injection (mass credential exfiltration via search) | Blocked — parameterized queries |
| Plain-text password storage | Fixed — PBKDF2-HMAC-SHA256 + per-user salt |
| Insecure `pickle` deserialization (RCE) | Fixed — signed JSON, no code-execution surface |
| Verbose error / internal leakage | Fixed — generic user-facing errors, detailed server-side logging |
| Hardcoded secret key | Fixed — read from environment, hard-fails if missing |
| No input validation | Fixed — username/email/password validated before any DB write |
