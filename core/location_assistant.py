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

    def __init__(self, extract_location_fn: Callable[[str], Optional[str]],*, single_message: bool = True):
        self._extract_location = extract_location_fn
        self._single_message = single_message
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
        last_block: Optional[tuple[int, int]] = None  # (start, end_inclusive)

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
                if ctx_location(j):  # не перескакиваем другой контекст
                    break
                if is_product(j) and self._final[j] is None:
                    self._final[j] = loc  # footer перекрывает header, но НЕ inline
                j -= 1

        for i, raw in enumerate(self._lines):
            s = raw.strip()
            if not s:
                # закрываем текущий блок и запоминаем его границы
               if in_block and block_start is not None:
                   last_block = (block_start, i - 1)
                   
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
                if in_block:
                    # FOOTER внутри текущего блока
                    apply_footer_back(block_start, i, loc_ctx)
                    print(f"[DEBUG location] 🔻 Footer внутри блока {block_start}–{i}: {loc_ctx}")
                else:
                    # Возможный FOOTER сразу после блока (через пустую строку)
                    if last_block is not None:
                        start, end_incl = last_block
                        # допускаем маленький «зазор» из пустых строк между блоком и footer
                        gap_is_blank = all(is_blank(k) for k in range(end_incl + 1, i))
                        if gap_is_blank:
                            # применяем footer к последнему блоку
                            apply_footer_back(start, end_incl + 1, loc_ctx)
                            # если письмо одно — растягиваем footer на все предыдущие товарные строки
                            if self._single_message:
                                apply_footer_back(0, end_incl + 1, loc_ctx)
                            # применили как footer, не записываем в header_hint
                            last_block = None
                            print(f"[DEBUG location] 🔙 Footer после блока {start}–{end_incl}: {loc_ctx}")
                            continue
                    # иначе это реальный HEADER → вперёд
                    header_hint = loc_ctx
                   
                continue
            # остальное игнор

    def resolve_locations(self) -> List[Optional[str]]:
        return self._final

    def lines(self) -> List[str]:
        return self._lines
