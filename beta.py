import streamlit as st
import psycopg2
import pandas as pd
import os
from datetime import datetime
from datetime import datetime, timedelta

#user passwords
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

from datetime import datetime, timedelta

def calculate_total_time(time_in, time_out):
    if time_in and time_out:
        time_in = datetime.strptime(str(time_in), "%H:%M:%S")
        time_out = datetime.strptime(str(time_out), "%H:%M:%S")
        total_time_seconds = (time_out - time_in).total_seconds()
        total_time_hours = round(total_time_seconds / 3600, 2)  # Convert to hours, rounded to 2 decimal places
        return total_time_hours
    return None

def insert_operations_data(name, sort_or_ship, whos_break, show_date):
    """Inserts data into the Operations table"""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO Operations (name, sort_or_ship, whos_break, show_date)
                VALUES (%s, %s, %s, %s)
                """,
                (name, sort_or_ship, whos_break, show_date)
            )
        conn.commit()

def insert_payday_data(name, date, time_in, time_out, total_time, num_breaks):
    """Inserts data into the Payday table"""
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

def archive_and_reset():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # Ensure archive tables exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Operations_Archive AS 
                SELECT * FROM Operations WHERE 1=0;
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Payday_Archive AS 
                SELECT * FROM Payday WHERE 1=0;
            """)

            # Move existing data to archive tables
            cursor.execute("INSERT INTO Operations_Archive SELECT * FROM Operations;")
            cursor.execute("INSERT INTO Payday_Archive SELECT * FROM Payday;")

            # Clear the original tables
            cursor.execute("DELETE FROM Operations;")
            cursor.execute("DELETE FROM Payday;")
            
        conn.commit()


# Function to retrieve archived data
def get_archived_data():
    with get_connection() as conn:
        df_operations_archive = pd.read_sql("SELECT * FROM Operations_Archive", conn)
        df_payday_archive = pd.read_sql("SELECT * FROM Payday_Archive", conn)
    return df_operations_archive, df_payday_archive

def insert_data(name, date, sort_or_ship, num_breaks, whos_break, show_date, shows_packed, time_in, time_out):
    total_time = calculate_total_time(time_in, time_out)  # Calculate total time in hours


def insert_data(name, date, sort_or_ship, num_breaks, whos_break, show_date, shows_packed, time_in, time_out):
    # Ensure numeric fields default to 0 if missing
    num_breaks = num_breaks if num_breaks is not None else 0
    shows_packed = shows_packed if shows_packed is not None else 0
    time_in = time_in if time_in is not None else "00:00:00"  # Default midnight
    time_out = time_out if time_out is not None else "00:00:00"  # Default midnight
    total_time = calculate_total_time(time_in, time_out) if sort_or_ship == "Ship" else 0  # Default 0 if not "Ship"


    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_data (name, date, sort_or_ship, num_breaks, whos_break, show_date, shows_packed, time_in, time_out, total_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (name, date, sort_or_ship, num_breaks, whos_break, show_date, shows_packed, time_in, time_out, total_time)
            )
        conn.commit()

# Function to retrieve all data
def get_all_data():
    with get_connection() as conn:
        df = pd.read_sql("SELECT * FROM user_data", conn)
    return df


# UI for Title
st.title("Log your work")

def convert_to_24_hour(hour, minute, am_pm):
    """Convert 12-hour format to 24-hour format"""
    if am_pm == "PM" and hour != 12:
        hour += 12
    elif am_pm == "AM" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}:00"  # Format as HH:MM:SS

# Sample names for now (you can replace these later)
all_names = ["Emily", "Anthony", "Greg"]


# **Expander for User Input Form**
with st.expander("📥 Submit Work Log (Click to Expand/Collapse)", expanded=True):
    with st.form("user_input_form"):
        name = st.selectbox("Name *", all_names, key="name")
        date = st.date_input("Date *", key="date")
        sort_or_ship = st.selectbox("Sort or Ship *", ["Sort", "Ship"], key="sort_or_ship")

        # Conditional fields
        col1, col2 = st.columns(2)

        with col1:
            whos_break = st.text_input("Who's Break *", key="whos_break")
        with col2:
            show_date = st.date_input("Show Date *", key="show_date")

        num_breaks = None
        shows_packed = None
        time_in = None
        time_out = None

        if sort_or_ship == "Sort":
            num_breaks = st.number_input("Number of Breaks *", min_value=0, step=1, key="num_breaks")
        
        if sort_or_ship == "Ship":
            shows_packed = st.number_input("Shows Packed *", min_value=0, step=1, key="shows_packed")

        col3, col4 = st.columns(2)
        with col3:
            st.write("⏰ Time In *, HR:MIN, AM/PM")
            time_in_hour = st.selectbox("Hour", list(range(1, 13)), key="time_in_hour")
            time_in_minute = st.selectbox("Minute", list(range(0, 60)), key="time_in_minute")
            time_in_am_pm = st.selectbox("AM/PM", ["AM", "PM"], key="time_in_am_pm")
            time_in = convert_to_24_hour(time_in_hour, time_in_minute, time_in_am_pm)

        with col4:
            st.write("⏰ Time Out *, HR:MIN, AM/PM")
            time_out_hour = st.selectbox("Hour", list(range(1, 13)), key="time_out_hour")
            time_out_minute = st.selectbox("Minute", list(range(0, 60)), key="time_out_minute")
            time_out_am_pm = st.selectbox("AM/PM", ["AM", "PM"], key="time_out_am_pm")
            time_out = convert_to_24_hour(time_out_hour, time_out_minute, time_out_am_pm)

        # Validation Checks
        errors = []
        if not name:
            errors.append("⚠️ Name is required.")
        if not date:
            errors.append("⚠️ Date is required.")
        if not sort_or_ship:
            errors.append("⚠️ Sort or Ship selection is required.")
        if not whos_break:
            errors.append("⚠️ Who's Break is required.")
        if not show_date:
            errors.append("⚠️ Show Date is required.")
        if sort_or_ship == "Sort" and num_breaks is None:
            errors.append("⚠️ Number of Breaks is required for Sort.")
        if sort_or_ship == "Ship" and (shows_packed is None or time_in is None or time_out is None):
            errors.append("⚠️ Shows Packed and Time In/Out are required for Ship.")

        submit = st.form_submit_button("Submit")
        if submit:
            if errors:
                for error in errors:
                    st.error(error)
            else:
                try:
                    # Insert data into Operations Table
                    insert_operations_data(name, sort_or_ship, whos_break, show_date)

                    # Insert data into Payday Table
                    total_time = calculate_total_time(time_in, time_out)
                    insert_payday_data(name, date, time_in, time_out, total_time, num_breaks)

                    st.success(f"✅ Data submitted successfully!")
                except Exception as e:
                    st.error(f"❌ Error: {e}")




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
