# SQL Injection Detection System

A simple Streamlit + SQLite project that demonstrates how to detect and block
common SQL injection patterns in login/registration input, while also using
proper parameterized queries under the hood.

## Features

- **Register page** — create a new user account (password is hashed with SHA-256).
- **Login page** — logs in existing users.
- **SQL Injection detection** — before any login/registration is processed, the
  username and password are scanned for common SQL injection keywords/patterns
  such as:
  - `' OR '1'='1`
  - `OR 1=1`
  - `DROP TABLE`
  - `UNION`
  - `--` (SQL comment)
  - `SELECT ... FROM`, `INSERT INTO`, `DELETE FROM`, `UPDATE ... SET`
  - `xp_cmdshell`, `EXEC`

  If detected, the app shows **"SQL Injection Detected!"**, blocks the request,
  and logs it to the database.
- **Admin page** — view the full login history (successful, failed, and
  blocked attempts) and export it to a CSV file.

> **Note:** All actual database queries in this project use parameterized
> SQL (`sqlite3` `?` placeholders), which is the real defense against SQL
> injection. The keyword-based detector is an additional, educational layer
> that intercepts obviously malicious-looking input before it even reaches
> the database logic.

## Project Structure

```
sql_injection_detector/
├── app.py            # Main Streamlit app (UI + page routing)
├── auth.py           # Registration & login logic
├── database.py       # SQLite setup and data access functions
├── security.py       # SQL injection keyword/pattern detector
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

## Setup & Run

1. **Install dependencies** (Python 3.9+ recommended):

   ```bash
   pip install -r requirements.txt
   ```

2. **Run the app:**

   ```bash
   streamlit run app.py
   ```

3. Open the URL Streamlit prints in your terminal (usually
   `http://localhost:8501`).

The SQLite database file (`app_data.db`) is created automatically in the
project folder on first run.

## How to Test the Detector

On the **Login** or **Register** page, try entering values like:

| Field    | Example Input           |
|----------|--------------------------|
| Username | `admin' OR '1'='1`       |
| Username | `admin'; DROP TABLE users;--` |
| Password | `' UNION SELECT * FROM users --` |

You should see a **"SQL Injection Detected!"** error, and the attempt will be
recorded in the Admin page's login history with status `BLOCKED`.

For a normal flow:
1. Go to **Register**, create a username/password.
2. Go to **Login**, sign in with those credentials.
3. Go to **Admin** to see the login history and export it as CSV.

## Disclaimer

This project is built for **educational purposes** to demonstrate SQL
injection detection concepts in a beginner-friendly way. It is not intended
as a production-grade security solution. Real-world applications should rely
on parameterized queries/ORMs, input validation, least-privilege database
accounts, and a proper Web Application Firewall (WAF) as their primary
defenses.
