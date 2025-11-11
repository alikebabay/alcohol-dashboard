import re

def _extract_label_number(s: str):
    m = re.search(r"\b([a-z]+)\s*[-]?\s*(\d{1,3})\b", s.lower())
    if not m:
        return None, None
    return m.group(1), int(m.group(2))

def _same_label_number(a: str, b: str):
    la, na = _extract_label_number(a)
    lb, nb = _extract_label_number(b)
    if la and lb and la[:3] == lb[:3] and na and nb:
        return na == nb
    return False