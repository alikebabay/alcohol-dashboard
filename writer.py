
from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from gsheets_integration import load_master_from_gsheets, update_master_to_gsheets
import os

import pandas as pd

# --- создание матрицы ------------------------------------------------------------

def merge_with_master(old: pd.DataFrame, new: pd.DataFrame, supplier: str) -> pd.DataFrame:
    """
    Сливает новые данные по поставщику с существующим master.xlsx.
    - Ключ для совпадения: Наименование + шт / кор
    - Если колонок для этого поставщика нет → добавляем
    - Если цена изменилась → обновляем
    - Если строка новая → добавляем
    """
    # добавляем колонки для текущего поставщика, если их нет
    for col in [f"цена за бутылку {supplier}"]:
        if col not in old.columns:
            old[col] = None

    updated, inserted = 0, 0

    for i, row in new.iterrows():
        

        name = row["Наименование"]
        bpc = row["шт / кор"]
        

        # поддержка старого и нового формата
        price_case = row.get("price_per_case")
        price_bottle = row.get("price_per_bottle")
        
        if price_case is None and price_bottle is None:
            col_case = f"цена за кейс {supplier}"
            col_bottle = f"цена за бутылку {supplier}"
            price_case = row.get(col_case)
            price_bottle = row.get(col_bottle)

        

        mask = (old["Наименование"] == name) & (old["шт / кор"] == bpc)
        if mask.any():
            # обновляем только если цена отличается
            if pd.notna(price_case):
                old_price = old.loc[mask, f"цена за кейс {supplier}"].values[0]
                if pd.isna(old_price) or old_price != price_case:
                    old.loc[mask, f"цена за кейс {supplier}"] = price_case
                    updated += 1
            if pd.notna(price_bottle):
                old_price_b = old.loc[mask, f"цена за бутылку {supplier}"].values[0]
                if pd.isna(old_price_b) or old_price_b != price_bottle:
                    old.loc[mask, f"цена за бутылку {supplier}"] = price_bottle
                    updated += 1
        else:
            # новой строки ещё нет → добавляем
            old = pd.concat([old, pd.DataFrame([row])], ignore_index=True)
            inserted += 1

    
    return old


# --- сохранение ------------------------------------------------------------

def save_to_excel(df: pd.DataFrame, supplier: str) -> pd.DataFrame:
    """
    Приводит DataFrame к фиксированным 10 колонкам.
    На выходе всегда 10 фиксированных колонок:
      Тип | Доступ | Наименование | cl | шт / кор | Место загрузки | Поставщик 1 | Поставщик 2 | Поставщик 3 | Поставщик 4
    Заполняются только Наименование, cl, шт / кор и цена.
    Остальные пока пустые.
    """
    column_map = {
        "name": "Наименование",
        "bottles_per_case": "шт / кор", 
        "cl": "cl",
        "Тип": "Тип",
    }

    base_cols = [
        "Тип",
        "Доступ",
        "Наименование",
        "cl",
        "шт / кор",
        "Место загрузки",
    ]
    
    df_out = pd.DataFrame(index=range(len(df)), columns=base_cols)

    # добавляем колонку с ценой за бутылку
    if "price_per_bottle" in df.columns:
        df_out[f"цена за бутылку {supplier}"] = df["price_per_bottle"]

    # переносим найденные данные
    for raw_col, target_col in column_map.items():
        if raw_col in df.columns:
            df_out[target_col] = df[raw_col]

    return df_out



