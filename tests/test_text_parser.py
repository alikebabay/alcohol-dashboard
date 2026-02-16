import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.logger import setup_logging
from core.text_parser import parse_text

# включаем логгер
setup_logging()

SAMPLE_TEXT = """

Peroni Nastro Azzurro 24/330/5%     161cs   28.2.2025  
Amsterdam NAVIGATOR CAN 24/500/8%   216cs 19.4.2025  
Grolsch NL Can  24/500/5.0%   240cs 2.12.2024 1,99eur
Grolsch NL Can  24/500/5.0%   240cs 18.7.2025 2,20eur
Grolsch NL Can  24/500/5.0%   385cs 12.9.2025 2,50 eur
ASAHI SUPER DRY BOTTLE  24/330/5.0%  1035cs  18.5.2025  
Peroni Nastro Azzurro Bottle 24/330/0%  700 cs 30.7.2025  
Peroni Nastro Azzurro Bottle 24/330/0%  5234cs (3 loads) 1.9.2025 
Peroni Nastro Azzurro Bottle 24/330/0% 1080cs 30.9.2025 

ALL TOGETHER 5-6 LOADS = TAKE ALL PRICE €2.50 CASE EVERY BEER
EXW revera
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