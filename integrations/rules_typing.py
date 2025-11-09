import pandas as pd
import numpy as np
import logging
from utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def enforce_base_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    base_types = {
        "Тип": "string",
        "Наименование": "string",
        "cl": "string",
        "шт / кор": "Int64",
    }
    tech_types = {
        "Поставщик": "string",
        "date_int": "Int64",
        "crc32_hash": "string",
        "b64": "string",
    }
    logger.debug(f"[COLUMNS] incoming columns: {list(df.columns)}")
    logger.debug(f"[CHECK] df.head(2):\n{df.head(2).to_string(index=False)}")


    # 👇 ADD THIS LINE HERE
    logger.debug(f"[FLOAT TEST] columns starting with 'price_': {[c for c in df.columns if c.startswith('price_')]}")

    float_cols = [
        c for c in df.columns
        if c.startswith(("цена за бутылку", "цена за кейс", "price_per_bottle", "price_per_case"))
    ]
    logger.debug(f"[FLOAT] candidate float_cols={float_cols}")    

    str_cols   = [c for c in df.columns if c.startswith("Доступ") or c.startswith("Место загрузки")]
    currency_cols = [c for c in df.columns if c.startswith("currency ")]

    # ---------------- БАЗОВЫЕ ТИПЫ ----------------
    for col, dtype in {**base_types, **tech_types}.items():
        if col not in df.columns:
            continue
        try:
            before_shape = df.shape
            logger.debug(f"[CONVERT] {col}: trying to {dtype} (before shape={before_shape})")

            if dtype == "Int64":
                df[col] = (
                    df[col]
                    .replace(["", " ", "-"], pd.NA)
                    .pipe(pd.to_numeric, errors="coerce")
                    .astype("Int64")
                )
            else:
                df[col] = df[col].astype("string")

            after_shape = df.shape
            n_inf = np.isinf(df[col].astype(float, errors="ignore")).sum() if df[col].dtype != "string" else 0
            n_nan = df[col].isna().sum()
            logger.debug(f"[OK] {col}: {dtype}, shape={after_shape}, NaN={n_nan}, inf={n_inf}")

        except Exception as e:
            logger.warning(f"[WARN] {col}: cannot convert to {dtype} ({e})")

    logger.debug(f"[FLOAT] candidate float_cols={float_cols}")
    logger.debug(f"[FLOAT] proceeding with columns={float_cols or 'none found'} for df shape={df.shape}")
    logger.debug(f"[DTYPE CHECK] current dtypes:\n{df.dtypes}")


    # ---------------- FLOAT КОЛОНКИ ----------------
    for col in float_cols:
        try:
            logger.debug(f"[FLOAT] starting {col}, dtype={df[col].dtype}, sample={list(df[col].head(5))}")        
            before = df[col].copy()
            # 👇 normalize locale commas/spaces before parsing
            df[col] = (
                df[col]
                .astype("string")
                .str.replace(",", ".", regex=False)
                .str.replace(" ", "", regex=False)
                .replace(["", "-", "None"], pd.NA)
                .pipe(pd.to_numeric, errors="coerce")
                .astype("float64")
            )
            logger.debug(f"[FLOAT] {col}: after to_numeric sample={list(df[col].dropna().head(5))}")
            inf_mask = np.isinf(df[col])
            if inf_mask.any():
                logger.warning(f"[INF] {col}: contains {inf_mask.sum()} inf values → replaced with NaN")
                df.loc[inf_mask, col] = np.nan
            logger.debug(f"[FLOAT] {col}: converted ok, NaN={df[col].isna().sum()}")
        except Exception as e:
            logger.warning(f"[WARN] {col}: cannot convert to float ({e})")

    # ---------------- STRING КОЛОНКИ ----------------
    for col_group, label in [(str_cols, "str_cols"), (currency_cols, "currency_cols")]:
        for col in col_group:
            try:
                df[col] = df[col].astype("string")
                logger.debug(f"[STR] {label}: {col} → ok")
            except Exception as e:
                logger.warning(f"[WARN] {label} {col}: cannot convert to string ({e})")

    # ---------------- ФИНАЛ ----------------
    dtype_groups = {
        "float": [c for c, t in df.dtypes.items() if "float" in str(t)],
        "int":   [c for c, t in df.dtypes.items() if "int" in str(t)],
        "str":   [c for c, t in df.dtypes.items() if "string" in str(t) or "object" in str(t)],
    }
    logger.info(
        f"[TYPE] enforced: float→{dtype_groups['float']}, int→{dtype_groups['int']}, str→{dtype_groups['str']}"
    )
    logger.debug(f"[FINAL] shape={df.shape}, memory={df.memory_usage(deep=True).sum()/1024:.1f} KB")

    return df
