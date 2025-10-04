# text_extractors.py
import re
from core.distillator import _extract_volume, _infer_bpc_from_name, RX_ABV

def extract_volume(text: str):
    return _extract_volume(text)

def extract_bottles_per_case(text: str):
    return _infer_bpc_from_name(text)

def extract_abv(text: str):
    if not isinstance(text, str):
        return None
    m = RX_ABV.search(text)
    if m:
        return float(m.group(0).replace("%", "").replace(",", "."))
    return None

def extract_price_per_bottle(text: str):
    """
    Находит цену за бутылку: '28.75 per bottle', '€28.75/btl', 'Euro 28.75 per bottle',
    а также '28.75 eur per bottle', 'price per bottle 13.2 eur', 'price 13 eur per bottle'.
    """
    if not text:
        return None

    s = str(text)
    patterns = [
        # вариант: валюта перед числом ("€28.75 per bottle")
        re.compile(r'(?:@?\s*(?:eur|euro|€|usd|gbp))\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:per\s*bottle|btl)\b', re.I),
        # вариант: число перед валютой ("28.75 eur per bottle")
        re.compile(r'([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\s*(?:per\s*bottle|btl)\b', re.I),
        # вариант: price per bottle 13.2 eur
        re.compile(r'price\s+per\s+bottle\s+([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\b', re.I),
        # вариант: price 13 eur per bottle
        re.compile(r'price\s+([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\s+per\s+bottle\b', re.I),
    ]
    for rx in patterns:
        m = rx.search(s)
        if m:
            val = float(m.group(1).replace(",", "."))
            print(f"[DEBUG extractor] bottle match in {text!r} → {val}")
            return val
    print(f"[DEBUG extractor] bottle no match in {text!r}")
    return None


def extract_price_per_case(text: str):
    """
    Находит цену за кейс: '172.5 per case', '€172.5/cs', 'price 180 eur per case'
    """
    if not text:
        return None
    s = str(text)
    patterns = [
        # стандарт: "€183 per case"
        re.compile(r'(?:@?\s*(?:eur|euro|€|usd|gbp))?\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:per\s*case|case|cs)\b', re.I),
        # вариант: "price 180 eur per case"
        re.compile(r'price\s+([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\s+per\s*case\b', re.I),
    ]
    for rx in patterns:
        m = rx.search(s)
        if m:
            val = float(m.group(1).replace(",", "."))
            print(f"[DEBUG extractor] case match in {text!r} → {val}")
            return val
    print(f"[DEBUG extractor] case no match in {text!r}")
    return None


