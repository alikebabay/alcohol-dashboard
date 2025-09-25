
from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


# --- утилиты ---------------------------------------------------------------

def _clean_header(s: str) -> str:
    s = str(s or "").strip().lower()
    s = s.replace("\n", " ").replace("\r", " ")
    s = re.sub(r"\s+", " ", s)
    s = s.replace("ё", "е")
    return s

def _to_number(x) -> Optional[float]:
    if pd.isna(x):
        return None
    s = str(x).strip()
    # убираем валюты, пробелы-разделители, нечисловые символы
    s = s.replace("\xa0", "").replace(" ", "")
    s = s.replace(",", ".")
    s = re.sub(r"[^0-9\.\-]", "", s)
    if s in ("", "-", ".", "-.", ".-"):
        return None
    try:
        return float(s)
    except Exception:
        return None

def _find_col(df: pd.DataFrame, patterns: List[str]) -> Optional[str]:
    """
    Возвращает имя первой подходящей колонки (по списку regex-паттернов) или None.
    Поиск идёт по нормализованным заголовкам.
    """
    norm_cols = {col: _clean_header(col) for col in df.columns}
    for col, norm in norm_cols.items():
        for pat in patterns:
            if re.search(pat, norm):
                return col
    return None


# --- ядро нормализации -----------------------------------------------------

NAME_PATS = [
    r"^name", r"^наимен", r"^descr", r"описан", r"товар", r"product", r"бренд|марка"
]

BOTTLES_PER_CASE_PATS = [
    r"bt.?/?cs", r"btl.?/?case", r"bottl.*case",
    r"шт.*[/ ]*кор", r"шт.*в.*кор", r"шт.*в.*ящ",
    r"pcs.*[/ ]*case", r"qty.*case", r"per.*case"
]

PRICE_CASE_PATS = [
    r"usd.?/?cs", r"eur.?/?cs", r"€.?/?cs", r"\$.?/?cs",
    r"price.*case", r"цена.*кейс", r"цена.?/?кейс", r"$/case", r"usd.*per.*case"
]


def normalize_alcohol_df(
    df_in: pd.DataFrame,
) -> Tuple[pd.DataFrame, Dict[str, Optional[str]]]:
    """
    Принимает исходный DataFrame с произвольными заголовками.
    Возвращает:
      - нормализованный DataFrame со столбцами:
        ['name', 'bottles_per_case', 'cases', 'price_per_case', 'price_per_bottle']
      - mapping: какие исходные колонки были использованы.
    Отсутствующие поля допускаются (заполняются None).
    """
    # работаем с копией
    df = df_in.copy()

    # ищем колонки
    col_name  = _find_col(df, NAME_PATS)
    col_bpc   = _find_col(df, BOTTLES_PER_CASE_PATS)
    col_price = _find_col(df, PRICE_CASE_PATS)

    mapping = {
        "name": col_name,
        "bottles_per_case": col_bpc,
        "price_per_case": col_price,
        "price_per_bottle": "calculated",
    }

    # собираем нормализованные данные
    out = pd.DataFrame()

    if col_name:
        out["name"] = df[col_name].astype(str).str.strip()
    else:
        out["name"] = None  # поле допустимо отсутствующим

    if col_bpc:
        out["bottles_per_case"] = df[col_bpc].map(_to_number)
    else:
        out["bottles_per_case"] = None

    if col_price:
        out["price_per_case"] = df[col_price].map(_to_number)
    else:
        out["price_per_case"] = None

    out["price_per_bottle"] = out["price_per_case"] / out["bottles_per_case"]
    out["price_per_bottle"] = out["price_per_bottle"].where(~pd.isna(out["price_per_bottle"]))
    out["price_per_bottle"] = out["price_per_bottle"].round(4)

    # уберём полностью пустые строки (если в исходнике были групповые заголовки и т.п.)
    if col_name:
        out = out[~out["name"].fillna("").str.strip().eq("")].reset_index(drop=True)

    return out, mapping


# --- сохранение ------------------------------------------------------------

def save_to_excel(df: pd.DataFrame, filename: str) -> Path:
    """
    Сохраняет DataFrame в Excel.
    На выходе всегда 10 фиксированных колонок:
      Тип | Доступ | Наименование | cl | шт / кор | Место загрузки | Поставщик 1 | Поставщик 2 | Поставщик 3 | Поставщик 4
    Заполняются только Наименование, cl, шт / кор и цена.
    Остальные пока пустые.
    """

    # соответствие сырых колонок -> наши поля
    column_map = {
        "Description": "Наименование",
        "Bt/Cs": "шт / кор",            
    }

    # базовый шаблон с пустыми колонками
    base_cols = [
        "Тип",
        "Доступ",
        "Наименование",
        "cl",
        "шт / кор",
        "Место загрузки",
    ]
    # формируем шаблон на количество строк во входном df
    df_out = pd.DataFrame(index=df.index, columns=base_cols)
    # имя поставщика из имени входного файла
    supplier = Path(filename).stem
    price_col = f"цена {supplier}"

    # добавляем колонку с ценой за бутылку
    if "price_per_bottle" in df.columns:
        df_out[price_col] = df["price_per_bottle"]


    # переносим из сырых данных только то, что нашли
    for raw_col, target_col in column_map.items():
        if raw_col in df.columns:
            df_out[target_col] = df[raw_col]

    out_dir = Path("processed")
    out_dir.mkdir(exist_ok=True)
    path = out_dir / "master.xlsx"

    # считаем, сколько строк пришло на вход
    added_rows = len(df_out)

    # если файл уже есть → читаем и добавляем новые строки вниз
    if path.exists():
        old = pd.read_excel(path)
        df_out = pd.concat([old, df_out], ignore_index=True)

    df_out.to_excel(path, index=False, engine="openpyxl")

    print(f"[OK] Master обновлён: {path}, добавлено {added_rows} строк, всего {df_out.shape[0]}")
    return path