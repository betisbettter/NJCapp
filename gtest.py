import gspread
from google.oauth2.credentials import Credentials

# Replace with your actual credentials
creds = Credentials(
    client_id="your_client_id",
    client_secret="your_client_secret",
    token_uri="https://oauth2.googleapis.com/token",
    refresh_token="your_refresh_token",
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)

client = gspread.authorize(creds)

# Replace with your actual Google Sheet ID
SHEET_ID = "1-naSW8EsTqLd19RoLbl7wNTKrMPJYK4Gd_E0qQUFaG8"
sheet = client.open_by_key(SHEET_ID).worksheet("Sheet1")

# Fetch and print data
data = sheet.get_all_records()
print("Google Sheets Data:", data)
