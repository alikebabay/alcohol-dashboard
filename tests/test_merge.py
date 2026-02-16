import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.logger import setup_logging
from core.text_parser import parse_text
from core.text_parser import _merge_short_headers

# ------------------------------------------------------------------
# enable logging
# ------------------------------------------------------------------

setup_logging()

# ------------------------------------------------------------------
# SAMPLE INPUTS — crafted to trigger merge logic
# ------------------------------------------------------------------

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

# ------------------------------------------------------------------
# RAW LINE-LEVEL DEBUG
# ------------------------------------------------------------------

def debug_raw_merge_only(text: str):
    print("\n================ RAW MERGE DEBUG ================\n")

    lines = [l for l in text.splitlines() if l.strip()]

    print(">>> INPUT LINES:")
    for i, l in enumerate(lines):
        print(f"{i:02d}: {l}")

    merged = _merge_short_headers(lines)

    print("\n>>> MERGED LINES:")
    for i, l in enumerate(merged):
        print(f"{i:02d}: {l}")

    return merged


# ------------------------------------------------------------------
# FULL PIPELINE DEBUG
# ------------------------------------------------------------------

def debug_full_parse(text: str):
    print("\n================ FULL PARSE DEBUG ================\n")

    df, mapping = parse_text(text)

    print("\n=== PARSE RESULT DF ===\n")
    print(df)

    print("\n=== MAPPING ===\n")
    print(mapping)


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------

if __name__ == "__main__":

    # 1️⃣ isolate merge logic
    merged_lines = debug_raw_merge_only(SAMPLE_TEXT)

    # 2️⃣ run full pipeline (merge already applied inside)
    debug_full_parse(SAMPLE_TEXT)
