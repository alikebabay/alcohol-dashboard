
from __future__ import annotations
import pandas as pd
import logging

from state_machine import AlcoholStateMachine
from integrations.fingerprint_utils import add_offer_metadata
from utils.logger import setup_logging

# активируем общий логгер (matrix_debug.txt)
setup_logging()
logger = logging.getLogger(__name__)


def detect_currency(df_raw: pd.DataFrame) -> str:
    if df_raw is None or df_raw.empty:
        return ""

    # объединяем текст и заголовки
    text = " ".join(
        list(df_raw.columns.astype(str)) +
        list(df_raw.astype(str).fillna("").values.ravel())
    ).lower()

    for cur in ["eur", "€", "usd", "$", "₸", "kzt", "rub", "₽"]:
        if cur in text:
            if cur in ["eur", "€"]:
                return "EUR"
            if cur in ["usd", "$"]:
                return "USD"
            if cur in ["₸", "kzt"]:
                return "KZT"
            if cur in ["rub", "₽"]:
                return "RUB"
    return ""

  


# --- сохранение ------------------------------------------------------------

def save_to_excel(df: pd.DataFrame, supplier: str) -> pd.DataFrame:
    """
    Фиксируем базовые колонки товара, а цены/доступ/место — в колонках конкретного поставщика.
    Формат:
      Тип | Наименование | cl | шт / кор |
      цена за бутылку {supplier} | Доступ {supplier} | Место загрузки {supplier}
    """
    # 1) базовые маппинги товара
    column_map = {
        "name": "Наименование",
        "bottles_per_case": "шт / кор",
        "cl": "cl",
        "Тип": "Тип",
    }

    base_cols = ["Тип", "Наименование", "cl", "шт / кор"]
    df_out = pd.DataFrame(index=range(len(df)), columns=base_cols)

    for raw_col, target_col in column_map.items():
        if raw_col in df.columns:
            df_out[target_col] = df[raw_col]
    
    # 💡 Добавляем колонку "Винтаж" сразу после "Наименование", если есть
    if "vintage" in df.columns:
        insert_pos = df_out.columns.get_loc("Наименование") + 1
        df_out.insert(insert_pos, "Винтаж", df["vintage"])
        logger.debug("[save_to_excel] добавлен столбец 'Винтаж' после 'Наименование'")

    # 2) поставщик-специфичные колонки
    col_price_bottle = f"цена за бутылку {supplier}"
    col_price_case   = f"цена за кейс {supplier}"   

    col_access       = f"Доступ {supplier}"
    col_location     = f"Место загрузки {supplier}"

    # цена за бутылку (из нормализатора)
    if "price_per_bottle" in df.columns:
        df_out[col_price_bottle] = df["price_per_bottle"]

    # 3) 💰 добавляем колонку валюты
    fsm = AlcoholStateMachine.get_active()
    currency = detect_currency(fsm.df_raw if fsm else None)
    df_out[f"currency {supplier}"] = currency

    df_out[f"Поставщик"] = supplier

    # цена за кейс (если вдруг уже есть в df)
    if "price_per_case" in df.columns:
        df_out[col_price_case] = df["price_per_case"]

    # доступ и место загрузки: принимаем и en/ru варианты источников
    access_src   = df.get("Доступ", df.get("access"))
    location_src = df.get("Место загрузки", df.get("location"))

    if access_src is not None:
        df_out[col_access] = access_src
    if location_src is not None:
        df_out[col_location] = location_src    

    # 3) минимальная чистка
    df_out = df_out.fillna("")

    # 4) добавляем отпечатки предложений, колонки: crc32_hash, b64 
    
    df_out = add_offer_metadata(df_out)

    return df_out



