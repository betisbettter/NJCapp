import streamlit as st
import psycopg2
import pandas as pd
import os
from datetime import datetime
from datetime import datetime, timedelta

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

# Function to insert data into the table
def insert_data(name, date, sort_or_ship, num_breaks, whos_break, show_date, shows_packed, time_in, time_out):
    total_time = calculate_total_time(time_in, time_out)  # Calculate total time


# Function to create archive table if not exists
def create_archive_table():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_data_archive AS 
                SELECT * FROM user_data WHERE 1=0;  -- Copies structure but not data
            """)
        conn.commit()

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

# Function to archive and reset data
def archive_and_reset():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # Create archive table if not exists
            create_archive_table()

            # Move all data to the archive table
            cursor.execute("""
                INSERT INTO user_data_archive SELECT * FROM user_data;
            """)

            # Clear the user_data table
            cursor.execute("DELETE FROM user_data;")
        conn.commit()

# UI for Title
st.title("Log your work")

def convert_to_24_hour(hour, minute, am_pm):
    """Convert 12-hour format to 24-hour format"""
    if am_pm == "PM" and hour != 12:
        hour += 12
    elif am_pm == "AM" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}:00"  # Format as HH:MM:SS

# **Expander for User Input Form**
with st.expander("📥 Submit Work Log (Click to Expand/Collapse)", expanded=True):
    with st.form("user_input_form"):
        name = st.text_input("Name *", key="name")
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
            st.write("⏰ Time In *")
            time_in_hour = st.selectbox("Hour", list(range(1, 13)), key="time_in_hour")
            time_in_minute = st.selectbox("Minute", list(range(0, 60)), key="time_in_minute")
            time_in_am_pm = st.selectbox("AM/PM", ["AM", "PM"], key="time_in_am_pm")
            time_in = convert_to_24_hour(time_in_hour, time_in_minute, time_in_am_pm)

        with col4:
            st.write("⏰ Time Out *")
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
                    insert_data(name, date, sort_or_ship, num_breaks, whos_break, show_date, shows_packed, time_in, time_out)
                    st.success(f"✅ Data submitted successfully! ({time_in} to {time_out})")
                except Exception as e:
                    st.error(f"❌ Error: {e}")










# Sidebar for Admin Access
with st.sidebar:
    if os.path.exists("NJCimage.png"):
        st.image("NJCimage.png", caption="Where the champions work", use_container_width=True)
    else:
        st.warning("⚠️ Image not found. Please upload `NJCimage.png`.")
    
    st.title("Admin Access")

admin_password = st.sidebar.text_input("Enter Admin Password", type="password")

# Admin View (Secure with Password)
if admin_password == "leroy":
    st.sidebar.success("Access granted! Viewing all submissions.")
    st.subheader("📊 All Submitted Data")
    
    try:
        with st.spinner("🔄 Loading data..."):
            df = get_all_data()
            st.dataframe(df)
    except Exception as e:
        st.error(f"❌ Failed to fetch data: {e}")

    # Add Archive & Reset Button
    if st.button("📦 Archive & Reset Data"):
        archive_and_reset()
        st.success("✅ Data has been archived and the table has been reset!")
        st.rerun()  # Refresh the page to show empty table

    # Function to get archived data
    def get_archived_data():
        with get_connection() as conn:
            df = pd.read_sql("SELECT * FROM user_data_archive", conn)
        return df

    # Add Button to View Archived Data
    if st.button("📂 View Archived Data"):
        try:
            with st.spinner("🔄 Loading archived data..."):
                df_archive = get_archived_data()
                st.subheader("📦 Archived Data")
                st.dataframe(df_archive)
        except Exception as e:
            st.error(f"❌ Failed to fetch archived data: {e}")

