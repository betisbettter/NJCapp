import streamlit as st
import pandas as pd

import subprocess
# Check installed packages
installed_packages = subprocess.run(["pip", "list"], capture_output=True, text=True)
st.text(installed_packages.stdout)

# Check installed packages
installed_packages = subprocess.run(["pip", "list"], capture_output=True, text=True)
st.text(installed_packages.stdout)



#import gspread
#from google.oauth2.credentials import Credentials

# Load OAuth credentials from Streamlit secrets
oauth_creds = {
    "client_id": st.secrets["gcp_oauth"]["client_id"],
    "client_secret": st.secrets["gcp_oauth"]["client_secret"],
    "auth_uri": st.secrets["gcp_oauth"]["auth_uri"],
    "token_uri": st.secrets["gcp_oauth"]["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["gcp_oauth"]["auth_provider_x509_cert_url"],
    "refresh_token": st.secrets["gcp_oauth"].get("refresh_token")  # Ensure refresh token is present
}

# Authenticate with Google Sheets API
creds = Credentials(
    client_id=oauth_creds["client_id"],
    client_secret=oauth_creds["client_secret"],
    token_uri=oauth_creds["token_uri"],
    refresh_token=oauth_creds["refresh_token"],
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)

client = gspread.authorize(creds)

# Open Google Sheet
SHEET_ID = "1-naSW8EsTqLd19RoLbl7wNTKrMPJYK4Gd_E0qQUFaG8"
sheet = client.open_by_key(SHEET_ID).worksheet("Sheet1")

# Read and display data
data = sheet.get_all_records()

st.set_page_config(layout="wide")

# Main Section
st.title("No Job Cards Work Log")
st.subheader("Welcome to the NJC work log. Fill in the fields below so that you can get paid for the work that you do. Go Team!")

with st.sidebar:
    try:
        st.image("NJCimage.png", caption="Where the champions work", use_container_width=True)
    except Exception:
        st.warning("Image not found. Please upload NJCimage.png to the working directory.")

    # Initialize admin mode in session state
    if "admin_mode" not in st.session_state:
        st.session_state.admin_mode = False
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    # Admin Button
    if st.button("Admin"):
        st.session_state.admin_mode = True
        st.session_state.password_correct = False  # Reset access when Admin button is pressed

    # Admin Password Input
    if st.session_state.admin_mode:
        password = st.text_input("Enter Admin Password:", type="password")

        if password:
            if password == "leroy":
                st.session_state.password_correct = True
                st.success("Access Granted! Data will be displayed in the main section.")
            else:
                st.session_state.password_correct = False
                st.error("Incorrect Password!")

# Display DataFrame in the main section if access is granted
if st.session_state.password_correct:
    st.subheader("Admin Dashboard - Work Log Data")
    
    # Ensure it's converted to a DataFrame
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df)
    else:
        st.info("No data available in the Google Sheet.")
