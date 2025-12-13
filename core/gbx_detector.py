# core/gbx_detector.py
import re
import pandas as pd
import logging
import sys

from utils.logger import setup_logging
from libraries.regular_expressions import RX_GBX_MARKER, RX_GBX_NEGATIVE
from libraries.distillator import looks_like_product


# инициализация общего логгера
setup_logging()

logger = logging.getLogger(__name__)

# символы чекбоксов для fallback-детектора по колонке
CHECK_POSITIVE = {"☑", "✓", "✔"}
CHECK_NEGATIVE = {"⮽", "✗", "x", "X"}

def _cell_to_str(v):
    try:
        return str(v).lower()
    except:
        return ""

def _normalize_punct(s: str) -> str:
    # unify separators — same logic as in text extractor
    return re.sub(r"[,.;:/\\|+]", " ", s)


def detect_gbx_in_row(row: pd.Series) -> str | None:
    """
    Detects any GB/GBX marker in ANY cell of the row.
    Returns:
        "GBX" if found
        None otherwise
    """
    for cell in row:
        if not isinstance(cell, str):
            continue

        s = _normalize_punct(cell.lower())

        # explicit negative (NoGBX, No GBX, Without Box)
        if RX_GBX_NEGATIVE.search(s):
            return None

        # positive
        if RX_GBX_MARKER.search(s):
            return "GBX"

    return None

def _detect_gbx_by_blocks(df: pd.DataFrame) -> pd.Series:
    """
    Block-based GBX detection:
    If GBX appears in a non-product row,
    it applies to the nearest preceding product row.
    """
    gb_flag = pd.Series(False, index=df.index)

    last_product_idx = None

    for idx, row in df.iterrows():
        row_text = " ".join(map(str, row.values))

        if looks_like_product(row_text):
            last_product_idx = idx
            continue

        if last_product_idx is None:
            continue

        s = _normalize_punct(row_text.lower())

        if RX_GBX_NEGATIVE.search(s):
            continue

        if RX_GBX_MARKER.search(s):
            gb_flag.at[last_product_idx] = True

    return gb_flag

def _detect_gbx_column(df: pd.DataFrame) -> str | None:
    """
    Fallback-детектор: ищет колонку-флаг (☑ / ⮽),
    безопасно работает при дублях колонок.
    """
    for col in df.columns:
        col_data = df[col]

        # если по ошибке это DataFrame — берем первую колонку
        if isinstance(col_data, pd.DataFrame):
            logger.error(
                f"[GBX] Column {col!r} returned DataFrame with columns {col_data.columns.tolist()} → using first column"
            )
            col_data = col_data.iloc[:, 0]

        vals = (
            col_data.dropna()
            .astype(str)
            .str.strip()
            .unique()
        )

        if len(vals) <= 4:
            svals = set(vals)
            if svals & CHECK_POSITIVE or svals & CHECK_NEGATIVE:
                logger.debug(f"[GBX] fallback: detected checkbox column {col!r} values={svals}")
                return col

    return None



def detect_gbx(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Универсальный GBX-детектор:
       1) ищет текст GBX в любом поле строки
       2) если 0 — ищет чекбокс-колонку
       3) если нет — возвращает пустые флаги
    """
     # === DEBUG: RAW INPUT PREVIEW ===
    try:
        logger.debug(
            "\n=== RAW DF (first 10 rows) ===\n" +
            df.head(10).to_string()
        )
    except Exception as e:
        logger.debug(f"[ERROR] cannot preview RAW DF: {e}")
    
    N = len(df_raw)
    logger.debug(f"[GBX] ====== GBX DETECTOR START ====== rows={N}")

    # 1) Inline search
    logger.debug("[GBX/TEXT] scanning rows for textual GBX markers...")
    gb_type = df_raw.apply(detect_gbx_in_row, axis=1)
    gb_flag = gb_type.notna()

    #remapping in case of footers
    if gb_flag.any():
        logger.debug("[GBX/TEXT] found GBX markers → checking for footer rows")

        gb_flag_final = gb_flag.copy()

        last_product_idx = None

        for idx, row in df_raw.iterrows():
            row_text = " ".join(map(str, row.values))

            if looks_like_product(row_text):
                last_product_idx = idx
                continue

            # 👇 only remap if this GBX hit is in a footer row
            if gb_flag.at[idx] and not looks_like_product(row_text):
                if last_product_idx is not None:
                    gb_flag_final.at[last_product_idx] = True
                    gb_flag_final.at[idx] = False

        if gb_flag_final.any():
            gb_type = gb_flag_final.map(lambda x: "GBX" if x else None)
            logger.debug("[GBX] ====== GBX DETECTOR DONE (text+footer remap) ======")
            return pd.DataFrame({"gb_flag": gb_flag_final, "gb_type": gb_type})

    count_text = int(gb_flag.sum())

    if count_text > 0:
        logger.debug(
            f"[GBX/TEXT] found {count_text} GBX rows (text-based). "
            f"Examples: {gb_type[gb_flag].head(5).to_dict()}"
        )
        logger.debug("[GBX] ====== GBX DETECTOR DONE (text mode) ======")
        return pd.DataFrame({"gb_flag": gb_flag, "gb_type": gb_type})

    logger.debug("[GBX/TEXT] no textual GBX detected → trying checkbox fallback")

    # 2) Block search

    logger.debug("[GBX/BLOCK] trying block-based footer detection...")

    gb_flag_block = _detect_gbx_by_blocks(df_raw)
    count_block = int(gb_flag_block.sum())

    if count_block > 0:
        logger.debug(
            f"[GBX/BLOCK] detected {count_block} GBX rows via footer blocks"
        )
        gb_type = gb_flag_block.map(lambda x: "GBX" if x else None)
        logger.debug("[GBX] ====== GBX DETECTOR DONE (block mode) ======")
        return pd.DataFrame({"gb_flag": gb_flag_block, "gb_type": gb_type})


    # 3) Checkbox search
    col = _detect_gbx_column(df_raw)

    if col:
        logger.debug(f"[GBX/FALLBACK] using checkbox column: {col!r}")

        s = df_raw[col].astype(str).str.strip()
        gb_flag = s.isin(CHECK_POSITIVE)
        gb_type = gb_flag.map(lambda x: "GBX" if x else None)

        logger.debug(
            f"[GBX/FALLBACK] checkbox results: {int(gb_flag.sum())} true flags. "
            f"Examples: {gb_flag.head(10).tolist()}"
        )

        logger.debug("[GBX] ====== GBX DETECTOR DONE (checkbox mode) ======")
        return pd.DataFrame({"gb_flag": gb_flag, "gb_type": gb_type})

    # 2.5) Полный брут-форс поиск чекбоксов в *каждой* ячейке DF
    logger.debug("[GBX/FULLSCAN] no checkbox column detected → scanning all cells...")

    # Приводим все ячейки к строкам
    df_str = df_raw.astype(str).applymap(lambda x: x.strip())

    # матрица True/False по чекбоксам
    mask_pos = df_str.isin(CHECK_POSITIVE)
    mask_neg = df_str.isin(CHECK_NEGATIVE)

    # если нет ни одного чекбокса вообще → пропускаем
    if mask_pos.any().any() or mask_neg.any().any():
        gb_flag = mask_pos.any(axis=1)
        gb_type = gb_flag.map(lambda x: "GBX" if x else None)

        logger.debug(
            f"[GBX/FULLSCAN] detected {int(gb_flag.sum())} GBX rows via brute-force cell scan"
        )
        logger.debug("[GBX] ====== GBX DETECTOR DONE (full-scan mode) ======")

        return pd.DataFrame({"gb_flag": gb_flag, "gb_type": gb_type})

    # 3) Вообще ничего не нашли
    logger.debug("[GBX/NONE] no GBX found (text, column or full-scan)")
    logger.debug("[GBX] ====== GBX DETECTOR DONE (none mode) ======")

    return pd.DataFrame({
        "gb_flag": [False] * N,
        "gb_type": [None] * N,
    })