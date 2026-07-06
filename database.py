"""
database.py
------------
All database access for the Cloud-Based Bus Pass System lives in this module.
Keeping it separate from app.py keeps the project modular, easy to maintain,
and easy to port to any cloud SQLite-compatible host (Streamlit Cloud, etc.).

Every query uses parameterized placeholders ("?") to prevent SQL Injection.
"""

import os
import sqlite3
import hashlib
import secrets
import string
import random
from datetime import datetime, timedelta

# --------------------------------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

PASS_VALIDITY_DAYS = 30  # A booked pass stays "Active" for 30 days from travel date

# Static route/distance matrix (km) — used for automatic fare calculation.
# In a production system this could be its own table; kept as a constant here
# for simplicity and fast lookups.
CITIES = ["Mumbai", "Pune", "Nashik", "Nagpur", "Aurangabad", "Kolhapur", "Solapur", "Thane"]

DISTANCE_MATRIX = {
    ("Mumbai", "Pune"): 150, ("Mumbai", "Nashik"): 167, ("Mumbai", "Nagpur"): 837,
    ("Mumbai", "Aurangabad"): 335, ("Mumbai", "Kolhapur"): 395, ("Mumbai", "Solapur"): 402,
    ("Mumbai", "Thane"): 25,
    ("Pune", "Nashik"): 210, ("Pune", "Nagpur"): 710, ("Pune", "Aurangabad"): 235,
    ("Pune", "Kolhapur"): 230, ("Pune", "Solapur"): 250, ("Pune", "Thane"): 150,
    ("Nashik", "Nagpur"): 680, ("Nashik", "Aurangabad"): 180, ("Nashik", "Kolhapur"): 450,
    ("Nashik", "Solapur"): 380, ("Nashik", "Thane"): 165,
    ("Nagpur", "Aurangabad"): 500, ("Nagpur", "Kolhapur"): 850, ("Nagpur", "Solapur"): 460,
    ("Nagpur", "Thane"): 830,
    ("Aurangabad", "Kolhapur"): 380, ("Aurangabad", "Solapur"): 260, ("Aurangabad", "Thane"): 320,
    ("Kolhapur", "Solapur"): 225, ("Kolhapur", "Thane"): 385,
    ("Solapur", "Thane"): 400,
}

BUS_TYPES = ["Ordinary", "Express", "AC"]
DEFAULT_FARE_RATES = {"Ordinary": 1.0, "Express": 1.5, "AC": 2.5}  # ₹ per km


# --------------------------------------------------------------------------------------
# CONNECTION HELPERS
# --------------------------------------------------------------------------------------
def get_connection():
    """Return a new SQLite connection with row_factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """
    Create all required tables if they do not already exist, and seed
    default fare rates. Safe to call every time the app starts.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            phone         TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            salt          TEXT NOT NULL,
            created_at    TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS fares (
            bus_type     TEXT PRIMARY KEY,
            rate_per_km  REAL NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            pass_id       TEXT NOT NULL UNIQUE,
            user_id       INTEGER NOT NULL,
            source        TEXT NOT NULL,
            destination   TEXT NOT NULL,
            bus_type      TEXT NOT NULL,
            distance_km   REAL NOT NULL,
            travel_date   TEXT NOT NULL,
            fare          REAL NOT NULL,
            booking_date  TEXT NOT NULL,
            expiry_date   TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'Active',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )

    # Seed default fare rates only if the table is empty
    cur.execute("SELECT COUNT(*) AS cnt FROM fares")
    if cur.fetchone()["cnt"] == 0:
        for bus_type, rate in DEFAULT_FARE_RATES.items():
            cur.execute(
                "INSERT INTO fares (bus_type, rate_per_km) VALUES (?, ?)",
                (bus_type, rate),
            )

    conn.commit()
    conn.close()


# --------------------------------------------------------------------------------------
# PASSWORD SECURITY (PBKDF2-HMAC-SHA256 with per-user salt)
# --------------------------------------------------------------------------------------
def hash_password(password: str, salt: str) -> str:
    """Return a secure PBKDF2-HMAC-SHA256 hash of the password using the given salt."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    ).hex()


def generate_salt() -> str:
    """Generate a cryptographically secure random salt."""
    return secrets.token_hex(16)


# --------------------------------------------------------------------------------------
# USER MANAGEMENT
# --------------------------------------------------------------------------------------
def email_exists(email: str) -> bool:
    """Check whether an email is already registered (parameterized query)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE email = ?", (email.strip().lower(),))
    found = cur.fetchone() is not None
    conn.close()
    return found


def register_user(name: str, email: str, phone: str, password: str):
    """
    Register a new user with a securely hashed password.
    Returns (success: bool, message: str).
    """
    try:
        if email_exists(email):
            return False, "This email is already registered. Please log in instead."

        salt = generate_salt()
        pw_hash = hash_password(password, salt)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (name, email, phone, password_hash, salt, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name.strip(),
                email.strip().lower(),
                phone.strip(),
                pw_hash,
                salt,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        conn.close()
        return True, "Registration successful! You can now log in."
    except sqlite3.IntegrityError:
        return False, "This email is already registered."
    except Exception as exc:  # noqa: BLE001
        return False, f"Unexpected error during registration: {exc}"


def authenticate_user(email: str, password: str):
    """
    Verify email/password. Returns the user row (dict) on success, else None.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    computed_hash = hash_password(password, row["salt"])
    if secrets.compare_digest(computed_hash, row["password_hash"]):
        return dict(row)
    return None


def get_user_by_id(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_users():
    """Return all registered users as a list of dicts (for admin panel)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, phone, created_at FROM users ORDER BY id ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def search_users(term: str):
    """Search users by name or email (admin panel)."""
    conn = get_connection()
    cur = conn.cursor()
    like_term = f"%{term.strip()}%"
    cur.execute(
        """
        SELECT id, name, email, phone, created_at FROM users
        WHERE name LIKE ? OR email LIKE ?
        ORDER BY id ASC
        """,
        (like_term, like_term),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def delete_user(user_id: int):
    """Delete a user and all their bookings (admin action). Returns (success, message)."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM bookings WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        affected = cur.rowcount
        conn.close()
        if affected == 0:
            return False, "No user found with that ID."
        return True, "User and their bookings were deleted successfully."
    except Exception as exc:  # noqa: BLE001
        return False, f"Unexpected error: {exc}"


# --------------------------------------------------------------------------------------
# FARE MANAGEMENT
# --------------------------------------------------------------------------------------
def get_fare_rates():
    """Return a dict {bus_type: rate_per_km}."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT bus_type, rate_per_km FROM fares")
    rates = {row["bus_type"]: row["rate_per_km"] for row in cur.fetchall()}
    conn.close()
    return rates


def update_fare_rate(bus_type: str, new_rate: float):
    """Admin: update the per-km rate for a bus type."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE fares SET rate_per_km = ? WHERE bus_type = ?",
            (new_rate, bus_type),
        )
        conn.commit()
        conn.close()
        return True, f"Fare for {bus_type} updated to ₹{new_rate:.2f}/km."
    except Exception as exc:  # noqa: BLE001
        return False, f"Unexpected error: {exc}"


def get_distance(source: str, destination: str):
    """Look up distance (km) between two cities from the static matrix."""
    if source == destination:
        return None
    key = (source, destination)
    reverse_key = (destination, source)
    if key in DISTANCE_MATRIX:
        return DISTANCE_MATRIX[key]
    if reverse_key in DISTANCE_MATRIX:
        return DISTANCE_MATRIX[reverse_key]
    return None


def calculate_fare(source: str, destination: str, bus_type: str):
    """Return (distance_km, fare) for a given route and bus type, or (None, None)."""
    distance = get_distance(source, destination)
    if distance is None:
        return None, None
    rates = get_fare_rates()
    rate = rates.get(bus_type, DEFAULT_FARE_RATES.get(bus_type, 1.0))
    fare = round(distance * rate, 2)
    return distance, fare


# --------------------------------------------------------------------------------------
# BOOKING / PASS MANAGEMENT
# --------------------------------------------------------------------------------------
def generate_pass_id():
    """Generate a unique, human-readable Pass ID, e.g. BP-7F3K9QZ2."""
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=8))
    return f"BP-{suffix}"


def create_booking(user_id: int, source: str, destination: str, bus_type: str, travel_date: str):
    """
    Create a new bus pass booking with automatic fare calculation and a unique
    Pass ID. Returns (success, message, booking_dict_or_None).
    """
    distance, fare = calculate_fare(source, destination, bus_type)
    if distance is None:
        return False, "No route found between the selected cities.", None

    pass_id = generate_pass_id()
    booking_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        travel_dt = datetime.strptime(travel_date, "%Y-%m-%d")
    except ValueError:
        return False, "Invalid travel date format.", None

    expiry_dt = travel_dt + timedelta(days=PASS_VALIDITY_DAYS)
    expiry_date = expiry_dt.strftime("%Y-%m-%d")

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO bookings
                (pass_id, user_id, source, destination, bus_type, distance_km,
                 travel_date, fare, booking_date, expiry_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active')
            """,
            (pass_id, user_id, source, destination, bus_type, distance,
             travel_date, fare, booking_date, expiry_date),
        )
        conn.commit()
        conn.close()
        booking = {
            "pass_id": pass_id, "user_id": user_id, "source": source,
            "destination": destination, "bus_type": bus_type, "distance_km": distance,
            "travel_date": travel_date, "fare": fare, "booking_date": booking_date,
            "expiry_date": expiry_date, "status": "Active",
        }
        return True, "Bus pass booked successfully!", booking
    except sqlite3.IntegrityError:
        return False, "Pass ID collision occurred, please try again.", None
    except Exception as exc:  # noqa: BLE001
        return False, f"Unexpected error: {exc}", None


def get_bookings_by_user(user_id: int):
    """Return all bookings for a specific user, most recent first."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM bookings WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_all_bookings():
    """Return all bookings joined with user name/email (for admin panel)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.*, u.name AS user_name, u.email AS user_email
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        ORDER BY b.id DESC
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def search_booking_by_pass_id(pass_id: str):
    """Find a single booking by its exact/partial Pass ID."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.*, u.name AS user_name, u.email AS user_email
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        WHERE b.pass_id LIKE ?
        ORDER BY b.id DESC
        """,
        (f"%{pass_id.strip()}%",),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def filter_bookings_by_date(start_date: str, end_date: str, user_id: int = None):
    """
    Filter bookings whose travel_date falls within [start_date, end_date].
    If user_id is given, restrict to that user; otherwise return all (admin use).
    """
    conn = get_connection()
    cur = conn.cursor()
    if user_id is not None:
        cur.execute(
            """
            SELECT * FROM bookings
            WHERE travel_date BETWEEN ? AND ? AND user_id = ?
            ORDER BY travel_date ASC
            """,
            (start_date, end_date, user_id),
        )
    else:
        cur.execute(
            """
            SELECT b.*, u.name AS user_name, u.email AS user_email
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            WHERE b.travel_date BETWEEN ? AND ?
            ORDER BY b.travel_date ASC
            """,
            (start_date, end_date),
        )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def cancel_booking(pass_id: str, user_id: int = None):
    """
    Cancel (soft-delete) a booking by setting its status to 'Cancelled'.
    If user_id is provided, ensures the booking belongs to that user.
    Returns (success, message).
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        if user_id is not None:
            cur.execute(
                "UPDATE bookings SET status = 'Cancelled' WHERE pass_id = ? AND user_id = ?",
                (pass_id, user_id),
            )
        else:
            cur.execute(
                "UPDATE bookings SET status = 'Cancelled' WHERE pass_id = ?",
                (pass_id,),
            )
        conn.commit()
        affected = cur.rowcount
        conn.close()
        if affected == 0:
            return False, "Pass not found or you do not have permission to cancel it."
        return True, "Bus pass cancelled successfully."
    except Exception as exc:  # noqa: BLE001
        return False, f"Unexpected error: {exc}"


def get_active_pass_count(user_id: int) -> int:
    """Count currently active (not cancelled, not expired) passes for a user."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS cnt FROM bookings
        WHERE user_id = ? AND status = 'Active' AND expiry_date >= ?
        """,
        (user_id, today),
    )
    count = cur.fetchone()["cnt"]
    conn.close()
    return count


def get_total_spent(user_id: int) -> float:
    """Sum of fares for all non-cancelled bookings of a user."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COALESCE(SUM(fare), 0) AS total FROM bookings WHERE user_id = ? AND status != 'Cancelled'",
        (user_id,),
    )
    total = cur.fetchone()["total"]
    conn.close()
    return total


def get_next_expiry(user_id: int):
    """Return the soonest upcoming expiry date among active passes, or None."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT MIN(expiry_date) AS next_expiry FROM bookings
        WHERE user_id = ? AND status = 'Active' AND expiry_date >= ?
        """,
        (user_id, today),
    )
    row = cur.fetchone()
    conn.close()
    return row["next_expiry"] if row and row["next_expiry"] else None


# --------------------------------------------------------------------------------------
# ADMIN DASHBOARD STATISTICS
# --------------------------------------------------------------------------------------
def get_admin_stats():
    """Return summary statistics for the admin dashboard."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS cnt FROM users")
    total_users = cur.fetchone()["cnt"]

    cur.execute("SELECT COUNT(*) AS cnt FROM bookings")
    total_bookings = cur.fetchone()["cnt"]

    cur.execute("SELECT COUNT(*) AS cnt FROM bookings WHERE status = 'Active'")
    active_bookings = cur.fetchone()["cnt"]

    cur.execute("SELECT COUNT(*) AS cnt FROM bookings WHERE status = 'Cancelled'")
    cancelled_bookings = cur.fetchone()["cnt"]

    cur.execute("SELECT COALESCE(SUM(fare), 0) AS total FROM bookings WHERE status != 'Cancelled'")
    total_revenue = cur.fetchone()["total"]

    conn.close()
    return {
        "total_users": total_users,
        "total_bookings": total_bookings,
        "active_bookings": active_bookings,
        "cancelled_bookings": cancelled_bookings,
        "total_revenue": total_revenue,
    }
