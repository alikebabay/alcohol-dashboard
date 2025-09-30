import os
import json
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# грузим локальный .env если есть
if os.path.exists("bot_token.env"):
    load_dotenv("bot_token.env")

TOKEN = os.getenv("bot_token")
BOT_USERNAME = os.getenv("BOT_USERNAME")

# сервисный аккаунт Google Sheets из переменной окружения и локально
def get_gsheets_credentials(scopes=None):
    if scopes is None:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    # 1. сначала пробуем creds из переменной окружения (Heroku / облако)
    creds_json = os.getenv("google_creds")
    if creds_json:
        creds_dict = json.loads(creds_json)
        return Credentials.from_service_account_info(creds_dict, scopes=scopes)

    # 2. fallback — локальный файл service_account.json
    if os.path.exists("service_account.json"):
        return Credentials.from_service_account_file("service_account.json", scopes=scopes)

    raise RuntimeError("Google service account credentials not found")