from rapidfuzz import fuzz, process
import unicodedata
import re

from libraries.regular_expressions import RX_CURRENCY_MARKER


#helper funcions for brand match
def has_price(s: str) -> bool:
    return bool(RX_CURRENCY_MARKER.search(s))


#helper for brand match in case of no product
def _unicode_normalize_text(s: str) -> str:
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s



def fuzzy_brand_match(s: str, brands: list[str]) -> bool:
    s = s.strip()
    if not s or has_price(s):
        return False

    s_norm = _unicode_normalize_text(s)

    # try prefix of first 1–3 words
    parts = s_norm.split()
    if not parts:
        return False

    # progressively test 3, 2, 1 word prefix
    for n in (3, 2, 1):
        prefix = " ".join(parts[:n])
        if len(prefix) < 4:
            continue

        match = process.extractOne(
            prefix,
            brands,
            scorer=fuzz.token_set_ratio,
            score_cutoff=88
        )

        if match:
            return True

    return False
