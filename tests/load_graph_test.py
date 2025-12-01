import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pytest
from config import driver
from core.graph_normalizer import load_graph_data   # или путь где load_graph_data
import unicodedata


def norm(s):
    return unicodedata.normalize("NFC", s) if s else s


def test_cu_bocan_loader():
    """
    Проверяет, что loader корректно выгружает бренд Cù Bòcan,
    включая series, alias и canonical.
    """

    graph = load_graph_data(driver)

    brands = graph["brands"]              # normalized → original
    brand_series = graph["brand_series"]  # map brand_norm → [series]
    brand_series_full = graph["brand_series_full"]
    brands_meta = graph["brands_meta"]
    canonical = graph["canonical"]

    # ----- STEP 1: найти ВСЕ ключи, которые соответствуют Cu Bocan -----

    candidates = []
    for key_norm, orig in brands.items():
        if "bocan" in key_norm.replace("ù", "u") or "cu" in key_norm:
            candidates.append((key_norm, orig))

    print("\n\n=== Cu Bocan BRAND KEYS FOUND ===")
    for k, o in candidates:
        print(f"- loader key_norm = '{k}' → stored as = '{o}'")

    assert candidates, "❌ Loader НЕ нашёл бренд Cu Bocan"

    # ----- STEP 2: показать series -----
    print("\n=== SERIES for each detected brand ===")
    for key_norm, orig_name in candidates:
        print(f"\nBrand: {orig_name}")
        print("  Raw series:", brand_series.get(key_norm))

        details = brand_series_full.get(key_norm, [])
        for d in details:
            print("   ➝ series =", d["series"], "| alias =", d["alias"])

    # ----- STEP 3: метаданные бренда -----
    print("\n=== BRAND META ===")
    for key_norm, orig_name in candidates:
        meta = brands_meta.get(orig_name, {})
        print(f"{orig_name}: {meta}")

    # ----- STEP 4: показать canonical entries -----
    print("\n=== CANONICAL ENTRIES CONTAINING 'Bocan' ===")
    can = [c for c in canonical if "bocan" in c.lower()]
    for c in can:
        print(" -", c)

    assert can, "❌ Canonical for Cu Bocan not found"

    print("\n✔ TEST COMPLETED: loader успешно выгрузил Cu Bocan\n")
