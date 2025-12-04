import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import difflib
import pandas as pd
from colorama import Fore, Style


from core.graph_normalizer import normalize_dataframe
from utils.abbreviations_helper import convert_abbreviation

# 🧾 Just paste your text here — no need for quotes or commas
text = """
2200 cs Moët & Chandon Brut Imp. (no GBX) 6x75cl 12.5% T1 @ €150.00 cs, DAP Loend/PLG, 6–7 weeks
500 cs Moet Chandon Imperial Brut 6x75cl GBX,T2 @ 26,50€ /btl Exwork Van de Mark - Holland, 1 week after deposit
1500cs *12 btl Finlandia 50 cl - 2.75 eur/btl DAP Riga, lead time 2-3 weeks
360 cs *12 btl Glenfiddich 12yo GBX 50 cl - 15.80 eur/btl DAP Riga
12000 btl Hennessy VS GBX 70 cl -18.50 eur/btl DAP Riga, lead time 2-3 weeks
18000 btl JD 70 cl - 8.95 eur/btl DAP Riga, lead time 2 weeks
1800 btl JD 3 L with cradle - 49.5 eur/btl DAP Riga, lead time 3-4 weeks
3150 *6 btl Olmeca Silver 50 cl - 5.05 eur/btl DAP Riga
3125*6 btl Jameson 70 cl - 8.03 eur/btl DAP Riga
2300*12 btl Jameson 50 cl - 6.10 eur/btl DAP Riga
3000 cs *6 btl Jim Beam - 5.20 eur/btl DAP Riga
2200 cs*6 btl Moët & Chandon Brut без ПУ - 25,80 eur/btl DAP Riga
2200 cs*6 btl Veuve Clicquot без ПУ - 30.90 eur/btl DAP Riga
3125 cs*6 btl Tullamore Dew (Round Bottle) 70 cl - 5.33 eur/btl DAP Riga, lead time 1-2 weeks


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
