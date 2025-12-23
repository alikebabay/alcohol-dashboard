import pandas as pd
import logging
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

# --- Initialize logging once ---
setup_logging(logging.DEBUG)
logger = logging.getLogger("core.text_parser")

#helper funcion for merge
def has_price(s: str) -> bool:
    return any(rx.search(s) for rx in RX_BOTTLE) or any(rx.search(s) for rx in RX_CASE)


#для случаев "Magners"
#           "cider bottle 24x330ml"

def _merge_short_headers(lines):
    merged = []
    skip_next = False

    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue

        s = line.strip()

        # ---------- STAGE 1: короткие строки ----------
        if 0 < len(s) < MIN_PRODUCT_LEN and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            merged.append(f"{s} {next_line}")
            skip_next = True
            continue

        # ---------- STAGE 2: продукт БЕЗ инлайн-цены ----------
        if (
            detect_product_without_price(s)
            and i + 1 < len(lines)
            and has_price(lines[i + 1])
        ):
            next_line = lines[i + 1].strip()
            merged.append(f"{s} {next_line}")
            skip_next = True
            continue

        merged.append(line)

    return merged



def parse_text(raw_text: str) -> tuple[pd.DataFrame, dict]:
    """
    Базовый адаптер: превращает сырой текст в DataFrame
    с колонками, совпадающими с Excel-пайплайном.
    """
    logger.debug("=== START parse_text ===")
    logger.debug("Raw input:\n%s", raw_text[:500])  # ограничим, если текст длинный

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