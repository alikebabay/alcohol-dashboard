
from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

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

def _find_cols(df: pd.DataFrame, patterns: List[str]) -> List[str]:
    """Вернёт все колонки, подходящие под паттерны (нормализованный хедер)."""
    norm_cols = {col: _clean_header(col) for col in df.columns}
    out = []
    for col, norm in norm_cols.items():
        if any(re.search(pat, norm) for pat in patterns):
            out.append(col)
    return out

_RX_CASES_FROM_SIZE = re.compile(r'(?i)\b(\d{1,3})\s*[x×]\s*\d')
def _cases_from_size_text(x) -> Optional[float]:
    if pd.isna(x):
        return None
    m = _RX_CASES_FROM_SIZE.search(str(x))
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return None
    return _to_number(x)


# --- ядро нормализации -----------------------------------------------------

NAME_PATS = [
    r"^name", r"^наимен", r"^descr", r"описан", r"товар", r"product", r"бренд|марка"
]

BOTTLES_PER_CASE_PATS = [
    r"^\s*bt\s*/?\s*cs\s*$",          # точное совпадение Bt/Cs
    r"bt.?/?cs", r"btl.?/?case",
    r"\bbottles?\b", r"bottl.?/case",  # ← только bottles
    r"шт.*[/ ]*кор", r"шт.*в.*кор", r"шт.*в.*ящ",
    r"pcs.*[/ ]*case", r"qty.*case",
    r"size(?!.*price)",   # ← исключаем Price/Size
    r"规格"
]

PRICE_CASE_PATS = [
    r"(?:price|цена).*(?:case|cs|ctn|carton)",                 # явно цена за кейс
    r"(?:usd|eur|\$|€)\s*(?:/|per)?\s*(?:case|cs|ctn|carton)", # валюта + кейс
    r"usd.?/?cs", r"eur.?/?cs",                                # явные варианты
    r"\b\$\s*/?\s*cs\b", r"\b€\s*/?\s*cs\b"
    # ВАЖНО: без голого '/cs', чтобы не ловить 'Bt/Cs'
]

#последний этап поиска колонок
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

    # ищем ВСЕ подходящие колонки и берём "первую непустую" по строке
    name_cols  = _find_cols(df, NAME_PATS)
    price_cols = _find_cols(df, PRICE_CASE_PATS)
    bpc_cols   = [c for c in _find_cols(df, BOTTLES_PER_CASE_PATS) if c not in price_cols]
    

    mapping = {
        "name": name_cols,
        "bottles_per_case": bpc_cols,
        "price_per_case": price_cols,
        "price_per_bottle": "calculated",
    }

    # собираем нормализованные данные
    out = pd.DataFrame()

    if name_cols:
        tmp = df[name_cols].bfill(axis=1)
        out["name"] = tmp.iloc[:, 0].astype(str).str.strip()
    else:
        out["name"] = None  # поле допустимо отсутствующим

    if bpc_cols:
        tmp = df[bpc_cols].bfill(axis=1)
        # если хоть один из найденных хедеров похож на Size/规格 или значения содержат Nx...
        col0 = tmp.columns[0]
        header_norm = _clean_header(col0)
        looks_like_size = bool(re.search(r"size|规格", header_norm)) or \
            tmp.iloc[:,0].astype(str).str.contains(r"\d\s*[x×]\s*\d", case=False, na=False).any()
        if looks_like_size:
            out["bottles_per_case"] = tmp.iloc[:,0].map(_cases_from_size_text)
        else:
            out["bottles_per_case"] = tmp.iloc[:,0].map(_to_number)
    else:
         out["bottles_per_case"] = None

    if price_cols:
        tmp = df[price_cols].bfill(axis=1)
        out["price_per_case"] = tmp.iloc[:,0].map(_to_number)
    else:
        out["price_per_case"] = None

    out["price_per_bottle"] = out["price_per_case"] / out["bottles_per_case"]
    # преобразуем к числу (оставляем NaN, если не парсится)
    out["price_per_bottle"] = pd.to_numeric(out["price_per_bottle"], errors="coerce")

    # теперь можно безопасно округлить
    out["price_per_bottle"] = out["price_per_bottle"].round(4)

    # уберём полностью пустые строки (если в исходнике были групповые заголовки и т.п.)
    if name_cols:
        out = out[~out["name"].fillna("").str.strip().eq("")].reset_index(drop=True)

    return out, mapping

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
    for col in [f"цена за кейс {supplier}", f"цена за бутылку {supplier}"]:
        if col not in old.columns:
            old[col] = None

    updated, inserted = 0, 0

    for i, row in new.iterrows():
        print(f"\n[DEBUG merge_with_master] row {i}:")
        print(row.to_dict())
        print(f"[DEBUG] row.keys() = {list(row.index)}")

        name = row["Наименование"]
        bpc = row["шт / кор"]
        print(f"[DEBUG] name={name}, bpc={bpc}")

        # поддержка старого и нового формата
        price_case = row.get("price_per_case")
        price_bottle = row.get("price_per_bottle")
        
        if price_case is None and price_bottle is None:
            col_case = f"цена за кейс {supplier}"
            col_bottle = f"цена за бутылку {supplier}"
            price_case = row.get(col_case)
            price_bottle = row.get(col_bottle)

        print(f"[DEBUG] price_case={price_case}, price_bottle={price_bottle}")

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

    print(f"[DEBUG merge_with_master] updated={updated}, inserted={inserted}")
    return old


# --- сохранение ------------------------------------------------------------

def save_to_excel(df: pd.DataFrame, filename: str) -> Path:
    """
    Сохраняет DataFrame в Excel.
    На выходе всегда 10 фиксированных колонок:
      Тип | Доступ | Наименование | cl | шт / кор | Место загрузки | Поставщик 1 | Поставщик 2 | Поставщик 3 | Поставщик 4
    Заполняются только Наименование, cl, шт / кор и цена.
    Остальные пока пустые.
    """
    print("[DEBUG save_to_excel] первые цены:")
    print(df[["name", "bottles_per_case", "price_per_case", "price_per_bottle"]].head(10))

    # соответствие сырых колонок -> наши поля
    column_map = {
        "name": "Наименование",
        "bottles_per_case": "шт / кор", 
        "cl": "cl", # уже должна быть в df 
        # добавили:
        "Тип": "Тип",          
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
    
    # формируем шаблон на количество строк во входном df (с непрерывным индексом)
    df_out = pd.DataFrame(index=range(len(df)), columns=base_cols)
    # имя поставщика из имени входного файла
    supplier = Path(filename).stem
    
    # добавляем колонку с ценой за кейс
    if "price_per_case" in df.columns:
        df_out[f"цена за кейс {supplier}"] = df["price_per_case"]

    # добавляем колонку с ценой за бутылку
    if "price_per_bottle" in df.columns:
        df_out[f"цена за бутылку {supplier}"] = df["price_per_bottle"]


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
        df_final = merge_with_master(old, df_out, supplier)
    else:
        df_final = df_out

    df_final.to_excel(path, index=False, engine="openpyxl")

    print(f"[OK] Master обновлён: {path}, добавлено {path} строк, всего {df_final.shape[0]}")
    print("[DEBUG save_to_excel] первые 10 наименований:",
      df_out["Наименование"].head(10).tolist())
    return path, df_final


