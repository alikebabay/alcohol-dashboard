#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

import re
import pandas as pd
from typing import Optional
import importlib
import logging

from libraries.regular_expressions import CL, RX_PACK_CASES_FLEX, RX_PACK_PCS, RX_ABV, RX_AGE, RX_VINTAGE
from libraries.regular_expressions import RX_BOTTLE, RX_CASE, RX_BPC, RX_BPC_TRIPLE
from utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


CATEGORY_LEX = {
    'vodka','gin','rum','tequila','whisky','whiskies','whiskey',
    'bourbon','cognac','brandy','liqueur','champagne','champagnes',
    'wines','wine','spirits','spirits/liquors','sparkling wines'
}


def _normalize_token(s: str) -> str:
    s = str(s or "").lower()
    s = s.replace("×", "x").replace("х", "x")  # кириллица → латиница
    s = s.replace("л", "l")
    s = re.sub(r"[%@]", " ", s)                # убираем % и @
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def _normalize_text(s: str) -> str:
    s = str(s or "").strip().lower()
    s = s.replace("\n", " ").replace("\r", " ")
    s = re.sub(r"\s+", " ", s)
    s = s.replace("ё", "е")
    return s

def _cl_from_text(text) -> Optional[float]:
     if not text: return None
     s = str(text).lower().replace('\xa0',' ')
     m = CL.CASE.search(s)
     if not m:
         m = re.search(r'(\d{1,4}(?:[.,]\d{1,2})?)\s*(ml|cl|l)\b', s)
     if not m:
         return None
     val = float(m.group(1 if m.re is not CL.CASE else 2).replace(',', '.'))
     unit = m.group(2 if m.re is not CL.CASE else 3)
     if unit == 'ml': return round(val / 10, 2)   # 750ml -> 75.0
     if unit == 'l':  return round(val * 100, 2)  # 1l -> 100.0
     return val                                     # cl

def _strip_casevol_tokens(s: str) -> str:
     if not isinstance(s, str): s = str(s or '')
     s = CL.CASE.sub('', s)
     s = CL.VOL.sub('', s)
     s = re.sub(r'\s{2,}', ' ', s).strip(' -,—–')
     return s

def _remove_volume_tokens(name: str) -> str:
    if not isinstance(name, str):
        return name
    # убираем кейс+объём: 6x75cl, 12x1L, 120x5cl
    s = CL.CASE.sub("", name)
    # убираем одиночные объёмы: 75cl, 1L, 200ml
    s = CL.VOL.sub("", s)
    return re.sub(r"\s{2,}", " ", s).strip(" -")


def extract_volume_smart(row: pd.Series, df_raw: pd.DataFrame | None = None) -> float | str | None:
    """
    Пытается вытащить объём (cl/ml/l) из разных полей строки:
    1. name / Наименование / Description
    2. Size / 规格 / Size/规格
    3. (если не найдено) ищет в других колонках
    """
    possible_fields = ["name", "Наименование", "Size", "规格", "Description", "Item"]
    

    # 1️⃣ Перебираем колонки текущей строки
    for col in row.index:
        col_name = str(col).lower()
        for key in possible_fields:
            if key.lower() in col_name:
                cell_val = row[col]
                if isinstance(cell_val, str):
                    
                    val = _extract_volume(cell_val)
                    if val:
                        
                        return val

    # 2️⃣ fallback — если есть df_raw и индекс совпадает
    if df_raw is not None and row.name in df_raw.index:
        for col in df_raw.columns:
            cell_val = df_raw.at[row.name, col]
            if isinstance(cell_val, str):
                val = _extract_volume(cell_val)
                if val:
                    
                    return val

    return None




def _extract_volume(text: str):
    if not isinstance(text, str):
        return None
    s = text.lower().replace('\xa0',' ')
    # 0) NEW: "6/70/40" → volume is middle value (cl)
    m0 = CL.SLASH.search(s)
    if m0:
        return float(m0.group(1))   # already in cl
    
    # 1) классика: 6x70cl, 12x1l — unit обязателен
    m = CL.CASE.search(s)
    if m:
        val = float(m.group(2).replace(',', '.'))
        unit = m.group(3).lower()
        if unit == "ml": return round(val/10, 2)   # 750ml -> 75.0
        if unit == "l":  return round(val*100, 2)  # 1l -> 100.0
        return val

    # 2) особый случай: две 'x' и есть '%': 6x100x15% → берём второе число как объём (в cl)
    m2 = CL.CASE_ABV.search(s)
    if m2:
        return float(m2.group(1).replace(',', '.'))

    # 3) одиночные форматы: 75cl / 1l / 50ml
    m = CL.VOL.search(s)
    if not m:
        return None
    val_unit = m.group(0).replace(" ", "").lower()
    return val_unit   # ("75cl", "1l", "50ml")

def _infer_bpc_from_name(text: str) -> float | None:
    """Пытаемся понять bottles_per_case из строки (включая кривые форматы 6x70clx40%)."""
    if not text:
        return None
    s = _normalize_token(text)
    logger.debug(f"[BPC] raw='{text}' | normalized='{s}'")

    m = RX_PACK_CASES_FLEX.search(s) or RX_PACK_PCS.search(s)
    if m:
        cases = float(m.group("cases"))   
        logger.debug(f"[BPC] matched primary regex: '{m.group(0)}' → cases={cases}")     
        return cases

    # fallback — ищем просто N x число
    m = re.search(r'(?i)\b(?P<cases>\d{1,2})\s*[x×]\s*\d+', s)
    if m:
        cases = float(m.group("cases"))
        logger.debug(f"[BPC] matched fallback regex: '{m.group(0)}' → cases={cases}")
        return cases    
    # 👇 новый fallback — формат с тире, например "— 6 —" или "- 12 -"
    m = re.search(r'(?i)[—\-–]\s*(?P<cases>\d{1,2})\s*[—\-–]', s)
    if m:
        cases = float(m.group("cases"))
        logger.debug(f"[BPC] matched dash-style fallback: '{m.group(0)}' → cases={cases}")
        return cases
    
    # 🔹 fallback через FSM (лениво)
    logger.debug("[BPC] trying FSM fallback...")

    try:
        import importlib
        fsm_module = importlib.import_module("state_machine")
        fsm_cls = getattr(fsm_module, "AlcoholStateMachine", None)
        fsm = fsm_cls.get_active() if fsm_cls else None
    except Exception as e:
        logger.debug(f"[BPC] FSM import failed: {e}")
        fsm = None

    if not fsm:
        logger.debug("[BPC] FSM not active → skip fallback")
        return None

    if getattr(fsm, "df_raw", None) is None:
        logger.debug("[BPC] FSM has no df_raw → skip fallback")
        return None

    logger.debug(f"[BPC] FSM active, scanning df_raw ({len(fsm.df_raw)} rows)...")

    for _, row in fsm.df_raw.iterrows():
        row_str = " ".join(map(str, row.values))
        m2 = RX_PACK_CASES_FLEX.search(row_str) or RX_PACK_PCS.search(row_str)
        if m2:
            cases = float(m2.group("cases"))
            logger.debug(f"[BPC] extracted {cases} from df_raw row: '{row_str[:80]}...'")
            return cases

    logger.debug("[BPC] no pattern matched in df_raw → None")
    return None

def looks_like_category(name: str, row: pd.Series | None = None) -> bool:
    """Эвристика: категория, а не продукт"""
    if not name:
        return False
    s = _normalize_text(str(name))
    
    if s in CATEGORY_LEX:
        return True
    
    # если мало слов, нет цифр и в строке вообще пустые цены — тоже категория
    if row is not None:
        if pd.isna(row.get("price_per_case")) and pd.isna(row.get("bottles_per_case")):
            if len(s) <= 30 and len(s.split()) <= 4 and not re.search(r'\d', s):
                return True
    return False


#helper function for location and access

def looks_like_product(s: str) -> bool:
        # Используем ТВОИ рантайм-выражения из text_extractors.py
        if RX_BPC.search(s):
            return True
        # NEW: triple pattern 6/70/40, 6/70/43
        if RX_BPC_TRIPLE.search(s):
            return True
        if any(rx.search(s) for rx in RX_BOTTLE):
            return True
        if any(rx.search(s) for rx in RX_CASE):
            return True
        return False