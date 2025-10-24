# -*- coding: utf-8 -*-
"""
Доменные правила для расчёта бонусов/штрафов при выборе Canonical.
На данный момент: штраф за 'Magnum', если в названии нет объёма около 1.5 л. введено изза проблем с парсингом Veuve Clicquot.
Костыль.
"""

import re
from utils.normalize import normalize as _normalize


def penalty_for_magnum(raw_norm: str, cn_norm: str) -> float:
    """
    Штраф за 'Magnum', если объём в названии не около 1.5 л.
    Пример: 'Yellow Label Magnum' → -0.3, если в raw нет 150cl / 1.5l.
    """
    if "magnum" not in cn_norm:
        return 0.0

    # Ищем объём в тексте
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:cl|l)\b", raw_norm)
    if not match:
        # Объём не указан → вероятно, обычная бутылка
        return -0.6

    val = float(match.group(1).replace(",", "."))
    # Magnum — это примерно 150cl (1.5l)
    if 120 <= val <= 170:
        return 0.0  # Всё ок, совпадает
    return -0.6  # Не совпадает по объёму


def apply_canonical_rules(raw: str, cname: str) -> float:
    """
    Применяет все бонусы/штрафы к canonical name.
    Возвращает итоговую дельту для score.
    """
    raw_norm = _normalize(raw)
    cn_norm = _normalize(cname)

    delta = penalty_for_magnum(raw_norm, cn_norm)
    return delta
