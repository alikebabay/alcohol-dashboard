import re
import json

# --- 1) Грузим JSON ---
with open("libraries/location_aliases.json", encoding="utf-8") as f:
    loc = json.load(f)

CITY_ALIASES = loc["cities"]

# --- 2) Собираем RX_CITY ---
RX_CITY = "|".join(
    rf"(?:{re.escape(k)})"
    for k in CITY_ALIASES.keys()
)

print("RX_CITY =", RX_CITY)

# --- 3) RX_MONTH как в проекте ---
RX_MONTH = (
    r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
)

# --- 4) Собираем ПОЛНЫЙ ПАТТЕРН ---
pattern = (
    rf'\b(?:arriving|expected|delivery|shipping|ready|landing|ETA|schedule)\b'
    rf'(?:\s+(?:in|on|at|around|about|towards|by))?\s*'
    rf'(?:{RX_CITY}[\s\-]*)?'                    # ← города ИЗ JSON
    rf'(?:end|mid|early)?\s*'
    rf'(?:{RX_MONTH}|\d{{1,2}}[.\-/ ]?(?:{RX_MONTH})|\bweek\s*\d{{1,2}}\b)'
    rf'(?:\s*\d{{4}})?(?=[\s.,;]|$)'
)

print("\nFinal regex pattern:\n", pattern)

# --- 5) Тестовая строка как у тебя ---
text = "Shipping schedule: ETA Riga - 22NOV. Deposit we need to have until 26 SEP"

m = re.search(pattern, text, re.I)

print("\nMatch result:", m.group(0) if m else None)
