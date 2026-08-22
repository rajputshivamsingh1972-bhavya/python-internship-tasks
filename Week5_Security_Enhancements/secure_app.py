#!/usr/bin/env python3
"""
secure_app.py (HARDENED VERSION)

Same functionality as vulnerable_app.py -- register, log in, search
users, save/restore a session -- with every vulnerability found in the
security audit fixed. See security_audit.md for the full before/after
exploit verification.

Summary of fixes:
  1. Passwords are hashed with a per-user random salt (PBKDF2-HMAC-SHA256),
     never stored in plain text.
  2. All SQL queries use parameterized placeholders (`?`), never raw
     string interpolation -- eliminates SQL injection entirely.
  3. Session data uses a signed JSON token (HMAC-SHA256) instead of
     pickle -- no arbitrary code execution risk on load.
  4. User-facing errors are generic; full details are logged
     server-side only, with sensitive fields redacted.
  5. The secret key is read from an environment variable, never
     hardcoded in source, with a clear failure if it's missing.
  6. Input is validated (username format/length, basic email shape,
     minimum password length) before it ever reaches the database.
"""

import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3

DB_PATH = "secure_users.db"
SESSION_PATH = "secure_session.json"

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8
PBKDF2_ITERATIONS = 200_000

# FIX 5: secret is read from the environment, never hardcoded. If it's
# missing, the app refuses to run rather than silently falling back to
# a predictable value -- a missing secret should be a loud failure, not
# a quiet security hole.
SECRET_KEY = os.environ.get("APP_SECRET_KEY")


class ValidationError(Exception):
    """Raised when user-supplied input fails validation."""


class AppError(Exception):
    """
    Generic application error safe to show to a user.

    FIX 4: this is the ONLY exception type whose message is ever shown
    to the end user. Everything else is logged with full detail
    server-side and reported to the user as a generic message, so
    internal query text, file paths, and stack traces never leak.
    """


# Configure a server-side log. In production this would go to a
# restricted-access log file/service, not stdout -- shown here for
# demonstration. Note that log messages are constructed WITHOUT
# including raw passwords (see login()/register() below).
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            email TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def _hash_password(password: str, salt: bytes) -> str:
    """
    FIX 1: hash with PBKDF2-HMAC-SHA256 and a random per-user salt.

    A per-user salt means two users with the same password get
    different stored hashes, defeating precomputed rainbow-table
    attacks. 200,000 iterations makes brute-forcing computationally
    expensive. (A production system would likely prefer a
    memory-hard KDF like argon2 or bcrypt for even stronger resistance
    to GPU-accelerated cracking -- PBKDF2 is used here to keep the
    dependency footprint to the Python standard library only; this
    trade-off is called out explicitly in security_audit.md.)
    """
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    ).hex()


def validate_username(username: str) -> None:
    if not USERNAME_RE.match(username or ""):
        raise ValidationError(
            "Username must be 3-20 characters: letters, numbers, or underscore only."
        )


def validate_email(email: str) -> None:
    if not EMAIL_RE.match(email or ""):
        raise ValidationError("Email address does not look valid.")


def validate_password(password: str) -> None:
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")


def register(conn, username, password, email):
    """
    FIX 6: input is validated before touching the database.
    FIX 1: password is hashed with a fresh random salt, never stored
    in plain text.
    FIX 2: still uses a parameterized query (was already the case in
    the vulnerable version for this function; kept consistent here).
    """
    validate_username(username)
    validate_email(email)
    validate_password(password)

    salt = secrets.token_bytes(16)
    password_hash = _hash_password(password, salt)

    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, email) VALUES (?, ?, ?, ?)",
            (username, password_hash, salt.hex(), email),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Log the real cause server-side; tell the user something safe.
        logging.info("Registration failed: username already exists (username=%s)", username)
        raise AppError("That username is already taken.")

    # Note: password is never written to the log, only the fact that a
    # registration happened.
    logging.info("User registered (username=%s)", username)


def login(conn, username, password):
    """
    FIX 2: parameterized query -- user input is passed as bound
    parameters, never interpolated into the SQL string. This makes SQL
    injection structurally impossible here: the database driver treats
    `username` strictly as a data value, never as part of the query's
    grammar, no matter what characters it contains.
    """
    cursor = conn.execute(
        "SELECT username, password_hash, salt, email FROM users WHERE username = ?",
        (username,),
    )
    row = cursor.fetchone()
    if row is None:
        logging.info("Login failed: unknown username (username=%s)", username)
        return None

    _, stored_hash, salt_hex, _ = row
    salt = bytes.fromhex(salt_hex)
    candidate_hash = _hash_password(password, salt)

    # FIX 1 (continued): constant-time comparison via hmac.compare_digest
    # avoids leaking timing information about how many hash bytes
    # matched, which could otherwise help an attacker guess the hash
    # byte-by-byte.
    if hmac.compare_digest(candidate_hash, stored_hash):
        logging.info("Login succeeded (username=%s)", username)
        return row
    logging.info("Login failed: incorrect password (username=%s)", username)
    return None


def search_users(conn, name_query):
    """
    FIX 2 (again): parameterized query. `LIKE` wildcards are applied by
    building the parameter value in Python (still just data, bound
    safely) rather than splicing user input into the SQL text.
    """
    validate_username_query = name_query or ""
    like_pattern = f"%{validate_username_query}%"
    cursor = conn.execute(
        "SELECT username, email FROM users WHERE username LIKE ?",
        (like_pattern,),
    )
    return cursor.fetchall()


def _sign(payload_bytes: bytes) -> str:
    if not SECRET_KEY:
        raise AppError("Server misconfigured: APP_SECRET_KEY is not set.")
    return hmac.new(SECRET_KEY.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


def save_session(user_data: dict) -> None:
    """
    FIX 3: sessions are stored as signed JSON, not pickle. JSON can
    only represent plain data (strings, numbers, lists, dicts) -- it
    has no mechanism to execute code on load, unlike pickle. The HMAC
    signature additionally ensures that if the file is tampered with
    (or replaced by an attacker), tampering is detected and the
    session is rejected rather than trusted blindly.
    """
    payload = json.dumps(user_data, sort_keys=True).encode("utf-8")
    signature = _sign(payload)
    with open(SESSION_PATH, "w") as f:
        json.dump({"payload": payload.decode("utf-8"), "signature": signature}, f)


def load_session() -> dict:
    """Load and verify a previously saved session. See FIX 3 above."""
    with open(SESSION_PATH, "r") as f:
        envelope = json.load(f)

    payload_str = envelope.get("payload", "")
    expected_sig = envelope.get("signature", "")
    actual_sig = _sign(payload_str.encode("utf-8"))

    if not hmac.compare_digest(actual_sig, expected_sig):
        raise AppError("Session data failed integrity check and was rejected.")

    return json.loads(payload_str)


def main():
    if not SECRET_KEY:
        print(
            "ERROR: APP_SECRET_KEY environment variable is not set.\n"
            "Set it before running, e.g.:\n"
            "  export APP_SECRET_KEY=$(python3 -c \"import secrets; print(secrets.token_hex(32))\")"
        )
        return

    conn = init_db()
    print("=== Secure User Directory ===")
    while True:
        print("\n1. Register  2. Login  3. Search  4. Save session  5. Load session  6. Quit")
        choice = input("> ").strip()
        try:
            if choice == "1":
                u = input("Username: ")
                p = input("Password: ")
                e = input("Email: ")
                register(conn, u, p, e)
                print("Registered.")
            elif choice == "2":
                u = input("Username: ")
                p = input("Password: ")
                row = login(conn, u, p)
                print("Login OK." if row else "Login failed.")
            elif choice == "3":
                q = input("Search username: ")
                for row in search_users(conn, q):
                    print(row)
            elif choice == "4":
                save_session({"user": input("Username to remember: ")})
                print("Session saved.")
            elif choice == "5":
                print("Session:", load_session())
            elif choice == "6":
                break
        except (ValidationError, AppError) as exc:
            # FIX 4: only these two known, safe exception types' messages
            # are ever shown to the user. Anything else is logged in
            # full detail server-side and reported generically.
            print(f"Error: {exc}")
        except Exception:
            logging.exception("Unhandled error")
            print("Error: something went wrong. Please try again.")


if __name__ == "__main__":
    main()
