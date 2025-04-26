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

    shift_df["Date"] = pd.to_datetime(shift_df["Date"]).dt.date  # <<< Make sure this matches your real column name!

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
                (shift_df["Date"] >= start_date) &
                (shift_df["Date"] <= end_date)
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
    st.subheader("Add New Shift Entry")
    with st.form("log_form", clear_on_submit=True):
        st.text_input("Name", value=user_name, disabled=True)
        shift_date = st.date_input("Date of Work", value=datetime.today())
        shift_type = st.multiselect("Sort / Ship / Pack", ["Sort", "Ship", "Pack"])
        shift_type_str = ", ".join(shift_type)
        num_breaks = st.number_input("Number of Breaks", min_value=0, max_value=5, step=1)
        size_break = st.radio("Break Size", ["Standard", "Large"], horizontal=True)
        whos_break = st.text_input("Who's Show?")
        show_date = st.date_input("Show Date", value=datetime.today())
        notes = st.text_area("Shift Notes", height=100)
        submit = st.form_submit_button("Submit Entry")

        if submit:
            row = [
                user_name,
                shift_date.strftime("%Y-%m-%d"),
                shift_type_str,
                num_breaks,
                size_break,
                whos_break,
                show_date.strftime("%Y-%m-%d"),
                notes,
            ]
            shift_sheet.append_row(row)
            st.success("✅ Entry submitted!")

# --- Display Existing Work Log ---

with st.expander("🎬 Track Your Work (Click to Expand/Collapse)", expanded=False):
    st.subheader("📊 Work Log History")
    df = load_shift_data()
    user_df = df[df["Name"] == user_name]
    if not user_df.empty:
        st.dataframe(user_df)
    else:
        st.info("No entries found for your name.")

