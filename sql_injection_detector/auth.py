"""
auth.py
Handles user registration and login logic, including password
hashing and calling the SQL-injection detector before touching
the database.
"""

import hashlib
import database
import security


def hash_password(password: str) -> str:
    """Return a SHA-256 hash of the password (simple, for demo purposes)."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register_user(username: str, password: str):
    """
    Register a new user.

    Returns (success: bool, message: str)
    """
    is_malicious, offending_value, pattern = security.check_inputs(username, password)
    if is_malicious:
        return False, "SQL Injection Detected! Registration blocked."

    if not username or not password:
        return False, "Username and password cannot be empty."

    hashed = hash_password(password)
    success = database.add_user(username, hashed)

    if success:
        return True, "Registration successful! You can now log in."
    else:
        return False, "Username already exists. Please choose another."


def login_user(username: str, password: str):
    """
    Attempt to log a user in.

    Returns (success: bool, message: str)
    Every attempt (blocked, failed, or successful) is logged to login_history.
    """
    # 1. Check for SQL injection patterns first.
    is_malicious, offending_value, pattern = security.check_inputs(username, password)
    if is_malicious:
        database.log_login_attempt(
            username or "(empty)",
            status="BLOCKED",
            reason=f"SQL Injection pattern detected: {pattern}",
        )
        return False, "SQL Injection Detected!"

    # 2. Normal credential check using parameterized queries.
    user_row = database.get_user(username)
    if user_row is None:
        database.log_login_attempt(username, status="FAILED", reason="User not found")
        return False, "Invalid username or password."

    hashed = hash_password(password)
    if user_row["password"] == hashed:
        database.log_login_attempt(username, status="SUCCESS", reason="")
        return True, f"Welcome back, {username}!"
    else:
        database.log_login_attempt(username, status="FAILED", reason="Incorrect password")
        return False, "Invalid username or password."
