import streamlit as st
import psycopg2
import pandas as pd
import os
from datetime import datetime, time


# === 📌 Database Connection & Utility Functions ===

# User passwords
user_passwords = {
    "Emily": "Kali",
    "Anthony": "TuaTime",
    "Greg": "GoJets",
    "Jeff": "Champion",
    "Dave": "BlackBird",
    "Sean": "BlueCat",
    "Cam": "YellowDog",
    "Joanna": "PinkPirate",
    "Brandon": "RedDog",
    "Jarren": "BlueJay",
    "Ingy": "Siberia",
    "Claire": "GoodDay",
    "Aimee": "HappyKid",
    "Manu": "GoDolphins"
}

# Load database credentials from Streamlit Secrets
DB_URL = st.secrets["database"]["url"]

# Function to connect to the PostgreSQL database
def get_connection():
    return psycopg2.connect(DB_URL, sslmode="require")

# Function to calculate total work hours
def calculate_total_time(time_in, time_out):
    if time_in and time_out:
        time_in = datetime.combine(datetime.today(), time_in)
        time_out = datetime.combine(datetime.today(), time_out)

        total_time_seconds = (time_out - time_in).total_seconds()
        total_time_hours = round(total_time_seconds / 3600, 2)
        return total_time_hours
    return None

# Function to insert data into the Operations table
def insert_operations_data(name, sort_or_ship, whos_break, show_date, break_numbers):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO Operations (name, sort_or_ship, whos_break, show_date, Break_Numbers)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (name, sort_or_ship, whos_break, show_date, break_numbers)  # ✅ Insert Break_Numbers
            )
        conn.commit()


# Function to insert data into the Payday table with Total Pay
def insert_payday_data(name, date, time_in, time_out, total_time, num_breaks):
    total_pay = calculate_total_pay(name, total_time, num_breaks)  # ✅ New Pay Calculation

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO Payday (name, date, time_in, time_out, total_time, num_breaks, total_pay)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (name, date, time_in, time_out, total_time, num_breaks, total_pay)  # ✅ Insert Total Pay
            )
        conn.commit()


# Function to archive and reset data
def archive_and_reset():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS Operations_Archive AS SELECT * FROM Operations WHERE 1=0;")
            cursor.execute("CREATE TABLE IF NOT EXISTS Payday_Archive AS SELECT * FROM Payday WHERE 1=0;")

            cursor.execute("INSERT INTO Operations_Archive SELECT * FROM Operations;")
            cursor.execute("INSERT INTO Payday_Archive SELECT * FROM Payday;")

            cursor.execute("DELETE FROM Operations;")
            cursor.execute("DELETE FROM Payday;")
        conn.commit()

# Function to retrieve archived data
def get_archived_data():
    with get_connection() as conn:
        df_operations_archive = pd.read_sql_query("SELECT * FROM Operations_Archive", conn)
        df_payday_archive = pd.read_sql_query("SELECT * FROM Payday_Archive", conn)
    return df_operations_archive, df_payday_archive


# Users List
all_names = ["Select your name"] + sorted([
    "Emily", "Anthony", "Greg", "Jeff", "Dave", "Sean", "Cameron",
    "Joanna", "Brandon", "Jarren", "Ingy", "Claire", "Aimee", "Manu", "Kylie", "Kaley"
])

pay_rates = {
    "Emily": {"type": "break", "rate": 15.00},  
    "Anthony": {"type": "break", "rate": 15.00},  
    "Greg": {"type": "hourly", "rate": 18.50},
    "Jeff": {"type": "hourly", "rate": 25.00},
    "Dave": {"type": "hourly", "rate": 25.00},
    "Sean": {"type": "hourly", "rate": 22.00},
    "Cameron": {"type": "hourly", "rate": 20.00},
    "Joanna": {"type": "break", "rate": 15.00},
    "Brandon": {"type": "hourly", "rate": 20.00},
    "Claire": {"type": "hourly", "rate": 22.00},
    "Aimee": {"type": "hourly", "rate": 22.00},
    "Kylie": {"type": "hourly", "rate": 21.00},
    "Kaley": {"type": "hourly", "rate": 20.00},

}

def calculate_total_pay(name, total_time, num_breaks):
    """Calculates the total pay based on hourly or break pay structure."""
    if name not in pay_rates:
        return 0  # Default to 0 if no pay rate is set

    pay_type = pay_rates[name]["type"]
    rate = pay_rates[name]["rate"]

    if pay_type == "hourly":
        return round(total_time * rate, 2)  # Multiply hours worked by hourly rate
    elif pay_type == "break":
        return round(num_breaks * rate, 2)  # Multiply breaks by break rate
    else:
        return 0  # Default case (should never happen)




# === APP MAIN SECTION  ===


# Display Image (if available)
if os.path.exists("NJCimage2.png"):
    st.image("NJCimage2.png", use_container_width=True)  # Adjust width as needed
else:
    st.warning("⚠️ Image not found. Please upload `NJCimage.png`.")



# === 📌 Expander 1: Get Paid Section ===
with st.expander("💰 Get Paid (Click to Expand/Collapse)", expanded=False):
    st.markdown("""
        <h2 style='text-align: center; font-size: 24px;'>💰 Get Paid</h2>
        <hr style='border: 1px solid gray;'>
    """, unsafe_allow_html=True)

    with st.form("base_data_form"):
        name = st.selectbox("Name *", all_names, key="name")
        date = st.date_input("📅 Date *", key="date")
        num_breaks = st.number_input("☕ Number of Breaks", min_value=0, step=1, key="num_breaks")

        st.write("⏰ Work Hours:")
        time_in = st.time_input("🔵 Time In", value=time(9, 0))
        time_out = st.time_input("🔴 Time Out", value=time(17, 0))

        submit_button = st.form_submit_button("💾 Save Pay Data", use_container_width=True)

    if submit_button:
        if name == "Select your name":
            st.error("❌ You must select a valid name.")
        else:
            total_time = calculate_total_time(time_in, time_out)
            insert_payday_data(name, date, time_in, time_out, total_time, num_breaks)
            st.success("✅ Data saved!")

# === 📌 Expander 2: Track Shows ===
with st.expander("🎬 Track Shows (Click to Expand/Collapse)", expanded=False):
    st.markdown("""
        <h2 style='text-align: center; font-size: 24px;'>🎬 Track Shows</h2>
        <hr style='border: 1px solid gray;'>
    """, unsafe_allow_html=True)

    num_entries = st.number_input("Number of entries *", min_value=1, step=1, key="num_shows")

    show_data = []
    for i in range(num_entries):
        st.markdown(f"### Entry {i+1}")
        col1, col2 = st.columns(2)

        with col1:
            sort_or_ship = st.selectbox(f"Sort or Ship", ["Sort", "Ship"], key=f"sort_or_ship_{i}")
            whos_show = st.text_input(f"Who's Show", key=f"whos_show_{i}")

        with col2:
            show_date = st.date_input(f"Show Date", key=f"show_date_{i}")
            break_numbers = st.text_input(f"Break Numbers Worked On", key=f"break_numbers_{i}")

        show_data.append({
            "sort_or_ship": sort_or_ship,
            "whos_show": whos_show,
            "show_date": show_date,
            "break_numbers": break_numbers  # ✅ New field added
        })

    show_submit = st.button("Submit Show Data")

    if show_submit:
    
        if name == "Select your name" or not name:  # ✅ Ensure Name is selected
            st.error("❌ You must submit your name in the Get Paid form before submitting this form.")
        else:
            for show in show_data:
                insert_operations_data(
                    name, 
                    show["sort_or_ship"], 
                    show["whos_show"], 
                    show["show_date"], 
                    show["break_numbers"]  # ✅ Pass new value to database function
                )
            st.success("✅ Show Data submitted successfully!")

    # === 📌 Expander 3: View Data ===
with st.expander("📊 View Your Data (Click to Expand/Collapse)", expanded=False):
    st.markdown("""
        <h2 style='text-align: center; font-size: 24px;'>Your Work</h2>
        <hr style='border: 1px solid gray;'>
    """, unsafe_allow_html=True)

    
    selected_user = st.selectbox("Select Your Name", all_names)
    entered_password = st.text_input("Enter Password", type="password")

    if entered_password:
        if selected_user in user_passwords and entered_password == user_passwords[selected_user]:
            st.success(f"✅ Welcome, {selected_user}!")
            st.session_state["authenticated_user"] = selected_user
        else:
            st.error("❌ Incorrect password.")
            st.session_state.pop("authenticated_user", None)

    if "authenticated_user" in st.session_state and st.session_state["authenticated_user"]:
        logged_in_user = st.session_state["authenticated_user"]
        st.subheader(f"📊 Your Work Log, {logged_in_user}")

        try:
            with st.spinner("🔄 Loading your Operations log..."):
                df_operations = pd.read_sql_query(
                    "SELECT * FROM Operations WHERE name = %s",
                    get_connection(),
                    params=(logged_in_user,)
                )
                st.subheader("📋 Operations Log")
                st.dataframe(df_operations)

            with st.spinner("🔄 Loading your Payday log..."):
                df_payday = pd.read_sql_query(
                    "SELECT * FROM Payday WHERE name = %s",
                    get_connection(),
                    params=(logged_in_user,)
                )
                st.subheader("💰 Payday Log")
                st.dataframe(df_payday)

        except Exception as e:
            st.error(f"❌ Failed to fetch data: {e}")

# === 📌 Admin View (Secure with Password) ===
with st.expander("Admin Access (Click to Expand/Collapse)", expanded=False):
    st.markdown("""
        <h2 style='text-align: center; font-size: 24px;'>Admin View</h2>
        <hr style='border: 1px solid gray;'>
    """, unsafe_allow_html=True)
    admin_password = st.text_input("Enter Admin Password", type="password")

    if admin_password == "leroy":
        st.success("Access granted! Viewing all submissions.")
        st.subheader("📊 All Submitted Data")

        try:
            with st.spinner("🔄 Loading Operations data..."):
                df_operations = pd.read_sql_query("SELECT * FROM Operations", get_connection())
                st.subheader("📋 Operations Table")
                st.dataframe(df_operations)

            with st.spinner("🔄 Loading Payday data..."):
                df_payday = pd.read_sql_query("SELECT * FROM Payday", get_connection())
                st.subheader("💰 Payday Table")
                st.dataframe(df_payday)

        except Exception as e:
            st.error(f"❌ Failed to fetch data: {e}")

        if st.button("📦 Archive & Reset Data"):
            archive_and_reset()
            st.success("✅ Data has been archived and reset!")
            st.rerun()

        if st.button("📂 View Archived Data"):
            try:
                df_operations_archive, df_payday_archive = get_archived_data()
                st.subheader("📦 Archived Operations Table")
                st.dataframe(df_operations_archive)
                st.subheader("📦 Archived Payday Table")
                st.dataframe(df_payday_archive)
            except Exception as e:
                st.error(f"❌ Failed to fetch archived data: {e}")
