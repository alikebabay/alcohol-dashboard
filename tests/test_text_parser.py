import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.logger import setup_logging
from core.text_parser import parse_text

# включаем логгер
setup_logging()

SAMPLE_TEXT = """
600 cs Singleton of Dufftown 12yo 6/70/40 (no GB) @ EUR 74 (12,33 p/btl)
560 cs Glenfiddich 12yo 6/70/40 GB @ EUR 111 (18,50 p/btl)
560 cs Glenfiddich 12yo Triple Oak 6/70/40 GB @ EUR 130 (21,67 p/btl)
80 cs Glenfiddich Orchard 6/70/43 GB @ EUR 159 (26,50 p/btl)
80 cs Glenfiddich Fire and Cane 6/70/43 @ EUR 140 (23,33 p/btl)
EXW Loendersloot, Revera or Newcorp / Lead time is about 2 weeks / T2
We can also assist with shipping to your destination

Looking forward to your comments.


Kind regards,

Daan Hoefman
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