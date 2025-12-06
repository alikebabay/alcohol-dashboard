# utils/wine_guard.py - сбрасывает состояние при поиске серий внутри бренда, запускает новый поиск бренда
import re
import logging
from utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


# базовые, которые почти всегда означают новый бренд алкоголя, а не серию бренда
WINE_KEYWORDS = [
    "sauvignon blanc",
    "anejo",
    "vsop",
    "v.s.o.p",
    "silver",
    "Single Barrel",
    "Year Old",
    "Flora & Fauna",
    "Classic",
    "Original",
    "originale",
    "Single Malt",
    "Especial Reposado",
    "Reposado",
    "NRB",
    "CAN",
    "brut"
]

# подготавливаем нормализованные формы
_WINE_RE = re.compile(r"|".join(map(re.escape, WINE_KEYWORDS)), re.IGNORECASE)

def looks_like_new_wine(raw_norm: str) -> bool:
    """
    Возвращает True, если строка содержит типичные винные обозначения сортов
    (например, "Sauvignon Blanc", "Cabernet", "Pinot Noir"). Также используется для текил (anejo - выдержанный)
    Используется как хелпер-костыль: при True пропускаем поиск серий текущего бренда.
    """
    logger.debug(f"[WINE GUARD] Checking raw_norm={raw_norm!r}")
    logger.debug(f"[WINE GUARD] regex pattern={_WINE_RE.pattern!r}")

    m = _WINE_RE.search(raw_norm)
    if m:
        logger.debug(f"[WINE GUARD] MATCHED keyword={m.group(0)!r} at pos={m.start()}")
        return True
    
    logger.debug("[WINE GUARD] No keywords matched")
    return False