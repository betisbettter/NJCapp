# ✅ USER SHIFT ENTRY FORM: Organized by Task Type (Sort / Pack / Sleeve)

import psycopg2
from psycopg2.extras import execute_values
import json
from datetime import datetime
import pandas as pd
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# --- Clear old cache (optional during development) ---
st.cache_data.clear()

#----- IMAGE ------
if os.path.exists("NJCimage2.png"):
    st.image("NJCimage2.png", use_container_width=True)
else:
    st.warning("⚠️ Image not found. Please upload `NJCimage.png`.")
st.title("No Job Cards Work Log")

# --- Google Sheets Setup ---
credentials_dict = st.secrets["gcp_service_account"]
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(credentials)

# Only load Users sheet at startup
user_sheet = client.open("Users").sheet1
if "user_df" not in st.session_state:
    st.session_state["user_df"] = pd.DataFrame(user_sheet.get_all_records())

# --- Neon DB Connection ---
def get_db_connection():
    return psycopg2.connect(
        host=st.secrets["neon"]["host"],
        dbname=st.secrets["neon"]["dbname"],
        user=st.secrets["neon"]["user"],
        password=st.secrets["neon"]["password"],
        sslmode="require"
    )

# --- Helper for Google Sheet appending with retry protection ---
@st.cache_data(ttl=1, show_spinner=False)
def append_shift_rows(rows):
    try:
        shift_ws = client.open("WORK LOG").worksheet("Shifts")
        shift_ws.append_rows(rows)
    except Exception as e:
        st.error("⚠️ Failed to log to Google Sheets. Try again in a few seconds.")
        st.stop()

# --- Set Login and Admin State ---
def check_user_credentials(input_name, input_pass):
    df = st.session_state["user_df"]
    match = df[(df["Name"] == input_name) & (df["Passkey"] == input_pass)]
    return not match.empty

user_names = st.session_state["user_df"]["Name"].tolist()
user_names.sort()

with st.expander("🔐 User Authentication", expanded=True):
    name_input = st.selectbox("Select Your Name", options=["Name"] + user_names)
    pass_input = st.text_input("Passkey", type="password")
    if st.button("Login"):
        if check_user_credentials(name_input, pass_input):
            st.session_state["logged_in"] = True
            st.session_state["user_name"] = name_input
            st.session_state["is_admin"] = name_input in ["Anthony Gartman", "Greg Oneill"]
            st.success(f"Welcome {name_input}!")
        else:
            st.error("Invalid credentials")
            st.stop()

    if "logged_in" not in st.session_state:
        st.stop()

user_name = st.session_state["user_name"]
user_row = st.session_state["user_df"][st.session_state["user_df"]["Name"] == user_name]
user_wage_type = user_row.iloc[0]["Wage"].lower() if not user_row.empty else "task"

st.subheader("💰 Get Paid - Log Your Work Tasks")

with st.expander("Log Your Shift Tasks", expanded=True):
    shift_date = st.date_input("🗓️ Date of Shift", value=datetime.today(), key="main_shift_date")
    general_notes = st.text_area("📝 General Shift Notes (optional)", height=80, key="general_notes")

    task_entries = []
    date_logged = datetime.today().strftime("%Y-%m-%d")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### Sort")
        sort_show = st.text_input("Who's Show? (Sort)", key="sort_show")
        sort_date = st.date_input("Show Date (Sort)", value=datetime.today(), key="sort_date")
        sort_breaks = st.number_input("Number of Breaks (Sort)", min_value=0, step=1, key="sort_breaks")
        sort_large = st.checkbox("Large Break (Sort)", key="sort_large")
        sort_notes = st.text_area("Notes (Sort)", key="sort_notes")

        if sort_show and sort_breaks > 0:
            for _ in range(sort_breaks):
                rate_bonus = 5 if sort_large else 0
                task_entries.append([
                    user_name, "Sort", 1, sort_show,
                    sort_date.strftime("%Y-%m-%d"), shift_date.strftime("%Y-%m-%d"),
                    f"Large Break: {sort_large} | {sort_notes} | {general_notes}",
                    date_logged, rate_bonus
                ])

    with col2:
        st.markdown("### Pack")
        pack_show = st.text_input("Who's Show? (Pack)", key="pack_show")
        pack_date = st.date_input("Show Date (Pack)", value=datetime.today(), key="pack_date")
        pack_breaks = st.number_input("Number of Breaks (Pack)", min_value=0, step=1, key="pack_breaks")
        pack_large = st.checkbox("Large Break (Pack)", key="pack_large")
        pack_notes = st.text_area("Notes (Pack)", key="pack_notes")

        if pack_show and pack_breaks > 0:
            for _ in range(pack_breaks):
                task_entries.append([
                    user_name, "Pack", 1, pack_show,
                    pack_date.strftime("%Y-%m-%d"), shift_date.strftime("%Y-%m-%d"),
                    f"Large Break: {pack_large} | {pack_notes} | {general_notes}",
                    date_logged, 0
                ])

    with col3:
        st.markdown("### Sleeve")
        sleeve_count = st.number_input("Number of Shows Sleeved", min_value=0, step=1, key="sleeve_count")

        for i in range(sleeve_count):
            show = st.text_input(f"Who's Show? (Sleeve {i+1})", key=f"sleeve_show_{i}")
            date = st.date_input(f"Show Date (Sleeve {i+1})", value=datetime.today(), key=f"sleeve_date_{i}")
            if show:
                task_entries.append([
                    user_name, "Sleeve", 1, show,
                    date.strftime("%Y-%m-%d"), shift_date.strftime("%Y-%m-%d"),
                    f"Sleeve Entry | {general_notes}",
                    date_logged, 0
                ])

    submit = st.button("✅ Submit All Logged Tasks")

    if submit:
        if task_entries:
            append_shift_rows(task_entries)
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    execute_values(
                        cur,
                        """
                        INSERT INTO shifts ("Name", "Task", "Breaks", "Who's Show", "Show Date", "Shift Date", "Notes", "Date Logged", "Rate Bonus")
                        VALUES %s
                        """,
                        task_entries
                    )
            st.success("✅ All tasks successfully logged!")
        else:
            st.warning("⚠️ Please enter at least one task in Sort, Pack, or Sleeve.")
