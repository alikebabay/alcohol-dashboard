import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import difflib
import pandas as pd
from colorama import Fore, Style


from core.graph_normalizer import normalize_dataframe
from utils.abbreviations_helper import convert_abbreviation

# 🧾 Just paste your text here — no need for quotes or commas
text = """
1044 cases Jose Cuervo 12x70cl @ Euro 72.5 per case, on floor, Ex Loendersloot
4979 bottles Grants Triple Wood 12YO 40% 100cl+GBX @ Euro 8.15 per bottle, Ex PLG on floor
FTL Ron Zacapa Solera Rum 70clx40% @ Euro 24 per bottle, 2 weeks, T2, DAP Loendersloot
750 cases Macallan 12YO Sherry Oak 6x70cl RF GBX @ USD 395 per case, 8 weeks, CFR any port
FTL Cointreau RF 6x70cl @ Euro 6.5 per bottle, 3 weeks, Ex Loendersloot
3000 cases Jameson 6x70cl @ Euro 7.8 per bottle, on floor, Ex New Corp
2000 cases (MOQ) Glenfiddich 12YO 6x70cl GBX @ Euro 17.75 per bottle, 1 week, Ex Loendersloot
FTL Ron Zacapa Solera Rum 1L GBX @ Euro 28.25 per bottle, 2 weeks, T2, DAP Loendersloot
19200 bottles Gordons 70cl @ Euro 3.95 per bottle, T2, DAP Top Logistics, 1 week
800 cases Gin Mare 6x1L @ Euro 18 per bottle, on floor, Ex New Corp

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
