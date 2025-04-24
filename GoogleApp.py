import streamlit as st
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

# Example: Read and write
data = sheet.get_all_records()
sheet.append_row(["New Entry", 123])




