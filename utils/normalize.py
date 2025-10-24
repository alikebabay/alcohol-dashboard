import re, unicodedata
# ==========================================================
# HELPERS
# ==========================================================
def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower().replace("&", "and")
    # collapse apostrophes (e.g. "grant's" -> "grants")
    s = re.sub(r"(\w)'s\b", r"\1s", s)
    s = re.sub(r"'", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()