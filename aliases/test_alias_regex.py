"""
Тест регулярки для city_aliases.json и incoterms_aliases.json.
Показывает, какие ключи реально матчятся с тестовым текстом.
"""

import re, json, pprint

# --- настройки ---------------------------------------------------------------
TEXT = "Price per case EUR EXW NL"
CITY_PATH = "aliases/city_aliases.json"
INCOTERM_PATH = "aliases/incoterms_aliases.json"

# --- загрузка алиасов --------------------------------------------------------
with open(CITY_PATH, encoding="utf-8") as f:
    city_aliases = json.load(f)["aliases"]
with open(INCOTERM_PATH, encoding="utf-8") as f:
    incoterms_aliases = json.load(f)["aliases"]

print(f"[INFO] Загружено {len(city_aliases)} городов и {len(incoterms_aliases)} инкотермсов")

# --- сборка regex ------------------------------------------------------------
pattern = r"\b(" + "|".join(map(re.escape, list(city_aliases.keys()) + list(incoterms_aliases.keys()))) + r")\b"
rx = re.compile(pattern, re.I)

# --- тест -------------------------------------------------------------------
print(f"\n[TEST] Текст: {TEXT!r}")
matches = rx.findall(TEXT)
print(f"[RESULT] Найдено совпадений: {len(matches)}")
if matches:
    for m in matches:
        norm = city_aliases.get(m.lower()) or incoterms_aliases.get(m.lower())
        print(f"  → '{m}' → '{norm}'")
else:
    print("⚠️  Ничего не найдено")

# --- отладочная часть -------------------------------------------------------
print("\n[DEBUG] Первые 20 алиасов в паттерне:")
pprint.pp(list(city_aliases.keys())[:20])
print("\n[DEBUG] Фрагмент регулярки:")
print(pattern[:200] + " ...")
