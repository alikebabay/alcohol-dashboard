# ============================================================
#   VOLUME DETECTOR MODULE
#   Detects headless numeric volume column (ml/cl)
#   Activates ONLY if text-based extraction is absent.
# ============================================================

import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Allowed pure bottle volumes (ml + cl)
VOLUME_KNOWN = {
    20, 25, 30, 35, 50,
    100, 150, 187, 200, 250, 275, 300, 330, 350, 375, 500,
    550, 600, 700, 720, 750, 1000,
    1500, 1750, 2000, 2250, 3000, 4500, 6000,
    12000, 15000, 18000,
}


# ------------------------------------------------------------
# Normalization: convert numeric volume to centiliters
# ------------------------------------------------------------
def normalize_volume_num_to_cl(v):
    """
    Convert numeric volume to CL.
    Assumptions:
        • ml: integers >=100 → ml/10
        • cl: integers 10–100 → stay as cl
    We do NOT parse liters or floats here — handled by extract_volume_smart.
    """
    if pd.isna(v):
        return None

    try:
        v = float(v)
    except Exception:
        return None

    # ml → cl
    if v >= 100 and v.is_integer():
        return v / 10.0

    # cl → cl
    if 10 <= v <= 100 and v.is_integer():
        return v

    return None


# ------------------------------------------------------------
# Check if a series looks like a numeric volume column
# ------------------------------------------------------------
def is_volume_numeric_series(s: pd.Series) -> bool:
    """
    Heuristic detection of numeric-only volume column.
    No strings. No ml/cl/l. Only headless numbers.
    """
    s_num = pd.to_numeric(s, errors="coerce").dropna()
    if s_num.empty:
        logger.debug("[VOLUME_DETECTOR] reject: empty or no numeric values")
        return False

    # 1) Almost all values must be integer-like
    non_int_ratio = (s_num % 1 != 0).mean()
    if non_int_ratio > 0.05:
        logger.debug(f"[VOLUME_DETECTOR] reject: not integer-like (non_int_ratio={non_int_ratio:.3f})")
        return False

    s_int = s_num.astype(int)

    # 2) Divisible by 5
    not_div5_ratio = ((s_int % 5) != 0).mean()
    if not_div5_ratio > 0.05:
        logger.debug(f"[VOLUME_DETECTOR] reject: not divisible by 5 (ratio={not_div5_ratio:.3f})")
        return False

    # 3) Low entropy (volumes repeat)
    nunique = s_int.nunique()
    if nunique > 25:
        logger.debug(f"[VOLUME_DETECTOR] reject: too many unique values (nunique={nunique})")
        return False

    # 4) Reasonable ranges
    vmax = s_int.max()
    if vmax < 20:
        logger.debug(f"[VOLUME_DETECTOR] reject: max < 20 (max={vmax})")
        return False

    # 5) Match known clusters or ml→cl conversion
    good = 0
    total = len(s_int)

    for v in s_int:
        if v in VOLUME_KNOWN:
            good += 1
            continue
        if v >= 100 and (v // 10) in VOLUME_KNOWN:
            good += 1
            continue

    ratio = good / total
    if ratio < 0.90:
        logger.debug(f"[VOLUME_DETECTOR] reject: cluster match too low (good={good}, total={total}, ratio={ratio:.3f})")
        return False

    logger.debug(f"[VOLUME_DETECTOR] accept: series looks like volume (n={total}, nunique={nunique}, max={vmax})")
    return True


# ------------------------------------------------------------
# Auto-detect numeric volume column
# ------------------------------------------------------------
def detect_volume_column(df: pd.DataFrame) -> str | None:
    """
    Find a numeric-only volume column in a headless table.
    Returns column INDEX (0-based) or None if no volume detected.
    """

    blacklist = {
        "bottles_per_case", "price_per_case", "price_per_bottle",
        "cl", "gb_flag", "gb_type", "access", "location",
    }

    logger.debug("[VOLUME_DETECTOR] Starting column scan, columns=%s", list(df.columns))

    best = None
    best_idx = None
    best_uniques = 9999

    for idx, col in enumerate(df.columns):
        if col in blacklist:
            logger.debug(f"[VOLUME_DETECTOR] skip blacklisted column: {col!r}")
            continue

        # берём КОНКРЕТНУЮ физическую колонку, даже если имя дублируется
        s_raw = df.iloc[:, idx]

        try:
            sample = s_raw.head(5).astype(str).tolist()
            logger.debug(f"[VOLUME_DETECTOR] checking column #{idx} {col!r}, head={sample}")
        except Exception as e:
            logger.debug(f"[VOLUME_DETECTOR] cannot read column #{idx} {col!r}: {e}")
            continue

        s = pd.to_numeric(s_raw, errors="coerce")
        if is_volume_numeric_series(s):
            uniq = s.nunique()
            logger.debug(f"[VOLUME_DETECTOR] column #{idx} {col!r} PASSED numeric checks (nunique={uniq})")
            if uniq < best_uniques:
                best = col
                best_uniques = uniq
                best_idx = idx
        else:
            logger.debug(f"[VOLUME_DETECTOR] column #{idx} {col!r} rejected by is_volume_numeric_series")


    if best_idx is not None:
        logger.debug(
            f"[VOLUME_DETECTOR] numeric volume column detected: {best!r} "
            f"(index={best_idx}, nunique={best_uniques})"
        )
    else:
        logger.debug("[VOLUME_DETECTOR] no numeric volume column detected")

    return best_idx
