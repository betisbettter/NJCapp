import streamlit as st
import psycopg2
import pandas as pd
import os


#DATABASE
# Load database credentials from Streamlit Secrets
DB_URL = st.secrets["database"]["url"]

# Connect to Neon PostgreSQL
def get_connection():
    return psycopg2.connect(DB_URL, sslmode="require")

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

def get_all_data():
    with get_connection() as conn:
        df = pd.read_sql("SELECT * FROM user_data", conn)
    return df



# UI for User Input

st.title("Log your work")
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

# Admin View (with Password)

with st.sidebar:
    
    st.image("NJCimage.png", caption="Where the champions work", use_container_width=True)
    st.title("Admin Access") 

admin_password = st.sidebar.text_input("Enter Admin Password", type="password")

if admin_password == "leroy":
    st.sidebar.success("Access granted! Viewing all submissions.")
    st.subheader("📊 All Submitted Data")
    
    try:
        df = get_all_data()
        st.dataframe(df)
    except Exception as e:
        st.error(f"❌ Failed to fetch data: {e}")

