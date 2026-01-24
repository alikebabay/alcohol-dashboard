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
 
 
500CS GLENLIVET FOUNDERS RESERVE 6/70/40 @ E 97.85
T2 / CODED / REFILL / GBX / EAN CODE 500299609347 / ON THE FLOOR
 
 
1686CS JAMESON 6/100/40 @ EURO 62.83
T2 / CODED / REFILL / EAN CODE 5011007003227 / ON THE FLOOR
 
 
40CS ABERLOUR 16YRS DOUBLE CASK MATURED 3/70/40 @ EURO 138.02
T2 / CODED / REFILL / GBX / EAN CODE 500299298022 / ON THE FLOOR
 
 
244CS ABERLOUR 14YRS DOUBLE CASK MATURED 3/70/40 @ EURO 92.70
T2 / CODED / REFILL / EAN CODE 500299620915 / ON THE FLOOR
 Anil
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
