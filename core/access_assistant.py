# core/access_assistant.py
import re
from typing import Callable, Optional, List
import logging

from libraries.regular_expressions import RX_BOTTLE, RX_CASE, RX_BPC
from libraries.distillator import looks_like_product
import utils.text_extractors as te
from utils.logger import setup_logging

# инициализация общего логгера
setup_logging()
logger = logging.getLogger(__name__)

class AccessAssistant:
    """
    Финальное решение по access на строку:
      1) inline через extract_access(line)
      2) если нет — header → вперёд
      3) если после блока пришёл footer — назад, и перекрывает header
    Логика полностью зеркалирует LocationAssistant.
    """

    RX_SIGNATURE = re.compile(r"(kind\s+regards|best\s+regards|www\.|@\w+\.\w+|mobile|whatsapp|phone)", re.I)

    def __init__(self, extract_access_fn: Callable[[str], Optional[str]], *, single_message: bool = True):
        self._extract_access = extract_access_fn
        self._single_message = single_message
        self._lines: List[str] = []
        self._final: List[Optional[str]] = []

    def prepare(self, raw_text: str) -> None:
        self._lines = raw_text.splitlines()
        n = len(self._lines)
        self._final = [None] * n

        header_hint: Optional[str] = None
        in_block = False
        block_start: Optional[int] = None
        last_block: Optional[tuple[int, int]] = None

        def is_blank(i): return not self._lines[i].strip()
        def is_signature(i): return bool(self.RX_SIGNATURE.search(self._lines[i]))
        def is_product(i): return looks_like_product(self._lines[i])

        def ctx_access(i) -> Optional[str]:
            """Контекстная строка: не продукт, не подпись, но содержит access"""
            if is_signature(i):
                return None
            val = self._extract_access(self._lines[i])
            if not val or is_product(i):
                return None
            return val

        def apply_footer_back(start_idx: int, end_idx_excl: int, access_val: str):
            """Применяет footer назад к блоку"""
            j = end_idx_excl - 1
            while j >= (start_idx if start_idx is not None else 0):
                if ctx_access(j):  # не перескакиваем другой контекст
                    break
                if is_product(j) and self._final[j] is None:
                    self._final[j] = access_val  # footer перекрывает header
                j -= 1

        for i, raw in enumerate(self._lines):
            s = raw.strip()
            if not s:
                # закрываем текущий блок
                if in_block and block_start is not None:
                    last_block = (block_start, i - 1)
                in_block = False
                block_start = None
                continue

            if is_signature(i):
                continue

            # 1️⃣ inline access — высший приоритет
            if is_product(i):
                if not in_block:
                    in_block = True
                    block_start = i

                inline_val = self._extract_access(self._lines[i])
                if inline_val:
                    self._final[i] = inline_val
                    logger.debug(f"[DEBUG access] ⚡ Inline на строке {i}: {inline_val}")
                elif header_hint and self._final[i] is None:
                    self._final[i] = header_hint
                    logger.debug(f"[DEBUG access] ↘ Header hint применён к {i}: {header_hint}")
                continue

            # 2️⃣ Контекстная строка (header/footer)
            acc_ctx = ctx_access(i)
            if acc_ctx:
                if in_block:
                    # FOOTER внутри блока
                    apply_footer_back(block_start, i, acc_ctx)
                    logger.debug(f"[DEBUG access] 🔻 Footer внутри блока {block_start}–{i}: {acc_ctx}")
                
                # Если FOOTER единственный в тектсе
                if last_block is not None:
                    start, end_incl = last_block                    
                    apply_footer_back(start, end_incl + 1, acc_ctx)
                    if self._single_message:
                        apply_footer_back(0, end_incl + 1, acc_ctx)
                    logger.debug(f"[DEBUG access] 🔙 Footer после блока {start}–{end_incl}: {acc_ctx}")
                    last_block = None
                    continue
                # иначе это HEADER
                header_hint = acc_ctx
                logger.debug(f"[DEBUG access] ⬆ Header установлен: {acc_ctx}")
                continue
            # остальное игнор

    def resolve_access(self) -> List[Optional[str]]:
        return self._final

    def lines(self) -> List[str]:
        return self._lines
