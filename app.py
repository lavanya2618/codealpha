"""
app.py
------
Cloud-Based Bus Pass System — main Streamlit UI.

All database logic lives in database.py (kept separate for modularity and
scalability). This file is purely responsible for:
    - Page layout / navigation
    - Session management (user login, admin login)
    - Input validation
    - Wiring UI actions to database.py functions
    - PDF pass generation

Run with: streamlit run app.py
"""

import io
import re
from datetime import datetime, date

import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

import database as db

# --------------------------------------------------------------------------------------
# APP CONFIG
# --------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Cloud-Based Bus Pass System",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Hardcoded admin credentials (for a real deployment, move these to
# st.secrets or environment variables instead of source code).
ADMIN_EMAIL = "admin@buspass.com"
ADMIN_PASSWORD = "Admin@123"

# --------------------------------------------------------------------------------------
# DARK, PROFESSIONAL THEME (custom CSS)
# --------------------------------------------------------------------------------------
st.markdown(
    """
    <style>
        .stApp {
            background-color: #0e1117;
            color: #e6e6e6;
        }
        section[data-testid="stSidebar"] {
            background-color: #131722;
            border-right: 1px solid #262a3a;
        }
        h1, h2, h3, h4 {
            color: #f5f7fa;
            font-family: 'Segoe UI', sans-serif;
        }
        p, label, span, div {
            color: #d7dbe0;
        }

        .brand-title {
            font-size: 1.7rem;
            font-weight: 800;
            color: #00d4b0;
            margin-bottom: 0;
        }
        .brand-sub {
            color: #8a93a3;
            font-size: 0.85rem;
            margin-top: 0;
        }

        .stat-card {
            background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
            border: 1px solid #2c3444;
            padding: 22px;
            border-radius: 14px;
            text-align: center;
            box-shadow: 0 4px 14px rgba(0,0,0,0.4);
        }
        .stat-card h2 { color: #00d4b0; margin-bottom: 0; font-size: 2rem; }
        .stat-card p  { color: #9aa4b2; margin-top: 4px; font-size: 0.9rem; }

        .pass-card {
            background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
            border-radius: 16px;
            padding: 24px 28px;
            color: white;
            box-shadow: 0 6px 20px rgba(0,0,0,0.5);
            border: 1px solid #00d4b0;
        }
        .pass-card h3 { color: #00d4b0; margin-bottom: 4px; }
        .pass-card .pid { font-size: 1.4rem; font-weight: 700; letter-spacing: 1px; }

        div.stButton > button, div.stDownloadButton > button {
            border-radius: 8px;
            font-weight: 600;
            padding: 0.5rem 1.3rem;
            background-color: #00d4b0;
            color: #0e1117;
            border: none;
        }
        div.stButton > button:hover, div.stDownloadButton > button:hover {
            background-color: #00b89a;
            color: #0e1117;
        }

        .section-box {
            background: #151a26;
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid #262a3a;
            margin-bottom: 1.2rem;
        }

        .footer-note {
            text-align: center;
            color: #5a6472;
            font-size: 0.8rem;
            margin-top: 2rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------------------
# VALIDATION HELPERS
# --------------------------------------------------------------------------------------
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
PHONE_REGEX = re.compile(r"^\+?[0-9]{10,13}$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email.strip())) if email else False


def is_valid_phone(phone: str) -> bool:
    cleaned = re.sub(r"[\s\-()]", "", phone.strip()) if phone else ""
    return bool(PHONE_REGEX.match(cleaned)) if cleaned else False


def is_valid_password(password: str):
    """Password must be 8+ chars, with at least one letter and one digit."""
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one digit."
    return True, ""


# --------------------------------------------------------------------------------------
# PDF PASS GENERATION (reportlab)
# --------------------------------------------------------------------------------------
def generate_pass_pdf(booking: dict, user: dict) -> bytes:
    """Build a professional-looking digital bus pass as a PDF and return raw bytes."""
    buffer = io.BytesIO()
    page_size = landscape(letter)
    c = canvas.Canvas(buffer, pagesize=page_size)
    width, height = page_size

    # Background card
    c.setFillColor(HexColor("#0f2027"))
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # Header bar
    c.setFillColor(HexColor("#00d4b0"))
    c.rect(0, height - 90, width, 90, fill=1, stroke=0)
    c.setFillColor(HexColor("#0e1117"))
    c.setFont("Helvetica-Bold", 26)
    c.drawString(40, height - 58, "CLOUD-BASED BUS PASS SYSTEM")
    c.setFont("Helvetica", 13)
    c.drawString(40, height - 78, "Official Digital Bus Pass")

    # Pass ID box
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 20)
    c.drawRightString(width - 40, height - 50, f"Pass ID: {booking['pass_id']}")
    c.setFont("Helvetica", 12)
    c.setFillColor(HexColor("#c9d6df"))
    c.drawRightString(width - 40, height - 72, f"Status: {booking.get('status', 'Active')}")

    # Body details
    left_x = 50
    top_y = height - 140
    line_gap = 26

    details = [
        ("Passenger Name", user["name"]),
        ("Email", user["email"]),
        ("Phone", user["phone"]),
        ("Route", f"{booking['source']}  →  {booking['destination']}"),
        ("Distance", f"{booking['distance_km']} km"),
        ("Bus Type", booking["bus_type"]),
        ("Travel Date", booking["travel_date"]),
        ("Fare Paid", f"Rs. {booking['fare']:.2f}"),
        ("Booking Date", booking["booking_date"]),
        ("Valid Until", booking["expiry_date"]),
    ]

    c.setFont("Helvetica-Bold", 13)
    for i, (label, value) in enumerate(details):
        y = top_y - i * line_gap
        c.setFillColor(HexColor("#00d4b0"))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(left_x, y, f"{label}:")
        c.setFillColor(HexColor("#ffffff"))
        c.setFont("Helvetica", 12)
        c.drawString(left_x + 160, y, str(value))

    # Footer
    c.setFillColor(HexColor("#8a93a3"))
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(40, 30, "This is a system-generated pass and does not require a physical signature.")
    c.drawRightString(width - 40, 30, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# --------------------------------------------------------------------------------------
# INITIALIZE DATABASE & SESSION STATE
# --------------------------------------------------------------------------------------
db.init_db()

if "user" not in st.session_state:
    st.session_state.user = None          # Logged-in normal user (dict)
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False     # Logged-in admin flag


def logout():
    st.session_state.user = None
    st.session_state.is_admin = False
    st.success("You have been logged out.")
    st.rerun()


# --------------------------------------------------------------------------------------
# SIDEBAR BRANDING
# --------------------------------------------------------------------------------------
st.sidebar.markdown('<p class="brand-title">🚌 Bus Pass System</p>', unsafe_allow_html=True)
st.sidebar.markdown('<p class="brand-sub">Cloud-Based Digital Bus Pass Platform</p>', unsafe_allow_html=True)
st.sidebar.markdown("---")

# --------------------------------------------------------------------------------------
# NAVIGATION LOGIC (depends on login state)
# --------------------------------------------------------------------------------------
if st.session_state.is_admin:
    page = st.sidebar.radio(
        "Admin Navigation",
        ["🛠️ Admin Dashboard", "👥 Manage Users", "🎫 Manage Bookings", "💰 Fare Settings", "📑 Reports"],
    )
    st.sidebar.markdown("---")
    st.sidebar.success("Logged in as **Admin**")
    if st.sidebar.button("🚪 Logout"):
        logout()

elif st.session_state.user:
    page = st.sidebar.radio(
        "Navigation",
        ["🏠 Dashboard", "🎟️ Book Bus Pass", "📇 My Passes", "📑 Reports"],
    )
    st.sidebar.markdown("---")
    st.sidebar.success(f"Logged in as **{st.session_state.user['name']}**")
    if st.sidebar.button("🚪 Logout"):
        logout()

else:
    page = st.sidebar.radio("Navigation", ["🏠 Home", "🔐 Login", "📝 Register", "🛠️ Admin Login"])

st.sidebar.markdown("---")
st.sidebar.caption("Built with Streamlit + SQLite | Ready for Streamlit Cloud deployment")

# ========================================================================================
# PUBLIC PAGES (NOT LOGGED IN)
# ========================================================================================
if not st.session_state.user and not st.session_state.is_admin:

    if page == "🏠 Home":
        st.title("🚌 Cloud-Based Bus Pass System")
        st.markdown(
            """
            Welcome to the **Cloud-Based Bus Pass System** — a modern platform to
            register, book digital bus passes, manage your travel history, and
            download passes as PDF, all backed by a secure SQLite database.
            """
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                """<div class="stat-card"><h2>🚍</h2><p>Ordinary • Express • AC Buses</p></div>""",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                """<div class="stat-card"><h2>🔒</h2><p>Secure, Encrypted Passwords</p></div>""",
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                """<div class="stat-card"><h2>📄</h2><p>Instant PDF Digital Passes</p></div>""",
                unsafe_allow_html=True,
            )
        st.markdown("---")
        st.info("Use the sidebar to **Register** a new account or **Login** if you already have one.")

    elif page == "🔐 Login":
        st.title("🔐 User Login")
        with st.form("login_form"):
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", type="primary")

            if submitted:
                if not email.strip() or not password:
                    st.error("Please enter both email and password.")
                else:
                    user = db.authenticate_user(email, password)
                    if user:
                        st.session_state.user = user
                        st.success(f"Welcome back, {user['name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")

    elif page == "📝 Register":
        st.title("📝 Create a New Account")
        with st.form("register_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name *")
                email = st.text_input("Email Address *")
            with col2:
                phone = st.text_input("Phone Number *", placeholder="10-digit mobile number")
                password = st.text_input("Password *", type="password", help="Min 8 characters, letters + digits")

            confirm_password = st.text_input("Confirm Password *", type="password")
            submitted = st.form_submit_button("Register", type="primary")

            if submitted:
                errors = []
                if not name.strip():
                    errors.append("Full name is required.")
                if not is_valid_email(email):
                    errors.append("Please enter a valid email address.")
                if not is_valid_phone(phone):
                    errors.append("Please enter a valid phone number (10–13 digits).")
                pw_ok, pw_msg = is_valid_password(password)
                if not pw_ok:
                    errors.append(pw_msg)
                if password != confirm_password:
                    errors.append("Passwords do not match.")

                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    success, message = db.register_user(name, email, phone, password)
                    if success:
                        st.success(message)
                        st.balloons()
                    else:
                        st.error(message)

    elif page == "🛠️ Admin Login":
        st.title("🛠️ Admin Login")
        with st.form("admin_login_form"):
            admin_email = st.text_input("Admin Email")
            admin_password = st.text_input("Admin Password", type="password")
            submitted = st.form_submit_button("Login as Admin", type="primary")

            if submitted:
                if admin_email.strip() == ADMIN_EMAIL and admin_password == ADMIN_PASSWORD:
                    st.session_state.is_admin = True
                    st.success("Admin login successful!")
                    st.rerun()
                else:
                    st.error("Invalid admin credentials.")
        st.caption("Default demo credentials — admin@buspass.com / Admin@123 (change in production).")

# ========================================================================================
# USER PAGES (LOGGED IN AS NORMAL USER)
# ========================================================================================
elif st.session_state.user:
    user = st.session_state.user

    # ---------------- DASHBOARD ----------------
    if page == "🏠 Dashboard":
        st.title("🏠 My Dashboard")
        st.write(f"Welcome, **{user['name']}**!")

        active_passes = db.get_active_pass_count(user["id"])
        total_spent = db.get_total_spent(user["id"])
        next_expiry = db.get_next_expiry(user["id"])
        history = db.get_bookings_by_user(user["id"])

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""<div class="stat-card"><h2>{active_passes}</h2><p>Active Passes</p></div>""",
                        unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="stat-card"><h2>₹{total_spent:.2f}</h2><p>Total Amount Spent</p></div>""",
                        unsafe_allow_html=True)
        with col3:
            expiry_display = next_expiry if next_expiry else "—"
            st.markdown(f"""<div class="stat-card"><h2 style="font-size:1.3rem;">{expiry_display}</h2>
                        <p>Next Pass Expiry</p></div>""", unsafe_allow_html=True)
        with col4:
            st.markdown(f"""<div class="stat-card"><h2>{len(history)}</h2><p>Total Bookings</p></div>""",
                        unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 👤 Account Details")
        st.markdown(
            f"""
            <div class="section-box">
            <b>Name:</b> {user['name']}<br>
            <b>Email:</b> {user['email']}<br>
            <b>Phone:</b> {user['phone']}<br>
            <b>Member Since:</b> {user['created_at']}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### 📜 Recent Booking History")
        if history:
            df = pd.DataFrame(history)
            st.dataframe(
                df[["pass_id", "source", "destination", "bus_type", "travel_date", "fare", "status"]],
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("You have no bookings yet. Head to 'Book Bus Pass' to get started!")

    # ---------------- BOOK BUS PASS ----------------
    elif page == "🎟️ Book Bus Pass":
        st.title("🎟️ Book a New Bus Pass")

        with st.form("booking_form"):
            col1, col2 = st.columns(2)
            with col1:
                source = st.selectbox("Source", db.CITIES, index=0)
            with col2:
                destination = st.selectbox("Destination", db.CITIES, index=1)

            bus_type = st.selectbox("Bus Type", db.BUS_TYPES)
            travel_date = st.date_input("Travel Date", min_value=date.today())

            # Live fare preview
            if source != destination:
                distance, fare = db.calculate_fare(source, destination, bus_type)
                if distance:
                    st.info(f"📏 Distance: **{distance} km**  |  💰 Estimated Fare: **₹{fare:.2f}**  "
                            f"|  🗓️ Valid for **{db.PASS_VALIDITY_DAYS} days** from travel date")

            submitted = st.form_submit_button("🎫 Book Pass", type="primary")

            if submitted:
                if source == destination:
                    st.error("Source and destination cannot be the same.")
                else:
                    success, message, booking = db.create_booking(
                        user["id"], source, destination, bus_type,
                        travel_date.strftime("%Y-%m-%d"),
                    )
                    if success:
                        st.success(message)
                        st.session_state["last_booking"] = booking
                        st.balloons()
                    else:
                        st.error(message)

        # Show freshly generated pass with download button
        if "last_booking" in st.session_state:
            booking = st.session_state["last_booking"]
            st.markdown("---")
            st.markdown("### ✅ Your New Digital Bus Pass")
            st.markdown(
                f"""
                <div class="pass-card">
                    <h3>Digital Bus Pass</h3>
                    <p class="pid">Pass ID: {booking['pass_id']}</p>
                    <p><b>Route:</b> {booking['source']} → {booking['destination']}<br>
                    <b>Bus Type:</b> {booking['bus_type']}<br>
                    <b>Travel Date:</b> {booking['travel_date']}<br>
                    <b>Fare:</b> ₹{booking['fare']:.2f}<br>
                    <b>Valid Until:</b> {booking['expiry_date']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            pdf_bytes = generate_pass_pdf(booking, user)
            st.download_button(
                "⬇️ Download Pass as PDF",
                data=pdf_bytes,
                file_name=f"{booking['pass_id']}.pdf",
                mime="application/pdf",
            )

    # ---------------- MY PASSES ----------------
    elif page == "📇 My Passes":
        st.title("📇 My Bus Passes")

        tab_all, tab_search, tab_filter = st.tabs(["📋 All Passes", "🔎 Search by Pass ID", "📅 Filter by Date"])

        with tab_all:
            bookings = db.get_bookings_by_user(user["id"])
            if bookings:
                for b in bookings:
                    with st.expander(f"🎫 {b['pass_id']}  —  {b['source']} → {b['destination']}  ({b['status']})"):
                        st.write(f"**Bus Type:** {b['bus_type']}  |  **Distance:** {b['distance_km']} km")
                        st.write(f"**Travel Date:** {b['travel_date']}  |  **Fare:** ₹{b['fare']:.2f}")
                        st.write(f"**Booked On:** {b['booking_date']}  |  **Valid Until:** {b['expiry_date']}")
                        st.write(f"**Status:** {b['status']}")

                        col1, col2 = st.columns(2)
                        with col1:
                            pdf_bytes = generate_pass_pdf(b, user)
                            st.download_button(
                                "⬇️ Download PDF", data=pdf_bytes,
                                file_name=f"{b['pass_id']}.pdf", mime="application/pdf",
                                key=f"dl_{b['pass_id']}",
                            )
                        with col2:
                            if b["status"] == "Active":
                                if st.button("🗑️ Cancel Pass", key=f"cancel_{b['pass_id']}"):
                                    ok, msg = db.cancel_booking(b["pass_id"], user["id"])
                                    if ok:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            else:
                                st.caption("This pass is already cancelled.")
            else:
                st.info("No bus passes booked yet.")

        with tab_search:
            search_term = st.text_input("Enter Pass ID (partial match allowed)")
            if st.button("Search", key="search_pass_id"):
                results = [b for b in db.search_booking_by_pass_id(search_term) if b["user_id"] == user["id"]]
                if results:
                    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
                else:
                    st.warning("No matching pass found.")

        with tab_filter:
            col1, col2 = st.columns(2)
            with col1:
                start = st.date_input("From Date", key="filter_start")
            with col2:
                end = st.date_input("To Date", key="filter_end")
            if st.button("Filter", key="filter_btn"):
                if start > end:
                    st.error("'From Date' must be before 'To Date'.")
                else:
                    results = db.filter_bookings_by_date(
                        start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), user_id=user["id"]
                    )
                    if results:
                        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
                    else:
                        st.info("No bookings found in that date range.")

    # ---------------- REPORTS ----------------
    elif page == "📑 Reports":
        st.title("📑 My Reports")
        history = db.get_bookings_by_user(user["id"])
        if history:
            df = pd.DataFrame(history)
            st.dataframe(df, use_container_width=True, hide_index=True)
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Export My Booking History to CSV",
                data=csv_bytes, file_name="my_booking_history.csv", mime="text/csv",
                type="primary",
            )
        else:
            st.info("No booking history to export yet.")

# ========================================================================================
# ADMIN PAGES (LOGGED IN AS ADMIN)
# ========================================================================================
elif st.session_state.is_admin:

    # ---------------- ADMIN DASHBOARD ----------------
    if page == "🛠️ Admin Dashboard":
        st.title("🛠️ Admin Dashboard")
        stats = db.get_admin_stats()

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"""<div class="stat-card"><h2>{stats['total_users']}</h2><p>Total Users</p></div>""",
                        unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="stat-card"><h2>{stats['total_bookings']}</h2><p>Total Bookings</p></div>""",
                        unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class="stat-card"><h2>{stats['active_bookings']}</h2><p>Active Passes</p></div>""",
                        unsafe_allow_html=True)
        with col4:
            st.markdown(f"""<div class="stat-card"><h2>{stats['cancelled_bookings']}</h2><p>Cancelled Passes</p></div>""",
                        unsafe_allow_html=True)
        with col5:
            st.markdown(f"""<div class="stat-card"><h2>₹{stats['total_revenue']:.2f}</h2><p>Total Revenue</p></div>""",
                        unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📈 Bookings Over Time")
        bookings = db.get_all_bookings()
        if bookings:
            df = pd.DataFrame(bookings)
            df["booking_day"] = pd.to_datetime(df["booking_date"]).dt.date
            chart_data = df.groupby("booking_day").size().reset_index(name="bookings").set_index("booking_day")
            st.bar_chart(chart_data)

            st.markdown("### 🚌 Bookings by Bus Type")
            type_counts = df["bus_type"].value_counts()
            st.bar_chart(type_counts)
        else:
            st.info("No booking data available yet.")

    # ---------------- MANAGE USERS ----------------
    elif page == "👥 Manage Users":
        st.title("👥 Manage Registered Users")

        search_term = st.text_input("🔎 Search by name or email")
        users = db.search_users(search_term) if search_term else db.get_all_users()

        if users:
            st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### 🗑️ Delete a User")
            user_id_to_delete = st.number_input("Enter User ID to delete", min_value=1, step=1)
            confirm = st.checkbox("I confirm I want to permanently delete this user and all their bookings.")
            if st.button("Delete User", type="primary", disabled=not confirm):
                ok, msg = db.delete_user(int(user_id_to_delete))
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.info("No users found.")

    # ---------------- MANAGE BOOKINGS ----------------
    elif page == "🎫 Manage Bookings":
        st.title("🎫 Manage All Bookings")

        tab_all, tab_search, tab_filter = st.tabs(["📋 All Bookings", "🔎 Search by Pass ID", "📅 Filter by Date"])

        with tab_all:
            bookings = db.get_all_bookings()
            if bookings:
                df = pd.DataFrame(bookings)
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.markdown("### 🗑️ Cancel a Pass")
                pass_id_to_cancel = st.text_input("Enter exact Pass ID to cancel")
                if st.button("Cancel Pass", type="primary"):
                    ok, msg = db.cancel_booking(pass_id_to_cancel)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
            else:
                st.info("No bookings found.")

        with tab_search:
            term = st.text_input("Enter Pass ID (partial match allowed)", key="admin_search_pid")
            if st.button("Search", key="admin_search_btn"):
                results = db.search_booking_by_pass_id(term)
                if results:
                    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
                else:
                    st.warning("No matching bookings found.")

        with tab_filter:
            col1, col2 = st.columns(2)
            with col1:
                start = st.date_input("From Date", key="admin_filter_start")
            with col2:
                end = st.date_input("To Date", key="admin_filter_end")
            if st.button("Filter", key="admin_filter_btn"):
                if start > end:
                    st.error("'From Date' must be before 'To Date'.")
                else:
                    results = db.filter_bookings_by_date(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
                    if results:
                        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
                    else:
                        st.info("No bookings found in that date range.")

    # ---------------- FARE SETTINGS ----------------
    elif page == "💰 Fare Settings":
        st.title("💰 Fare Settings")
        rates = db.get_fare_rates()

        st.markdown("### Current Fare Rates (₹ per km)")
        cols = st.columns(len(db.BUS_TYPES))
        for i, bus_type in enumerate(db.BUS_TYPES):
            with cols[i]:
                st.markdown(
                    f"""<div class="stat-card"><h2>₹{rates.get(bus_type, 0):.2f}</h2><p>{bus_type}</p></div>""",
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        st.markdown("### ✏️ Update a Fare Rate")
        with st.form("fare_update_form"):
            bus_type = st.selectbox("Bus Type", db.BUS_TYPES)
            new_rate = st.number_input("New Rate (₹ per km)", min_value=0.1, step=0.1,
                                        value=float(rates.get(bus_type, 1.0)))
            submitted = st.form_submit_button("Update Rate", type="primary")
            if submitted:
                ok, msg = db.update_fare_rate(bus_type, new_rate)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # ---------------- ADMIN REPORTS ----------------
    elif page == "📑 Reports":
        st.title("📑 Reports & Exports")

        tab_users, tab_bookings = st.tabs(["👥 Registered Users", "🎫 Booking History"])

        with tab_users:
            users = db.get_all_users()
            if users:
                df = pd.DataFrame(users)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button(
                    "⬇️ Export Registered Users to CSV",
                    data=df.to_csv(index=False).encode("utf-8"),
                    file_name="registered_users.csv", mime="text/csv", type="primary",
                )
            else:
                st.info("No users to export.")

        with tab_bookings:
            bookings = db.get_all_bookings()
            if bookings:
                df = pd.DataFrame(bookings)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button(
                    "⬇️ Export Booking History to CSV",
                    data=df.to_csv(index=False).encode("utf-8"),
                    file_name="booking_history.csv", mime="text/csv", type="primary",
                )
            else:
                st.info("No bookings to export.")

# --------------------------------------------------------------------------------------
# FOOTER
# --------------------------------------------------------------------------------------
st.markdown(
    """<p class="footer-note">Cloud-Based Bus Pass System &nbsp;|&nbsp; Streamlit + SQLite + Pandas
    &nbsp;|&nbsp; Ready for Streamlit Cloud Deployment</p>""",
    unsafe_allow_html=True,
)
