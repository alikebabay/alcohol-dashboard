import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.logger import setup_logging

import pandas as pd
from io import BytesIO
from colorama import Fore, Style

from core.parser import parse_excel

setup_logging()
FILE = "test_documents/Connexion Offer List Week 38 -2025.xlsx"


def load_xlsx(path: str) -> BytesIO:
    with open(path, "rb") as f:
        return BytesIO(f.read())


def color(s, c):
    return c + s + Style.RESET_ALL


try:
    print("\n=== PARSER DEBUG TEST ===\n")

    src = load_xlsx(FILE)

    df, mappings = parse_excel(src)

    print(Fore.CYAN + f"\n[FILE] {FILE}" + Style.RESET_ALL)
    print(Fore.GREEN + f"\n[DF SHAPE] {df.shape}" + Style.RESET_ALL)

    print("\n[MAPPINGS]:")
    for sheet, m in mappings.items():
        print(f"  sheet={sheet}")
        print(f"    header_row={m['header_row']}")
        print(f"    columns={m['columns']}")

    

except Exception as e:
    print(Fore.RED + f"[ERROR] parse_excel failed: {e}" + Style.RESET_ALL)
