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

# --- Admin-only Sheets Load (on demand) ---
def load_admin_data():
    try:
        st.session_state["pay_df"] = pd.DataFrame(client.open("WORK LOG").worksheet("Pay").get_all_records())
        st.session_state["time_df"] = pd.DataFrame(client.open("WORK LOG").worksheet("Time").get_all_records())
        st.session_state["earnings_df"] = pd.DataFrame(client.open("WORK LOG").worksheet("Earnings").get_all_records())
    except Exception as e:
        st.error("🛑 Could not load one or more admin sheets. Check sheet names or permissions.")
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
            st.session_state["is_admin"] = name_input in ["Anthony", "Greg"]
            st.success(f"Welcome {name_input}!")
        else:
            st.error("Invalid credentials")
            st.stop()

    if "logged_in" not in st.session_state:
        st.stop()

user_name = st.session_state["user_name"]

# --- Load Admin Data if Admin ---
if st.session_state.get("is_admin") and "pay_df" not in st.session_state:
    load_admin_data()

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


    # --- USER DASHBOARD ---
st.subheader("📊 My Earnings Dashboard")

@st.cache_data(ttl=120)
def fetch_shifts_from_db(user_name):
    with get_db_connection() as conn:
        return pd.read_sql("SELECT * FROM shifts WHERE name = %s", conn, params=(user_name,))

if st.button("📥 Load My Shifts"):
    shift_df = fetch_shifts_from_db(user_name)
    shift_df.columns = shift_df.columns.astype(str).str.strip().str.title()

    shift_df["Show Date"] = pd.to_datetime(shift_df["Show Date"], errors="coerce").dt.date
    shift_df["Shift Date"] = pd.to_datetime(shift_df["Shift Date"], errors="coerce").dt.date

    pay_periods = sorted(
        set(row["Pay Period"] for _, row in time_df.iterrows() if row["Name"] == user_name),
        key=lambda x: parse_pay_period(x)[0], reverse=True
    )
    selected_period = st.selectbox("📆 Filter by Pay Period:", options=["All"] + pay_periods)

    def get_shift_pay_period(date):
        for period in pay_periods:
            start, end = parse_pay_period(period)
            if start <= date <= end:
                return period
        return "Unmatched"

    shift_df["Pay Period"] = shift_df["Shift Date"].apply(get_shift_pay_period)

    if selected_period != "All":
        shift_df = shift_df[shift_df["Pay Period"] == selected_period]

    if shift_df.empty:
        st.info("No shift data found yet. Log some tasks!")
    else:
        earnings = []
        total_pay = 0
        for _, row in shift_df.iterrows():
            task = row["Task"].lower()
            breaks = row["Breaks"] if not pd.isnull(row["Breaks"]) else 0

            match = user_pay_df[user_pay_df["Type"].str.lower() == task]
            if not match.empty:
                rate = float(match.iloc[0]["Rate"])
                earned = rate * breaks
                total_pay += earned
                earnings.append(earned)
            else:
                earnings.append(0)

        shift_df["Earned"] = earnings

        st.metric("💰 Total Earned", f"${total_pay:,.2f}")
        st.metric("Total Tasks Logged", len(shift_df))

        st.dataframe(shift_df.sort_values(["Pay Period", "Shift Date"], ascending=[False, False]), use_container_width=True)


