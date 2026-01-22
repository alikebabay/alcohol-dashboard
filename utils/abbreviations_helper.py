#Модуль переводит сокращения в расширенную форму для улучшения парсинга. 
# Также исправляет грамматические ошибки поставщиков
import re
from config import ABBREVIATIONS


def convert_abbreviation(text: str) -> str:
    """
    Преобразует сокращения брендов и типичные паттерны в нормализованный вид.
    Например:
      12yo → 12 yo
      YL → Yellow Label
      Moët → Moet & Chandon
    """
    if not isinstance(text, str):
        return text

    # 🧠 1️⃣ Отделяем "yo" от чисел (например 12yo → 12 yo)
    text = re.sub(r"(?<=\d)(?=yo\b|YO\b)", " ", text)

    # 🧩 2️⃣ Проходим по всем известным сокращениям
    for abbrev, full_form in ABBREVIATIONS.items():
        # \b — границы слова; re.IGNORECASE — чувствительность к регистру
        text = re.sub(rf"\b{re.escape(abbrev)}\b", full_form, text, flags=re.IGNORECASE)

    return text
