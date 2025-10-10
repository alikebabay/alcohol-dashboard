# core/location_assistant.py
import re
from typing import Callable, Optional, List
from utils.text_extractors import RX_BOTTLE, RX_CASE, RX_BPC
import utils.text_extractors as te
from utils.regular_expressions import RX_BOTTLE, RX_CASE, RX_BPC  # ← общий источник

class LocationAssistant:
    """
    Финальное решение по location на строку:
      1) inline через extract_location(line)
      2) если нет — header → вперёд
      3) если после блока пришёл footer — назад, и перекрывает header
    Ничего не трогает про access.
    """

    RX_SIGNATURE = re.compile(r"(kind\s+regards|best\s+regards|www\.|@\w+\.\w+|mobile|whatsapp|phone)", re.I)

    def __init__(self, extract_location_fn: Callable[[str], Optional[str]]):
        self._extract_location = extract_location_fn
        self._lines: List[str] = []
        self._final: List[Optional[str]] = []

    def _looks_like_product(self, s: str) -> bool:
        # Используем ТВОИ рантайм-выражения из text_extractors.py
        if te.RX_BPC.search(s):
            return True
        if any(rx.search(s) for rx in te.RX_BOTTLE):
            return True
        if any(rx.search(s) for rx in te.RX_CASE):
            return True
        return False

    def prepare(self, raw_text: str) -> None:
        self._lines = raw_text.splitlines()
        n = len(self._lines)
        self._final = [None] * n

        header_hint: Optional[str] = None
        in_block = False
        block_start: Optional[int] = None

        def is_blank(i): return not self._lines[i].strip()
        def is_signature(i): return bool(self.RX_SIGNATURE.search(self._lines[i]))
        def is_product(i): return self._looks_like_product(self._lines[i])

        # контекстная строка = не продукт и не сигнатура, но extract_location её распознаёт
        def ctx_location(i) -> Optional[str]:
            if is_signature(i):
                return None
            loc = self._extract_location(self._lines[i])
            if not loc or is_product(i):
                return None
            return loc

        def apply_footer_back(start_idx: int, end_idx_excl: int, loc: str):
            j = end_idx_excl - 1
            while j >= (start_idx if start_idx is not None else 0):
                if is_blank(j):
                    break
                if ctx_location(j):  # не перескакиваем другой контекст
                    break
                if is_product(j) and self._final[j] is None:
                    self._final[j] = loc  # footer перекрывает header, но НЕ inline
                j -= 1

        for i, raw in enumerate(self._lines):
            s = raw.strip()
            if not s:
                in_block = False
                block_start = None
                continue
            if is_signature(i):
                continue

            # 1) inline на продуктовой строке — финальное и неперезаписываемое
            if is_product(i):
                if not in_block:
                    in_block = True
                    block_start = i
                inline_loc = self._extract_location(self._lines[i])
                if inline_loc:
                    self._final[i] = inline_loc   # ← inline-приоритет, футер не трогает
                elif header_hint and self._final[i] is None:
                    self._final[i] = header_hint  # временно, может перекрыться футером позже
                continue

            # 2) контекст (header/footer)
            loc_ctx = ctx_location(i)
            if loc_ctx:
                if not in_block:
                    header_hint = loc_ctx          # HEADER → вперёд
                else:
                    apply_footer_back(block_start, i, loc_ctx)  # FOOTER → назад
                continue
            # остальное игнор

    def resolve_locations(self) -> List[Optional[str]]:
        return self._final

    def lines(self) -> List[str]:
        return self._lines
