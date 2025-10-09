import pandas as pd
import utils.text_extractors as te
from utils.text_extractors import PriceExtractor

def parse_text(raw_text: str) -> tuple[pd.DataFrame, dict]:
    """
    Базовый адаптер: превращает сырой текст в DataFrame
    с колонками, совпадающими с Excel-пайплайном.
    """
    rows = []
    extractor = PriceExtractor()
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue

        #цены
        result = extractor.extract(line)
        price_bottle = result.get("price_bottle")
        price_case = result.get("price_case")
        bpc = result.get("bottles_per_case")

        access = te.extract_access(line)
        location = te.extract_location(line)


        rows.append({
            "name": line,                # пока кладём полное имя, очистка в filter_and_enrich
            "cl": te.extract_volume(line),
            "bottles_per_case": bpc,
            "price_per_bottle": price_bottle,
            "price_per_case": price_case,
            "access": access,
            "location": location,
            "raw": line                  # оригинальная строка для отладки
        })

    df = pd.DataFrame(rows)
    mapping = {"source": "text"}
    return df, mapping