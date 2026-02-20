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



def filter_and_enrich(df: pd.DataFrame, col_name: str = "name", df_raw: pd.DataFrame | None = None, df_gbx: pd.DataFrame| None = None) -> pd.DataFrame:

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

    # --- GBX DETECTION (unified: text + excel) ---
    # --- ensure raw_idx exists ---
    # --- ensure raw_idx exists ---
    if df_gbx is not None and "raw_idx" not in df_gbx.columns:
        logger.debug("[GBX] raw_idx missing → creating from index")
        df_gbx = df_gbx.copy()
        df_gbx["raw_idx"] = df_gbx.index

    if df_gbx is None:
        logger.error("[GBX] df_gbx is None — cannot detect GBX reliably")
        gbx_df = pd.DataFrame({
            "raw_idx": df.get("raw_idx", pd.Series(dtype=int)),
            "gb_flag": [False] * len(df),
            "gb_type": [None] * len(df),
        })
    else:
        alive_raw_idx = None

        if "raw_idx" in df.columns:
            alive_raw_idx = set(df["raw_idx"].dropna().astype(int))
            logger.debug(
                "[GBX] alive_raw_idx sample: %s",
                list(sorted(alive_raw_idx))[:10]
            )

        gbx_df = detect_gbx(
            df_gbx=df_gbx,
            alive_raw_idx=alive_raw_idx,
        )

    logger.debug("=== DF (before GBX assign) ===")
    logger.debug("DF columns: %s", df.columns.tolist())
    logger.debug("DF head(2):\n%s", df.head(2).to_string())
    logger.debug("DF index: %s", df.index.tolist())

    logger.debug("=== GBX_DF ===")
    logger.debug("GBX columns: %s", gbx_df.columns.tolist())
    logger.debug("GBX head(2):\n%s", gbx_df.head(2).to_string())
    logger.debug("GBX index: %s", gbx_df.index.tolist())


    logger.debug(
        "GBX DF before merge:\n%s",
        gbx_df.head(5).to_string()
    )

    logger.debug("GBX DF before merge:\n%s", gbx_df.head(5).to_string())

    # --- merge GBX safely ---
    if "raw_idx" in df.columns and "raw_idx" in gbx_df.columns:
        df = df.merge(
            gbx_df[["raw_idx", "gb_flag", "gb_type"]],
            on="raw_idx",
            how="left"
        )
    else:
        logger.debug("[GBX] raw_idx missing → positional merge")
        df["gb_flag"] = gbx_df.get("gb_flag", pd.Series([False]*len(df)))
        df["gb_type"] = gbx_df.get("gb_type", pd.Series([None]*len(df)))


    df["gb_flag"] = df["gb_flag"].fillna(False)
    df["gb_type"] = df["gb_type"].where(df["gb_flag"], None)

    if "raw_idx" in df.columns:
        logger.debug(
            "\n=== WORKING DF (raw_idx + name) ===\n%s",
            df[["raw_idx", col_name]]
                .sort_values("raw_idx")
                .to_string(index=False)
        )
    else:
        logger.debug(
            "\n=== WORKING DF (name only) ===\n%s",
            df[[col_name]].to_string(index=False)
        )


    df[col_name] = df[col_name].map(convert_abbreviation)
    logger.debug("normalize_alcohol_df: применяется convert_abbreviation к наименованиям")
    # --- запуск верифаера с графовым состоянием ---  
    logger.debug("BEFORE VERIFIER:\n%s", df[["name","gb_flag","gb_type"]])
  
    verifier.set_state("graph")
    df = verifier.run(df)
    print(verifier.report())
    logger.debug("AFTER VERIFIER:\n%s", df[["name","gb_flag","gb_type"]])

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
