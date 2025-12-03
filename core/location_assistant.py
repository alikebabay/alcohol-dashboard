# core/location_assistant.py
import re
from typing import Callable, Optional, List
import logging

import utils.text_extractors as te
from libraries.distillator import looks_like_product
from utils.logger import setup_logging

# инициализация общего логгера
setup_logging()
logger = logging.getLogger(__name__)

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

    def prepare(self, raw_text: str) -> None:
        self._lines = raw_text.splitlines()
        n = len(self._lines)
        self._final = [None] * n

        logger.debug(f"[loc] === prepare() START, {n} lines ===")

        header_hint: Optional[str] = None
        in_block = False
        block_start: Optional[int] = None
        last_block: Optional[tuple[int, int]] = None  # (start, end_inclusive)

        def is_blank(i): return not self._lines[i].strip()
        def is_signature(i): return bool(self.RX_SIGNATURE.search(self._lines[i]))
        def is_product(i): return looks_like_product(self._lines[i])

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
                    logger.debug(f"[loc]     footer_back STOP at {j} (ctx exists)")
                    break
                if is_product(j) and self._final[j] is None:
                    logger.debug(f"[loc]     footer_back APPLY '{loc}' → line {j}: {self._lines[j]!r}")
                    self._final[j] = loc  # footer перекрывает header, но НЕ inline
                j -= 1

        for i, raw in enumerate(self._lines):
            logger.debug(f"[loc] ▶ Line {i}: {raw!r}")
            s = raw.strip()
            if not s:
                # закрываем текущий блок и запоминаем его границы
               if in_block and block_start is not None:
                   logger.debug(f"[loc]   END block {block_start}–{i-1}")
                   last_block = (block_start, i - 1)
                   
               in_block = False
               block_start = None
               continue
            if is_signature(i):
                logger.debug(f"[loc]   signature skipped")
                continue

            # 1) inline на продуктовой строке — финальное и неперезаписываемое
            is_prod = is_product(i)
            logger.debug(f"[loc]   is_product={is_prod}")
            if is_prod:
                if not in_block:
                    in_block = True
                    block_start = i
                    logger.debug(f"[loc]   START block at {i}")
                    
                inline_loc = self._extract_location(self._lines[i])
                logger.debug(f"[loc]     inline_loc={inline_loc!r}, header_hint={header_hint!r}")

                if inline_loc:
                    self._final[i] = inline_loc   # ← inline-приоритет, футер не трогает
                    logger.debug(f"[loc]     FINAL[{i}] = {inline_loc!r}  (inline)")
                    
                elif header_hint and self._final[i] is None:
                    self._final[i] = header_hint  # временно, может перекрыться футером позже
                    logger.debug(f"[loc]     FINAL[{i}] = {header_hint!r}  (header_hint)")
                    
                continue

            # 2) контекст (header/footer)
            loc_ctx = ctx_location(i)
            logger.debug(f"[loc]   ctx_location={loc_ctx!r}")
            if loc_ctx:
                if in_block:
                    # FOOTER внутри текущего блока
                    apply_footer_back(block_start, i, loc_ctx)
                    logger.debug(f"[DEBUG location] 🔻 Footer внутри блока {block_start}–{i}: {loc_ctx}")
                else:
                    # Возможный FOOTER сразу после блока (через пустую строку)
                    if last_block is not None:
                        start, end_incl = last_block
                        
                        # применяем footer к последнему блоку
                        apply_footer_back(start, end_incl + 1, loc_ctx)
                        # если письмо одно — растягиваем footer на все предыдущие товарные строки
                        if self._single_message:
                            apply_footer_back(0, end_incl + 1, loc_ctx)
                        # применили как footer, не записываем в header_hint
                        last_block = None
                        logger.debug(f"[DEBUG location] 🔙 Footer после блока {start}–{end_incl}: {loc_ctx}")
                        continue
                    # иначе это реальный HEADER → вперёд
                    header_hint = loc_ctx
                    logger.debug(f"[loc]   HEADER_HINT = {header_hint!r}")
                   
                continue
            # остальное игнор

    def resolve_locations(self) -> List[Optional[str]]:
        return self._final

    def lines(self) -> List[str]:
        return self._lines
