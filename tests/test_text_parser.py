import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.logger import setup_logging
from core.text_parser import parse_text

# включаем логгер
setup_logging()

SAMPLE_TEXT = """
Maxim

We can offer:
827 cs Bushmills 6 x 1 ltr at Euro 46.80 ex Loendersloot - T2
2 load - 3125 cs Jameson 6 x 70cl at Euro 48 exw Newcorp - T1
1000 cs Jack Daniels 12x 70cl NRF at 113 ex Riga 
864 bottles Clase Azul 6 x 75cl at Euro 128 per bottle ex Loendersloot - T1 goods

Best Regards

Anil Khetan

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