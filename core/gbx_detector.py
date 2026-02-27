# core/gbx_detector.py
import re
import pandas as pd
import logging

from utils.logger import setup_logging
from libraries.regular_expressions import RX_GBX_MARKER, RX_GBX_NEGATIVE
from libraries.distillator import looks_like_product
from utils.brand_match import fuzzy_brand_match
from core.graph_loader import BRAND_KEYMAP


# инициализация общего логгера
setup_logging()

logger = logging.getLogger(__name__)

# символы чекбоксов для fallback-детектора по колонке
CHECK_POSITIVE = {"☑", "✓", "✔", "yes", "YES"}
CHECK_NEGATIVE = {"⮽", "✗", "x", "X", "no", "NO"}

# normalized brand list
BRAND_NAMES = [b.lower() for b in BRAND_KEYMAP.keys()]

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
    row_text = " ".join(map(str, row.values))
    #logger.debug(
    #    "[GBX][SCAN] row_idx=%s text='%s'",
    #    row.name,
    #    row_text[:120]
    #)

    for cell in row:
        s = _normalize_punct(str(cell).lower())

        # explicit negative (NoGBX, No GBX, Without Box)
        if RX_GBX_NEGATIVE.search(s):
            logger.debug(
                "[GBX][SCAN] row_idx=%s -> NEGATIVE",
                row.name,
            )
            return None

        # positive
        if RX_GBX_MARKER.search(s):
            logger.debug(
                "[GBX][SCAN] row_idx=%s -> FOUND GBX",
                row.name,
            )
            return "GBX"
    logger.debug(
        "[GBX][SCAN] row_idx=%s -> NO GBX",
        row.name,
    )
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
        #excluding header rows
        if not looks_like_product(row_text) and last_product_idx is None:
            continue

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
            header = str(col).lower()
            if not any(k in header for k in ["gb", "box", "gift"]):
                continue
            svals = set(vals)
            if svals & CHECK_POSITIVE or svals & CHECK_NEGATIVE:
                logger.debug(f"[GBX] fallback: detected checkbox column {col!r} values={svals}")
                return col

    return None



def detect_gbx(
    df_gbx: pd.DataFrame,
    alive_raw_idx: set[int] | None = None
) -> pd.DataFrame:
    """
    Универсальный GBX-детектор:
       1) ищет текст GBX в любом поле строки
       2) если 0 — ищет чекбокс-колонку
       3) если нет — возвращает пустые флаги
    """    
    # ---- normalize duplicate / empty column names ----
    df_gbx = df_gbx.copy()
    df_gbx.columns = [
        f"col_{i}" if not str(c).strip() else str(c)
        for i, c in enumerate(df_gbx.columns)
    ]

    logger.debug("GBX input raw_idx head: %s", df_gbx["raw_idx"].head(10).tolist())
    logger.debug("[GBX/SHAPE] rows=%d cols=%d", df_gbx.shape[0], df_gbx.shape[1])
    try:
        logger.debug("[GBX/COLS] %s", list(df_gbx.columns))
    except Exception:
        pass
    # excel mode → no alive filtering
    if alive_raw_idx is None:
        logger.debug("[GBX] alive_raw_idx=None → no product filtering")


     # === DEBUG: RAW INPUT PREVIEW ===
    try:
        logger.debug(
            "\n=== RAW DF (first 10 rows) ===\n" +
            df_gbx.head(10).to_string()
        )
    except Exception as e:
        logger.debug(f"[ERROR] cannot preview RAW DF: {e}")
    
    N = len(df_gbx)
    logger.debug(f"[GBX] ====== GBX DETECTOR START ====== rows={N}")
    # ==========================================================
    # 0) STRUCTURAL CHECKBOX DETECTION FIRST (highest priority)
    # ==========================================================
    col = _detect_gbx_column(df_gbx)
    if col:
        logger.debug(f"[GBX/MODE] checkbox column detected first: {col!r}")

        s = df_gbx[col].astype(str).str.strip()
        gb_flag = s.isin(CHECK_POSITIVE)
        gb_type = gb_flag.map(lambda x: "GBX" if x else None)

        logger.debug("[GBX] ====== GBX DETECTOR DONE (checkbox-first mode) ======")
        return pd.DataFrame({
            "raw_idx": df_gbx["raw_idx"].values,
            "gb_flag": gb_flag,
            "gb_type": gb_type,
        })

    # 1) Inline search
    logger.debug("[GBX/TEXT] scanning rows for textual GBX markers...")
    gb_type = df_gbx.apply(detect_gbx_in_row, axis=1)
    gb_flag = gb_type.notna()
    try:
        logger.debug("[GBX/TEXT] gb_type unique=%s", gb_type.dropna().astype(str).value_counts().head(10).to_dict())
        logger.debug("[GBX/TEXT] gb_flag.sum=%d", int(gb_flag.sum()))
    except Exception:
        pass

    # ----------------------------------------------------------
    # Separate product-level hits from noise (e.g. header "gb")
    # ----------------------------------------------------------
    product_hits = []
    footer_hits = []

    last_product_seen = False

    for idx, row in df_gbx.iterrows():
        if not gb_flag.at[idx]:
            continue

        row_text = " ".join(map(str, row.values))
        is_prod = looks_like_product(row_text)
        is_brand = fuzzy_brand_match(row_text, BRAND_NAMES)
        try:
            # show WHY it became a hit + product/non-product classification
            logger.debug(
                "[GBX/HIT] idx=%s raw_idx=%s is_product=%s is_brand=%s last_product_seen=%s text=%r",
                idx,
                df_gbx.at[idx, "raw_idx"] if "raw_idx" in df_gbx.columns else None,
                is_prod,
                is_brand,
                last_product_seen,
                row_text[:160],
            )
        except Exception:
            logger.debug("[GBX/HIT] idx=%s is_product=%s is_brand=%s last_product_seen=%s", idx, is_prod, is_brand, last_product_seen)
 

        # ---- NEW LOGIC: positional pairing ----
        prev_idx = idx - 1 if idx - 1 in df_gbx.index else None
        prev_is_prod = False

        if prev_idx is not None:
            prev_text = " ".join(map(str, df_gbx.loc[prev_idx].values))
            prev_is_prod = looks_like_product(prev_text)

        if is_prod or is_brand:
            product_hits.append(idx)
            logger.debug(
                "[GBX/HIT] -> classified as INLINE (product=%s brand=%s)",
+                is_prod,
+                is_brand,
            )

        elif prev_is_prod:
            footer_hits.append(idx)
            logger.debug(
                "[GBX/HIT] -> classified as FOOTER (previous row is product idx=%s)",
                prev_idx,
            )

        else:
            logger.debug(
                "[GBX/HIT] -> classified as PREAMBLE/NOISE (no product above)"
            )

    logger.debug(
        "[GBX/DECIDE] product_hits=%d footer_hits=%d first_product_hit=%s first_footer_hit=%s",
        len(product_hits),
        len(footer_hits),
        product_hits[0] if product_hits else None,
        footer_hits[0] if footer_hits else None,
    )

    # ==========================================================
    # 1A) INLINE MODE (only if product rows contain GBX)
    # ==========================================================
    if len(product_hits) > 0:
        logger.debug(
            f"[GBX/MODE] inline text mode selected (product_hits={len(product_hits)})"
        )
        return pd.DataFrame({
            "raw_idx": df_gbx["raw_idx"].values,
            "gb_flag": gb_flag,
            "gb_type": gb_type,
        })

    # ==========================================================
    # 1B) BLOCK MODE (GBX found only in footer rows)
    # ==========================================================
    if len(footer_hits) > 0:
        logger.debug(
            f"[GBX/MODE] block mode selected (footer_hits={len(footer_hits)})"
        )
        # extra debug: show the exact footer rows that triggered block mode (head)
        try:
            for j in footer_hits[:5]:
                row_text = " ".join(map(str, df_gbx.loc[j].values))
                logger.debug("[GBX/FOOTER_HIT] idx=%s raw_idx=%s text=%r", j, df_gbx.at[j, "raw_idx"], row_text[:160])
        except Exception:
            pass
        gb_flag_block = _detect_gbx_by_blocks(df_gbx)
        gb_type_block = gb_flag_block.map(lambda x: "GBX" if x else None)

        return pd.DataFrame({
            "raw_idx": df_gbx["raw_idx"].values,
            "gb_flag": gb_flag_block,
            "gb_type": gb_type_block,
        })


    logger.debug("[GBX/TEXT] no textual GBX detected → trying checkbox fallback")

    
    # 3) Checkbox search
    col = _detect_gbx_column(df_gbx)

    if col:
        logger.debug(f"[GBX/FALLBACK] using checkbox column: {col!r}")

        s = df_gbx[col].astype(str).str.strip()
        gb_flag = s.isin(CHECK_POSITIVE)
        gb_type = gb_flag.map(lambda x: "GBX" if x else None)

        logger.debug(
            f"[GBX/FALLBACK] checkbox results: {int(gb_flag.sum())} true flags. "
            f"Examples: {gb_flag.head(10).tolist()}"
        )

        logger.debug("[GBX] ====== GBX DETECTOR DONE (checkbox mode) ======")
        return pd.DataFrame({
            "raw_idx": df_gbx["raw_idx"].values,
            "gb_flag": gb_flag,
            "gb_type": gb_type,
        })


    # 2.5) Полный брут-форс поиск чекбоксов в *каждой* ячейке DF
    logger.debug("[GBX/FULLSCAN] no checkbox column detected → scanning all cells...")

    # Приводим все ячейки к строкам
    df_str = df_gbx.astype(str).map(str.strip)

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

        return pd.DataFrame({
            "raw_idx": df_gbx["raw_idx"].values,
            "gb_flag": gb_flag,
            "gb_type": gb_type,
        })


    # 3) Вообще ничего не нашли
    logger.debug("[GBX/NONE] no GBX found (text, column or full-scan)")
    logger.debug("[GBX] ====== GBX DETECTOR DONE (none mode) ======")

    result = pd.DataFrame({
    "raw_idx": df_gbx["raw_idx"].values,
        "gb_flag": gb_flag,
        "gb_type": gb_type,
    })
    logger.debug("GBX output raw_idx head: %s", result["raw_idx"].head(10).tolist())
    return result
