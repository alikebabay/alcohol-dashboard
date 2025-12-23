# product_detector.py - определяет продуктовую строку без цены
import re
from libraries.regular_expressions import RX_BPC, RX_BPC_TRIPLE
from utils.text_extractors import RX_BOTTLE, RX_CASE

RX_CS = re.compile(r"\b\d+\s*cs\b", re.I)
RX_VOLUME_CL = re.compile(r"\b\d{2,3}\s*cl\b", re.I)
RX_YEAR = re.compile(r"\b(19\d{2}|20\d{2})\b")
RX_AGE = re.compile(r"\b\d{1,2}\s*yo\b", re.I)

# letters / digits считаем ПОСИМВОЛЬНО (ASCII-плотность строки)
# why letters >= 4:
#   <4 букв = почти всегда не продукт:
#     "EXW", "T2", "Daan", "GB", "NV"
#   продуктовые строки всегда содержат хотя бы несколько слов
#
# why digits >= 1:
#   продукт БЕЗ ЦЕНЫ всё равно содержит цифры:
#     упаковка (6/70/40), объём (75cl), возраст (10yo), год (2015)
#   строки без цифр = shared-meta / дисклеймеры

def detect_product_without_price(s: str) -> bool:
    if not s:
        return False

    s = s.strip()

    # --- HARD GATE 1: price MUST NOT exist ---
    if any(rx.search(s) for rx in RX_BOTTLE) or any(rx.search(s) for rx in RX_CASE):
        return False
    
    # считаем буквы и цифры
    letters = sum(c.isalpha() for c in s)
    digits = sum(c.isdigit() for c in s)

    # --- HARD GATE 2: minimal density ---
    if letters < 4 or digits < 1:
        return False

    score = 0

    # --- PACKAGING ---
    if RX_BPC.search(s) or RX_BPC_TRIPLE.search(s):
        score += 2
    if RX_VOLUME_CL.search(s):
        score += 1

    # --- QUANTITY ---
    if RX_CS.search(s):
        score += 1

    # --- PRODUCT SEMANTICS ---
    if RX_YEAR.search(s):
        score += 1
    if RX_AGE.search(s):
        score += 1

    # --- TEXT DENSITY ---
    if letters >= 8:
        score += 1
    if digits >= 3:
        score += 1

    # --- FINAL THRESHOLD ---
    return score >= 3
