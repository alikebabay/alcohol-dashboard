import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import difflib
import pandas as pd
from colorama import Fore, Style


from core.graph_normalizer import normalize_dataframe
from utils.abbreviations_helper import convert_abbreviation

# 🧾 Just paste your text here — no need for quotes or commas
text = """
1770 Glasgow Single Malt Original 
Aberfeldy 12 YO Madeira Cask 
Aberfeldy 16 YO Madeira Cask 
Aberlour 16 YO Double Cask 
Aberlour A'bunadh Alba Batch 7
Aberlour A'bunadh Alba Batch 7 
Absolut Vodka 
Absolut Vodka 
Absolut Vodka Keith Haring Edition 
Amaro Averna Siciliano
Aperol
Arbikie Highland Rye 1794 Single Grain 2020 Release 
Ardbeg 10 YO 
Ardbeg 10 YO 
Ardbeg 5 YO Wee Beastie
Ardbeg An Oa
Ardbeg Corryvreckan 
Ardbeg Smoketrails Cote Rotie 
Ardbeg Smoketrails V3 Napa Valley 
Ardbeg Uigeadail 
Arran Barrel Reserve 
Arran Port Cask Finish 
Arran Quarter Cask 
Arran Sauternes Cask
Arran Sherry Cask 
Auchentoshan American Oak 
Auchentoshan Blood Oak  
Auchentoshan Dark Oak 
Baileys 03-2027
Baileys 11-2026 
Baileys 11-2026 
Ballantines  
Ballantines 15 YO Glentauchers 
Balvenie 12 YO Double Wood   
Balvenie 12 YO Golden Cask   
Balvenie 12 YO Golden Cask T1  Non European Goods 
Balvenie 12 YO Sweet Toast of American Oak 
Balvenie 16 YO French Oak 
Balvenie 18 YO PX Cask  



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
