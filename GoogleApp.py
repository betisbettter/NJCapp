
import psycopg2
import pandas as pd
import os
from datetime import datetime, time, timedelta
import re
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# Use credentials from secrets
credentials_dict = st.secrets["gcp_service_account"]

# Define scope
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Create credentials
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

# Authorize client
client = gspread.authorize(credentials)

# Open your sheet (by name or URL)
spreadsheet = client.open("WORK LOG")
sheet = spreadsheet.sheet1
#############################################


st.title("📋 Work Log Entry")

with st.form("log_form"):
    name = st.text_input("Your Name")
    task = st.text_input("Task Description")
    hours = st.number_input("Hours Worked", min_value=0.0, step=0.5)
    submit = st.form_submit_button("Submit Entry")

    if submit and name and task:
        sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), name, task, hours])
        st.success("✅ Entry added to sheet!")





