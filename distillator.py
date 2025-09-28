#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

import re
import pandas as pd
from typing import Optional


# --- регексы для признаков продукта ---
# ловит 50ml / 75cl / 1L / 37.5cl и т.п. (без жесткой границы слева)
_RX_VOLUME   = re.compile(r'(?i)(\d{1,4}(?:[.,]\d{1,2})?\s?(?:ml|cl|l))\b')
# NxVol (12x75cl, 06x1L, 120x5cl)
_RX_CASEVOL = re.compile(r'(?i)\b(\d{1,3})\s*[x×]\s*(\d{1,4}(?:[.,]\d{1,2})?)\s*(ml|cl|l)\b')
RX_ABV      = re.compile(r'(?i)\b\d{1,2}(?:[.,]\d)?\s?%(\s*abv)?\b')
RX_AGE      = re.compile(r'(?i)\b(\d{1,2})\s?(yo|years?|лет)\b')
RX_VINTAGE  = re.compile(r'\b(19\d{2}|20(0\d|1\d|2[0-6]))\b')

CATEGORY_LEX = {
    'vodka','gin','rum','tequila','whisky','whiskies','whiskey',
    'bourbon','cognac','brandy','liqueur','champagne','champagnes',
    'wines','wine','spirits','spirits/liquors','sparkling wines'
}

# извлечение количества бутылок из паттернов вида 6x75cl, 12x0.7l, 24x200ml
RX_PACK_CASES = re.compile(r'(?i)\b(?P<cases>\d{1,2})\s*[x×]\s*\d{2,4}\s?(?:ml|cl|l)\b')

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
    s = _RX_VOLUME.sub("", s)
    return re.sub(r"\s{2,}", " ", s).strip(" -")

def _extract_volume(text: str):
    if not isinstance(text, str):
        return None
    s = text.lower().replace('\xa0',' ')
    # сначала ищем форматы 12x75cl, 6x1l и т.п.
    m = _RX_CASEVOL.search(s)
    if m:
        val, unit = m.group(2), m.group(3).lower()
    else:
        m = _RX_VOLUME.search(s)
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
    """Пытаемся понять bottles_per_case из названия (6x75cl, 12x0.7L, 24x200ml)."""
    if not text:
        return None
    m = RX_PACK_CASES.search(text)
    if m:
        try:
            return float(m.group("cases"))
        except Exception:
            return None
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


def filter_and_enrich(df: pd.DataFrame, col_name: str = "name") -> pd.DataFrame:
    """
    - убирает строки с категориями
    - добавляет колонку 'volume' (если найден в тексте)
    - аппендит volume к name (например: 'Macallan 12' -> 'Macallan 12 (700ml)')
    """
    if col_name not in df.columns:
        return df

    df = df.copy()

    # убираем категории
    mask_cat = df.apply(lambda r: looks_like_category(r[col_name], r), axis=1)
    removed = df[mask_cat]
    if not removed.empty:
        
        for val in removed[col_name].dropna().unique():
            print(f"   - {val!r}")

    df = df[~mask_cat].reset_index(drop=True)

    # вытащим cl (объем) в отдельную колонку
    df["cl"] = df[col_name].map(_extract_volume)

    # удаляем cl-часть из названия (все токены)
    df[col_name] = df[col_name].map(_remove_volume_tokens)

    # ---- ДОзаполнение и чистка числовых полей ----
    # 1) если bottles_per_case пусто, пробуем вытащить из названия (6x75cl → 6)
    if "bottles_per_case" in df.columns:
        bpc_before_na = int(df["bottles_per_case"].isna().sum())
        if bpc_before_na:
            df["bottles_per_case"] = df.apply(
                lambda r: r["bottles_per_case"] if pd.notna(r["bottles_per_case"]) else _infer_bpc_from_name(r[col_name]),
                axis=1
            )
            bpc_filled = bpc_before_na - int(df["bottles_per_case"].isna().sum())
            if bpc_filled:
                print(f"[DEBUG distillator] дозаполнено bottles_per_case из названия: {bpc_filled}")

    # 2) приведение к числам
    if "price_per_case" in df.columns:
        df["price_per_case"] = pd.to_numeric(df["price_per_case"], errors="coerce")
    if "bottles_per_case" in df.columns:
        df["bottles_per_case"] = pd.to_numeric(df["bottles_per_case"], errors="coerce")

    # 3) отбрасываем только строки где НЕТ цены (qty может быть NaN)
    if "price_per_case" in df.columns:
        mask_invalid = df["price_per_case"].isna()
        drop_cnt = int(mask_invalid.sum())
        if drop_cnt:
            print(f"[DEBUG distillator] удалено без цены: {drop_cnt} (примеры: {df.loc[mask_invalid, col_name].head(5).tolist()})")
        df = df[~mask_invalid].reset_index(drop=True)

    # 4) убираем дубли по (name, bottles_per_case)
    if {"name","bottles_per_case"}.issubset(df.columns):
        before = len(df)
        df = df.drop_duplicates(subset=["name","bottles_per_case"], keep="last")
        removed_dups = before - len(df)
        if removed_dups:
            print(f"[DEBUG distillator] удалено дублей: {removed_dups}")
    return df
