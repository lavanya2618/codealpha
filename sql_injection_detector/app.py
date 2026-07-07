"""
app.py
Main Streamlit application for the SQL Injection Detection System.

Pages:
    - Login
    - Register
    - Admin (view login history + export CSV)
"""

import streamlit as st
import pandas as pd

import database
import auth
import security

st.set_page_config(page_title="SQL Injection Detection System", page_icon="🛡️", layout="centered")

# Initialize the database (creates tables if they don't exist).
database.init_db()

# Keep track of login state.
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

st.title("🛡️ SQL Injection Detection System")

# ---- Sidebar navigation ----
if st.session_state.logged_in:
    page_options = ["Home", "Admin", "Logout"]
else:
    page_options = ["Login", "Register", "Admin"]

page = st.sidebar.radio("Navigate", page_options)


# =========================================================
# LOGIN PAGE
# =========================================================
def show_login_page():
    st.subheader("🔐 Login")
    st.caption("Try entering something like `' OR '1'='1` to see the detector in action.")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        # Quick live check so we can style the block message distinctly.
        is_malicious, offending_value, pattern = security.check_inputs(username, password)

        if is_malicious:
            st.error("🚨 SQL Injection Detected!")
            st.warning(
                f"Suspicious input blocked and logged. Matched pattern: `{pattern}`"
            )
            database.log_login_attempt(
                username or "(empty)",
                status="BLOCKED",
                reason=f"SQL Injection pattern detected: {pattern}",
            )
        else:
            success, message = auth.login_user(username, password)
            if success:
                st.success(message)
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error(message)


# =========================================================
# REGISTER PAGE
# =========================================================
def show_register_page():
    st.subheader("📝 Register")

    with st.form("register_form"):
        username = st.text_input("Choose a username")
        password = st.text_input("Choose a password", type="password")
        confirm_password = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Register")

    if submitted:
        if password != confirm_password:
            st.error("Passwords do not match.")
            return

        is_malicious, offending_value, pattern = security.check_inputs(username, password)
        if is_malicious:
            st.error("🚨 SQL Injection Detected!")
            st.warning(f"Suspicious input blocked. Matched pattern: `{pattern}`")
            return

        success, message = auth.register_user(username, password)
        if success:
            st.success(message)
        else:
            st.error(message)


# =========================================================
# HOME PAGE (after login)
# =========================================================
def show_home_page():
    st.subheader(f"👋 Welcome, {st.session_state.username}!")
    st.write("You have successfully logged in.")
    st.info("Use the sidebar to view the Admin page or log out.")


# =========================================================
# ADMIN PAGE
# =========================================================
def show_admin_page():
    st.subheader("🗄️ Admin: Login History")

    rows = database.get_all_login_history()

    if not rows:
        st.info("No login attempts recorded yet.")
        return

    df = pd.DataFrame(
        [dict(row) for row in rows],
        columns=["id", "username", "status", "reason", "timestamp"],
    )

    # Simple color-coded summary counts.
    col1, col2, col3 = st.columns(3)
    col1.metric("✅ Successful", int((df["status"] == "SUCCESS").sum()))
    col2.metric("❌ Failed", int((df["status"] == "FAILED").sum()))
    col3.metric("🚨 Blocked (SQLi)", int((df["status"] == "BLOCKED").sum()))

    st.dataframe(df, use_container_width=True)

    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Export Login History to CSV",
        data=csv_data,
        file_name="login_history.csv",
        mime="text/csv",
    )


# =========================================================
# LOGOUT
# =========================================================
def do_logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.success("You have been logged out.")
    st.rerun()


# =========================================================
# ROUTER
# =========================================================
if page == "Login":
    show_login_page()
elif page == "Register":
    show_register_page()
elif page == "Home":
    show_home_page()
elif page == "Admin":
    show_admin_page()
elif page == "Logout":
    do_logout()
