#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

# text_extractors.py
import re
import pandas as pd
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

class PriceExtractor:
    """
    Унифицированный извлекатель цен.
    Состояния:
      - 'bottle'  → ищет цену за бутылку
      - 'case'    → ищет цену за кейс
      - 'derived' → вычисляет недостающую цену из другой и кол-ва бутылок
    """

    RX_BOTTLE = [
        re.compile(r'(?:eur|euro|€|usd|gbp)\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:per\s*bottle|btl)\b', re.I),
        re.compile(r'([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\s*(?:per\s*bottle|btl)\b', re.I),
        re.compile(r'price\s+per\s*bottle\s+([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\b', re.I),
    ]

    RX_CASE = [
        re.compile(r'(?:eur|euro|€|usd|gbp)\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:per\s*case|case|cs)\b', re.I),
        re.compile(r'([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\s*(?:per\s*case|case|cs)\b', re.I),
        re.compile(r'price\s+per\s*case\s+([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\b', re.I),
    ]

    RX_BPC = re.compile(r'(\d{1,2})\s*[x×]\s*\d{1,3}', re.I)

    def __init__(self):
        self.state = "init"
        self.price_bottle = None
        self.price_case = None
        self.bottles_per_case = None

    # --- main entry ---
    def extract(self, text: str) -> dict:
        if not text:
            return {}

        s = str(text)
        self._extract_bpc(s)

        # 1️⃣ bottle price direct
        self.price_bottle = self._match_any(s, self.RX_BOTTLE)
        if self.price_bottle is not None:
            self.state = "bottle"
            print(f"[DEBUG extractor] found bottle price → {self.price_bottle}")
            self._derive_case()
            return self._result()

        # 2️⃣ case price direct
        self.price_case = self._match_any(s, self.RX_CASE)
        if self.price_case is not None:
            self.state = "case"
            print(f"[DEBUG extractor] found case price → {self.price_case}")
            self._derive_bottle()
            return self._result()

        # 3️⃣ derived nothing
        self.state = "none"
        print(f"[DEBUG extractor] no price found in {text!r}")
        return self._result()

    # --- helpers ---
    def _match_any(self, text, patterns):
        for rx in patterns:
            m = rx.search(text)
            if m:
                return float(m.group(1).replace(",", "."))
        return None

    def _extract_bpc(self, text):
        m = self.RX_BPC.search(text)
        if m:
            self.bottles_per_case = int(m.group(1))

    def _derive_case(self):
        if self.price_bottle and self.bottles_per_case:
            self.price_case = round(self.price_bottle * self.bottles_per_case, 2)
            self.state = "derived"
            print(f"[DEBUG extractor] derived case price {self.price_case} = {self.price_bottle}×{self.bottles_per_case}")

    def _derive_bottle(self):
        if self.price_case and self.bottles_per_case:
            self.price_bottle = round(self.price_case / self.bottles_per_case, 4)
            self.state = "derived"
            print(f"[DEBUG extractor] derived bottle price {self.price_bottle} = {self.price_case}/{self.bottles_per_case}")

    def _result(self):
        return {
            "state": self.state,
            "price_bottle": self.price_bottle,
            "price_case": self.price_case,
            "bottles_per_case": self.bottles_per_case,
        }


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

