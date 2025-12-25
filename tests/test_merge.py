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
Bud Light 15 x 300ml ex Newcorp Logistics Holland 

1 load - 3185 cases (Apr) £4.46 and 175 cases (May) £4.48

More loads  - (Apil expiry 2026 )@ £4.46 GBP
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
