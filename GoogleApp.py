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
# ✅ USER SHIFT ENTRY FORM: Organized by Task Type (Sort / Pack / Sleeve)

st.subheader("💰 Get Paid - Log Your Work Tasks")

with st.expander("🧱 Log Your Shift Tasks", expanded=True):
    shift_date = st.date_input("🗓️ Date of Shift", value=datetime.today(), key="main_shift_date")
    general_notes = st.text_area("📝 General Shift Notes (optional)",  key="general_notes")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### Sort")
        sort_show = st.text_input("Who's Show? (Sort)", key="sort_show")
        sort_date = st.date_input("Show Date (Sort)", value=datetime.today(), key="sort_date")
        sort_breaks = st.number_input("Number of Breaks (Sort)", min_value=0, step=1, key="sort_breaks")
        sort_large = st.checkbox("Large Break (Sort)", key="sort_large")
        sort_notes = st.text_area("Notes (Sort)",  key="sort_notes")

    with col2:
        st.markdown("### Pack")
        pack_show = st.text_input("Who's Show? (Pack)", key="pack_show")
        pack_date = st.date_input("Show Date (Pack)", value=datetime.today(), key="pack_date")
        pack_breaks = st.number_input("Number of Breaks (Pack)", min_value=0, step=1, key="pack_breaks")
        pack_large = st.checkbox("Large Break (Pack)", key="pack_large")
        pack_notes = st.text_area("Notes (Pack)", key="pack_notes")

    with col3:
        st.markdown("### Sleeve")
        sleeve_count = st.number_input("Number of Shows Sleeved", min_value=0, step=1, key="sleeve_count")

        sleeve_entries = []
        for i in range(sleeve_count):
            show = st.text_input(f"Who's Show? (Sleeve {i+1})", key=f"sleeve_show_{i}")
            date = st.date_input(f"Show Date (Sleeve {i+1})", value=datetime.today(), key=f"sleeve_date_{i}")
            if show:
                sleeve_entries.append((show, date))

    submit = st.button("✅ Submit All Logged Tasks")

    if submit:
        # Submit Sort entry
        if sort_show:
            shift_sheet.append_row([
                user_name, "Sort", sort_breaks, sort_show,
                sort_date.strftime("%Y-%m-%d"), shift_date.strftime("%Y-%m-%d"),
                f"Large Break: {sort_large} | {sort_notes} | {general_notes}"
            ])

        # Submit Pack entry
        if pack_show:
            shift_sheet.append_row([
                user_name, "Pack", pack_breaks, pack_show,
                pack_date.strftime("%Y-%m-%d"), shift_date.strftime("%Y-%m-%d"),
                f"Large Break: {pack_large} | {pack_notes} | {general_notes}"
            ])

        # Submit Sleeve entries
        for show, date in sleeve_entries:
            shift_sheet.append_row([
                user_name, "Sleeve", 1, show,
                date.strftime("%Y-%m-%d"), shift_date.strftime("%Y-%m-%d"),
                f"Sleeve Entry | {general_notes}"
            ])

        st.success("✅ All tasks successfully logged!")
    elif submit and not (sort_show or pack_show or sleeve_entries):
        st.warning("⚠️ Please enter at least one task in Sort, Pack, or Sleeve.")



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
