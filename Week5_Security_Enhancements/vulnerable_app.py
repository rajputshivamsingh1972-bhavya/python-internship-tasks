#!/usr/bin/env python3
"""
vulnerable_app.py (BASELINE / INSECURE VERSION)

A small user-directory CLI application backed by SQLite: register a
user, log in, search users, and save/restore a "remember me" session.

This is the "provided" application for the Week 5 security exercise.
It contains several deliberate, realistic vulnerabilities, each
labeled below. security_audit.md documents each one being actually
exploited, then fixed in secure_app.py, then re-verified as blocked.

DO NOT deploy this file anywhere real -- it is intentionally insecure.
"""

import pickle
import sqlite3
import traceback

DB_PATH = "users.db"
SESSION_PATH = "session.pkl"

# VULNERABILITY 5: hardcoded secret committed directly in source code.
# Anyone with read access to this file (or the git history) has the
# "secret" -- and because it's baked into the module, it can never be
# rotated without a code change and redeploy.
SECRET_KEY = "supersecretkey123"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def register(conn, username, password, email):
    """
    Register a new user.

    VULNERABILITY 1: password is stored in plain text. Anyone who
    reads users.db (a copy of the file, a backup, a leaked snapshot)
    has every user's real password immediately, with no cracking
    required.

    VULNERABILITY 6: no input validation at all -- username/email can
    be empty, arbitrary length, or contain characters that make later
    processing (or display) unpredictable.
    """
    conn.execute(
        "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
        (username, password, email),
    )
    conn.commit()


def login(conn, username, password):
    """
    Check a username/password pair.

    VULNERABILITY 2: builds the SQL query via an f-string using raw
    user input, instead of a parameterized query. This is a classic
    SQL injection point: an attacker can supply a "username" that
    changes the query's logic entirely (e.g. commenting out the
    password check), bypassing authentication without knowing any
    real password.
    """
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor = conn.execute(query)
    return cursor.fetchone()


def search_users(conn, name_query):
    """
    Search users by partial username match.

    VULNERABILITY 2 (again): also built via raw string interpolation,
    also injectable. Here injection is even more dangerous: an
    attacker can use a UNION-based injection to make this "search"
    endpoint return the `password` column for every user, exfiltrating
    every credential in the database through a feature that was only
    ever meant to return usernames and emails.
    """
    query = f"SELECT username, email FROM users WHERE username LIKE '%{name_query}%'"
    cursor = conn.execute(query)
    return cursor.fetchall()


def save_session(user_data):
    """
    Persist a "remember me" session to disk.

    VULNERABILITY 3: uses `pickle` to serialize session data. Pickle
    is not a data format -- it's a bytecode-like stream that can
    execute arbitrary Python during deserialization via an object's
    `__reduce__` method. If an attacker can get their own bytes into
    session.pkl (e.g. by intercepting it, or if it's ever loaded from
    a location they can write to), loading it can run arbitrary code
    with the privileges of whatever process calls load_session().
    """
    with open(SESSION_PATH, "wb") as f:
        pickle.dump(user_data, f)


def load_session():
    """Load a previously saved session. See VULNERABILITY 3 above."""
    with open(SESSION_PATH, "rb") as f:
        return pickle.load(f)


def handle_error(exc):
    """
    Report an error to the user.

    VULNERABILITY 4: prints the full exception traceback directly to
    the console/user, including file paths, line numbers, and --
    critically -- the raw SQL query text in cases like a malformed
    injection attempt. This leaks internal implementation details
    (schema, code structure, query construction) that make follow-up
    attacks easier, and is a form of information/data leakage.
    """
    print("An error occurred:")
    traceback.print_exc()


def main():
    conn = init_db()
    print("=== Vulnerable User Directory (for security audit purposes) ===")
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
                print("Login OK:", row) if row else print("Login failed.")
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
        except Exception as exc:
            handle_error(exc)


if __name__ == "__main__":
    main()
