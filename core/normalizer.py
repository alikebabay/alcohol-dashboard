from __future__ import annotations
import re
import pandas as pd
from typing import Dict, List, Optional, Tuple

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
    s = s.replace("\xa0", "").replace(" ", "").replace(",", ".")
    s = re.sub(r"[^0-9\.\-]", "", s)
    if s in ("", "-", ".", "-.", ".-"):
        return None
    try:
        return float(s)
    except Exception:
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
    r"bottles_per_case",
    r"^\s*bt\s*/?\s*cs\s*$",
    r"bt.?/?cs", r"btl.?/?case",
    r"\bbottles?\b", r"bottl.?/case",
    r"шт.*[/ ]*кор", r"шт.*в.*кор", r"шт.*в.*ящ",
    r"pcs.*[/ ]*case", r"qty.*case",
    r"size(?!.*price)",   # исключаем Price/Size
    r"规格"
]

PRICE_CASE_PATS = [
    r"(?:price|цена).*(?:case|cs|ctn|carton)",
    r"(?:usd|eur|\$|€)\s*(?:/|per)?\s*(?:case|cs|ctn|carton)",
    r"usd.?/?cs", r"eur.?/?cs",
    r"\b\$\s*/?\s*cs\b", r"\b€\s*/?\s*cs\b"
]

AVAILABILITY_PATS = [
    r"stock", r"lead\s*time", r"availability", r"status", r"eta", 
    r"ready", r"t1", r"t2", r"tbo", r"доступ", r"наличи"
]

LOCATION_PATS = [
    r"wareh", r"склад", r"origin", r"отгруз", r"exw", r"dap", r"fob", r"cif", r"место\s*загруз"
]



def normalize_alcohol_df(df_in: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Optional[str]]]:
    """
    Нормализует DataFrame с произвольными заголовками.
    Возвращает:
      - нормализованный DataFrame со столбцами:
        ['name', 'bottles_per_case', 'price_per_case', 'price_per_bottle']
      - mapping: какие исходные колонки были использованы.
    """

    print(f"\n[DEBUG normalizer] входной DataFrame shape={df_in.shape}")
    print(f"[DEBUG normalizer] входные колонки: {list(df_in.columns)}")


    df = df_in.copy()

    # --- поиск колонок ---
    name_cols  = _find_cols(df, NAME_PATS)
    price_cols = _find_cols(df, PRICE_CASE_PATS)
    bpc_cols   = [c for c in _find_cols(df, BOTTLES_PER_CASE_PATS) if c not in price_cols]
    avail_cols = _find_cols(df, AVAILABILITY_PATS)
    loc_cols   = _find_cols(df, LOCATION_PATS)

    mapping = {
        "name": name_cols,
        "bottles_per_case": bpc_cols,
        "price_per_case": price_cols,
        "price_per_bottle": "calculated",
    }


    #тестовый код
    print(f"[DEBUG normalizer] распознанные колонки:")
    for k, v in mapping.items():
        print(f"   {k:<20} → {v}")
    #тестовый код

    out = pd.DataFrame()

    # --- Наименование ---
    if name_cols:
        tmp = df[name_cols].bfill(axis=1)
        out["name"] = tmp.iloc[:, 0].astype(str).str.strip()
    else:
        out["name"] = None

    # --- Кол-во бутылок в кейсе ---
    if bpc_cols:
        tmp = df[bpc_cols].bfill(axis=1)
        col0 = tmp.columns[0]
        header_norm = _clean_header(col0)
        looks_like_size = bool(re.search(r"size|规格", header_norm)) or \
            tmp.iloc[:, 0].astype(str).str.contains(r"\d\s*[x×]\s*\d", case=False, na=False).any()
        if looks_like_size:
            out["bottles_per_case"] = tmp.iloc[:, 0].map(_cases_from_size_text)
        else:
            out["bottles_per_case"] = tmp.iloc[:, 0].map(_to_number)
    else:
        out["bottles_per_case"] = None

    # --- Цена за кейс ---
    if price_cols:
        tmp = df[price_cols].bfill(axis=1)
        out["price_per_case"] = tmp.iloc[:, 0].map(_to_number)
    else:
        out["price_per_case"] = None

    # --- Расчёт цены за бутылку ---
    out["price_per_bottle"] = out["price_per_case"] / out["bottles_per_case"]
    out["price_per_bottle"] = pd.to_numeric(out["price_per_bottle"], errors="coerce").round(4)

    # --- доступность и место загрузки ---
    if avail_cols:
        tmp = df[avail_cols].bfill(axis=1)
        if tmp.shape[1] > 1:
        # склеиваем доступность и T1/T2
            out["access"] = tmp.iloc[:,0].astype(str).str.strip() + " (" + tmp.iloc[:,1].astype(str).str.strip() + ")"
        else:
            out["access"] = tmp.iloc[:,0].astype(str).str.strip()
    else:
        out["access"] = None

    if loc_cols:
        tmp = df[loc_cols].bfill(axis=1)
        out["location"] = tmp.iloc[:, 0].astype(str).str.strip()
    else:
        out["location"] = None

    # --- Очистка пустых строк ---
    if name_cols:
        out = out[~out["name"].fillna("").str.strip().eq("")].reset_index(drop=True)

    print(f"[DEBUG normalizer] выходной shape={out.shape}")
    print(f"[DEBUG normalizer] пример нормализованных данных:\n{out.head(3)}\n")

    return out, mapping
