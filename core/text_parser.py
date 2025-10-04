import pandas as pd
import utils.text_extractors as te

def parse_text(raw_text: str) -> tuple[pd.DataFrame, dict]:
    """
    Базовый адаптер: превращает сырой текст в DataFrame
    с колонками, совпадающими с Excel-пайплайном.
    """
    rows = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue

        price_bottle = te.extract_price_per_bottle(line)
        bpc = te.extract_bottles_per_case(line)
        price_case = te.extract_price_per_case(line)

        # если есть bottle + bpc → считаем цену за кейс
        if price_case is None and price_bottle is not None and bpc is not None:
            price_case = price_bottle * bpc

        rows.append({
            "name": line,                # пока кладём полное имя, очистка в filter_and_enrich
            "cl": te.extract_volume(line),
            "bottles_per_case": bpc,
            "price_per_bottle": price_bottle,
            "price_per_case": price_case,
            "raw": line                  # оригинальная строка для отладки
        })

    df = pd.DataFrame(rows)

    mapping = {"source": "text"}
    return df, mapping
