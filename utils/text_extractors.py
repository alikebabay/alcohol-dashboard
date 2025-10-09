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
            
            return val
    
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
            
            return val
    
    return None


def extract_access(text: str):
    """
    Detects stock status or lead time: 'On stock', 'T1', 'T2', 'TBO', 'on floor',
    'lead time 2 weeks', '7 days after deposit', '2-3 weeks', etc.
    Returns combined string like 'T2, 2 weeks'.
    """
    if not text:
        return None
    s = str(text).strip()

    parts = []
    patterns = [
        re.compile(r'\b(T[12]|TBO)\b', re.I),
        re.compile(r'\b(on\s*(?:stock|floor)|in\s*stock|available|ready)\b', re.I),
        re.compile(r'\blead\s*time\s*\d+\s*(?:days?|weeks?)\b', re.I),
        re.compile(r'\b\d+\s*(?:-\s*\d+)?\s*(?:days?|weeks?)\b(?:\s*after\s*deposit(?:\s*\w+)?)?', re.I),
    ]
    for rx in patterns:
        m = rx.search(s)
        if m:
            parts.append(m.group(0).strip())

    if parts:
        val = ", ".join(dict.fromkeys(parts))
        
        return val

    
    return None


def extract_location(text: str):
    """
    Detects and normalizes shipment/warehouse location.
    Examples:
      'Dap Riga' → 'DAP Riga'
      'Exw Riga or Loendersloot' → 'EXW Riga or Loendersloot'
      'Ex Loen' → 'EXW Loendersloot'
    Returns normalized string with proper capitalization.
    """
    if not text:
        return None
    s = str(text).strip()

    # --- known city name expansions ---
    CITY_ALIASES = {
        "loen": "Loendersloot",
        "niderland": "Netherlands",
        "rig": "Riga",
        "riga": "Riga",
        "rot": "Rotterdam",
        "amst": "Amsterdam",
    }

    # --- match location phrases ---
    patterns = [
        re.compile(r'\b(EXW|Exw|Ex|DAP|Dap|FOB|Fob|CIF|Cif)\b[\s\-]*([A-Za-zА-Яа-я\-]+(?:\s+or\s+[A-Za-zА-Яа-я\-]+)?)', re.I),
        re.compile(r'\b(on\s*floor|warehouse|origin|склад|место\s*загрузки)\b[:\- ]*([A-ZА-Я][A-Za-zА-Яа-я0-9\- ]+)?', re.I),
    ]
   

    for rx in patterns:
        m = rx.search(s)
        if not m:
            continue

        prefix = m.group(1) if len(m.groups()) >= 1 else None
        body = m.group(2) if len(m.groups()) >= 2 else ""
        raw = (prefix or "") + " " + (body or "")
        raw = raw.strip()

        

        # --- normalize prefix ---
        norm_prefix = None
        for candidate in ["EXW", "DAP", "FOB", "CIF"]:
            if raw.lower().startswith(candidate.lower()[:2]):
                norm_prefix = candidate
                break
        

        # --- expand city names if abbreviated ---
        parts = raw.split()
        norm_parts = []
        for p in parts[1:]:
            p_clean = p.strip(",. ").lower()
            expanded = CITY_ALIASES.get(p_clean, CITY_ALIASES.get(p_clean[:4], p))
            # keep proper capitalization
            expanded = expanded[0].upper() + expanded[1:] if expanded else p
            norm_parts.append(expanded)
            
        city_part = " ".join(norm_parts).replace("  ", " ").strip()
        

        if norm_prefix and city_part:
            val = f"{norm_prefix} {city_part}"
        elif norm_prefix:
            val = norm_prefix
        else:
            val = raw

        # cleanup
        val = val.replace("  ", " ").strip().rstrip(",")
        
        return val

   
    return None

