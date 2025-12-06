import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import difflib
import pandas as pd
from colorama import Fore, Style


from core.graph_normalizer import normalize_dataframe
from utils.abbreviations_helper import convert_abbreviation

# 🧾 Just paste your text here — no need for quotes or commas
text = """
Dom Perignon vintage naked 6 x 75cl at 143 USD 
Dom Perignon Rose GBX 6 x 75cl at 242.60 USD 

Moet & Chandon Imperial Brut Naked 6 x 75cl at 31.50 USD
Rose Imperial GBX 6 x 75cl at 38.80 USD
Ice Imperial Naked 6 x 75cl at 37.15 USD 
Ice Imperial Rose naked 6 x 75cl at 37.15 USD 
Nectar Imperial naked 6 x 75cl at 34.32 USD
Nectar Imperial Rose naked 6 x 75cl at 39 USD

Veuve Clicquot YL Naked 6 x 75cl at 34.95 USD

DAP Loendersloot
MOQ 10 pallets, can be mixed
4/5 weeks lead time after deposit 

Kai
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
