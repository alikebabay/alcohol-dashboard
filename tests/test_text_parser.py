import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.logger import setup_logging
from core.text_parser import parse_text

# включаем логгер
setup_logging()

SAMPLE_TEXT = """
EX LOENDERSLOOT
For larger orders, prices can be discussed
140CS BALLANTINE’S 12/100/40 @ EURO 86.00
T2 / CODED / REFILL / EAN CODE 5010106111956 / ON THE FLOOR
 
 
600CS BEEFEATER 12/50/40 @ E 53.56
T2 / CODED / REFILL / EAN CODE 5000299605981 / ON THE FLOOR
 
 
486CS ABSOLUT 24/20/40 @ E 55.62
T2 / CODED / REFILL / EAN CODE 7312040017201 / 2 WEEKS LEAD TIME
 
 
120CS ABSOLUT 6/70/40 @ EURO 32.96
T2 / CODED / REFILL / EAN CODE 7312040017683 / ON THE FLOOR
 
 
1000CS ABSOLUT 24/35/40 @ EURO 86.52
T2 / CODED / REFILL / EAN CODE 7312040017355 / ON THE FLOOR
 
 
1000CS ABSOLUT 12/35/40 @ EURO 43.26
T2 / CODED / REFILL / EAN CODE 7312040017355 / ON THE FLOOR
 
 
 
 
1686CS JAMESON 6/100/40 @ EURO 62.83
T2 / CODED / REFILL / EAN CODE 5011007003227 / ON THE FLOOR
 
 
40CS ABERLOUR 16YRS DOUBLE CASK MATURED 3/70/40 @ EURO 138.02
T2 / CODED / REFILL / GBX / EAN CODE 500299298022 / ON THE FLOOR
 
 
244CS ABERLOUR 14YRS DOUBLE CASK MATURED 3/70/40 @ EURO 92.70
T2 / CODED / REFILL / EAN CODE 500299620915 / ON THE FLOOR
 Anil

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