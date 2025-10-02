# text_extractors.py
import re
from distillator import _extract_volume, _infer_bpc_from_name, RX_ABV

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
    Находит цену за бутылку: '28.75 per bottle', '€28.75/btl', 'Euro 28.75 per bottle'
    """
    if not text:
        return None
    m = re.search(
        r'(?:@?\s*(?:eur|euro|€|usd|gbp))?\s*'      # опциональная валюта перед числом (и @)
        r'([0-9]+(?:[.,][0-9]+)?)\s*'               # число
        r'(?:per\s*bottle|btl)\b',                  # маркер бутылки
        str(text), re.I
    )
    if m:
        val = float(m.group(1).replace(",", "."))
        print(f"[DEBUG extractor] bottle match in {text!r} → {val}")
        return val
    else:
        print(f"[DEBUG extractor] bottle no match in {text!r}")
    return None


def extract_price_per_case(text: str):
    """
    Находит цену за кейс: '172.5 per case', '€172.5/cs'
    """
    if not text:
        return None
    m = re.search(
        r'(?:@?\s*(?:eur|euro|€|usd|gbp))?\s*'      # опциональная валюта
        r'([0-9]+(?:[.,][0-9]+)?)\s*'               # число
        r'(?:per\s*case|case|cs)\b',                # маркер кейса
        str(text), re.I
    )
    if m:
        val = float(m.group(1).replace(",", "."))
        print(f"[DEBUG extractor] case match in {text!r} → {val}")
        return val
    else:
        print(f"[DEBUG extractor] case no match in {text!r}")
    return None
