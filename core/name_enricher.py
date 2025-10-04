# enricher.py
import pandas as pd
from core.distillator import looks_like_category, _remove_volume_tokens, _extract_volume, _infer_bpc_from_name


import re

def _clean_name_extras(s: str) -> str:
    """
    Убираем лишние токены из названия:
    - префиксы типа 'FTL.' или 'EXW.'
    - хвосты с '@ Euro ...', 'per bottle', 'per case'
    - служебные маркеры (T1, T2, weeks, on stock)
    """
    if not isinstance(s, str):
        return s
    s = re.sub(r'^(FTL\.?|EXW\.?)\s*', '', s, flags=re.I)           # убираем FTL., EXW.
    s = re.sub(r'@.*', '', s)                                        # всё после @ (цену и условия)
    s = re.sub(r'\bT[0-9]\b', '', s, flags=re.I)                     # T1, T2
    s = re.sub(r'\b\d+\s*weeks?\b', '', s, flags=re.I)               # "2 weeks"
    s = re.sub(r'\bon stock\b', '', s, flags=re.I)                   # "on stock"
    s = re.sub(r'\s+', ' ', s).strip()
    return s

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
    # дополнительно чистим от лишних слов и хвостов
    df[col_name] = df[col_name].map(_clean_name_extras)

    # ---- ДОзаполнение и чистка числовых полей ----
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

    if "price_per_case" in df.columns:
        df["price_per_case"] = pd.to_numeric(df["price_per_case"], errors="coerce")
    if "bottles_per_case" in df.columns:
        df["bottles_per_case"] = pd.to_numeric(df["bottles_per_case"], errors="coerce")

    if {"price_per_case","price_per_bottle"}.issubset(df.columns):
        mask_invalid = df["price_per_case"].isna() & df["price_per_bottle"].isna()
        drop_cnt = int(mask_invalid.sum())
        if drop_cnt:
            print(f"[DEBUG distillator] удалено без цены: {drop_cnt} (примеры: {df.loc[mask_invalid, col_name].head(5).tolist()})")
        df = df[~mask_invalid].reset_index(drop=True)

    if {"name","bottles_per_case"}.issubset(df.columns):
        before = len(df)
        df = df.drop_duplicates(subset=["name","bottles_per_case"], keep="last")
        removed_dups = before - len(df)
        if removed_dups:
            print(f"[DEBUG distillator] удалено дублей: {removed_dups}")

    return df
