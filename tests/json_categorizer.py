import json
import re
from typing import List, Tuple

# === твой список категорий ===
CATEGORY_ORDER: List[str] = [
    "Whiskey", "Cognac", "Brandy", "Vodka", "Gin", "Rum", "Tequila",
    "Liqueur", "Champagne", "Wine", "Beer", "Без категории"
]

# === твой список паттернов ===
BRAND_TO_CATEGORY: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(macallan|glenfiddich|glen\s*grant|dalmore|laphroaig|aultmore|old\s*pulteney|monkey\s*shoulder|ballantine'?s|ballantines|chivas|j(?:ohnnie)?\s*walker|j&b|grants?|famous\s*grouse|old\s*parr|bushmills|canadian\s*club|gentleman\s*jack|jack\s*daniels?|jameson|knob\s*creek|makers?\s*mark|nikka|russell'?s\s*reserve|suntory|wild\s*turkey|woodford\s*reserve|blantons?)\b", re.I), "Whiskey"),
    (re.compile(r"\b(hennessy|rémy|remy\s*martin|martell)\b", re.I), "Cognac"),
    (re.compile(r"\b(absolut|ciroc|grey\s*goose|ketel\s*one|stolichnaya|stoli|beluga)\b", re.I), "Vodka"),
    (re.compile(r"\b(beefeater|bombay\s*sapphire|hendrick'?s|the\s*botanist|ungava)\b", re.I), "Gin"),
    (re.compile(r"\b(havana\s*club|mount\s*gay|pusser'?s|pyrat|zacapa)\b", re.I), "Rum"),
    (re.compile(r"\b(1800|clase\s*azul|corazon|espolon|jose\s*cuervo|patr[oó]n)\b", re.I), "Tequila"),
    (re.compile(r"\b(baileys?|kahl[uú]a|j[aä]germeister|drambuie|cointreau|campari|aperol|southern\s*comfort|dekuyper|de\s*kuyper)\b", re.I), "Liqueur"),
]

BRAND_TO_CATEGORY.extend([
    (re.compile(r"\b(budweiser|heineken|guinness|leffe|krombacher|hofbrau|peroni|pilsner\s+urquell|stella\s+artois|corona|carlsberg|asahi|tuborg|paulaner|hoegaarden|warsteiner|bitburger)\b", re.I), "Beer"),
    (re.compile(r"\b(balvenie|caol\s*ila|glen\s*scotia|glenfarclas|glenlivet|glenmorangie|loch\s*lomond|singleton|tomatin|tomintoul)\b", re.I), "Whiskey"),
    (re.compile(r"\b(chichibu|mars\s*kasei|senju)\b", re.I), "Whiskey"),
    (re.compile(r"\b(jim\s*beam|basil\s*hayden|baker'?s|1792|buchanan'?s)\b", re.I), "Whiskey"),
    (re.compile(r"\b(dom\s*perignon|moe?t|ruinart|krug|jacquesson|veuve\s*cliquot?|barons?\s*de\s*rothschild)\b", re.I), "Champagne"),
    (re.compile(r"\b(aalto|barista|braida|cloudy\s*bay|lafite|egon\s*muller|los\s*vascos|luce|penfolds|quintarelli|rioja\s*alta|sassicaia|tenuta\s*san\s*guido|ornellaia|opus\s*one)\b", re.I), "Wine"),
    (re.compile(r"\b(martini|bols|disaronno|passoa|tia\s*maria|vecchia\s*romagna|villa\s*massa|malibu|molinari|meukow)\b", re.I), "Liqueur"),
    (re.compile(r"\b(cazadores|don\s*julio|olmeca|teremana)\b", re.I), "Tequila"),
    (re.compile(r"\b(boulard)\b", re.I), "Brandy"),
    (re.compile(r"\b(moutai|kweichow)\b", re.I), "Baijiu"),
])

# === обработка JSON ===
with open("canonical_mapping_master.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def detect_category(name: str) -> str:
    for pattern, cat in BRAND_TO_CATEGORY:
        if pattern.search(name):
            return cat
    return "Без категории"

for item in data:
    brand_name = item.get("brand") or item.get("canonical_name", "")
    item["category"] = detect_category(brand_name)

# === сортировка по CATEGORY_ORDER ===
def sort_key(item):
    try:
        return CATEGORY_ORDER.index(item["category"])
    except ValueError:
        return len(CATEGORY_ORDER)

data.sort(key=sort_key)

with open("canonical_mapping_master_with_categories.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
