import streamlit as st
import psycopg2
import pandas as pd
import os
from datetime import datetime, timedelta, time

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

# Connect to Neon PostgreSQL
def get_connection():
    return psycopg2.connect(DB_URL, sslmode="require")

# Function to calculate total time in hours
def calculate_total_time(time_in, time_out):
    if time_in and time_out:
        time_in = datetime.combine(datetime.today(), time_in)  # Convert time to full datetime
        time_out = datetime.combine(datetime.today(), time_out)

        total_time_seconds = (time_out - time_in).total_seconds()
        total_time_hours = round(total_time_seconds / 3600, 2)  # Convert to hours
        return total_time_hours
    return None

# Function to insert data into the Operations table
def insert_operations_data(name, sort_or_ship, whos_break, show_date):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO Operations (name, sort_or_ship, whos_break, show_date)
                VALUES (%s, %s, %s,%s )
                """,
                (name, sort_or_ship, whos_break, show_date)
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

def get_archived_data():
    with get_connection() as conn:
        df_operations_archive = pd.read_sql_query("SELECT * FROM Operations_Archive", conn)
        df_payday_archive = pd.read_sql_query("SELECT * FROM Payday_Archive", conn)
    return df_operations_archive, df_payday_archive

#APP MAIN
st.title(The NJC app)
if os.path.exists("NJCimage.png"):
        st.image("NJCimage.png", caption="Where the champions work", use_container_width=True)
    else:
        st.warning("⚠️ Image not found. Please upload `NJCimage.png`.")


# Function to convert 12-hour time to 24-hour format
def convert_to_24_hour(hour, minute, am_pm):
    if am_pm == "PM" and hour != 12:
        hour += 12
    elif am_pm == "AM" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}:00"


# Users
all_names = ["Select your name"] + sorted([
    "Emily", "Anthony", "Greg", "Jeff", "Dave", "Sean", "Cam", 
    "Joanna", "Brandon", "Jarren", "Ingy", "Claire", "Aimee", "Manu"
])

# 📌 Expander 1: Get Paid 
with st.expander("💰 Get Paid (Click to Expand/Collapse)", expanded=True):
    st.markdown("""
        <h2 style='text-align: center; font-size: 24px;'>💰 Get Paid</h2>
        <hr style='border: 1px solid gray;'>
    """, unsafe_allow_html=True)

    with st.form("base_data_form"):
        name = st.selectbox("Name *", all_names, key="name")
        date = st.date_input("📅 Date *", key="date")
        num_breaks = st.number_input("☕ Number of Breaks", min_value=0, step=1, key="num_breaks")

        # More efficient time logging using `st.time_input()`
        st.write("⏰ Work Hours:")
        time_in = st.time_input("🔵 Time In", value=time(9, 0))  # Default 9:00 AM
        time_out = st.time_input("🔴 Time Out", value=time(17, 0))  # Default 5:00 PM

        # Submit Button
        submit_button = st.form_submit_button("💾 Save Pay Data", use_container_width=True)

    if submit_button:
        if name == "Select your name":
            st.error("❌ You must select a valid name.")
        else:
            total_time = calculate_total_time(time_in, time_out)
            insert_payday_data(name, date, time_in, time_out, total_time, num_breaks)
            st.success(f"✅ Data saved!")


     
        
#📌 Expander 2: track shows
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
            sort_or_ship = st.selectbox(f"Sort or Ship for Show {i+1} *", ["Sort", "Ship"], key=f"sort_or_ship_{i}")
            whos_show = st.text_input(f"Who's Show for Show {i+1} *", key=f"whos_show_{i}")
        with col2:
            show_date = st.date_input(f"Show Date for Show {i+1} *", key=f"show_date_{i}")

        show_data.append({"sort_or_ship": sort_or_ship, "whos_show": whos_show, "show_date": show_date})

    show_submit = st.button("Submit Show Data")
    if show_submit:
        for show in show_data:
            insert_operations_data(name, show["sort_or_ship"], show["whos_show"], show["show_date"])
        st.success("✅ Show Data submitted successfully!")




#📌 Expander3: View Data
with st.expander("📊 View Your Data (Click to Expand/Collapse)", expanded=False):
     
    st.title("Track your stats")

# Name selection dropdown
selected_user = st.sidebar.selectbox("Select Your Name", all_names)

# Password input field
entered_password = st.sidebar.text_input("Enter Password", type="password")

# Authentication check
if entered_password:
    if selected_user in user_passwords and entered_password == user_passwords[selected_user]:
        st.sidebar.success(f"✅ Welcome, {selected_user}!")
        st.session_state["authenticated_user"] = selected_user
    else:
        st.sidebar.error("❌ Incorrect password.")
        st.session_state.pop("authenticated_user", None)  # Safely remove

# Keep previous session if no new password entered
if "authenticated_user" not in st.session_state:
    st.session_state["authenticated_user"] = None

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
