import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.logger import setup_logging
from core.text_parser import parse_text

# включаем логгер
setup_logging()

SAMPLE_TEXT = """
Magners cider bottle 24x330ml
Locatie: van der Mark | Cases: 2160cs | BBD: fresh | Prijs: €20.25

Estrella damm bottle 24x330ml
Locatie: van der Mark | Cases: 1728cs | BBD: fresh | Prijs: €12.30

Stella artois can 24x500ml
Locatie: van der Mark | Cases: 1840cs | BBD: fresh | Prijs: €13.75

Grolsch bottle 24x330ml
Locatie: van der Mark | Cases: 1872cs | BBD: fresh | Prijs: €13.99

Pilsner urquell bottle 24x330ml
Locatie: van der Mark | Cases: 1728cs | BBD: fresh | Prijs: €13.50

Staropramen bottle 24x330ml
Locatie: van der Mark | Cases: 1728cs | BBD: fresh | Prijs: €13.15

Staropramen can 24x500ml
Locatie: van der Mark | Cases: 1890cs | BBD: fresh | Prijs: €15.05

Coors bottle 24x330ml
Locatie: van der Mark | Cases: 1728cs | BBD: fresh | Prijs: €13.10

Coors can 24x500ml
Locatie: van der Mark | Cases: 2016cs | BBD: fresh | Prijs: €14.90

Strongbow cider British dry bottle 24x330ml
Locatie: van der Mark | Cases: 2016cs | BBD: fresh | Prijs: €16.10

Strongbow cider British dry can 24x500ml
Locatie: van der Mark | Cases: 2060cs | BBD: fresh | Prijs: €14.00

John smiths extra smooth can 24x500ml
Locatie: van der Mark | Cases: 1890cs | BBD: fresh | Prijs: €14.10

Paulaner hefen weizen can 24x500ml
Locatie: van der Mark | Cases: 1890cs | BBD: fresh | Prijs: €16.50
"""

if __name__ == "__main__":
    df, mapping = parse_text(SAMPLE_TEXT)

    print("\n=== PARSE RESULT ===\n")
    print(df)
    print("\n=== PRICE DETAILS PER ROW ===\n")

    # Если в df есть колонка с сырой строкой — используем её.
    # Обычно это 'raw' или 'name' или 'text'.
    raw_col = None
    for c in df.columns:
        if c.lower() in ("raw", "text", "name", "description"):
            raw_col = c
            break

    if raw_col is None:
        print("No raw/text column found → cannot extract price details.")
    else:
        from utils.text_extractors import PriceExtractor
        pe = PriceExtractor()

        for idx, row in df.iterrows():
            raw = str(row[raw_col])
            result = pe.extract(raw)

            print(f"--- ROW {idx} ---")
            print(f"RAW: {raw}")
            print(
                f"  BPC: {result.get('bottles_per_case')}\n"
                f"  PRICE_CASE: {result.get('price_case')}\n"
                f"  PRICE_BOTTLE: {result.get('price_bottle')}\n"
                f"  STATE: {result.get('state')}"
            )
            print()