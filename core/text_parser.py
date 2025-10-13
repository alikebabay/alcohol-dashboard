import pandas as pd
import utils.text_extractors as te
from utils.text_extractors import PriceExtractor
from core.location_assistant import LocationAssistant


print(PriceExtractor().extract("Dom Perignon vintage naked 6 x 75cl at 143 USD"))

def parse_text(raw_text: str) -> tuple[pd.DataFrame, dict]:
    """
    Базовый адаптер: превращает сырой текст в DataFrame
    с колонками, совпадающими с Excel-пайплайном.
    """
    rows = []
    extractor = PriceExtractor()

    # ← добавили: заранее посчитать финальные локации
    assistant = LocationAssistant(te.extract_location)
    assistant.prepare(raw_text)
    all_lines = assistant.lines()
    final_locations = assistant.resolve_locations()

    for idx, raw in enumerate(all_lines):
        line = raw.strip()
        if not line:
            continue

        result = extractor.extract(line)
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
    mapping = {"source": "text"}   # ← как у вас
    return df, mapping             # ← как у вас