import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import difflib
import pandas as pd
from colorama import Fore, Style


from core.graph_normalizer import normalize_dataframe
from utils.abbreviations_helper import convert_abbreviation

# 🧾 Just paste your text here — no need for quotes or commas
text = """
WHISKY STOCK OFFER EX LOENDERSLOOT

40CS BOWMORE 15YRS GOLDEN & ELEGANT 6/100/43 @ EURO 190.00
T2 / CODED / REFILL / GBX / EAN CODE 5010496004548

40CS BOWMORE 18YRS DEEP & COMPLEX 6/70/43 @ EURO 340.00
T2 / CODED / REFILL / GBX / EAN CODE 5010496004555

100CS AUCHENTOSHAN AMERICAN OAK 12/100/40 @ EURO 204.00
T2 / CODED / REFILL / EAN CODE 5010496005378

36CS DEWAR’S 12YRS 6/70/40 @ EURO 75.00
T2 / CODED / REFILL / GBX / EAN CODE 5000277002450

39CS GLEN SCOTIA DOUBLE CASK CLASSIC CAMPBELTOWN 6/70/46 @ EURO 120.00
T2 / CODED / REFILL / GBX / EAN CODE 5016840151210

94CS LONGMORN 16YRS 3/70/48 @ EURO 244.00
T2 / CODED / REFILL / GBX / EAN CODE 5000299607152
EX LOENDERSLOOT

For larger orders, prices can be discussed

140CS BALLANTINE’S 12/100/40 @ EURO 86.00
T2 / CODED / REFILL / EAN CODE 5010106111956 / ON THE FLOOR

600CS BEEFEATER 12/50/40 @ E 52.00
T2 / CODED / REFILL / EAN CODE 5000299605981 / ON THE FLOOR

486CS ABSOLUT 24/20/40 @ E 54.00
T2 / CODED / REFILL / EAN CODE 7312040017201 / 2 WEEKS LEADTIME

120CS ABSOLUT 6/70/40 @ EURO 32.00
T2 / CODED / REFILL / EAN CODE 7312040017683 / ON THE FLOOR

1000CS ABSOLUT 24/35/40 @ EURO 84.00
T2 / CODED / REFILL / EAN CODE 7312040017355 / ON THE FLOOR

1000CS ABSOLUT 12/35/40 @ EURO 42.00
T2 / CODED / REFILL / EAN CODE 7312040017355 / ON THE FLOOR

500CS GLENLIVET FOUNDERS RESERVE 6/70/40 @ E 95.00
T2 / CODED / REFILL / GBX / EAN CODE 500299609347 / ON THE FLOOR

1686CS JAMESON 6/100/40 @ EURO 61.00
T2 / CODED / REFILL / EAN CODE 5011007003227 / ON THE FLOOR

40CS ABERLOUR 16YRS DOUBLE CASK MATURED 3/70/40 @ EURO 134.00
T2 / CODED / REFILL / GBX / EAN CODE 500299298022 / ON THE FLOOR

244CS ABERLOUR 14YRS DOUBLE CASK MATURED 3/70/40 @ EURO 90.00
T2 / CODED / REFILL / EAN CODE 500299620915 / ON THE FLOOR
If intrested we can also send you our full stock offer ex Loendersloot / Newcorp
We can offer many more items on request (Spirits/Waters/Wines/Beers)
Based on your request we can offer ex warehouse Holland or CNF port of destination
+31 6 29701510
wilfred@liquidsupply.nl
"""

# 🧩 Convert each non-empty line into a row
raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
df = pd.DataFrame({"Наименование": raw_lines})


def color_diff(a: str, b: str) -> str:
    """Word-level diff with color output (always visible)."""
    a_words, b_words = a.split(), b.split()
    sm = difflib.SequenceMatcher(None, a_words, b_words)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.extend(b_words[j1:j2])
        elif tag == "replace":
            out.append(Fore.YELLOW + " ".join(b_words[j1:j2]) + Style.RESET_ALL)
        elif tag == "insert":
            out.append(Fore.GREEN + " ".join(b_words[j1:j2]) + Style.RESET_ALL)
        elif tag == "delete":
            out.append(Fore.RED + " ".join(b_words[j1:j2]) + Style.RESET_ALL)
    return " ".join(out)



try:
    # 1️⃣ Make a copy of the original data
    df_raw = df.copy()

    # 2️⃣ Apply abbreviation conversion FIRST (for graph_normalizer input)
    df_abbr = df.copy()
    df_abbr["Наименование"] = df_abbr["Наименование"].apply(convert_abbreviation)

    # 3️⃣ Then normalize using graph_normalizer on the ABBREVIATED text
    df_norm = normalize_dataframe(df_abbr, col_name="Наименование")

    # 4️⃣ Now show how the raw text changed after both stages
    print("\n[OUTPUT: RAW vs PROCESSED (diff view)]\n")
    for raw, norm in zip(df_raw["Наименование"], df_norm["Наименование"]):
        if raw.strip() != norm.strip():
            diff = color_diff(raw, norm)
            print(f"{raw}\n→ {diff}\n")
        else:
            print(f"{raw}\n→ (no change)\n")


except Exception as e:
    print(f"[ERROR] normalize_dataframe() failed: {e}")
