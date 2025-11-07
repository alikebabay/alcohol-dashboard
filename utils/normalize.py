import re, unicodedata

def normalize(s: str) -> str:
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
    s = re.sub(r"[^a-z0-9 &'%+]", " ", s)
    return re.sub(r"\s+", " ", s).strip()
