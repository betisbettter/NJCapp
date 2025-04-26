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
    
    # Ensure date formats
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

    # Clear and write to Earnings Sheet
    earnings_sheet.clear()
    earnings_sheet.append_row(["Name", "Pay Period", "Total Earned"])  # Header
    for entry in results:
        earnings_sheet.append_row(entry)

# --- Page Setup ---

if os.path.exists("NJCimage2.png"):
    st.image("NJCimage2.png", use_container_width=True)
else:
    st.warning("⚠️ Image not found. Please upload `NJCimage2.png`.")

# --- User Authentication ---

user_records = load_user_data()
user_names = [row["Na_
