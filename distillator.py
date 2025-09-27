#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

import re
import pandas as pd

# --- регексы для признаков продукта ---
RX_VOLUME   = re.compile(r'(?i)\b(\d{2,4}\s?ml|\d{2}\s?cl|\d(?:[.,]\d)?\s?l)\b')
RX_ABV      = re.compile(r'(?i)\b\d{1,2}(?:[.,]\d)?\s?%(\s*abv)?\b')
RX_AGE      = re.compile(r'(?i)\b(\d{1,2})\s?(yo|years?|лет)\b')
RX_VINTAGE  = re.compile(r'\b(19\d{2}|20(0\d|1\d|2[0-6]))\b')

CATEGORY_LEX = {
    'vodka','gin','rum','tequila','whisky','whiskies','whiskey',
    'bourbon','cognac','brandy','liqueur','champagne','champagnes',
    'wines','wine','spirits','spirits/liquors','sparkling wines'
}


def _extract_volume(text: str) -> str | None:
    """Ищет объём (ml/cl/l) и возвращает строкой"""
    if not text:
        return None
    m = RX_VOLUME.search(text)
    if m:
        return m.group(0).replace(" ", "")
    return None

def _normalize_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    # убрать неразрывные пробелы, табы и т.п.
    s = s.replace("\xa0", " ").replace("\u200b", "")  
    # убрать все не-буквенно-цифровые символы с краёв
    s = re.sub(r"^\W+|\W+$", "", s)
    # схлопнуть пробелы
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


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
        print(f"[DEBUG distillator] вырезано категорий: {len(removed)}")
        for val in removed[col_name].dropna().unique():
            print(f"   - {val!r}")

    df = df[~mask_cat].reset_index(drop=True)

    # создаём колонку volume
    df["volume"] = df[col_name].map(_extract_volume)

    # добавляем volume к названию, если нашли
    df[col_name] = df.apply(
        lambda row: f"{row[col_name]} ({row['volume']})" if pd.notna(row["volume"]) else row[col_name],
        axis=1
    )

    return df
