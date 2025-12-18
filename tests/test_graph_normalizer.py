import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import difflib
import pandas as pd
from colorama import Fore, Style


from core.graph_normalizer import normalize_dataframe
from utils.abbreviations_helper import convert_abbreviation

# 🧾 Just paste your text here — no need for quotes or commas
text = """
Magners cider bottle 24x330ml Locatie: van der Mark | Cases: 2160cs | BBD: fresh | Prijs: €20.25

Estrella damm bottle 24x330ml Locatie: van der Mark | Cases: 1728cs | BBD: fresh | Prijs: €12.30

Stella artois can 24x500ml Locatie: van der Mark | Cases: 1840cs | BBD: fresh | Prijs: €13.75

Grolsch bottle 24x330ml Locatie: van der Mark | Cases: 1872cs | BBD: fresh | Prijs: €13.99

Pilsner urquell bottle 24x330ml Locatie: van der Mark | Cases: 1728cs | BBD: fresh | Prijs: €13.50

Staropramen bottle 24x330ml Locatie: van der Mark | Cases: 1728cs | BBD: fresh | Prijs: €13.15

Staropramen can 24x500ml Locatie: van der Mark | Cases: 1890cs | BBD: fresh | Prijs: €15.05

Coors bottle 24x330ml Locatie: van der Mark | Cases: 1728cs | BBD: fresh | Prijs: €13.10

Coors can 24x500ml Locatie: van der Mark | Cases: 2016cs | BBD: fresh | Prijs: €14.90

Strongbow cider British dry bottle 24x330ml Locatie: van der Mark | Cases: 2016cs | BBD: fresh | Prijs: €16.10

Strongbow cider British dry can 24x500ml Locatie: van der Mark | Cases: 2060cs | BBD: fresh | Prijs: €14.00

John smiths extra smooth can 24x500ml  Locatie: van der Mark | Cases: 1890cs | BBD: fresh | Prijs: €14.10

Paulaner hefen weizen can 24x500ml Locatie: van der Mark | Cases: 1890cs | BBD: fresh | Prijs: €16.50
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
