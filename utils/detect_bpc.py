# core/bpc_detector.py
import re
from libraries.regular_expressions import  RX_BPC, RX_BPC_STAR, RX_BPC_DASH, RX_BPC_TRIPLE
from libraries.distillator import RX_PACK_PCS

BPC_KNOWN = {
    1, 2, 3, 4, 5, 6,
    8, 9, 10, 11, 12,
    15, 20, 24, 25,
    30, 36, 48, 60,
}

def detect_bpc(s: str) -> int | None:
    """
    Найти bottles-per-case по локальной строке.
    Работает ТОЛЬКО по текущему string контексту.
    Возвращает int или None.
    """
    if not s:
        return None

    s = str(s).lower()

    # 0) triple format: 6/70/40
    m = RX_BPC_TRIPLE.search(s)
    if m:
        n = int(m.group("bpc"))
        if 1 <= n <= 60:
            return n

    # 1) 6x75 / 12×70 / 50cl x 12
    m = RX_BPC.search(s)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 60:
            return n

    # 2) cs*6 / *12 btl
    m = RX_BPC_STAR.search(s)
    if m:
        n = int(m.group("cases"))
        if 1 <= n <= 60:
            return n

    # 3) dash-style: — 6 —
    m = RX_BPC_DASH.search(s)
    if m:
        n = int(m.group("cases"))
        if 1 <= n <= 60:
            return n
        
    # 4) pcs
    m = RX_PACK_PCS.search(s)
    if m:
        n = int(m.group("cases"))
        if 1 <= n <= 60:
            return n

    # -------------------------------------------------
    # 5) FALLBACK: numeric x numeric|volume
    # -------------------------------------------------
    if "x" in s:
        s2 = s.replace("×", "x")

        # match: <num> x <num|volume>
        for m in re.finditer(
            r'(\d{1,3})\s*x\s*(\d{1,3}(?:\.\d+)?\s*(?:ml|cl|l)?)',
            s2
        ):
            left = int(m.group(1))
            if left in BPC_KNOWN:
                return left

        # match: <volume> x <num>
        for m in re.finditer(
            r'(\d{1,3}(?:\.\d+)?\s*(?:ml|cl|l))\s*x\s*(\d{1,3})',
            s2
        ):
            right = int(m.group(2))
            if right in BPC_KNOWN:
                return right


    return None
