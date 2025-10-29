# organizer.py
# категоризация по словарю брендов + ключевым словам и сортировка

import re
import pandas as pd
from typing import List, Tuple

# Порядок для сортировки в итоговом файле
CATEGORY_ORDER: List[str] = [
    "Whiskey", "Cognac", "Brandy", "Vodka", "Gin", "Rum", "Tequila",
    "Liqueur", "Champagne", "Wine", "Beer" "Без категории"
]

# Бренды → категория (покрыл то, что встречается у тебя в логах и в примерах)
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
    # Beer
    (re.compile(r"\b(budweiser|heineken|guinness|leffe|krombacher|hofbrau|peroni|pilsner\s+urquell|stella\s+artois|corona|carlsberg|asahi|tuborg|paulaner|hoegaarden|warsteiner|bitburger)\b", re.I), "Beer"),

    # Whiskey – шотландцы и не только
    (re.compile(r"\b(balvenie|caol\s*ila|glen\s*scotia|glenfarclas|glenlivet|glenmorangie|loch\s*lomond|singleton|tomatin|tomintoul)\b", re.I), "Whiskey"),
    (re.compile(r"\b(chichibu|cutty\s*sark|teacher'?s\s*highland\s*cream|mars\s*kasei|senju)\b", re.I), "Whiskey"),
    (re.compile(r"\b(jim\s*beam|basil\s*hayden|baker'?s|1792|buchanan'?s)\b", re.I), "Whiskey"),

    # Champagne
    (re.compile(r"\b(dom\s*perignon|veuve\s*clicquot|moe?t|ruinart|krug|jacquesson|veuve\s*cliquot?|barons?\s*de\s*rothschild)\b", re.I), "Champagne"),

    # Wine
    (re.compile(r"\b(aalto|barista|braida|cloudy\s*bay|lafite|egon\s*muller|los\s*vascos|luce|penfolds|quintarelli|rioja\s*alta|sassicaia|tenuta\s*san\s*guido|ornellaia|Minuty|opus\s*one)\b", re.I), "Wine"),
    (re.compile(r"\b(the\s*chocolate\s*block|Tenuta\s*di\s*biserno|domaines|dal\s*forno)\b", re.I), "Wine"),

    # Liqueur / Vermouth
    (re.compile(r"\b(martini|bols|disaronno|passoa|tia\s*maria|vecchia\s*romagna|villa\s*massa|malibu|molinari|meukow)\b", re.I), "Liqueur"),

    # Tequila
    (re.compile(r"\b(cazadores|don\s*julio|olmeca|teremana)\b", re.I), "Tequila"),

    # Brandy / Calvados
    (re.compile(r"\b(boulard)\b", re.I), "Brandy"),

    # Chinese Baijiu
    (re.compile(r"\b(moutai|kweichow)\b", re.I), "Baijiu"),
])

# Ключевые слова → категория (подстраховка, если бренд не узнали)
KEYWORD_RULES: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(blended\s+scotch\s+whisk\w+|single\s+malt|scotch|whisk(?:e)?y|bourbon|rye|tennessee|irish\s*whiskey|japanese\s*whisk\w+)\b", re.I), "Whiskey"),
    (re.compile(r"\bvodk\w+\b", re.I), "Vodka"),
    (re.compile(r"\bgin\b", re.I), "Gin"),
    (re.compile(r"\brum\b|\brhum\b|\bron\b", re.I), "Rum"),
    (re.compile(r"\btequil\w+\b|\bmezcal\b", re.I), "Tequila"),
    (re.compile(r"\bcognac\b", re.I), "Cognac"),
    (re.compile(r"\barmagnac\b|\bbrandy\b", re.I), "Brandy"),
    (re.compile(r"\bliqueur\b|\bliquer\b|\bamaro\b|\bsambuca\b|\btriple\s+sec\b|\bcr[eè]me\s+de\b|\baperitif\b|\baperitivo\b", re.I), "Liqueur"),
    (re.compile(r"\bchampagne\b|\bprosecco\b|\bcava\b", re.I), "Champagne"),
    (re.compile(r"\bwine(s)?\b", re.I), "Wine"),
    (re.compile(r"\bbeer\b|\blager\b|\bpils\b|\bstout\b|\bipa\b|\bale\b", re.I), "Beer"),
]

def _categorize_name(name: str) -> str:
    s = str(name or "").lower()

    # 1) Брендовые правила (приоритетнее)
    for rx, cat in BRAND_TO_CATEGORY:
        if rx.search(s):
            return cat

    # 2) Ключевые слова
    for rx, cat in KEYWORD_RULES:
        if rx.search(s):
            return cat

    return "Без категории"

def attach_categories(df: pd.DataFrame, name_col: str = "name", out_col: str = "Тип") -> pd.DataFrame:
    """Заполняет колонку 'Тип' на основе наименования."""
    df = df.copy()
    if out_col not in df.columns:
        df[out_col] = None
    mask = df[out_col].isna() | df[out_col].astype(str).str.strip().eq("")
    df.loc[mask, out_col] = df.loc[mask, name_col].map(_categorize_name)
    return df

def order_by_category(df: pd.DataFrame, category_col: str = "Тип") -> pd.DataFrame:
    """Стабильная сортировка: сначала по порядку категорий, затем по имени."""
    df = df.copy()
    order_map = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    df["_cat_ord"] = df[category_col].map(lambda x: order_map.get(x, len(order_map)))
    df.sort_values(by=["_cat_ord", "name"], inplace=True, kind="stable")
    df.drop(columns=["_cat_ord"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df
