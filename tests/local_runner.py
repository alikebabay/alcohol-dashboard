from core.graph_normalizer import extract_brand_series, _normalize, load_brands, find_canonical, driver

BRANDS = load_brands()

raw = "Nikka from barrel +glass 50cl, 200 bottles on floor Exw Riga price 35 eur per bottle"

print("\n--- TEST START ---")
brand, series = extract_brand_series(raw)
print(f"[RESULT] brand='{brand}', series='{series}'")

# проверим канон
with driver.session() as s:
    found = s.execute_read(find_canonical, brand, series, raw)
    print(f"[CANONICAL FOUND] {found}")
print("--- TEST END ---")
