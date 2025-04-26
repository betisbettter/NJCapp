import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time
import pandas as pd
import os

# --- Google Sheets Setup ---
credentials_dict = st.secrets["gcp_service_account"]
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(credentials)

shift_sheet = client.open("WORK LOG").worksheet("Shifts")
time_sheet = client.open("WORK LOG").worksheet("Time")
pay_sheet = client.open("WORK LOG").worksheet("Pay")
user_sheet = client.open("Users").sheet1


# --- Page -----
if os.path.exists("NJCimage2.png"):
    st.image("NJCimage2.png", use_container_width=True)  # Adjust width as needed
else:
    st.warning("⚠️ Image not found. Please upload `NJCimage.png`.")


def check_user_credentials(input_name, input_pass, user_data):
    for entry in user_data:
        if entry["Name"] == input_name:
            stored_pass = entry["Passkey"]
            # Simple match (not hashed)
            return stored_pass == input_pass
            # If using bcrypt instead:
            # return bcrypt.checkpw(input_pass.encode(), stored_pass.encode())
    return False

# Load user credentials from Google Sheet

user_records = user_sheet.get_all_records()
user_names = [row["Name"] for row in user_records]
user_names.sort()  # Optional: sort alphabetically

# Show login
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

    # Stop app here if not logged in
    if "logged_in" not in st.session_state:
        st.stop()

    user_name = st.session_state["user_name"]



# --- Form for new entry ---
with st.expander("💰 Get Paid (Click to Expand/Collapse)", expanded=False):
    st.subheader("Add New Shift Entry")
    with st.form("log_form", clear_on_submit=True):
        name = st.text_input("Name", value=st.session_state["user_name"], disabled=True)
        shift_date = st.date_input("Date of Work", value=datetime.today())
     
        shift_type = st.multiselect("Sort / Ship / Pack", ["Sort", "Ship", "Pack"])
        shift_type_str = ", ".join(shift_type)
        num_breaks = st.number_input("Number of Breaks", min_value=0, max_value=5, step=1)
        size_break = st.radio("Break Size", ["Standard", "Large"])
        whos_break = st.text_input("Who's Show?")
        show_date = st.date_input("Show Date", value=datetime.today())
        notes = st.text_area("Shift Notes", height=100)
        
        submit = st.form_submit_button("Submit Entry")

        if submit:
            row = [
                st.session_state["user_name"],
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

# --- Display existing log ---
with st.expander("🎬 Track Your Work (Click to Expand/Collapse)", expanded=False):
    st.subheader("📊 Work Log History")
    data = shift_sheet.get_all_records()
    df = pd.DataFrame(data)
    user_df = df[df["Name"] == user_name]
    if not user_df.empty:
        st.dataframe(user_df)
    else:
        st.info("No entries found for your name.")





