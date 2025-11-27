# enricher.py
import pandas as pd
import logging
import re

from libraries.distillator import looks_like_category, _remove_volume_tokens, extract_volume_smart, _infer_bpc_from_name
from utils.verifier import verifier
from utils.abbreviations_helper import convert_abbreviation
from libraries.regular_expressions import RX_GBX_MARKER, RX_GBX_NEGATIVE
from core.volume_detector import detect_volume_column, normalize_volume_num_to_cl
from core.gbx_detector import detect_gbx


logger = logging.getLogger(__name__)

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
    Очистка колонки name от лишних данных, использование данных для создания новых колонок
    - убирает строки с категориями
    - добавляет колонку 'volume' (если найден в тексте)    
    - добавляет колонку 'GBX' (если найден в тексте)    
    """
    
    if col_name not in df.columns:
        return df

    df = df.copy()    

    # убираем категории
    mask_cat = df.apply(lambda r: looks_like_category(r[col_name], r), axis=1)
    removed = df[mask_cat]
    if not removed.empty:
        for val in removed[col_name].dropna().unique():
            logger.debug(f"   - {val!r}")

    # --- 🔧 синхронное удаление категорий ---
    removed_idx = df[mask_cat].index
    if not removed_idx.empty:
        logger.debug(f"[SYNC DROP] removing {len(removed_idx)} category rows from both df and df_raw")
        df = df.drop(removed_idx, errors="ignore")
        if df_raw is not None:
            df_raw = df_raw.drop(removed_idx, errors="ignore")

    # теперь индексы снова полностью совпадают
    df = df.reset_index(drop=True)
    if df_raw is not None:
        df_raw = df_raw.reset_index(drop=True)
        logger.debug(f"[SYNC CHECK] df={len(df)}, df_raw={len(df_raw)} (aligned indices)")


    logger.debug("[VOLUME] Starting extract_volume_smart pass...")
    # Логируем первые 5 строк name перед поиском
    try:
        logger.debug(
            "[VOLUME] PRE-NAME HEAD:\n" +
            df[col_name].head(5).to_string()
        )
    except:
        pass
    # вытащим cl (объем) в отдельную колонку, поиск по нейме и другим колонкам    
    df["cl"] = df.apply(lambda r: extract_volume_smart(r, df_raw=df_raw), axis=1)
    # логируем первые 5 результатов
    logger.debug("[VOLUME] extract_volume_smart results (first 5 rows):\n" + df["cl"].head(5).astype(str).to_string())

    
    # детектор цифровых отдельно стоящих колонок cl
    if df["cl"].isna().all():
        logger.debug("[VOLUME] All cl values NaN → entering numeric detector (SEARCH IN df_raw!)")

        # ---- ВАЖНО: ищем volume-колонку ТОЛЬКО В df_raw ----
        volcol = detect_volume_column(df_raw)
        logger.debug(f"[VOLUME] detect_volume_column(df_raw) returned column index: {volcol!r}")

        if isinstance(volcol, int):
            logger.debug(f"[VOLUME] numeric detector accepted raw column index {volcol}, preview head:")
            logger.debug(df_raw.iloc[:, volcol].head(5).to_string())

            # нормализуем по сырым данным
            df["cl"] = df_raw.iloc[:, volcol].map(normalize_volume_num_to_cl)
            logger.debug(f"[VOLUME] mapped df_raw column #{volcol} → cl")
        else:
            logger.debug("[VOLUME] NO numeric volume column found in df_raw")

    # удаляем cl-часть из названия (все токены)
    df[col_name] = df[col_name].map(_remove_volume_tokens)

    # --- GBX DETECTION (row-wise, index-preserving) ---
    if df_raw is None:
        logger.error("[GBX] df_raw is None — cannot detect GBX reliably")
        gbx_df = pd.DataFrame({"gb_flag": [False]*len(df), "gb_type": [None]*len(df)})
    else:
        gbx_df = detect_gbx(df_raw)


    df["gb_flag"] = gbx_df["gb_flag"].values
    df["gb_type"] = gbx_df["gb_type"].values

    # дополнительно чистим от лишних слов и хвостов
    df[col_name] = df[col_name].map(_clean_name_extras)

    df[col_name] = df[col_name].map(convert_abbreviation)
    logger.debug("normalize_alcohol_df: применяется convert_abbreviation к наименованиям")
    # --- запуск верифаера с графовым состоянием ---    
    verifier.set_state("graph")
    df = verifier.run(df)
    print(verifier.report())

    #reattach GB/GBX to names after graph
    mask_gb = df["gb_flag"]
    if mask_gb.any():
        logger.debug(f"[GBX] reattaching GB/GBX suffix to {mask_gb.sum()} items")
        df.loc[mask_gb, col_name] = df.loc[mask_gb].apply(
            lambda r: f"{r[col_name]} {r['gb_type']}",
            axis=1
        )

    # ---- Дозаполнение и чистка числовых полей ----
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
            logger.debug(f"[DEBUG distillator] удалено без цены: {drop_cnt} (примеры: {df.loc[mask_invalid, col_name].head(5).tolist()})")
        df = df[~mask_invalid].reset_index(drop=True)
    return df
