# utils/wine_guard.py
import re

# базовые "винные слова", которые почти всегда означают новый продукт/вино, а не серию бренда
WINE_KEYWORDS = [
    "sauvignon blanc",
    "anejo",
    "vsop",
    "silver"
]

# подготавливаем нормализованные формы
_WINE_RE = re.compile(r"|".join(map(re.escape, WINE_KEYWORDS)), re.IGNORECASE)

def looks_like_new_wine(raw_norm: str) -> bool:
    """
    Возвращает True, если строка содержит типичные винные обозначения сортов
    (например, "Sauvignon Blanc", "Cabernet", "Pinot Noir"). Также используется для текил (anejo - выдержанный)
    Используется как хелпер-костыль: при True пропускаем поиск серий текущего бренда.
    """
    return bool(_WINE_RE.search(raw_norm))
