# enricher.py
import pandas as pd
from core.distillator import looks_like_category, _remove_volume_tokens, extract_volume_smart, _infer_bpc_from_name
from utils.verifier import verifier

import re

def _clean_name_extras(s: str) -> str:
    """
    Очищает поле 'name' от всего, что не относится к названию товара.
    Убирает:
      - логистику (FTL, EXW, DAP, lead time, on floor и т.п.)
      - валюты и цены (eur, usd, per bottle/case, price)
      - упаковку и статусы (cases, bottles, coded, GBX, NRF, etc.)
    """
    if not isinstance(s, str):
        return s

    original = s
    s = s.strip()

    # убираем FTL., EXW. и всё после @
    s = re.sub(r'^(FTL\.?|EXW\.?)\s*', '', s, flags=re.I)
    s = re.sub(r'@.*', '', s)

    # убираем служебные и торговые маркеры
    s = re.sub(
        r'\b(?:coded?|gbx|nogbx|nrf|rf|ftl|exw|dap|loendersloot|riga|niderland|deposit|confirm|'
        r'lead\s*time|on\s*floor|price|per\s*bottle|per\s*case|eur|usd|\$|€|t\d|weeks?|days?|cases?|bottles?)\b',
        '',
        s,
        flags=re.I,
    )

    # чистим дублирующиеся запятые и пробелы
    s = re.sub(r'[,\s]+', ' ', s).strip()
    s = re.sub(r'\s{2,}', ' ', s)

    

    return s


def filter_and_enrich(df: pd.DataFrame, col_name: str = "name", df_raw: pd.DataFrame | None = None) -> pd.DataFrame:

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

    # вытащим cl (объем) в отдельную колонку, поиск по нейме и другим колонкам
    
    df["cl"] = df.apply(lambda r: extract_volume_smart(r, df_raw=df_raw), axis=1)

   # удаляем cl-часть из названия (все токены)
    df[col_name] = df[col_name].map(_remove_volume_tokens)
    # дополнительно чистим от лишних слов и хвостов
    df[col_name] = df[col_name].map(_clean_name_extras)



    # --- запуск верифаера с графовым состоянием ---    
    verifier.set_state("graph")
    df = verifier.run(df)
    print(verifier.report())

    # ---- ДОзаполнение и чистка числовых полей ----
    if "bottles_per_case" in df.columns:
        bpc_before_na = int(df["bottles_per_case"].isna().sum())
        if bpc_before_na:
            df["bottles_per_case"] = df.apply(
                lambda r: r["bottles_per_case"] if pd.notna(r["bottles_per_case"]) else _infer_bpc_from_name(r[col_name]),
                axis=1
            )
            bpc_filled = bpc_before_na - int(df["bottles_per_case"].isna().sum())
           

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
    return df
