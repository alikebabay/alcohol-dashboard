# gsheets_integration.py
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# путь к JSON с ключом сервисного аккаунта
CREDENTIALS_FILE = Path("service_account.json")

# ID таблицы (из URL Google Sheets)
SPREADSHEET_ID = "1dISLvKdfi5DCTeYlQ5JXiBcyusrIlJkmikDvkWAcg60"
SHEET_NAME = "master"   # имя листа в таблице

def update_master_to_gsheets(df: pd.DataFrame):
    
    # авторизация
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    client = gspread.authorize(creds)

    # открываем таблицу
    sh = client.open_by_key(SPREADSHEET_ID)
    
    try:
        ws = sh.worksheet(SHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=SHEET_NAME, rows=str(len(df)+10), cols=str(len(df.columns)+5))
    
    # нормализация значений
    df_clean = df.copy()
    for col in df_clean.columns:
        if pd.api.types.is_datetime64_any_dtype(df_clean[col]):
            df_clean[col] = df_clean[col].astype(str)
    
    # --- DEBUG ---
    print("[DEBUG gsheets] DataFrame для аплоада:")
    print(" shape:", df_clean.shape)
    print(df_clean.head(5).to_string(index=False))

    # очищаем и загружаем заново
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.fillna("").values.tolist())

    print(f"[OK] Обновил Google Sheet: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")
