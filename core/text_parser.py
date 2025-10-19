import pandas as pd
import logging
from utils import text_extractors as te
from utils.text_extractors import PriceExtractor
from core.location_assistant import LocationAssistant
from utils.logger import setup_logging

# --- Initialize logging once ---
setup_logging(logging.DEBUG)
log = logging.getLogger("core.text_parser")

def _merge_short_headers(lines, max_words=3):
    merged = []
    skip_next = False
    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue

        words = line.strip().split()
        if 0 < len(words) <= max_words and i + 1 < len(lines):
            # merge this short header with the next non-empty line
            next_line = lines[i + 1].strip()
            merged_line = f"{line.strip()} {next_line}"
            merged.append(merged_line)
            skip_next = True
        else:
            merged.append(line)
    return merged


def parse_text(raw_text: str) -> tuple[pd.DataFrame, dict]:
    """
    Базовый адаптер: превращает сырой текст в DataFrame
    с колонками, совпадающими с Excel-пайплайном.
    """
    log.debug("=== START parse_text ===")
    log.debug("Raw input:\n%s", raw_text[:500])  # ограничим, если текст длинный

    # 1️⃣ Первичное разбиение и слияние коротких заголовков
    base_lines = raw_text.splitlines()
    merged_lines = _merge_short_headers(base_lines)
    log.debug("Lines before merge: %d, after merge: %d", len(base_lines), len(merged_lines))

    rows = []
    extractor = PriceExtractor()

    # ← добавили: заранее посчитать финальные локации
    merged_text = "\n".join(merged_lines)
    assistant = LocationAssistant(te.extract_location)
    assistant.prepare(merged_text)
    all_lines = assistant.lines()
    final_locations = assistant.resolve_locations()

    log.debug("Lines detected: %d", len(all_lines))
    log.debug("Resolved locations: %s", final_locations)

    for idx, raw in enumerate(all_lines):
        line = raw.strip()
        if not line:
            log.debug("Skipping empty line at idx=%d", idx)
            continue

        result = extractor.extract(line)
        log.debug(
            "[%02d] Parsed line: %s | Extracted: %s",
            idx,
            line,
            result,
        )

        rows.append({
            "name": line,
            "cl": te.extract_volume(line),
            "bottles_per_case": result.get("bottles_per_case"),
            "price_per_bottle": result.get("price_bottle"),
            "price_per_case": result.get("price_case"),
            "access": te.extract_access(line),          # access не трогаем
            "location": final_locations[idx],           # ← готовое решение помощника
            "raw": line
        })

    df = pd.DataFrame(rows)
    log.debug("DataFrame constructed: %d rows, %d cols", *df.shape)
    log.debug("DataFrame head:\n%s", df.head().to_string())

    mapping = {"source": "text"}   # ← как у вас

    log.debug("Mapping: %s", mapping)
    log.debug("=== END parse_text ===")
    return df, mapping             # ← как у вас