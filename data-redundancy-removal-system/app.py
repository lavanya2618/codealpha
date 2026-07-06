"""
Data Redundancy Removal System
--------------------------------
A professional Streamlit application for detecting and removing duplicate
records from CSV files and a SQLite database, with full CRUD support,
validation, search and an analytics dashboard.

Author  : Cloud Computing Internship Project
Run with: streamlit run app.py
"""

import io
import os
import re
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------------------
# APP CONFIG
# --------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Data Redundancy Removal System",
    page_icon="🧹",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

# --------------------------------------------------------------------------------------
# CUSTOM CSS  (Professional UI)
# --------------------------------------------------------------------------------------
st.markdown(
    """
    <style>
        .main { background-color: #f7f9fc; }
        .block-container { padding-top: 2rem; }

        h1, h2, h3 { color: #1f2d3d; font-family: 'Segoe UI', sans-serif; }

        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 22px;
            border-radius: 14px;
            color: white;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .stat-card h2 { color: white; margin-bottom: 0; font-size: 2.1rem; }
        .stat-card p { color: #eaeaff; margin-top: 4px; font-size: 0.95rem; }

        .stat-card-green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        .stat-card-red   { background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }
        .stat-card-blue  { background: linear-gradient(135deg, #2193b0 0%, #6dd5ed 100%); }
        .stat-card-orange{ background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%); }

        .section-box {
            background: white;
            padding: 1.6rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            margin-bottom: 1.2rem;
        }

        div.stButton > button {
            border-radius: 8px;
            font-weight: 600;
            padding: 0.5rem 1.2rem;
        }

        .footer-note {
            text-align: center;
            color: #8a8f98;
            font-size: 0.8rem;
            margin-top: 2rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------------------
# DATABASE LAYER
# --------------------------------------------------------------------------------------
def get_connection():
    """Return a new SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the records table if it does not already exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            email       TEXT NOT NULL UNIQUE,
            phone       TEXT,
            created_at  TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def insert_record(name, email, phone):
    """Insert a new record. Returns (success: bool, message: str)."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO records (name, email, phone, created_at) VALUES (?, ?, ?, ?)",
            (name.strip(), email.strip().lower(), phone.strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        conn.close()
        return True, "Record added successfully."
    except sqlite3.IntegrityError:
        return False, "A record with this email already exists (duplicate email prevented)."
    except Exception as exc:  # noqa: BLE001
        return False, f"Unexpected error: {exc}"


def update_record(record_id, name, email, phone):
    """Update an existing record by id. Returns (success, message)."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        # Check duplicate email on a *different* record
        cur.execute("SELECT id FROM records WHERE email = ? AND id != ?", (email.strip().lower(), record_id))
        if cur.fetchone():
            conn.close()
            return False, "Another record already uses this email address."

        cur.execute(
            "UPDATE records SET name = ?, email = ?, phone = ? WHERE id = ?",
            (name.strip(), email.strip().lower(), phone.strip(), record_id),
        )
        conn.commit()
        affected = cur.rowcount
        conn.close()
        if affected == 0:
            return False, "No record found with that ID."
        return True, "Record updated successfully."
    except Exception as exc:  # noqa: BLE001
        return False, f"Unexpected error: {exc}"


def delete_record(record_id):
    """Delete a record by id. Returns (success, message)."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM records WHERE id = ?", (record_id,))
        conn.commit()
        affected = cur.rowcount
        conn.close()
        if affected == 0:
            return False, "No record found with that ID."
        return True, "Record deleted successfully."
    except Exception as exc:  # noqa: BLE001
        return False, f"Unexpected error: {exc}"


def get_all_records():
    """Return all records as a pandas DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM records ORDER BY id ASC", conn)
    conn.close()
    return df


def search_records(by, term):
    """Search records by id, name or email."""
    conn = get_connection()
    term = term.strip()
    if by == "ID":
        query = "SELECT * FROM records WHERE CAST(id AS TEXT) = ?"
        params = (term,)
    elif by == "Name":
        query = "SELECT * FROM records WHERE name LIKE ?"
        params = (f"%{term}%",)
    else:  # Email
        query = "SELECT * FROM records WHERE email LIKE ?"
        params = (f"%{term.lower()}%",)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def bulk_insert_dataframe(df):
    """
    Insert a cleaned dataframe (name, email, phone columns) into the DB,
    skipping rows whose email already exists. Returns (inserted, skipped).
    """
    inserted, skipped = 0, 0
    conn = get_connection()
    cur = conn.cursor()
    for _, row in df.iterrows():
        try:
            cur.execute(
                "INSERT INTO records (name, email, phone, created_at) VALUES (?, ?, ?, ?)",
                (
                    str(row.get("name", "")).strip(),
                    str(row.get("email", "")).strip().lower(),
                    str(row.get("phone", "")).strip(),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1
    conn.commit()
    conn.close()
    return inserted, skipped


# --------------------------------------------------------------------------------------
# VALIDATION HELPERS
# --------------------------------------------------------------------------------------
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
PHONE_REGEX = re.compile(r"^\+?[0-9]{7,15}$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email.strip())) if email else False


def is_valid_phone(phone: str) -> bool:
    cleaned = re.sub(r"[\s\-()]", "", phone.strip()) if phone else ""
    return bool(PHONE_REGEX.match(cleaned)) if cleaned else False


def email_exists_in_db(email: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM records WHERE email = ?", (email.strip().lower(),))
    found = cur.fetchone() is not None
    conn.close()
    return found


# --------------------------------------------------------------------------------------
# CSV HELPERS
# --------------------------------------------------------------------------------------
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase & strip column names for consistent processing."""
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


# --------------------------------------------------------------------------------------
# INITIALIZE DATABASE
# --------------------------------------------------------------------------------------
init_db()

# --------------------------------------------------------------------------------------
# SIDEBAR NAVIGATION
# --------------------------------------------------------------------------------------
st.sidebar.markdown("## 🧹 Data Redundancy\n### Removal System")
st.sidebar.caption("Cloud Computing Internship Project")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    [
        "📊 Dashboard",
        "📁 Upload & Clean CSV",
        "✍️ Manual Data Entry",
        "🔍 Search Records",
        "✏️ Update / Delete Record",
        "📤 Export Database",
    ],
)

st.sidebar.markdown("---")
st.sidebar.info(
    "This system detects & removes duplicate data, validates emails & phone "
    "numbers, and prevents duplicate emails from entering the database."
)

# --------------------------------------------------------------------------------------
# PAGE: DASHBOARD
# --------------------------------------------------------------------------------------
if page == "📊 Dashboard":
    st.title("📊 Dashboard")
    st.write("Overview of your database and data quality statistics.")

    df = get_all_records()
    total_records = len(df)
    duplicate_emails = 0
    duplicate_names = 0

    if not df.empty:
        duplicate_emails = df["email"].duplicated().sum()
        duplicate_names = df["name"].str.lower().duplicated().sum()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""<div class="stat-card"><h2>{total_records}</h2><p>Total Records</p></div>""",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""<div class="stat-card stat-card-green"><h2>{duplicate_emails}</h2><p>Duplicate Emails</p></div>""",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""<div class="stat-card stat-card-orange"><h2>{duplicate_names}</h2><p>Duplicate Names</p></div>""",
            unsafe_allow_html=True,
        )
    with col4:
        last_added = df["created_at"].max() if not df.empty else "—"
        st.markdown(
            f"""<div class="stat-card stat-card-blue"><h2 style="font-size:1.1rem;">{last_added}</h2><p>Last Record Added</p></div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if not df.empty:
        st.markdown("### 📈 Records Added Over Time")
        try:
            chart_df = df.copy()
            chart_df["date"] = pd.to_datetime(chart_df["created_at"]).dt.date
            counts = chart_df.groupby("date").size().reset_index(name="records")
            counts = counts.set_index("date")
            st.bar_chart(counts)
        except Exception:
            st.caption("Not enough date information to render the chart yet.")

        st.markdown("### 🗂️ Current Database Records")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.warning("No records in the database yet. Add data via CSV upload or manual entry.")

# --------------------------------------------------------------------------------------
# PAGE: UPLOAD & CLEAN CSV
# --------------------------------------------------------------------------------------
elif page == "📁 Upload & Clean CSV":
    st.title("📁 Upload & Clean CSV")
    st.write(
        "Upload a CSV file to detect duplicate rows, remove them, download the "
        "cleaned file, and optionally import the cleaned records into the database."
    )

    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            raw_df = pd.read_csv(uploaded_file)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not read CSV file: {exc}")
            raw_df = None

        if raw_df is not None:
            raw_df = normalize_columns(raw_df)
            st.markdown("### 👀 Preview of Uploaded Data")
            st.dataframe(raw_df.head(20), use_container_width=True)
            st.caption(f"Total rows uploaded: **{len(raw_df)}** | Columns: {list(raw_df.columns)}")

            st.markdown("---")
            st.markdown("### ⚙️ Duplicate Detection Settings")

            dup_columns = st.multiselect(
                "Select column(s) to check for duplicates",
                options=list(raw_df.columns),
                default=["email"] if "email" in raw_df.columns else list(raw_df.columns)[:1],
                help="Rows matching on ALL selected columns will be considered duplicates.",
            )

            keep_option = st.radio(
                "When duplicates are found, which row should be kept?",
                ["first", "last"],
                horizontal=True,
                format_func=lambda x: "Keep First Occurrence" if x == "first" else "Keep Last Occurrence",
            )

            if dup_columns:
                duplicate_mask = raw_df.duplicated(subset=dup_columns, keep=False)
                duplicate_rows = raw_df[duplicate_mask]
                num_duplicates = raw_df.duplicated(subset=dup_columns, keep=keep_option).sum()

                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(
                        f"""<div class="stat-card stat-card-red"><h2>{len(duplicate_rows)}</h2>
                        <p>Rows Involved in Duplicates</p></div>""",
                        unsafe_allow_html=True,
                    )
                with col_b:
                    st.markdown(
                        f"""<div class="stat-card stat-card-green"><h2>{num_duplicates}</h2>
                        <p>Rows That Will Be Removed</p></div>""",
                        unsafe_allow_html=True,
                    )

                if not duplicate_rows.empty:
                    st.markdown("#### 🔎 Detected Duplicate Rows")
                    st.dataframe(duplicate_rows, use_container_width=True)
                else:
                    st.success("No duplicate rows detected based on the selected columns.")

                st.markdown("---")
                if st.button("🧹 Remove Duplicates", type="primary"):
                    cleaned_df = raw_df.drop_duplicates(subset=dup_columns, keep=keep_option).reset_index(drop=True)
                    st.session_state["cleaned_df"] = cleaned_df
                    st.success(f"Duplicates removed! Cleaned dataset has {len(cleaned_df)} rows.")

            if "cleaned_df" in st.session_state:
                cleaned_df = st.session_state["cleaned_df"]
                st.markdown("### ✅ Cleaned Data Preview")
                st.dataframe(cleaned_df, use_container_width=True)

                csv_bytes = to_csv_bytes(cleaned_df)
                st.download_button(
                    label="⬇️ Download Cleaned CSV",
                    data=csv_bytes,
                    file_name="cleaned_data.csv",
                    mime="text/csv",
                )

                st.markdown("---")
                st.markdown("#### 📥 Import Cleaned Data into Database")
                st.caption(
                    "Requires 'name', 'email' and 'phone' columns. Rows with duplicate "
                    "or already-existing emails will be skipped automatically."
                )
                required_cols = {"name", "email", "phone"}
                if required_cols.issubset(set(cleaned_df.columns)):
                    if st.button("Import into SQLite Database"):
                        valid_rows = cleaned_df[cleaned_df["email"].apply(lambda x: is_valid_email(str(x)))]
                        invalid_count = len(cleaned_df) - len(valid_rows)
                        inserted, skipped = bulk_insert_dataframe(valid_rows)
                        st.success(f"Imported {inserted} record(s). Skipped {skipped + invalid_count} record(s) "
                                   f"(duplicate/invalid email).")
                else:
                    st.info("CSV must contain 'name', 'email' and 'phone' columns to import into the database.")
    else:
        st.info("👆 Upload a CSV file to get started, or use the provided `sample_data.csv`.")

# --------------------------------------------------------------------------------------
# PAGE: MANUAL DATA ENTRY
# --------------------------------------------------------------------------------------
elif page == "✍️ Manual Data Entry":
    st.title("✍️ Manual Data Entry")
    st.write("Add a new record directly to the database with full validation.")

    with st.form("manual_entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name *")
        with col2:
            phone = st.text_input("Phone Number *", placeholder="e.g. +919876543210")

        email = st.text_input("Email Address *", placeholder="e.g. john.doe@example.com")

        submitted = st.form_submit_button("➕ Add Record", type="primary")

        if submitted:
            errors = []
            if not name.strip():
                errors.append("Name is required.")
            if not email.strip():
                errors.append("Email is required.")
            elif not is_valid_email(email):
                errors.append("Email format is invalid.")
            elif email_exists_in_db(email):
                errors.append("This email already exists in the database (duplicate prevented).")
            if not phone.strip():
                errors.append("Phone number is required.")
            elif not is_valid_phone(phone):
                errors.append("Phone number format is invalid (use 7–15 digits, optionally starting with +).")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                success, message = insert_record(name, email, phone)
                if success:
                    st.success(message)
                else:
                    st.error(message)

    st.markdown("---")
    st.markdown("### 📋 All Records")
    df = get_all_records()
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No records yet. Add one using the form above.")

# --------------------------------------------------------------------------------------
# PAGE: SEARCH RECORDS
# --------------------------------------------------------------------------------------
elif page == "🔍 Search Records":
    st.title("🔍 Search Records")
    st.write("Search the database by ID, Name, or Email.")

    col1, col2 = st.columns([1, 3])
    with col1:
        search_by = st.selectbox("Search by", ["ID", "Name", "Email"])
    with col2:
        search_term = st.text_input("Enter search term", placeholder=f"Search by {search_by}...")

    if st.button("🔎 Search", type="primary"):
        if not search_term.strip():
            st.warning("Please enter a search term.")
        else:
            results = search_records(search_by, search_term)
            if results.empty:
                st.error("No matching records found.")
            else:
                st.success(f"Found {len(results)} matching record(s).")
                st.dataframe(results, use_container_width=True, hide_index=True)

# --------------------------------------------------------------------------------------
# PAGE: UPDATE / DELETE RECORD
# --------------------------------------------------------------------------------------
elif page == "✏️ Update / Delete Record":
    st.title("✏️ Update / Delete Record")

    df = get_all_records()
    if df.empty:
        st.info("No records available. Add data first via CSV import or manual entry.")
    else:
        st.markdown("### 🗂️ Current Records")
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("---")
        record_id = st.number_input("Enter Record ID to Update / Delete", min_value=1, step=1)

        record_row = df[df["id"] == record_id]

        if not record_row.empty:
            existing = record_row.iloc[0]
            tab_update, tab_delete = st.tabs(["✏️ Update Record", "🗑️ Delete Record"])

            with tab_update:
                with st.form("update_form"):
                    new_name = st.text_input("Name", value=existing["name"])
                    new_email = st.text_input("Email", value=existing["email"])
                    new_phone = st.text_input("Phone", value=existing["phone"])
                    update_submitted = st.form_submit_button("💾 Save Changes", type="primary")

                    if update_submitted:
                        errors = []
                        if not new_name.strip():
                            errors.append("Name is required.")
                        if not is_valid_email(new_email):
                            errors.append("Email format is invalid.")
                        if not is_valid_phone(new_phone):
                            errors.append("Phone number format is invalid.")

                        if errors:
                            for e in errors:
                                st.error(e)
                        else:
                            success, message = update_record(int(record_id), new_name, new_email, new_phone)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)

            with tab_delete:
                st.warning(f"You are about to delete record ID **{int(record_id)}** — "
                           f"**{existing['name']}** ({existing['email']}).")
                confirm = st.checkbox("I confirm I want to permanently delete this record.")
                if st.button("🗑️ Delete Record", type="primary", disabled=not confirm):
                    success, message = delete_record(int(record_id))
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
        else:
            st.error(f"No record found with ID {int(record_id)}.")

# --------------------------------------------------------------------------------------
# PAGE: EXPORT DATABASE
# --------------------------------------------------------------------------------------
elif page == "📤 Export Database":
    st.title("📤 Export Database")
    st.write("Export the full database content to a CSV file at any time.")

    df = get_all_records()

    if df.empty:
        st.info("Database is empty. Nothing to export yet.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv_bytes = to_csv_bytes(df)
        st.download_button(
            label="⬇️ Export Full Database to CSV",
            data=csv_bytes,
            file_name=f"database_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            type="primary",
        )

        st.markdown("---")
        st.markdown("### 🧾 Export Summary")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Total Records", len(df))
        with c2:
            st.metric("Unique Emails", df["email"].nunique())

# --------------------------------------------------------------------------------------
# FOOTER
# --------------------------------------------------------------------------------------
st.markdown(
    """<p class="footer-note">Data Redundancy Removal System &nbsp;|&nbsp; Built with Streamlit &amp; SQLite
    &nbsp;|&nbsp; Cloud Computing Internship Project</p>""",
    unsafe_allow_html=True,
)
