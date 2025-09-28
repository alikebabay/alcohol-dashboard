# проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# путь к JSON с ключом сервисного аккаунта
CREDENTIALS_FILE = Path("service_account.json")

# ID таблицы (из URL Google Sheets)
SPREADSHEET_ID = "1dISLvKdfi5DCTeYlQ5JXiBcyusrIlJkmikDvkWAcg60"
SHEET_NAME = "master"   # имя листа в таблице


def _get_worksheet():
    """Авторизация и возврат worksheet (создаём при отсутствии)."""
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    client = gspread.authorize(creds)

    sh = client.open_by_key(SPREADSHEET_ID)
    try:
        return sh.worksheet(SHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        # создаём пустой лист
        return sh.add_worksheet(title=SHEET_NAME, rows="1000", cols="20")


def load_master_from_gsheets() -> pd.DataFrame:
    """Загружает мастер-таблицу из Google Sheets в DataFrame."""
    ws = _get_worksheet()
    data = ws.get_all_records()
    if not data:
        print(f"[INFO] Лист {SHEET_NAME} пустой")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    print(f"[OK] Загружено из Google Sheets: {df.shape[0]} строк, {df.shape[1]} колонок")
    return df


def update_master_to_gsheets(df: pd.DataFrame):
    """Очищает лист и загружает новые данные."""
    ws = _get_worksheet()

    # нормализация значений (например, даты → строки)
    df_clean = df.copy()
    for col in df_clean.columns:
        if pd.api.types.is_datetime64_any_dtype(df_clean[col]):
            df_clean[col] = df_clean[col].astype(str)

    ws.clear()
    ws.update([df_clean.columns.tolist()] + df_clean.fillna("").values.tolist())
    print(f"[OK] Обновил Google Sheet: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")
