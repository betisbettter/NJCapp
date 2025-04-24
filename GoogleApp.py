import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time
import pandas as pd

# --- Google Sheets Setup ---
credentials_dict = st.secrets["gcp_service_account"]
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(credentials)
sheet = client.open("WORK LOG").sheet1

st.title("📋 Ten Percent Work Log")

# --- Form for new entry ---
st.subheader("Add New Shift Entry")
with st.form("log_form", clear_on_submit=True):
    name = st.text_input("Name")
    work_date = st.date_input("Date", value=datetime.today())
    shift_type = st.selectbox("Sort / Ship / Pack", ["Sort", "Ship", "Pack", "Multiple"])
    num_breaks = st.number_input("Number of Breaks", min_value=0, max_value=5, step=1)
    whos_break = st.text_input("Who took a break?")
    show_date = st.date_input("Show Date", value=datetime.today())
    time_in = st.time_input("Time In", value=time(9, 0))
    time_out = st.time_input("Time Out", value=time(17, 0))
    notes = st.text_area("Shift Notes", height=100)
    submit = st.form_submit_button("Submit Entry")

    if submit:
        row = [
            name,
            work_date.strftime("%Y-%m-%d"),
            shift_type,
            num_breaks,
            whos_break,
            show_date.strftime("%Y-%m-%d"),
            time_in.strftime("%H:%M"),
            time_out.strftime("%H:%M"),
            notes,
        ]
        sheet.append_row(row)
        st.success("✅ Entry submitted!")

# --- Display existing log ---
st.subheader("📊 Work Log History")
data = sheet.get_all_records()
df = pd.DataFrame(data)
if not df.empty:
    st.dataframe(df)
else:
    st.info("No entries in the log yet.")






