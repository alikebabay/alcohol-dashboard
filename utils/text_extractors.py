#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

# text_extractors.py
import re
import pandas as pd
import json
import logging

from core.distillator import _extract_volume, _infer_bpc_from_name, RX_ABV
from utils.regular_expressions import RX_BOTTLE, RX_CASE, RX_BPC
from core.patterns import ACCESS_PATS

logger = logging.getLogger(__name__)
# отдельные логгеры для подгрупп
price_logger = logging.getLogger("utils.text_extractors.prices")
access_logger = logging.getLogger("utils.text_extractors.access")
location_logger = logging.getLogger("utils.text_extractors.location")

def extract_volume(text: str):
    return _extract_volume(text)

def extract_bottles_per_case(text: str):
    return _infer_bpc_from_name(text)

def extract_abv(text: str):
    if not isinstance(text, str):
        return None
    m = RX_ABV.search(text)
    if m:
        return float(m.group(0).replace("%", "").replace(",", "."))
    return None


class PriceExtractor:
    """
    Унифицированный извлекатель цен.
    Состояния:
      - 'bottle'  → ищет цену за бутылку
      - 'case'    → ищет цену за кейс
      - 'derived' → вычисляет недостающую цену из другой и кол-ва бутылок
    """

    # берём из единого источника
    RX_BOTTLE = RX_BOTTLE
    RX_CASE = RX_CASE
    RX_BPC = RX_BPC

    def __init__(self):
        self.state = "init"
        self.price_bottle = None
        self.price_case = None
        self.bottles_per_case = None
        


    # --- main entry ---
    def extract(self, text: str) -> dict:
        if not text:
            return {}
        # сброс состояния на каждый вызов
        logger.debug(f"[RESET] before → state={self.state}, bottle={self.price_bottle}, case={self.price_case}, bpc={self.bottles_per_case}")
        self.state = "init"
        self.price_bottle = None
        self.price_case = None
        self.bottles_per_case = None
        logger.debug(f"[RESET] after  → state={self.state}, bottle={self.price_bottle}, case={self.price_case}, bpc={self.bottles_per_case}")

        s = str(text)
           
        logger.debug(f"[PRICE] raw={text!r}")
        self._extract_bpc(s)
        price_logger.debug(f"[PRICE] bottles_per_case → {self.bottles_per_case}")
        # 🧠 Предварительная эвристика: если явно указано 'cases' → считаем ценой за кейс
        if re.search(r'\bcases?\b', s, re.I):
            m = re.search(r'at\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\b', s, re.I)
            if m:
                self.price_case = float(m.group(1).replace(",", "."))
                self.state = "case"
                self._derive_bottle()
                
                return self._result()

        # 1️⃣ явные указания (per bottle / per case)
        self.price_bottle = self._match_any(s, self.RX_BOTTLE)
        
        if self.price_bottle is not None:
            self.state = "bottle"
            
            self._derive_case()
            price_logger.debug(f"[PRICE] matched bottle={self.price_bottle} (state={self.state})")
            return self._result()

       
        self.price_case = self._match_any(s, self.RX_CASE)
        
        if self.price_case is not None:
            self.state = "case"
            
            self._derive_bottle()
            price_logger.debug(f"[PRICE] matched case={self.price_case} (state={self.state})")
            return self._result()

        # 2️⃣  эвристика по контексту
        at_match = re.search(r'at\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\b', s, re.I)
       
        if at_match:
            val = float(at_match.group(1).replace(',', '.'))
            has_cases = re.search(r'\bcases?\b', s, re.I)
            has_bpc = bool(self.RX_BPC.search(s))
            price_logger.debug(f"[PRICE] heuristic match at={val} cases={bool(has_cases)} bpc={has_bpc}")
 

            # если есть 'cases' — считаем ценой за кейс
            if has_cases:
                self.price_case = val
                self.state = "case"
                self._derive_bottle()
                
                return self._result()

            # если нет 'cases', но есть 6x75cl/12x70cl — считаем ценой за бутылку
            if has_bpc:
                self.price_bottle = val
                self.state = "bottle"
                self._derive_case()
                
                return self._result()



        # 3️⃣ derived nothing
        self.state = "none"
        price_logger.debug(f"[PRICE] nothing matched → state={self.state}")
        return self._result()

    # --- helpers ---
    def _match_any(self, text, patterns):
        for rx in patterns:
            m = rx.search(text)
            if m:
                raw_val = m.group(1)
                price_logger.debug(f"[REGEX] {rx.pattern} → match={raw_val!r}")
                try:
                    val = float(raw_val.replace(",", "").replace(" ", ""))
                    price_logger.debug(f"[REGEX] parsed float={val}")
                    return val
                except Exception as e:
                    price_logger.warning(f"[REGEX] parse fail {raw_val!r} ({e})")
        price_logger.debug("[REGEX] no match for any price pattern")
        return None

    def _extract_bpc(self, text):
        logger.debug(f"[BPC] start (before search) bpc={self.bottles_per_case} text[:60]={text[:60]!r}")
        # стандартный паттерн: "6x75", "12×70"
        m = self.RX_BPC.search(text)
        if m:
            self.bottles_per_case = int(m.group(1))
            logger.debug(f"[BPC] matched direct pattern → {self.bottles_per_case}")
            return

        # формат с тире: "— 6 —" или "- 12 -"
        m = re.search(r'[—\-–]\s*(\d{1,2})\s*[—\-–]', text)
        if m:
            self.bottles_per_case = int(m.group(1))
            logger.debug(f"[BPC] matched dash pattern → {self.bottles_per_case}")
            return

        # если всё остальное не сработало — пробуем общий инфер
        try:
            from utils.text_extractors import _infer_bpc_from_name
            inferred = _infer_bpc_from_name(text)
            logger.debug(f"[BPC] _infer_bpc_from_name returned {inferred!r}")
            if inferred:
                self.bottles_per_case = int(inferred)
                logger.debug(f"[BPC] final inferred → {self.bottles_per_case}")
            else:
                logger.debug("[BPC] no inferred value")
        except Exception as e:
            print(f"[BPC] _infer_bpc_from_name() failed: {e}")
           
 

    def _derive_case(self):
        if self.price_bottle and self.bottles_per_case:
            self.price_case = round(self.price_bottle * self.bottles_per_case, 2)
            self.state = "derived"
          

    def _derive_bottle(self):
        if self.price_case and self.bottles_per_case:
            self.price_bottle = round(self.price_case / self.bottles_per_case, 4)
            self.state = "derived"
           

    def _result(self):
        return {
            "state": self.state,
            "price_bottle": self.price_bottle,
            "price_case": self.price_case,
            "bottles_per_case": self.bottles_per_case,
        }


def extract_access(text: str):
    """
    Detects stock status or lead time: 'On stock', 'T1', 'T2', 'TBO', 'on floor',
    'lead time 2 weeks', '7 days after deposit', '2-3 weeks', etc.
    Returns combined string like 'T2, 2 weeks'.
    """
    if not text:
        access_logger.debug("extract_access: пустой ввод")
        return None
    s = str(text).strip()

    parts = []
    patterns = ACCESS_PATS
    for rx in patterns:
        # collect *all* matches for this regex, not just the first
        for m in rx.finditer(s):
            match_val = m.group(0).strip()
            if match_val and match_val not in parts:
                parts.append(match_val)

    if parts:
        # deduplicate while preserving order
        val = ", ".join(parts)
        access_logger.debug(f"extract_access: найдено → {val!r}")
        return val

    access_logger.debug(f"extract_access: ничего не найдено в '{s}'")
    return None


def extract_location(text: str):
    """
    Извлекает и нормализует *локацию поставки/склада*.
    Принципы:
      1️⃣ Должен содержать Incoterm (EXW, DAP, CIF, FOB, и т.д.)
      2️⃣ Должен содержать известное географическое слово (город/страна)
      3️⃣ Может содержать несколько городов через “or”, “/”, “and”
      4️⃣ Обычно находится ближе к концу строки
      5️⃣ Исправляет опечатки (например, “Niderland” → “Netherlands”)
    """

    if not text:
        location_logger.debug("extract_location: пустой ввод")
        return None
    s = str(text).strip()

    # загрузка словарей
    with open("aliases/city_aliases.json", encoding="utf-8") as f:
        CITY_ALIASES = json.load(f)["aliases"]
    with open("aliases/incoterms_aliases.json", encoding="utf-8") as f:
        INCOTERM_ALIASES = json.load(f)["aliases"]

    # предварительная очистка и нормализация
    s = re.sub(r'\s+', ' ', s)
    s = s.replace(",", ", ").replace("  ", " ").strip()

    # ищем incoterm (возможен любой вариант из словаря)
    incoterm = None
    for key, val in INCOTERM_ALIASES.items():
        if re.search(rf'\b{re.escape(key)}\b', s, re.I):
            incoterm = val.upper()
            break

    # если нет инкотерма, ищем конструкцию "in/at/from <city>"
    if not incoterm:
        m = re.search(r'\b(?:in|at|from)\s+([A-ZА-Я][A-Za-zА-Яа-я\-]+)\b', s, re.I)
        if m:
            city = m.group(1)
            expanded = CITY_ALIASES.get(city.lower()[:4], city)
            location_logger.debug(f"extract_location: без Incoterm, найден город {expanded!r}")
            return expanded
        location_logger.debug(f"extract_location: Incoterm не найден, город не распознан → {s!r}")
        return None


   

    # выделяем часть ближе к концу строки
    tail = s[-100:]  # последние 100 символов чаще всего содержат локацию

    # ищем все потенциальные города/страны
    found_cities = []
    for alias, canonical in CITY_ALIASES.items():
        if re.search(rf'\b{re.escape(alias)}\b', tail, re.I):
            if canonical not in found_cities:
                found_cities.append(canonical)

    if not found_cities:
        # нет географических совпадений — мусор
        location_logger.debug(f"extract_location: нет городов в '{tail}'")
        return None

    # нормализуем написание: соединяем города через " or " / "/" / "and"
    clean_parts = []
    for p in found_cities:
        p_clean = re.sub(r'\b(or|and|s)\b$', '', p, flags=re.I).strip(",. ")
        clean_parts.append(p_clean)
    joined = re.sub(r'\s+', ' ', ' or '.join(clean_parts)).strip()
    # финальная сборка
    val = f"{incoterm} {joined}".strip()

    # финальная постпроверка — только если Incoterm + город известен
    if not any(alias.lower() in val.lower() for alias in CITY_ALIASES.values()):
        location_logger.debug(f"extract_location: финальная проверка не прошла → {val!r}")
        return None

    location_logger.debug(f"extract_location: успешно → {val!r}")
    return val
