# integrations/graph_to_sheets.py
import pandas as pd
import logging
import gspread
from gspread_dataframe import set_with_dataframe

from config import driver, MODE
from config import get_gsheets_credentials


# ID таблицы (из URL Google Sheets)
if MODE == "prod":
    SPREADSHEET_ID = "1dISLvKdfi5DCTeYlQ5JXiBcyusrIlJkmikDvkWAcg60"
    SHEET_NAME = "master"   # имя листа в таблице
else:
    SPREADSHEET_ID = "1Dyr2Uz3GLQ_cM4ZZVUMTV0GhHw9vbLdrq518NOVqOh4"
    SHEET_NAME = "master_test"


# ─────────────────────────────
# 🧠 Настройка логгирования
# ─────────────────────────────
logging.basicConfig(
    filename="graph_to_sheets.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)



# ==========================================================
# 📊 Google Sheets creds (через config)
# ==========================================================
creds = get_gsheets_credentials()
gc = gspread.authorize(creds)
logger.info(f"[Google Sheets] Authorized via {'Vault' if MODE == 'prod' else 'local credentials'} mode")

# ─────────────────────────────
# 📊 Функции
# ─────────────────────────────

def get_all_offers() -> pd.DataFrame:
    """Извлекает все офферы из графа (включая все supplier-специфичные поля)."""
    with driver.session() as session:
        records = session.run("""
        MATCH (s:Supplier)-[:HAS_OFFER]->(o:Offer)
        RETURN s.name AS supplier, properties(o) AS props
        """).data()

    if not records:
        logger.warning("⚠️ Нет офферов в графе.")
        return pd.DataFrame()

    rows = []
    for rec in records:
        supplier = rec["supplier"]
        props = rec["props"]
        row = {"supplier": supplier}
        row.update(props)
        rows.append(row)

    df = pd.DataFrame(rows)
    logger.info(f"✅ Загружено {df.shape[0]} офферов из Neo4j.")
    return df


def make_master_sheet(df: pd.DataFrame, max_pairs: int = 12) -> pd.DataFrame:
    """
    Собирает мастер-структуру:
      Тип | Наименование | cl | шт / кор | ключ_1 | значение_1 | ... | ключ_N | значение_N
    Пары строятся из динамических полей (цены, доступ, место, валюта, поставщик и т.д.).
    """
    if df.empty:
        logger.warning("⚠️ Пустой DataFrame, нечего собирать.")
        return pd.DataFrame()

    # Базовые колонки (как в мастере)
    BASE = ["Тип", "Наименование", "cl", "шт / кор"]

    # Нормализация ключей — сводим supplier-специфику к «общим» именам
    def norm_key(col: str) -> str:
        c = str(col)
        # цена
        if c.startswith("цена за бутылку"):
            return "цена за бутылку"
        if c.startswith("цена за кейс"):
            return "цена за кейс"
        # доступ / место
        if c.startswith("Доступ"):
            return "Доступ"
        if c.startswith("Место загрузки") or c.startswith("location"):
            return "Место загрузки"
        # валюта
        if c.startswith("Валюта") or c.startswith("currency"):
            return "Валюта"
        # техполя (если решишь не включать — просто не возвращай)
        if c == "crc32_hash":
            return "crc32_hash"
        if c == "b64":
            return "b64"
        if c == "date_int":
            return "date_int"
        # по умолчанию — оставляем как есть
        return c

    # Приоритет вывода пар (как в MatrixMerger было по key_aliases)
    key_order = [
        "Поставщик",
        "цена за бутылку",
        "цена за кейс",
        "Валюта",
        "Место загрузки",
        "Доступ",
        "crc32_hash", "b64", "date_int",
    ]
    order_index = {k: i for i, k in enumerate(key_order)}

    # Готовим выходную таблицу
    out_cols = BASE + [x for i in range(1, max_pairs+1) for x in (f"ключ_{i}", f"значение_{i}")]
    out = []

    # Обеспечим совместимость имён колонок в df
    # шт / кор в исходном df лежит как "шт_кор" у нас в графе — учтём оба варианта
    def get_val(row, name):
        if name == "шт / кор":
            return row.get("шт / кор", row.get("шт_кор", ""))
        return row.get(name, "")

    for row in df.fillna("").to_dict(orient="records"):
        base = {
            "Тип": get_val(row, "Тип"),
            "Наименование": get_val(row, "Наименование"),
            "cl": get_val(row, "cl"),
            "шт / кор": get_val(row, "шт / кор"),
        }

        # Собираем пары. Всегда пишем «Поставщик/{имя}» из row['supplier'] если есть.
        pairs = []
        supplier_name = str(row.get("supplier", "")).strip()
        if supplier_name:
            pairs.append(("Поставщик", supplier_name))

        for col, val in row.items():            
            # пропускаем базовые и техполя, а также уже существующий "Поставщик"
            if col in BASE or col in ["supplier", "Поставщик", "шт_кор", "crc32_hash", "b64", "date_int"]:
                continue
            if val in ("", None):
                continue
            k = norm_key(col)
            # добавляем только поля, которые относятся к значениям (цены, доступ, место, валюта)
            if any(k.startswith(prefix) for prefix in [
                "цена за бутылку", "цена за кейс", "Доступ", "Место загрузки", "Валюта", "Поставщик"
            ]):
                pairs.append((k, str(val)))

        # стабильный порядок пар: сначала по key_order, потом лексикографически
        pairs.sort(key=lambda kv: (order_index.get(kv[0], 999), kv[0]))

        # Укладываем пары в фиксированные ячейки
        row_out = dict(base)
        for i in range(1, max_pairs+1):
            if i <= len(pairs):
                key, val = pairs[i-1]
                row_out[f"ключ_{i}"] = key
                row_out[f"значение_{i}"] = val
            else:
                row_out[f"ключ_{i}"] = None
                row_out[f"значение_{i}"] = None

        out.append(row_out)

    df_master = pd.DataFrame(out, columns=out_cols)
    # Сортируем по бизнес-колонкам
    df_master = df_master.sort_values(by=["Тип", "Наименование", "cl", "шт / кор"], kind="mergesort")
    return df_master


def upload_to_gsheets(df: pd.DataFrame):
    """Безопасная загрузка в Google Sheets: очищает диапазон данных, не ломая таблицу (оптимизировано для 10k+ строк)."""
    if df.empty:
        logger.warning("⚠️ DataFrame пуст, загрузка в Sheets пропущена.")
        return

    try:
        sh = gc.open_by_key(SPREADSHEET_ID)
        try:
            ws = sh.worksheet(SHEET_NAME)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=SHEET_NAME, rows="2000", cols="50")

        # ───────────────────────────────────────────────
        # 1️⃣ Безопасная очистка только диапазона данных
        # ───────────────────────────────────────────────
        try:
            ws.batch_clear(["A2:ZZ"])  # не трогаем заголовки
            logger.info("[Google Sheets] Data range cleared (A2:ZZ).")
        except Exception as e:
            logger.warning(f"[WARN] batch_clear failed: {e}")

        # ───────────────────────────────────────────────
        # 2️⃣ Автоматически расширяем лист под объём df
        # ───────────────────────────────────────────────
        n_rows, n_cols = df.shape
        target_rows = n_rows + 10     # небольшой буфер
        target_cols = n_cols + 2      # и справа немного места
        try:
            ws.resize(rows=target_rows, cols=target_cols)
            logger.info(f"[Google Sheets] Resized to {target_rows} rows × {target_cols} cols.")
        except Exception as e:
            logger.warning(f"[WARN] resize failed: {e}")

        # ───────────────────────────────────────────────
        # 3️⃣ Основная загрузка
        # ───────────────────────────────────────────────
        set_with_dataframe(ws, df, include_index=False, resize=False)
        logger.info(f"✅ Данные успешно загружены в Google Sheets → {SHEET_NAME} ({n_rows} строк).")

    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке в Google Sheets: {repr(e)}")
        raise



# ─────────────────────────────
# 🚀 Запуск
# ─────────────────────────────
if __name__ == "__main__":
    df_all = get_all_offers()
    master_view = make_master_sheet(df_all, max_pairs=12)
    upload_to_gsheets(master_view)
    print(f"✅ Готово! Загружено {len(master_view)} строк в лист '{SHEET_NAME}' Google Sheets")
