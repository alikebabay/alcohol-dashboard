#merge_short.py

import re
import pandas as pd
import logging
from config import MIN_PRODUCT_LEN
from libraries.regular_expressions import RX_CURRENCY
from core.text_parser import _looks_like_access_or_location

logger = logging.getLogger(__name__)

def merge_short (df: pd.DataFrame, col: str = "name") -> pd.DataFrame:
    """
    Text-only structural fix:
    If a row looks like a short brand/header line, prepend it to the next row's name
    and drop the header row.
    """
    if col not in df.columns or df.empty:
        return df

    df = df.copy().reset_index(drop=True)
    out_rows = []
    i = 0
    while i < len(df):
        s = str(df.at[i, col]).strip()
        if not s:
            i += 1
            continue

        # header candidate: short, no digits, no currency, not location/access
        is_short = 0 < len(s) < MIN_PRODUCT_LEN
        has_digits = any(c.isdigit() for c in s)
        has_currency = bool(RX_CURRENCY.search(s))
        is_loc = _looks_like_access_or_location(s)

        if is_short and (not has_digits) and (not has_currency) and (not is_loc) and i + 1 < len(df):
            nxt = str(df.at[i + 1, col]).strip()
            if nxt:
                merged = f"{s} {nxt}"
                # сохраняем текущую строку (НЕ дропаем)
                out_rows.append(df.iloc[i])
                # добавляем модифицированную следующую строку
                row = df.iloc[i + 1].copy()
                row[col] = merged
                out_rows.append(row)
                logger.debug("[TextState][GLUE] '%s' + '%s'", s, nxt)
                i += 2
                continue

        out_rows.append(df.iloc[i])
        i += 1

    return pd.DataFrame(out_rows).reset_index(drop=True)