import re, unicodedata

def normalize(s: str) -> str:
    if not isinstance(s, str):
        return ""
    # Normalize Unicode (но не убиваем апострофы)
    s = (
        s.replace("’", "'")
         .replace("‘", "'")
         .replace("`", "'")
         .replace("´", "'")
    )
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    # больше не удаляем апострофы
    # ✅ allow '&' to stay — it’s meaningful in names like J&B, H&M
    # 🟢 preserve dots inside short abbreviations (e.g. V.S, V.S.O.P, X.O)
    s = re.sub(r"(?<=\b[a-z])\.(?=[a-z]\b)", ".", s)
    # then remove other punctuation (but keep &, ', %, +, and abbreviation dots)
    s = re.sub(r"[^a-z0-9 &'%+\.]", " ", s)
    return re.sub(r"\s+", " ", s).strip()
