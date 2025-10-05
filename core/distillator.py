#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

import re
import pandas as pd
from typing import Optional


# --- регексы для признаков продукта ---
# Объём вида 50ml, 75cl, 1L, 37.5cl
# Теперь после ml|cl|l может быть конец строки, пробел, запятая, %, или буква x
RX_VOLUME = re.compile(
    r'(?i)(\d{1,4}(?:[.,]\d{1,2})?\s?(?:ml|cl|l))(?:\b|(?=[x%]))'
)
# NxVol (12x75cl, 06x1L, 120x5cl) — разрешаем слепленные варианты
_RX_CASEVOL = re.compile(
    r'(?i)\b(\d{1,3})\s*[x×]\s*(\d{1,4}(?:[.,]\d{1,2})?)\s*(ml|cl|l)(?:\b|(?=[x%]))'
)
# ABV: 40%, 46.3%, можно слепленные (70clx40%)
RX_ABV = re.compile(
    r'(?i)\b(\d{1,2}(?:[.,]\d)?)\s?%(?:\s*abv)?'
)
RX_AGE      = re.compile(r'(?i)\b(\d{1,2})\s?(yo|years?|лет)\b')
RX_VINTAGE  = re.compile(r'\b(19\d{2}|20(0\d|1\d|2[0-6]))\b')

CATEGORY_LEX = {
    'vodka','gin','rum','tequila','whisky','whiskies','whiskey',
    'bourbon','cognac','brandy','liqueur','champagne','champagnes',
    'wines','wine','spirits','spirits/liquors','sparkling wines'
}

# извлечение количества бутылок из паттернов вида 6x75cl, 12x0.7l, 24x200ml
RX_PACK_CASES_FLEX = re.compile(
    r'(?i)\b(?P<cases>\d{1,2})\s*[x×]\s*\d{1,4}(?:[.,]\d{1,2})?\s?(?:ml|cl|l)'
)


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
     m = _RX_CASEVOL.search(s)
     if not m:
         m = re.search(r'(\d{1,4}(?:[.,]\d{1,2})?)\s*(ml|cl|l)\b', s)
     if not m:
         return None
     val = float(m.group(1 if m.re is not _RX_CASEVOL else 2).replace(',', '.'))
     unit = m.group(2 if m.re is not _RX_CASEVOL else 3)
     if unit == 'ml': return round(val / 10, 2)   # 750ml -> 75.0
     if unit == 'l':  return round(val * 100, 2)  # 1l -> 100.0
     return val                                     # cl

def _strip_casevol_tokens(s: str) -> str:
     if not isinstance(s, str): s = str(s or '')
     s = _RX_CASEVOL.sub('', s)
     s = RX_VOLUME.sub('', s)
     s = re.sub(r'\s{2,}', ' ', s).strip(' -,—–')
     return s

def _remove_volume_tokens(name: str) -> str:
    if not isinstance(name, str):
        return name
    # убираем кейс+объём: 6x75cl, 12x1L, 120x5cl
    s = _RX_CASEVOL.sub("", name)
    # убираем одиночные объёмы: 75cl, 1L, 200ml
    s = RX_VOLUME.sub("", s)
    return re.sub(r"\s{2,}", " ", s).strip(" -")


def extract_volume_smart(row: pd.Series, df_raw: pd.DataFrame | None = None) -> float | str | None:
    """
    Пытается вытащить объём (cl/ml/l) из разных полей строки:
    1. name / Наименование
    2. Size / Size/规格 / 规格
    3. (если не найдено) ищет в исходном df_raw
    """
    possible_fields = ["name", "Наименование", "Size", "Size/规格", "规格"]

    # основной цикл
    for field in possible_fields:
        if field in row and isinstance(row[field], str):
            val = _extract_volume(row[field])
            if val:
                print(f"[DEBUG smart_volume] found in '{field}': {val}")
                return val

    # fallback — поиск в сыром df_raw
    if df_raw is not None:
        for col in df_raw.columns:
            joined_text = " ".join(df_raw[col].astype(str).tolist())
            val = _extract_volume(joined_text)
            if val:
                print(f"[DEBUG smart_volume] fallback match in df_raw[{col}]: {val}")
                return val

    return None



def _extract_volume(text: str):
    if not isinstance(text, str):
        return None
    s = text.lower().replace('\xa0',' ')
    # сначала ищем форматы 12x75cl, 6x1l и т.п.
    m = _RX_CASEVOL.search(s)
    if m:
        val, unit = m.group(2), m.group(3).lower()
    else:
        m = RX_VOLUME.search(s)
        if not m:
            return None
        # здесь m.group(1) = "75cl", надо разнести
        val_unit = m.group(0).replace(" ", "").lower()
        return val_unit   # ← сразу возвращаем как строку ("75cl", "1l", "50ml")

    # нормализуем в cl
    val = float(val.replace(',', '.'))
    if unit == "ml": return round(val/10, 2)   # 750ml -> 75.0
    if unit == "l":  return round(val*100, 2)  # 1l -> 100.0
    return val

def _infer_bpc_from_name(text: str) -> float | None:
    """Пытаемся понять bottles_per_case из строки (включая кривые форматы 6x70clx40%)."""
    if not text:
        return None
    s = _normalize_token(text)

    m = RX_PACK_CASES_FLEX.search(s)
    if m:
        cases = float(m.group("cases"))
        print(f"[DEBUG bpc] flex match in '{s}' → {cases}")
        return cases

    # fallback — ищем просто N x число
    m = re.search(r'(?i)\b(?P<cases>\d{1,2})\s*[x×]\s*\d+', s)
    if m:
        cases = float(m.group("cases"))
        print(f"[DEBUG bpc] loose match in '{s}' → {cases}")
        return cases

    print(f"[DEBUG bpc] no match in '{s}'")
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

