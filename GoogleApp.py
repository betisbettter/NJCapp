import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import os
import psycopg2
from psycopg2.extras import execute_values

# --- Clear old cache (optional during development) ---
st.cache_data.clear()

# --- Google Sheets Setup ---
credentials_dict = st.secrets["gcp_service_account"]
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(credentials)

shift_sheet = client.open("WORK LOG").worksheet("Shifts")
time_sheet = client.open("WORK LOG").worksheet("Time")
pay_sheet = client.open("WORK LOG").worksheet("Pay")
user_sheet = client.open("Users").sheet1
earnings_sheet = client.open("WORK LOG").worksheet("Earnings")

# --- Neon DB Connection ---
def get_db_connection():
    return psycopg2.connect(
        host=st.secrets["neon"]["host"],
        dbname=st.secrets["neon"]["dbname"],
        user=st.secrets["neon"]["user"],
        password=st.secrets["neon"]["password"],
        sslmode="require"
    )

# --- Load Cached Data ---
@st.cache_data(ttl=60)
def load_shift_data():
    return pd.DataFrame(shift_sheet.get_all_records())

@st.cache_data(ttl=60)
def load_time_data():
    return pd.DataFrame(time_sheet.get_all_records())

@st.cache_data(ttl=60)
def load_pay_data():
    return pd.DataFrame(pay_sheet.get_all_records())

@st.cache_data(ttl=300)
def load_user_data():
    return user_sheet.get_all_records()

# --- Helpers ---
def parse_pay_period(pay_period_str):
    start_str, end_str = pay_period_str.split("-")
    start_date = datetime.strptime(start_str.strip(), "%m/%d/%Y").date()
    end_date = datetime.strptime(end_str.strip(), "%m/%d/%Y").date()
    return start_date, end_date

def check_user_credentials(input_name, input_pass, user_data):
    for entry in user_data:
        if entry["Name"] == input_name:
            return entry["Passkey"] == input_pass
    return False

# --- Page Setup ---
if os.path.exists("NJCimage2.png"):
    st.image("NJCimage2.png", use_container_width=True)

user_records = load_user_data()
user_names = sorted([row["Name"] for row in user_records])

with st.expander("🔐 User Authentication", expanded=True):
    st.subheader("Log In")
    name_input = st.selectbox("Select Your Name", options=["Name"] + user_names)
    pass_input = st.text_input("Passkey", type="password")
    if st.button("Login"):
        if check_user_credentials(name_input, pass_input, user_records):
            st.session_state["logged_in"] = True
            st.session_state["user_name"] = name_input
            st.success(f"Welcome {name_input}!")
        else:
            st.error("Invalid credentials")
            st.stop()

    if "logged_in" not in st.session_state:
        st.stop()

user_name = st.session_state["user_name"]

# --- Load Cached Data (per session) ---
if "pay_df" not in st.session_state:
    st.session_state["pay_df"] = pd.DataFrame(pay_sheet.get_all_records())
if "time_df" not in st.session_state:
    st.session_state["time_df"] = pd.DataFrame(time_sheet.get_all_records())
if "earnings_df" not in st.session_state:
    st.session_state["earnings_df"] = pd.DataFrame(earnings_sheet.get_all_records())
if "user_pay_data" not in st.session_state:
    user_pay_data = st.session_state["pay_df"]
    st.session_state["user_pay_data"] = user_pay_data[user_pay_data["Name"] == user_name].copy()

pay_df = st.session_state["pay_df"]
time_df = st.session_state["time_df"]
user_pay_df = st.session_state["user_pay_data"]

# ✅ USER SHIFT ENTRY FORM: Organized by Task Type (Sort / Pack / Sleeve)

import psycopg2
from psycopg2.extras import execute_values
import json
from datetime import datetime
import pandas as pd

# --- Database Connection for Neon ---
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
        shift_sheet.append_rows(rows)
    except Exception as e:
        st.error("⚠️ Failed to log to Google Sheets. Try again in a few seconds.")
        st.stop()

# --- Load only the Users sheet (initial load optimization) ---
if "user_df" not in st.session_state:
    st.session_state["user_df"] = pd.DataFrame(user_sheet.get_all_records())

# --- Track API reads (optional debugging aid) ---
if "api_calls" not in st.session_state:
    st.session_state["api_calls"] = 1  # only the users sheet counted here

# --- Load Admin-only Sheets on Demand ---
def load_admin_data():
    st.session_state["pay_df"] = pd.DataFrame(pay_sheet.get_all_records())
    st.session_state["time_df"] = pd.DataFrame(time_sheet.get_all_records())
    st.session_state["earnings_df"] = pd.DataFrame(earnings_sheet.get_all_records())
    st.session_state["api_calls"] += 3

# --- Set User Name & Admin Status ---
if "user_name" in st.session_state:
    user_name = st.session_state["user_name"]
    if st.session_state.get("is_admin") and "pay_df" not in st.session_state:
        load_admin_data()
else:
    user_name = ""

pay_df = st.session_state.get("pay_df", pd.DataFrame())
time_df = st.session_state.get("time_df", pd.DataFrame())
earnings_df = st.session_state.get("earnings_df", pd.DataFrame())
user_pay_df = pay_df[pay_df["Name"] == user_name] if not pay_df.empty else pd.DataFrame()

st.subheader("💰 Get Paid - Log Your Work Tasks")

with st.expander("🧱 Log Your Shift Tasks", expanded=True):
    shift_date = st.date_input("🗓️ Date of Shift", value=datetime.today(), key="main_shift_date")
    general_notes = st.text_area("📝 General Shift Notes (optional)", height=80, key="general_notes")

    task_entries = []

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🔹 Sort")
        sort_show = st.text_input("Who's Show? (Sort)", key="sort_show")
        sort_date = st.date_input("Show Date (Sort)", value=datetime.today(), key="sort_date")
        sort_breaks = st.number_input("Number of Breaks (Sort)", min_value=0, step=1, key="sort_breaks")
        sort_large = st.checkbox("Large Break (Sort)", key="sort_large")
        sort_notes = st.text_area("Notes (Sort)",  key="sort_notes")

        if sort_show and sort_breaks > 0:
            task_entries.append([
                user_name, "Sort", sort_breaks, sort_show,
                sort_date.strftime("%Y-%m-%d"), shift_date.strftime("%Y-%m-%d"),
                f"Large Break: {sort_large} | {sort_notes} | {general_notes}"
            ])

    with col2:
        st.markdown("### 🔸 Pack")
        pack_show = st.text_input("Who's Show? (Pack)", key="pack_show")
        pack_date = st.date_input("Show Date (Pack)", value=datetime.today(), key="pack_date")
        pack_breaks = st.number_input("Number of Breaks (Pack)", min_value=0, step=1, key="pack_breaks")
        pack_large = st.checkbox("Large Break (Pack)", key="pack_large")
        pack_notes = st.text_area("Notes (Pack)",  key="pack_notes")

        if pack_show and pack_breaks > 0:
            task_entries.append([
                user_name, "Pack", pack_breaks, pack_show,
                pack_date.strftime("%Y-%m-%d"), shift_date.strftime("%Y-%m-%d"),
                f"Large Break: {pack_large} | {pack_notes} | {general_notes}"
            ])

    with col3:
        st.markdown("### 🟣 Sleeve")
        sleeve_count = st.number_input("Number of Shows Sleeved", min_value=0, step=1, key="sleeve_count")

        for i in range(sleeve_count):
            show = st.text_input(f"Who's Show? (Sleeve {i+1})", key=f"sleeve_show_{i}")
            date = st.date_input(f"Show Date (Sleeve {i+1})", value=datetime.today(), key=f"sleeve_date_{i}")
            if show:
                task_entries.append([
                    user_name, "Sleeve", 1, show,
                    date.strftime("%Y-%m-%d"), shift_date.strftime("%Y-%m-%d"),
                    f"Sleeve Entry | {general_notes}"
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
                        INSERT INTO shifts (name, task, breaks, show_name, show_date, shift_date, notes)
                        VALUES %s
                        """,
                        task_entries
                    )
            st.success("✅ All tasks successfully logged!")
        else:
            st.warning("⚠️ Please enter at least one task in Sort, Pack, or Sleeve.")
