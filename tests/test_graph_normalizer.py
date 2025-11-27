import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import difflib
import pandas as pd
from colorama import Fore, Style


from core.graph_normalizer import normalize_dataframe
from utils.abbreviations_helper import convert_abbreviation

# 🧾 Just paste your text here — no need for quotes or commas
text = """
1600 cs Peachtree 6×70cl 20% RF T2, CODED @ EUR 34.33€ cs, Exwork Loendersloot, On Floor
1500 cs Jose Cuervo Especial Silver 6×70cl 35% RF T2, CODED @ EUR 34.55€ cs, Exwork Loendersloot, On Floor
20 cs The Macallan 15YO Double Cask 6×70cl 43% RF T2, CODED @ EUR 596.74€ cs, Exwork Loendersloot, On Floor
-
22 cs The Macallan 18YO Double Cask 6×70cl 43% RF T2, CODED @ EUR 1238.80€ cs, Exwork Loendersloot, On Floor
500 cs Tia Maria 12×70cl 20% RF T2, CODED @ EUR 84.74€ cs, Exwork Loendersloot, On Floor

350 cs William Lawson’s 6×100cl 40% RF T2, CODED @ EUR 30.00€ cs, Exwork Loendersloot, On Floor
1000 cs Hendrick’s Gin 6×70cl 41.4% RF T2, CODED @ EUR 87€ cs, Exwork Loendersloot, On Floor
275 cs Chivas Regal 12yo GBX with Cradle 2x450cl 40% T1 @  181€ cs, Exwork Loendersloot, on Floor
110 cs Glenlivet Founder’s Reserve 6x70cl GBX, RF, T2@ € 92 cs, Exwork Loendersloot, on floor
110 cs Chivas Regal 12yo GBX with Cradle 2x450cl 40% T1 @  181€ cs, Exwork Loendersloot, on Floor

1200 cs Glenlivet Founder’s Reserve 6x70cl GBX, RF, T2@ € 92 cs, Exwork Loendersloot, 3-4 weeks after deposit

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
