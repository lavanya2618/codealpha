"""
database.py
Handles all SQLite database setup and access for the
SQL Injection Detection System.

NOTE: All queries in this project use parameterized statements
(the sqlite3 "?" placeholder style). This is the real defense
against SQL injection. The keyword-based detector in security.py
is an ADDITIONAL educational/demo layer that blocks obviously
malicious-looking input before it ever reaches the database.
"""

import sqlite3
import os
from datetime import datetime

DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_data.db")


def get_connection():
    """Return a new SQLite connection."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they do not already exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS login_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            status TEXT NOT NULL,
            reason TEXT,
            timestamp TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def add_user(username, password_hash):
    """Insert a new user. Returns True on success, False if username exists."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
            (username, password_hash, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_user(username):
    """Fetch a single user row by username (parameterized query)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row


def log_login_attempt(username, status, reason=""):
    """Record every login attempt (successful, failed, or blocked)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO login_history (username, status, reason, timestamp) VALUES (?, ?, ?, ?)",
        (username, status, reason, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def get_all_login_history():
    """Return all login history rows, most recent first."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM login_history ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows
