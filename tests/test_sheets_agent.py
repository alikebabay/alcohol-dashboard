import gspread
from google.oauth2.service_account import Credentials

creds = Credentials.from_service_account_file(
    "alcohol-service-agent.json",
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)

gc = gspread.authorize(creds)
print("Auth OK as:", creds.service_account_email)

try:
    sh = gc.open_by_key("1Dyr2Uz3GLQ_cM4ZZVUMTV0GhHw9vbLdrq518NOVqOh4")
    print("Opened:", sh.title)
except Exception as e:
    print("Error:", repr(e))
