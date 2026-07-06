# 🚌 Cloud-Based Bus Pass System

A professional, dark-themed **Streamlit** web application for registering
users, booking digital bus passes, managing tickets, and administering the
system — all backed by a lightweight, cloud-portable **SQLite** database.

Built as a Cloud Computing internship project.

---

## Features

### 1. User Registration
- Register with Name, Email, Phone Number, Password
- Email format validation (regex)
- Phone number format validation (regex)
- Duplicate email registration prevented (DB `UNIQUE` constraint + app check)
- Passwords stored securely using **PBKDF2-HMAC-SHA256** with a unique
  per-user salt (never stored in plain text)

### 2. User Login
- Login using email + password
- Session management via `st.session_state`
- Logout option in the sidebar

### 3. Dashboard
- User account details
- Number of currently active bus passes
- Nearest upcoming pass expiry date
- Full booking history table
- Total amount spent across all bookings

### 4. Bus Pass Booking
- Select source & destination from a predefined city list
- Select bus type: **Ordinary / Express / AC**
- Select travel date
- Automatic fare calculation (distance × per-km rate for the chosen bus type)
- Unique **Pass ID** generated per booking (e.g. `BP-7F3K9QZ2`)
- Instant digital pass card + downloadable **PDF**

### 5. Ticket Management
- View all booked passes (expandable cards)
- Download any pass as a PDF at any time
- Cancel an active pass (soft delete — status set to `Cancelled`)
- Full booking history per user

### 6. Admin Panel
- Secure hardcoded admin login (see credentials below)
- View all registered users
- View all bookings (joined with user name/email)
- Search users by name/email
- Delete a user (cascades to their bookings)
- Update per-km fare prices for each bus type
- Dashboard with statistics: total users, total bookings, active/cancelled
  passes, total revenue, bookings-over-time chart, bookings-by-bus-type chart

### 7. Cloud Features
- All data stored in a single-file **SQLite** database (`database.db`)
- No external services required — works entirely offline
- Modular structure (`app.py` / `database.py`) makes it straightforward to
  swap SQLite for a managed cloud database later if needed
- Ready to push directly to **Streamlit Community Cloud**

### 8. Security
- **Parameterized queries everywhere** — no string-formatted SQL, so the
  app is protected from SQL Injection
- Server-side input validation for name, email, phone, and password
- Passwords hashed with PBKDF2 (100,000 iterations) + random salt
- Constant-time password comparison (`secrets.compare_digest`)

### 9. Scalability & Code Quality
- Fully modular: all database logic isolated in `database.py`
- `app.py` only handles UI/navigation/session and calls into `database.py`
- Clear function-per-operation design (easy to unit test or extend)
- Consistent naming and inline comments throughout

### 10. Reports
- Export full booking history to CSV (user's own history, or all bookings
  for admin)
- Export all registered users to CSV (admin)

### 11. Extra Features
- Search bookings by Pass ID (partial match)
- Filter bookings by date range
- Dark-themed, professional custom UI (custom CSS)
- Clear success/error messages throughout
- Responsive, sidebar-driven navigation that adapts to login state
  (Guest / User / Admin)

---

## Project Structure

```
bus_pass_system/
├── app.py              # Streamlit UI, session management, PDF generation
├── database.py         # All SQLite database logic (parameterized queries)
├── database.db          # SQLite database file (auto-created on first run)
├── requirements.txt     # Python dependencies
├── README.md            # Project documentation (this file)
└── sample_data.csv      # Sample booking data illustrating the schema
```

---

## Tech Stack

- **Frontend / App Framework:** Streamlit
- **Database:** SQLite3 (Python standard library)
- **Data Handling:** Pandas
- **PDF Generation:** ReportLab
- **Language:** Python 3

---

## Installation & Setup

1. **Clone or download** this project folder.

2. **(Recommended) Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate      # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

5. Streamlit opens automatically at `http://localhost:8501`. The SQLite
   database (`database.db`) is created automatically on first run if it
   doesn't already exist, complete with default fare rates.

---

## Default Admin Credentials

```
Email:    admin@buspass.com
Password: Admin@123
```

> ⚠️ These are hardcoded in `app.py` (`ADMIN_EMAIL` / `ADMIN_PASSWORD`) for
> demo purposes. For a real deployment, move them to `st.secrets` or
> environment variables and change the password.

---

## How to Use

### As a passenger
1. **Register** with your name, email, phone, and a password (min 8
   characters, letters + digits).
2. **Login** with your email and password.
3. Go to **Book Bus Pass**, choose source, destination, bus type, and
   travel date — the fare is calculated automatically.
4. Download your pass as a **PDF**, or view/cancel it any time under
   **My Passes**.
5. Check your **Dashboard** for active passes, expiry dates, and total
   spend, and use **Reports** to export your booking history to CSV.

### As an admin
1. Go to **Admin Login** and use the credentials above.
2. **Admin Dashboard** — see platform-wide statistics and charts.
3. **Manage Users** — search and delete users.
4. **Manage Bookings** — view, search by Pass ID, filter by date, or
   cancel any booking.
5. **Fare Settings** — update the ₹/km rate for Ordinary, Express, or AC
   buses (affects fare calculation for all future bookings).
6. **Reports** — export all users or all bookings to CSV.

---

## Validation Rules

**Email:**
```
^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$
```

**Phone (10–13 digits, optional leading +):**
```
^\+?[0-9]{10,13}$
```

**Password:**
- Minimum 8 characters
- At least one letter and one digit

---

## Database Schema

```sql
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    phone         TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE fares (
    bus_type     TEXT PRIMARY KEY,
    rate_per_km  REAL NOT NULL
);

CREATE TABLE bookings (
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
);
```

- Passes are valid for **30 days** from the travel date (`PASS_VALIDITY_DAYS`
  in `database.py`).
- Fare = `distance_km × rate_per_km` (rate configurable by the admin).
- Distance between cities is looked up from a static matrix in
  `database.py` (`DISTANCE_MATRIX`) covering 8 Maharashtra cities: Mumbai,
  Pune, Nashik, Nagpur, Aurangabad, Kolhapur, Solapur, and Thane.

---

## Deploying to Streamlit Community Cloud

1. Push this folder to a GitHub repository (include `app.py`, `database.py`,
   `requirements.txt` — `database.db` will be created automatically, or you
   can commit an initial empty one).
2. Go to [share.streamlit.io](https://share.streamlit.io), connect your
   repo, and set `app.py` as the entry point.
3. Deploy. Since SQLite is a single file, it works out of the box; note
   that on most free hosting tiers the filesystem is **ephemeral**, so for
   a production deployment with persistent data across restarts, consider
   mounting persistent storage or migrating `database.py` to a hosted
   database (e.g. PostgreSQL) — the modular design makes this a
   contained change limited to `database.py`.

---

## Notes

- To reset the database, delete `database.db` and restart the app — it
  will be recreated automatically with default fare rates.
- `sample_data.csv` is a reference dataset showing the expected shape of
  exported booking data; it is not auto-imported by the app.

---

## Author

Cloud Computing Internship Project — Cloud-Based Bus Pass System.
