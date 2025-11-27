# core/bpc_detector.py
from typing import Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)

BPC_KNOWN = {
    1, 2, 3, 4, 5, 6,
    8, 9, 10, 11, 12,
    15, 20, 24, 25,
    30, 36, 48, 60,
}

def parse_bpc_loose(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass

    s = str(v).lower().strip()
    if not s:
        return None

    s = s.replace("\xa0", " ")
    s = " ".join(s.split())
    snorm = s.replace("×", "x").replace("/", "x").replace(" ", "")

    # integer-like
    try:
        f = float(s)
        if abs(f - round(f)) < 1e-9:
            n = int(round(f))
            if 1 <= n <= 200:
                return n
    except Exception:
        pass

    # NxM / NxMcl
    if "x" in snorm:
        left = snorm.split("x", 1)[0]
        if left.isdigit():
            n = int(left)
            if 1 <= n <= 200:
                return n

    return None


def is_bpc_series(series: pd.Series) -> bool:
    total = 0
    parsed = []

    for v in series:
        total += 1
        n = parse_bpc_loose(v)
        if n is not None:
            parsed.append(n)

    if total == 0:
        return False

    ratio = len(parsed) / total
    if ratio < 0.7:
        logger.debug(f"[BPC_DETECTOR] reject: ratio too low ({ratio:.3f})")
        return False

    uniq = len(set(parsed))
    if uniq > 20:
        logger.debug(f"[BPC_DETECTOR] reject: too many unique values (nuniq={uniq})")
        return False

    mn = min(parsed)
    mx = max(parsed)
    if mn < 1 or mx > 200:
        logger.debug(f"[BPC_DETECTOR] reject: out of range (min={mn}, max={mx})")
        return False

    logger.debug(
        f"[BPC_DETECTOR] accept: ratio={ratio:.3f}, unique={uniq}, min={mn}, max={mx}"
    )
    return True


def detect_bpc_column(df: pd.DataFrame) -> Optional[int]:
    """
    Возвращает ИНДЕКС колонки (0-based), которая похожа на BPC.
    Работает по физическим колонкам, а не по именам.
    """
    best_idx = None
    best_uniq = 9999

    for idx in range(df.shape[1]):
        col = df.columns[idx]
        series = df.iloc[:, idx]
        try:
            head = series.head(5).astype(str).tolist()
            logger.debug(f"[BPC_DETECTOR] checking col #{idx} {col!r}, head={head}")
        except Exception:
            continue

        if is_bpc_series(series):
            uniq = len(set(filter(lambda x: x is not None,
                                  (parse_bpc_loose(v) for v in series))))
            logger.debug(f"[BPC_DETECTOR] column #{idx} {col!r} → candidate (uniq={uniq})")
            if uniq < best_uniq:
                best_uniq = uniq
                best_idx = idx
        else:
            logger.debug(f"[BPC_DETECTOR] column #{idx} {col!r} rejected")

    if best_idx is not None:
        logger.debug(f"[BPC_DETECTOR] final choice: index={best_idx}, name={df.columns[best_idx]!r}")
    else:
        logger.debug("[BPC_DETECTOR] no BPC column detected")

    return best_idx
