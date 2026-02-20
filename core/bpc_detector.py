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
    Возвращает ИНДЕКС физической колонки (0-based),
    которая похожа на BPC.
    Игнорирует технические колонки.
    """

    best_idx = None
    best_score = -1

    for idx, col in enumerate(df.columns):

        # 🔒 ignore technical columns
        if str(col).lower() in {"raw_idx"}:
            logger.debug(f"[BPC_DETECTOR] skip technical col {col!r}")
            continue

        series = df.iloc[:, idx]

        parsed = []
        total = 0

        for v in series:
            total += 1
            n = parse_bpc_loose(v)
            if n is not None:
                parsed.append(n)

        if total == 0:
            continue

        ratio = len(parsed) / total
        if ratio < 0.7:
            continue

        uniq = len(set(parsed))
        if uniq > 20:
            continue

        mn = min(parsed)
        mx = max(parsed)
        if mn < 1 or mx > 200:
            continue

        # 🔥 NEW: score known BPC hits
        known_hits = sum(1 for n in parsed if n in BPC_KNOWN)
        score = ratio * 100 + known_hits

        logger.debug(
            f"[BPC_DETECTOR] candidate col #{idx} {col!r} "
            f"(ratio={ratio:.2f}, uniq={uniq}, known_hits={known_hits}, score={score})"
        )

        if score > best_score:
            best_score = score
            best_idx = idx

    if best_idx is not None:
        logger.debug(
            f"[BPC_DETECTOR] final choice: index={best_idx}, name={df.columns[best_idx]!r}"
        )
    else:
        logger.debug("[BPC_DETECTOR] no BPC column detected")

    return best_idx
