# product_detector.py - определяет продуктовую строку без цены
import re
import logging
from utils.logger import setup_logging
from libraries.regular_expressions import RX_BPC, RX_BPC_TRIPLE, RX_VOLUME
from utils.text_extractors import RX_BOTTLE, RX_CASE

logger = logging.getLogger(__name__)


RX_CS = re.compile(r"\b\d+\s*cs\b", re.I)
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
        logger.debug("[PROD_DETECT] empty string → reject")
        return False

    s = s.strip()
    logger.debug("[PROD_DETECT] CHECK %r", s)

    # -------------------------------------------------
    # HARD GATE 1 — цена ЗАПРЕЩЕНА
    # -------------------------------------------------
    for rx in RX_BOTTLE:
        if rx.search(s):
            logger.debug("[PROD_DETECT] reject: bottle price detected (%s)", rx.pattern)
            return False

    for rx in RX_CASE:
        if rx.search(s):
            logger.debug("[PROD_DETECT] reject: case price detected (%s)", rx.pattern)
            return False

    # -------------------------------------------------
    # HARD GATE 2 — ASCII-плотность
    # -------------------------------------------------
    letters = sum(c.isalpha() for c in s)
    digits  = sum(c.isdigit() for c in s)

    logger.debug(
        "[PROD_DETECT] density: letters=%d digits=%d",
        letters, digits
    )

    if letters < 4:
        logger.debug("[PROD_DETECT] reject: letters < 4")
        return False

    if digits < 1:
        logger.debug("[PROD_DETECT] reject: digits < 1")
        return False

    # -------------------------------------------------
    # SCORING
    # -------------------------------------------------
    score = 0
    reasons = []

    # --- PACKAGING ---
    if RX_BPC.search(s):
        score += 2
        reasons.append("BPC")

    if RX_BPC_TRIPLE.search(s):
        score += 2
        reasons.append("BPC_TRIPLE")

    if RX_VOLUME.search(s):
        score += 1
        reasons.append("VOLUME")

    # --- QUANTITY ---
    if RX_CS.search(s):
        score += 1
        reasons.append("CS")

    # --- PRODUCT SEMANTICS ---
    if RX_YEAR.search(s):
        score += 1
        reasons.append("YEAR")

    if RX_AGE.search(s):
        score += 1
        reasons.append("AGE")

    # --- TEXT DENSITY BOOST ---
    if letters >= 8:
        score += 1
        reasons.append("LETTERS>=8")

    if digits >= 3:
        score += 1
        reasons.append("DIGITS>=3")

    logger.debug(
        "[PROD_DETECT] score=%d reasons=%s",
        score, reasons
    )

    # -------------------------------------------------
    # FINAL DECISION
    # -------------------------------------------------
    if score >= 3:
        logger.debug("[PROD_DETECT] ACCEPT")
        return True
    else:
        logger.debug("[PROD_DETECT] reject: score < 3")
        return False
