import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import os

# --- Google Sheets Setup ---
credentials_dict = st.secrets["gcp_service_account"]
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(credentials)

# Open all worksheets
shift_sheet = client.open("WORK LOG").worksheet("Shifts")
time_sheet = client.open("WORK LOG").worksheet("Time")
pay_sheet = client.open("WORK LOG").worksheet("Pay")
user_sheet = client.open("Users").sheet1
earnings_sheet = client.open("WORK LOG").worksheet("Earnings")

# --- Caching Functions ---
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

# --- Helper Functions ---
def parse_pay_period(pay_period_str):
    start_str, end_str = pay_period_str.split("-")
    start_date = datetime.strptime(start_str.strip(), "%m/%d/%Y").date()
    end_date = datetime.strptime(end_str.strip(), "%m/%d/%Y").date()
    return start_date, end_date

def check_user_credentials(input_name, input_pass, user_data):
    for entry in user_data:
        if entry["Name"] == input_name:
            stored_pass = entry["Passkey"]
            return stored_pass == input_pass
    return False

def refresh_earnings():
    pay_df = load_pay_data()
    time_df = load_time_data()
    shift_df = load_shift_data()

    earnings_sheet = client.open("WORK LOG").worksheet("Earnings")

    shift_df["Date of Work"] = pd.to_datetime(shift_df["Date of Work"]).dt.date  

    merged_df = pd.merge(time_df, pay_df, on="Name", how="left")

    results = []

    for _, row in merged_df.iterrows():
        name = row["Name"]
        pay_period = row["Pay Period"]
        rate_type = row["Type"].lower()
        rate = row["Rate"]

        start_date, end_date = parse_pay_period(pay_period)

        if rate_type == "hourly":
            total_time = row["Total Time"]
            total_earned = total_time * rate

        elif rate_type == "break":
            shifts_for_period = shift_df[
                (shift_df["Name"] == name) &
                (shift_df["Date of Work"] >= start_date) &
                (shift_df["Date of Work"] <= end_date)
            ]
            total_breaks = shifts_for_period["num Breaks"].sum()
            total_earned = total_breaks * rate

        else:
            total_earned = 0

        results.append([name, pay_period, round(total_earned, 2)])

# ✅ Instead of clearing and appending one row at a time, we batch it
    values = [["Name", "Pay Period", "Total Earned"]] + results
    earnings_sheet.update('A1', values)

# Success Summary
    total_users = len(results)
    total_payroll = sum([entry[2] for entry in results])

    st.success(f"✅ Successfully updated earnings for {total_users} people!")
    st.info(f"💰 Total Payroll This Period: **${total_payroll:,.2f}**")


# --- Success Summary ---
    total_users = len(results)
    total_payroll = sum([entry[2] for entry in results])

    st.success(f"✅ Successfully updated earnings for {total_users} people!")
    st.info(f"💰 Total Payroll This Period: **${total_payroll:,.2f}**")


# --- Page Setup ---

if os.path.exists("NJCimage2.png"):
    st.image("NJCimage2.png", use_container_width=True)
else:
    st.warning("⚠️ Image not found. Please upload `NJCimage2.png`.")

# --- User Authentication ---

user_records = load_user_data()
user_names = [row["Name"] for row in user_records]
user_names.sort()

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

# --- Admin Controls ---
admin_users = ["Anthony", "Greg"]
is_admin = user_name in admin_users

if is_admin:
    with st.expander("🔧 Admin Controls", expanded=True):
        st.subheader("Admin Panel")
        if st.button("🔄 Refresh Earnings Calculations"):
            refresh_earnings()
            st.success("✅ Earnings sheet has been updated!")

# --- Form for New Shift Entry ---


with st.expander("💰 Get Paid (Click to Expand/Collapse)", expanded=False):
    st.subheader("Add Work Tasks")
    
    shift_date = st.date_input("🗓️ Date of Shift (Today’s Work)", value=datetime.today(), key="main_shift_date")
    notes = st.text_area("📝 General Shift Notes (optional)", height=100)

    work_blocks = []
    max_blocks = 5  # You can increase if users work many shows per day

    for i in range(1, max_blocks + 1):
        with st.expander(f"🎭 Work Block {i}", expanded=(i == 1)):
            task_types = st.multiselect("💼 Work Type(s)", ["Sort", "Ship", "Sleeve"], key=f"type_{i}")
            num_breaks = st.number_input("🔢 Number of Breaks", min_value=0, step=1, key=f"breaks_{i}")
            show_name = st.text_input("🎤 Who's Show?", key=f"show_{i}")
            show_date = st.date_input("📅 Date of Show", value=datetime.today(), key=f"date_{i}")

            if task_types and show_name:
                work_blocks.append({
                    "Work Types": task_types,
                    "Breaks": num_breaks,
                    "Show": show_name,
                    "Show Date": show_date
                })

    submit = st.button("✅ Submit All Tasks")

    if submit and work_blocks:
        for block in work_blocks:
            for task in block["Work Types"]:
                shift_sheet.append_row([
                    user_name,
                    task,  # Task Type: Sort, Ship, Sleeve
                    block["Breaks"],
                    block["Show"],
                    block["Show Date"].strftime("%Y-%m-%d"),
                    shift_date.strftime("%Y-%m-%d"),  # Date the shift was worked
                    notes
                ])
        st.success("✅ All tasks successfully logged!")
    elif submit and not work_blocks:
        st.warning("⚠️ Please enter at least one work block with task type and show info.")






# ✅ USER DASHBOARD: Shows logged shifts, total tasks, and total earnings

with st.expander("📊 My Earnings Dashboard", expanded=True):
    shift_df = load_shift_data()
    pay_df = load_pay_data()

    # Normalize headers
    shift_df.columns = shift_df.columns.str.strip().str.title()
    pay_df.columns = pay_df.columns.str.strip().str.title()

    # Filter user data
    user_shifts = shift_df[shift_df["Name"] == user_name].copy()
    user_shifts["Show Date"] = pd.to_datetime(user_shifts["Show Date"]).dt.date
    user_shifts["Shift Date"] = pd.to_datetime(user_shifts["Shift Date"]).dt.date

    if user_shifts.empty:
        st.info("No shift data found yet. Log some tasks!")
    else:
        # Calculate per-task earnings
        earnings = []
        total_pay = 0
        for _, row in user_shifts.iterrows():
            task = row["Task"].lower()
            breaks = row["Breaks"] if not pd.isnull(row["Breaks"]) else 0

            match = pay_df[(pay_df["Name"] == user_name) & (pay_df["Type"].str.lower() == task)]
            if not match.empty:
                rate = float(match.iloc[0]["Rate"])
                earned = rate * breaks
                total_pay += earned
                earnings.append(earned)
            else:
                earnings.append(0)

        user_shifts["Earned"] = earnings

        # Display summary
        st.metric("💰 Total Earned", f"${total_pay:,.2f}")
        st.metric("🧱 Total Tasks Logged", len(user_shifts))

        # Show full log
        st.dataframe(user_shifts.sort_values("Shift Date", ascending=False), use_container_width=True)
