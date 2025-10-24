from __future__ import annotations
import re
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging
import json


#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

logger = logging.getLogger(__name__)

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
    if out:
        logger.debug(f"_find_cols: найдено {out} по паттернам {patterns}")
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
            logger.debug(f"_cases_from_size_text: не удалось извлечь число из {x!r}")
            return None
    return _to_number(x)
    
    
        





# --- ядро нормализации -----------------------------------------------------

NAME_PATS = [
    r"^name", r"^наимен", r"^descr", r"описан", r"товар", r"product", r"бренд|марка", r"item"
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
    r"ready", r"t1", r"t2", r"tbo", r"доступ", r"наличи", r"access",
]

LOCATION_PATS = [
    r"wareh", r"склад", r"origin", r"отгруз", r"exw", r"dap", r"fob", r"cif", r"место\s*загруз", r"location", r"incoterm", r"ETA\s*Rdam",
]


class AccessLocationClassifier:
    """
    Проверяет найденные availability/location колонки по оси и шапке.
    Может создать недостающую колонку (access или location),
    и заполняет её токенами из aliases JSON.
    """

    def __init__(self, df, avail_cols, loc_cols):
        self.df = df
        self.avail_cols = avail_cols
        self.loc_cols = loc_cols

        with open("aliases/city_aliases.json", encoding="utf-8") as f:
            self.city_aliases = json.load(f)["aliases"]
        with open("aliases/incoterms_aliases.json", encoding="utf-8") as f:
            self.incoterms_aliases = json.load(f)["aliases"]

        # паттерны для анализа содержимого по вертикали
        self.rx_access = re.compile(r"\b(ready|t[12]|tbo|stock|lead\s*time|\d+\s*(?:day|week))", re.I)
        self.rx_location = re.compile(
            r"\b(" + "|".join(map(re.escape, list(self.city_aliases.keys()) + list(self.incoterms_aliases.keys()))) + r")\b",
            re.I
        )

    def _scan_down(self, col):
        s = self.df[col].astype(str).dropna().tolist()
        joined = " ".join(s[:50])
        has_access = bool(self.rx_access.search(joined))
        has_location = bool(self.rx_location.search(joined))
        return has_access, has_location

    def _check_header_for_location(self, col):
        h = str(col).lower()
        return any(k.lower() in h for k in list(self.city_aliases.keys()) + list(self.incoterms_aliases.keys()))

    def _normalize_location_cell(self, text: str, col_header: Optional[str] = None) -> Optional[str]:
        """Ищет алиасы в тексте ячейки или названии колонки и возвращает нормализованный токен."""
        # 1️⃣ проверяем содержимое ячейки
        if isinstance(text, str):
            txt = text.strip().lower()
            for k, v in {**self.city_aliases, **self.incoterms_aliases}.items():
                if k.lower() in txt:
                    return v

        # 2️⃣ fallback — проверяем заголовок колонки
        if col_header:
            hdr = str(col_header).lower()
            aliases = {k.lower(): v for k, v in {**self.city_aliases, **self.incoterms_aliases}.items()}
            for k, v in aliases.items():
                if k in hdr:
                    return v

        return None


    def _normalize_access_cell(self, text: str) -> Optional[str]:
        """Приводит доступность к токену (ready/T1/T2/TBO/lead time X days...)."""
        if not isinstance(text, str):
            return None
        t = text.strip().lower()
        if "ready" in t:
            return "READY"
        if re.search(r"\bt1\b", t):
            return "T1"
        if re.search(r"\bt2\b", t):
            return "T2"
        if "tbo" in t:
            return "TBO"
        if re.search(r"\d+\s*day", t):
            return re.findall(r"\d+\s*day", t)[0]
        if re.search(r"\d+\s*week", t):
            return re.findall(r"\d+\s*week", t)[0]
        return None

    def resolve(self):
        new_access_cols = list(self.avail_cols)
        new_loc_cols = list(self.loc_cols)

        for col in set(self.avail_cols + self.loc_cols):
            has_access, has_location = self._scan_down(col)

            # ETA-гибрид
            if has_access and has_location:
                logger.debug(f"AccessLocationClassifier: {col} содержит и доступ, и локацию → ETA-гибрид")
                self.df[f"{col}_access"] = self.df[col].map(self._normalize_access_cell)
                self.df[f"{col}_location"] = self.df[col].map(self._normalize_location_cell)
                new_access_cols.append(f"{col}_access")
                new_loc_cols.append(f"{col}_location")

            # access по содержимому + локация по header
            elif has_access and not has_location and self._check_header_for_location(col):
                logger.debug(f"AccessLocationClassifier: {col} → добавлена колонка location (по header)")
                self.df[f"{col}_location"] = self.df[col].map(
                    lambda x: self._normalize_location_cell(x, col)
                )
                new_loc_cols.append(f"{col}_location")

            # location по содержимому, добавляем access по содержимому
            elif has_location and not has_access:
                has_ready = any(re.search(self.rx_access, str(v)) for v in self.df[col].head(50))
                if has_ready:
                    logger.debug(f"AccessLocationClassifier: {col} → добавлена колонка access (по содержимому)")
                    self.df[f"{col}_access"] = self.df[col].map(self._normalize_access_cell)
                    new_access_cols.append(f"{col}_access")

        return new_access_cols, new_loc_cols

    
def normalize_alcohol_df(df_in: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Optional[str]]]:

    logger.info(f"🚀 normalize_alcohol_df: старт, shape={df_in.shape}")
    """
    Нормализует DataFrame с произвольными заголовками.
    Возвращает:
      - нормализованный DataFrame со столбцами:
        ['name', 'bottles_per_case', 'price_per_case', 'price_per_bottle']
      - mapping: какие исходные колонки были использованы.
    """

    df = df_in.copy()

    # --- поиск колонок ---
    name_cols  = _find_cols(df, NAME_PATS)
    price_cols = _find_cols(df, PRICE_CASE_PATS)
    bpc_cols   = [c for c in _find_cols(df, BOTTLES_PER_CASE_PATS) if c not in price_cols]
    avail_cols = _find_cols(df, AVAILABILITY_PATS)
    loc_cols   = _find_cols(df, LOCATION_PATS)
    price_bottle_cols = _find_cols(df, ["price_per_bottle", "цена за бутылку", "bottle price"])  # новый поиск
    

    mapping = {
        "name": name_cols,
        "bottles_per_case": bpc_cols,
        "price_per_case": price_cols,
        "price_per_bottle": price_bottle_cols or "calculated",
    }


    logger.debug(f"normalize_alcohol_df: mapping → {mapping}")
    out = pd.DataFrame()

    # --- Наименование ---
    if name_cols:        
        tmp = df[name_cols].bfill(axis=1)
        out["name"] = tmp.iloc[:, 0].astype(str).str.strip()
    else:
        out["name"] = None
        logger.warning("normalize_alcohol_df: не найдены колонки с именами товаров")

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

    # --- Цена за бутылку (из входных данных или расчетная) ---
    if price_bottle_cols:
        tmp = df[price_bottle_cols].bfill(axis=1)
        out["price_per_bottle"] = pd.to_numeric(tmp.iloc[:, 0], errors="coerce").round(4)
        
    else:
        out["price_per_bottle"] = out["price_per_case"] / out["bottles_per_case"]
        out["price_per_bottle"] = pd.to_numeric(out["price_per_bottle"], errors="coerce").round(4)

    # --- Доступность и место загрузки классификатор ---
    classifier = AccessLocationClassifier(df, avail_cols, loc_cols)
    avail_cols, loc_cols = classifier.resolve()
    
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
    
    if avail_cols:
        logger.debug(f"access заполнено из {avail_cols}")

    if loc_cols:
        tmp = df[loc_cols].bfill(axis=1)
        out["location"] = tmp.iloc[:, 0].astype(str).str.strip()
    else:
        out["location"] = None
    
    if loc_cols:
        logger.debug(f"location заполнено из {loc_cols}")

    # --- Очистка пустых строк ---
    if name_cols:
        out = out[~out["name"].fillna("").str.strip().eq("")].reset_index(drop=True)
    
    # --- Очистка пустых строк ---
    before = len(out)
    if name_cols:
        out = out[~out["name"].fillna("").str.strip().eq("")].reset_index(drop=True)
    
    logger.debug(f"normalize_alcohol_df: удалено пустых строк {before - len(out)}")
    logger.info(f"✅ normalize_alcohol_df: завершено, итог shape={out.shape}")
    return out, mapping