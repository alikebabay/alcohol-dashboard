# проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

import gspread
import pandas as pd
from config import get_gsheets_credentials



# ID таблицы (из URL Google Sheets)
SPREADSHEET_ID = "1dISLvKdfi5DCTeYlQ5JXiBcyusrIlJkmikDvkWAcg60"
SHEET_NAME = "master"   # имя листа в таблице


def _get_worksheet():
    """Авторизация и возврат worksheet (создаём при отсутствии)."""
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = get_gsheets_credentials(scopes)   # <-- переключатель уже внутри config
    client = gspread.authorize(creds)

    sh = client.open_by_key(SPREADSHEET_ID)
    try:
        return sh.worksheet(SHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        # создаём пустой лист
        return sh.add_worksheet(title=SHEET_NAME, rows="1000", cols="20")


def load_master_from_gsheets() -> pd.DataFrame:
    """Загружает мастер-таблицу из Google Sheets в DataFrame."""
    print("[DEBUG] load_master_from_gsheets вызвана")
    ws = _get_worksheet()
    data = ws.get_all_records(value_render_option="UNFORMATTED_VALUE")
    if not data:
        print(f"[INFO] Лист {SHEET_NAME} пустой")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    print(f"[OK] Загружено из Google Sheets: {df.shape[0]} строк, {df.shape[1]} колонок")
    # сразу приводим все числовые цены в float
    for col in df.columns:
        if "цена за бутылку" in col or "цена за кейс" in col:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def update_master_to_gsheets(df: pd.DataFrame):
    """Очищает лист и загружает новые данные."""
    if df is None:
        print("[ERROR] update_master_to_gsheets получил None вместо DataFrame — пропускаю обновление.")
        return  # ничего не делаем, чтобы не падать

    if not isinstance(df, pd.DataFrame):
        print(f"[ERROR] Ожидался DataFrame, но получен {type(df)} — пропускаю обновление.")
        return

    if df.empty:
        print("[WARN] Пустой DataFrame передан в update_master_to_gsheets — создаю заглушку.")
        df = pd.DataFrame({"Тип": [], "Наименование": []})  # минимальный placeholder



    ws = _get_worksheet()

    # нормализация значений (например, даты → строки)
    df_clean = df.copy()
    for col in df_clean.columns:
        if pd.api.types.is_datetime64_any_dtype(df_clean[col]):
            df_clean[col] = df_clean[col].astype(str)

    ws.clear()
    ws.update([df_clean.columns.tolist()] + df_clean.fillna("").values.tolist())
    print(f"[OK] Обновил Google Sheet: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")
