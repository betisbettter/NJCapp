import streamlit as st
import psycopg2
import pandas as pd
import os
from datetime import datetime, timedelta

# User passwords
user_passwords = {
    "Emily": "Emily",
    "Anthony": "Anthony",
    "Greg": "Greg"
}

# Load database credentials from Streamlit Secrets
DB_URL = st.secrets["database"]["url"]

# Connect to Neon PostgreSQL
def get_connection():
    return psycopg2.connect(DB_URL, sslmode="require")

# Function to calculate total time in hours
def calculate_total_time(time_in, time_out):
    if time_in and time_out:
        time_in = datetime.strptime(str(time_in), "%H:%M:%S")
        time_out = datetime.strptime(str(time_out), "%H:%M:%S")
        total_time_seconds = (time_out - time_in).total_seconds()
        total_time_hours = round(total_time_seconds / 3600, 2)  # Convert to hours
        return total_time_hours
    return None

# Function to insert data into the Operations table
def insert_operations_data(name, sort_or_ship, whos_break, show_date, break_numbers):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO Operations (name, sort_or_ship, whos_break, show_date, break_numbers)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (name, sort_or_ship, whos_break, show_date, break_numbers)
            )
        conn.commit()

# Function to insert data into the Payday table
def insert_payday_data(name, date, time_in, time_out, total_time, num_breaks):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO Payday (name, date, time_in, time_out, total_time, num_breaks)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (name, date, time_in, time_out, total_time, num_breaks)
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
        df_operations_archive = pd.read_sql("SELECT * FROM Operations_Archive", conn)
        df_payday_archive = pd.read_sql("SELECT * FROM Payday_Archive", conn)
    return df_operations_archive, df_payday_archive

# Function to convert 12-hour time to 24-hour format
def convert_to_24_hour(hour, minute, am_pm):
    if am_pm == "PM" and hour != 12:
        hour += 12
    elif am_pm == "AM" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}:00"

# Sample names
all_names = ["Emily", "Anthony", "Greg"]

# 📌 Expander 1: Base Data
with st.expander("📥 Get Paid (Click to Expand/Collapse)", expanded=True):
    with st.form("base_data_form"):
        name = st.selectbox("Name *", all_names, key="name")
        date = st.date_input("Date *", key="date")
        num_breaks = st.number_input("Number of Breaks (if you get paid by break)", min_value=0, step=1, key="num_breaks")

        col1, col2 = st.columns(2)
        with col1:
            st.write("⏰ Time In *, HR:MIN, AM/PM")
            time_in_hour = st.selectbox("Hour", list(range(1, 13)), key="time_in_hour")
            time_in_minute = st.selectbox("Minute", list(range(0, 60)), key="time_in_minute")
            time_in_am_pm = st.selectbox("AM/PM", ["AM", "PM"], key="time_in_am_pm")
            time_in = convert_to_24_hour(time_in_hour, time_in_minute, time_in_am_pm)

        with col2:
            st.write("⏰ Time Out *, HR:MIN, AM/PM")
            time_out_hour = st.selectbox("Hour", list(range(1, 13)), key="time_out_hour")
            time_out_minute = st.selectbox("Minute", list(range(0, 60)), key="time_out_minute")
            time_out_am_pm = st.selectbox("AM/PM", ["AM", "PM"], key="time_out_am_pm")
            time_out = convert_to_24_hour(time_out_hour, time_out_minute, time_out_am_pm)

        base_submit = st.form_submit_button("Save Pay Data")

        if base_submit:
            base_errors = []
            if not name:
                base_errors.append("⚠️ Name is required.")
            if not date:
                base_errors.append("⚠️ Date is required.")
            if not time_in:
                base_errors.append("⚠️ Time In is required.")
            if not time_out:
                base_errors.append("⚠️ Time Out is required.")

            if base_errors:
                for error in base_errors:
                    st.error(error)
            else:
                try:
                    total_time = calculate_total_time(time_in, time_out)
                    insert_payday_data(name, date, time_in, time_out, total_time, num_breaks)
                    st.success("✅ Base Data saved successfully! Now enter Show Data.")
                    st.session_state["base_data_submitted"] = True
                except Exception as e:
                    st.error(f"❌ Error: {e}")

# ✅ Fixed break_numbers input type
with st.expander("Track Shows (Click to Expand/Collapse)", expanded=False):
    num_entries = st.number_input("Number of entries *", min_value=1, step=1, key="num_shows")

    show_data = []
    for i in range(num_entries):
        st.markdown(f"### Entry {i+1}")
        col1, col2 = st.columns(2)
        with col1:
            sort_or_ship = st.selectbox(f"Sort or Ship for Show {i+1} *", ["Sort", "Ship"], key=f"sort_or_ship_{i}")
            whos_show = st.text_input(f"Who's Show for Show {i+1} *", key=f"whos_show_{i}")
        with col2:
            show_date = st.date_input(f"Show Date for Show {i+1} *", key=f"show_date_{i}")
            break_numbers = st.number_input_input(f"Break Number(s) for Show {i+1}", min_value=0, step=1, key=f"break_numbers_")

        show_data.append({"sort_or_ship": sort_or_ship, "whos_show": whos_show, "show_date": show_date, "break_numbers": break_numbers})

    show_submit = st.button("Submit Show Data")
    if show_submit:
        for show in show_data:
            insert_operations_data(name, show["sort_or_ship"], show["whos_show"], show["show_date"], show["break_numbers"])
        st.success("✅ Show Data submitted successfully!")


        




# SIDEBAR
with st.sidebar:
    if os.path.exists("NJCimage.png"):
        st.image("NJCimage.png", caption="Where the champions work", use_container_width=True)
    else:
        st.warning("⚠️ Image not found. Please upload `NJCimage.png`.")


#User Access   
    st.title("Track your stats")

# Name selection dropdown
selected_user = st.sidebar.selectbox("Select Your Name", all_names)

# Password input field
entered_password = st.sidebar.text_input("Enter Password", type="password")

# Authentication check
if entered_password:  # Only check password if the user has typed something
    if selected_user in user_passwords and entered_password == user_passwords[selected_user]:
        st.sidebar.success(f"✅ Welcome, {selected_user}!")
        st.session_state["authenticated_user"] = selected_user  # Store authenticated user
    else:
        st.sidebar.error("❌ Incorrect password.")
        st.session_state["authenticated_user"] = None
else:
    st.session_state["authenticated_user"] = None  # Reset authentication if no password entered

if "authenticated_user" in st.session_state and st.session_state["authenticated_user"]:
    logged_in_user = st.session_state["authenticated_user"]

    st.subheader(f"📊 Your Work Log, {logged_in_user}")

    try:
        with st.spinner("🔄 Loading your Operations log..."):
            df_operations = pd.read_sql(
                "SELECT * FROM Operations WHERE name = %s",
                get_connection(),
                params=(logged_in_user,)
            )
            st.subheader("📋 Operations Log")
            st.dataframe(df_operations)

        with st.spinner("🔄 Loading your Payday log..."):
            df_payday = pd.read_sql(
                "SELECT * FROM Payday WHERE name = %s",
                get_connection(),
                params=(logged_in_user,)
            )
            st.subheader("💰 Payday Log")
            st.dataframe(df_payday)

    except Exception as e:
        st.error(f"❌ Failed to fetch data: {e}")


        

# Admin View (Secure with Password)
    st.title("Admin Access")

admin_password = st.sidebar.text_input("Enter Admin Password", type="password")

if admin_password == "leroy":
    st.sidebar.success("Access granted! Viewing all submissions.")
    st.subheader("📊 All Submitted Data")

    try:
        with st.spinner("🔄 Loading Operations data..."):
            df_operations = pd.read_sql("SELECT * FROM Operations", get_connection())
            st.subheader("📋 Operations Table")
            st.dataframe(df_operations)

        with st.spinner("🔄 Loading Payday data..."):
            df_payday = pd.read_sql("SELECT * FROM Payday", get_connection())
            st.subheader("💰 Payday Table")
            st.dataframe(df_payday)

    except Exception as e:
        st.error(f"❌ Failed to fetch data: {e}")


    # Add Archive & Reset Button
    if st.button("📦 Archive & Reset Data"):
        archive_and_reset()
        st.success("✅ Data has been archived and the tables have been reset!")
        st.rerun()  # Refresh the page to show empty tables
        
    # Add Button to View Archived Data
    if st.button("📂 View Archived Data"):
        try:
            with st.spinner("🔄 Loading archived data..."):
                df_operations_archive, df_payday_archive = get_archived_data()
                
                st.subheader("📦 Archived Operations Table")
                st.dataframe(df_operations_archive)

                st.subheader("📦 Archived Payday Table")
                st.dataframe(df_payday_archive)

        except Exception as e:
            st.error(f"❌ Failed to fetch archived data: {e}")
