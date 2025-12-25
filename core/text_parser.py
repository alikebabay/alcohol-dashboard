import pandas as pd
import logging
import json
from pprint import pformat

from utils import text_extractors as te
from utils.text_extractors import PriceExtractor
from core.location_assistant import LocationAssistant
from core.access_assistant import AccessAssistant

from utils.logger import setup_logging
from config import MIN_PRODUCT_LEN
from libraries.regular_expressions import RX_BOTTLE, RX_BPC, RX_BPC_TRIPLE, RX_CASE
from libraries.distillator import looks_like_product
from core.product_detector import detect_product_without_price
from libraries.distillator import preprocess_raw_text

# --- Initialize logging once ---
setup_logging(logging.DEBUG)
logger = logging.getLogger("core.text_parser")

merge_logger = logging.getLogger("merge_headers")


#helper funcions for merge
def has_price(s: str) -> bool:
    return any(rx.search(s) for rx in RX_BOTTLE) or any(rx.search(s) for rx in RX_CASE)


# ---- global location aliases (loaded once) ----
try:
    with open("libraries/location_aliases.json", encoding="utf-8") as f:
        _loc_data = json.load(f)
        CITY_ALIASES = {k.lower(): v for k, v in _loc_data.get("cities", {}).items()}
        INCOTERM_ALIASES = {k.lower(): v for k, v in _loc_data.get("incoterms", {}).items()}
        WAREHOUSE_ALIASES = {k.lower(): v for k, v in _loc_data.get("warehouse", {}).items()}
except Exception as e:
    logger.error(f"[LOCATION] failed to load location_aliases.json: {e}")
    CITY_ALIASES = {}
    INCOTERM_ALIASES = {}
    WAREHOUSE_ALIASES = {}

def _looks_like_access_or_location(s: str) -> bool:
    s_norm = s.lower().strip()
    first = s_norm.split(" ", 1)[0]
    return (
        first in WAREHOUSE_ALIASES
        or first in INCOTERM_ALIASES
    )



#для случаев "Magners"
#           "cider bottle 24x330ml"

def _merge_short_headers(lines):
    lines = [l for l in lines if l.strip()]  # удаляем пустые строки

    merged = []
    skip_next = False

    for i, line in enumerate(lines):
        if skip_next:
            merge_logger.debug(
                "[MERGE][SKIP] idx=%d consumed_by_previous_merge",
                i
            )
            skip_next = False
            continue

        s = line.strip()
        #guard to prevent merging acces or location lines

        if _looks_like_access_or_location(s):
            merge_logger.debug(
                "[MERGE][SKIP][LOCATION] idx=%d '%s'",
                i, s
            )
            merged.append(line)
            continue

        # =========================
        # STAGE 1 — short line
        # =========================
        if not (0 < len(s) < MIN_PRODUCT_LEN):
            merge_logger.debug(
                "[MERGE][REJECT][S1] idx=%d reason=len=%d",
                i, len(s)
            )
        elif i + 1 >= len(lines):
            merge_logger.debug(
                "[MERGE][REJECT][S1] idx=%d reason=no_next_line",
                i
            )
        else:
            next_line = lines[i + 1].strip()
            merge_logger.debug(
                "[MERGE][S1][ACCEPT] idx=%d '%s' + '%s'",
                i, s, next_line
            )
            merged.append(f"{s} {next_line}")
            skip_next = True
            continue

        # =========================
        # STAGE 2 — product w/o price
        # =========================
        if not detect_product_without_price(s):
            merge_logger.debug(
                "[MERGE][REJECT][S2] idx=%d reason=not_product_without_price",
                i
            )
        elif i + 1 >= len(lines):
            merge_logger.debug(
                "[MERGE][REJECT][S2] idx=%d reason=no_next_line",
                i
            )
        elif not has_price(lines[i + 1]):
            merge_logger.debug(
                "[MERGE][REJECT][S2] idx=%d reason=next_line_has_no_price",
                i
            )
        else:
            next_line = lines[i + 1].strip()
            merge_logger.debug(
                "[MERGE][S2][ACCEPT] idx=%d '%s' + '%s'",
                i, s, next_line
            )
            merged.append(f"{s} {next_line}")
            skip_next = True
            continue

        # =========================
        # NO MERGE
        # =========================
        merge_logger.debug(
            "[MERGE][NO] idx=%d final_decision",
            i
        )
        merged.append(line)

    merge_logger.debug(
        "[MERGE][SUMMARY] input=%d output=%d",
        len(lines), len(merged)
    )

    return merged


def parse_text(raw_text: str) -> tuple[pd.DataFrame, dict]:
    """
    Базовый адаптер: превращает сырой текст в DataFrame
    с колонками, совпадающими с Excel-пайплайном.
    """
    logger.debug("=== START parse_text ===")
    logger.debug("Raw input:\n%s", raw_text[:500])  # ограничим, если текст длинный

    #0 нормализация - пока только слипшийся с цифрой евро
    raw_text = preprocess_raw_text(raw_text)

    # 1️⃣ Первичное разбиение и слияние коротких заголовков
    base_lines = raw_text.splitlines()
    logger.debug("=== RAW LINES ===")
    for i, l in enumerate(base_lines):
        logger.debug("  [%02d] %r", i, l)
    merged_lines = _merge_short_headers(base_lines)
    logger.debug("Lines before merge: %d, after merge: %d", len(base_lines), len(merged_lines))
    logger.debug("=== AFTER MERGE (short headers) ===")
    for i, l in enumerate(merged_lines):
        logger.debug("  [%02d] %r", i, l)

    rows = []
    extractor = PriceExtractor()

    # ← добавили: заранее посчитать финальные локации
    merged_text = "\n".join(merged_lines)
    loc_assistant = LocationAssistant(te.extract_location)
    acc_assistant = AccessAssistant(te.extract_access)

    loc_assistant.prepare(merged_text)
    acc_assistant.prepare(merged_text)

    all_lines = loc_assistant.lines()
    final_locations = loc_assistant.resolve_locations()
    final_access = acc_assistant.resolve_access()


    logger.debug("=== FINAL FILTERED LINES === %d", len(all_lines))
    for i, l in enumerate(all_lines):
        logger.debug("  [%02d] %r", i, l)

    logger.debug("=== RESOLVED LOCATIONS ===")
    logger.debug(pformat(final_locations))

    logger.debug("=== RESOLVED ACCESS ===")
    logger.debug(pformat(final_access))

    for idx, raw in enumerate(all_lines):
        line = raw.strip()
        if not line:
            logger.debug("Skipping empty line at idx=%d", idx)
            continue

        result = extractor.extract(line)
        logger.debug("=== LINE %02d ===", idx)
        logger.debug("SOURCE     : %r", line)
        logger.debug("EXTRACTED  : %s", pformat(result))
        logger.debug("VOLUME cl  : %r", te.extract_volume(line))
        logger.debug("ACCESS     : %r", final_access[idx] if idx < len(final_access) else None)
        logger.debug("LOCATION   : %r", final_locations[idx] if idx < len(final_locations) else None)
 

        row_dict = {
            "name": line,
            "cl": te.extract_volume(line),
            "bottles_per_case": result.get("bottles_per_case"),
            "price_per_bottle": result.get("price_bottle"),
            "price_per_case": result.get("price_case"),
            "access": final_access[idx],          # ← готовое решение помощника
            "location": final_locations[idx],           # ← готовое решение помощника
            "raw": line
        }
        # ключи строки
        logger.debug("ROW KEYS   : %s", pformat(sorted(row_dict.keys())))
        logger.debug("ROW DICT   : %s", pformat(row_dict))

        rows.append(row_dict)
    df = pd.DataFrame(rows)
    logger.debug("DataFrame constructed: %d rows, %d cols", *df.shape)
    logger.debug("DataFrame head:\n%s", df.head().to_string())
    logger.debug("DF columns: %s", df.columns.tolist())

    mapping = {"source": "text"}   # ← как у вас

    logger.debug("Mapping: %s", mapping)
    logger.debug("=== END parse_text ===")
    return df, mapping             # ← как у вас