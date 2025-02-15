import streamlit as st
import psycopg2
import pandas as pd
import os

# Load database credentials from Streamlit Secrets
DB_URL = st.secrets["database"]["url"]

# Connect to Neon PostgreSQL
def get_connection():
    return psycopg2.connect(DB_URL, sslmode="require")

# Function to create archive table if not exists
def create_archive_table():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_data_archive AS 
                SELECT * FROM user_data WHERE 1=0;  -- Copies structure but not data
            """)
        conn.commit()

# Function to insert data into the table
def insert_data(name, date, sort_or_ship, num_breaks, whos_break, show_date, shows_packed, time_in, time_out):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_data (name, date, sort_or_ship, num_breaks, whos_break, show_date, shows_packed, time_in, time_out)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (name, date, sort_or_ship, num_breaks, whos_break, show_date, shows_packed, time_in, time_out)
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

# User Input Form
with st.expander("📥  (Click to Expand/Collapse)", expanded=True):
    with st.form("user_input_form"):
        name = st.text_input("Name")
        date = st.date_input("Date")
        sort_or_ship = st.selectbox("Sort or Ship", ["Sort", "Ship"])
        num_breaks = st.number_input("Number of Breaks", min_value=0, step=1)
        whos_break = st.text_input("Who's Break")
        show_date = st.date_input("Show Date")
        shows_packed = st.number_input("Shows Packed", min_value=0, step=1)
        time_in = st.time_input("Time In")
        time_out = st.time_input("Time Out")

        submit = st.form_submit_button("Submit")
        if submit:
            try:
                insert_data(name, date, sort_or_ship, num_breaks, whos_break, show_date, shows_packed, time_in, time_out)
                st.success("✅ Data submitted successfully!")
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
