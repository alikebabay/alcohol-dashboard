#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

# text_extractors.py
import re
import pandas as pd
import json
import logging

from libraries.distillator import _extract_volume, _infer_bpc_from_name, RX_ABV
from utils.detect_bpc import detect_bpc
import libraries.regular_expressions as rx
from libraries.regular_expressions import normalize_currency_marker
from libraries.patterns import PATS, RX_DATE
from core.bpc_detector import BPC_KNOWN

logger = logging.getLogger(__name__)
# отдельные логгеры для подгрупп
price_logger = logging.getLogger("utils.text_extractors.prices")
access_logger = logging.getLogger("utils.text_extractors.access")
location_logger = logging.getLogger("utils.text_extractors.location")

# ---- global location aliases (loaded once) ----
try:
    with open("libraries/location_aliases.json", encoding="utf-8") as f:
        _loc_data = json.load(f)
        CITY_ALIASES = {k.lower(): v for k, v in _loc_data.get("cities", {}).items()}
        INCOTERM_ALIASES = {k.lower(): v for k, v in _loc_data.get("incoterms", {}).items()}
        WAREHOUSE_ALIASES = {k.lower(): v for k, v in _loc_data.get("warehouse", {}).items()}
except Exception as e:
    logger.error(f"[LOCATION] failed to load location_aliases.json: {e}")
    CITY_ALIASES = {}
    INCOTERM_ALIASES = {}
    WAREHOUSE_ALIASES = {}


def extract_volume(text: str):
    return _extract_volume(text)

#экстрактор BPC для создания колонки
def extract_bottles_per_case(text: str):
    return _infer_bpc_from_name(text)

def extract_abv(text: str):
    if not isinstance(text, str):
        return None
    m = RX_ABV.search(text)
    if m:
        return float(m.group(0).replace("%", "").replace(",", "."))
    return None


#normalizer for float prices 
def normalize_number(num: str) -> float:
    s = num.replace(" ", "")

    # Пример: "1,048.89" → decimal ".", thousand ","
    if "," in s and "." in s:
        if s.rfind(".") > s.rfind(","):
            # decimal ".", thousands ","
            s = s.replace(",", "")
        else:
            # decimal ",", thousands "."
            s = s.replace(".", "").replace(",", ".")
    else:
        # один разделитель → считаем decimal
        s = s.replace(",", ".")

    return float(s)


class PriceExtractor:
    """
    Новый контекстный извлекатель цен.
    Трёхслойная логика:
      1) собрать все числа + левый/правый контекст
      2) классификация: bottle/case/bpc/qty/unknown
      3) derive/fallback финальной цены
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.state = "init"
        self.price_bottle = None
        self.price_case = None
        self.bottles_per_case = None
        self.currency = None

    # ----------------------------
    # MAIN ENTRY
    # ----------------------------
    def extract(self, text: str) -> dict:
        self.reset()
        s = str(text)
        self.raw_text = s
        # HARD RULE: skip rows with no currency markers
        if not rx.RX_CURRENCY_MARKER.search(s):
            price_logger.debug("[HARD-RULE] No currency markers → skip")
            self.state = "none"
            return {
                "state": self.state,
                "price_bottle": None,
                "price_case": None,
                "bottles_per_case": None,
            }

        price_logger.debug(f"\n[EXTRACT] raw={s!r}")        

        # Layer 1 — collect raw numeric tokens
        numeric_tokens = self._collect_numeric_tokens(s)
        price_logger.debug(f"[L1] numeric tokens → {numeric_tokens}")

        # Layer 2 — classify those numeric tokens
        classified = self._classify_tokens(numeric_tokens, s)
        price_logger.debug(f"[L2] classified → {classified}")

        # Layer 3 — extract BPC
        self.bottles_per_case = detect_bpc(self.raw_text)
        price_logger.debug(f"[L3] BPC → {self.bottles_per_case}")

        # Layer 3 — resolve to final state
        self._decide_final(classified)

        return {
            "state": self.state,
            "price_bottle": self.price_bottle,
            "price_case": self.price_case,
            "bottles_per_case": self.bottles_per_case,
            "currency": self.currency,
            "price_detected": bool(self.price_bottle or self.price_case),
        }

    # ----------------------------
    # LAYER 1
    # ----------------------------
    def _collect_numeric_tokens(self, s: str):
        """
        Возвращает ВСЕ возможные валюта+число / число+валюта токены.
        Для каждого вхождения валюты ищет:
        • ближайшее число слева (через пробелы)
        • ближайшее число справа (через пробелы)
        Ничего не фильтрует. Оба кандидата передаются дальше в L2/L3.
        """

        tokens = []
        def _walk_number(s: str, i: int, step: int):
            """
            Walks over a numeric block in either direction.

            step:
                +1 → scan right
                -1 → scan left

            Returns new index where numeric block ends (exclusive for right,
            inclusive boundary handled by caller).
            """
            n = len(s)

            digits_since_sep = 0
            seen_sep = False

            while 0 <= i < n and (s[i].isdigit() or s[i] in "., "):
                c = s[i]

                if c.isdigit():
                    digits_since_sep += 1
                    i += step
                    continue

                if c in ".,":  # level-1 separators
                    if seen_sep:
                        # thousands group must be exactly 3 digits
                        if digits_since_sep != 3:
                            break
                    seen_sep = True
                    digits_since_sep = 0
                    i += step
                    continue

                # space (level-2 separator)
                if c == " ":
                    if digits_since_sep != 3:
                        break
                    digits_since_sep = 0
                    i += step
                    continue

            return i


        def scan_right(idx):
            n = len(s)
            i = idx

            while i < n and s[i].isspace():
                i += 1

            if i >= n or not s[i].isdigit():
                return None

            start = i
            i += 1

            i = _walk_number(s, i, +1)

            num = s[start:i].replace(" ", "")
            return {"num": num, "start": start, "end": i}

        
        def scan_left(idx):
            i = idx - 1

            while i >= 0 and s[i].isspace():
                i -= 1

            if i < 0 or not s[i].isdigit():
                return None

            end = i + 1
            i -= 1

            i = _walk_number(s, i, -1)

            start = i + 1

            num = s[start:end].replace(" ", "")
            return {"num": num, "start": start, "end": end}


        for m in rx.RX_CURRENCY_MARKER.finditer(s):
            cur_start, cur_end = m.span()
            
            cur_text = s[cur_start:cur_end]
            cur_code = normalize_currency_marker(cur_text)
            price_logger.debug(
                "[L1] CURRENCY FOUND '%s' at %d:%d → %s",
                cur_text, cur_start, cur_end, cur_code
            )

            left_info = scan_left(cur_start)
            right_info = scan_right(cur_end)

            price_logger.debug(
                f"[L1] scan_left → {left_info} | text='{s[left_info['start']:left_info['end']] if left_info else None}'"
            )
            price_logger.debug(
                f"[L1] scan_right → {right_info} | text='{s[right_info['start']:right_info['end']] if right_info else None}'"
            )

            # добавляем оба токена, не выбирая лучший
            if left_info:
                price_logger.debug(f"[L1] ADD LEFT TOKEN: {left_info['num']!r}")
                tokens.append({
                    "value": left_info["num"],
                    "start": left_info["start"],   # добавляем для ограничения контекста
                    "end": left_info["end"], # добавляем для ограничения контекста
                    "left": s[max(0, left_info["start"] - 32):left_info["start"]],
                    "right": s[left_info["end"]:left_info["end"] + 32],
                    "has_currency": True,
                    "side": "left",
                    "currency": cur_code,
                })

            if right_info:
                price_logger.debug(f"[L1] ADD RIGHT TOKEN: {right_info['num']!r}")
                tokens.append({
                    "value": right_info["num"],
                    "start": right_info["start"],   # добавляем для ограничения контекста
                    "end": right_info["end"], # добавляем для ограничения контекста
                    "left": s[max(0, right_info["start"] - 32):right_info["start"]],
                    "right": s[right_info["end"]:right_info["end"] + 32],
                    "has_currency": True,
                    "side": "right",
                    "currency": cur_code,
                })
        price_logger.debug(f"[L1] FINAL TOKENS: {tokens}")
        return tokens


    # ----------------------------
    # LAYER 2 — classification
    # ----------------------------
    def _classify_tokens(self, tokens, s):
        classified = []   # итог: [(val, token, scores_dict)]
        # --------------------------------------------------------
        # Универсальный скорер: ищет regex в строке и даёт баллы.
        # direction: "left" → проверяем m.end() == len(ctx)
        #             "right" → проверяем m.start() == 0
        # --------------------------------------------------------
        def score_side(score_dict, key, ctx, regex_list, direction):
            for rx in regex_list:
                m = rx.search(ctx)
                if not m:
                    continue
                if direction == "left":
                    score_dict[key] += 1 if m.end() == len(ctx) else 0.5
                else:  # "right"
                    score_dict[key] += 1 if m.start() == 0 else 0.5

        for t in tokens:
            val = normalize_number(t["value"])

            l = t["left"].lower()
            r = t["right"].lower()
            # Система баллов — минимально нужная
            scores = {
                "bottle": 0,
                "case":   0,
            }

            #ограничиваем контекст для регексов
            def tight_right(s, num_end):
                ctx = []
                i = num_end

                # пропускаем пробелы
                while i < len(s) and s[i].isspace():
                    ctx.append(s[i]); i+=1

                # допускаем 1 разделитель
                if i < len(s) and s[i] in "/-:":
                    ctx.append(s[i]); i+=1

                # допускаем до 1 слова
                start_word = i
                while i < len(s) and s[i].isalpha():
                    ctx.append(s[i]); i+=1

                return "".join(ctx)
            
            r_tight = tight_right(s, t["end"])  # end = позиция конца числа

            # Новый унифицированный вызов
            score_side(scores, "bottle", l, rx.RX_BOTTLE_LEFT,  "left")
            score_side(scores, "bottle", r_tight, rx.RX_BOTTLE_RIGHT, "right")
            score_side(scores, "case",   l, rx.RX_CASE_LEFT,    "left")            
            score_side(scores, "case",   r_tight, rx.RX_CASE_RIGHT, "right")         
            
            # ------------------------------------------
            # EXPLICIT CASE and bottle RULES 
            # for at <price> and
            # ("cases ... at <price>")
            # ------------------------------------------            
            #расширяем контекст локально для правила
            l_stripped = l.rstrip()
            # шире контекст слева: всё, что перед числом в исходной строке
            num_idx = s.lower().find(t["value"].lower())
            if num_idx != -1:
                global_left = s[:num_idx].lower()
            else:
                global_left = l
            
            # 1) LEFT: "... at <price>" → слабый сигнал bottle
            if l_stripped.endswith(" at"):
                scores["bottle"] += 0.5
                # 1b) если где-то слева есть "case"/"cases" → слабый сигнал case,
                # чтобы в примере "85 cases ... at 315 euro" бутылка/кейс сбалансировались
                # и мы упали в дефолт CASE.
                if " case" in global_left or " cases" in global_left:
                    scores["case"] += 0.5
            # RULE: nearest Noun prhase wins
            # If the NP immediately before the price contains a size → bottle bias
            if re.search(r'\b\d+\s*(?:cl|ml|l)\b', t["left"].lower()):
                scores["bottle"] += 1
            
            # ------------------------------------------
            # CASE SIGNAL: dash-number-dash pattern
            # must match BPC_known exactly
            # ------------------------------------------
            m = re.search(r'[-–—−]\s*(\d{1,2})\s*[-–—−]', t["left"])
            if m:
                n = int(m.group(1))
                if n in BPC_KNOWN:
                    scores["case"] += 1


            # 3) RIGHT: "<price> per bottle/btl"
             # RULE LOGIC — используем ТОЛЬКО t["right"]
            right_clean = t["right"].lower().lstrip()
            
            if any(x in right_clean for x in ("per bottle", "eur/btl", "per btl", "per-bottle", "per-btl")):
                 scores["bottle"] += 1.5
            
            if any(x in right_clean for x in ("per case", "per cs", "per-case", "/case", "eur/case", "euro/case", "usd/case", "gbp/case")):
                 scores["case"] += 1.5
            

            # ALL TOKENS HERE ARE CANDIDATES,
            # потому что L1 уже отфильтровал неценовые числа
            classified.append((val, t, scores))
        return classified
    # ----------------------------
    # LAYER 3 — price resolution logic
    # ----------------------------
    def _decide_final(self, classified):
        # Слой 3 = полноценный резолвер контекста.
        #
        # На входе:
        #   classified = [(val, token, scores_dict)]
        #
        # Задача:
        #   1) проверить делимость между токенами
        #   2) использовать лексические баллы
        #   3) fallback → BPC
        #   4) fallback → default case
        # извлекаем только числа
        
        tokens = [(val, t, scores) for (val, t, scores) in classified]
        if not tokens:
            self.state = "none"
            return
        # take currency from last strongest token
        self.currency = tokens[-1][1].get("currency")

        # Если два ценовых токена → пытаемся определить bottle/case и BPC
        if len(tokens) >= 2:
            vals = [x[0] for x in tokens]
            big = max(vals)
            small = min(vals)

            ratio = big / small
            rounded = round(ratio)

            # ratio должен быть ИНТЕРОМ (BPC = integer)
            if abs(ratio - rounded) < 0.0001:
                self.bottles_per_case = rounded
                self.price_case = big
                self.price_bottle = small
                self.state = "derived"
                return
        
        # Если токен один → работаем по весам и контексту
        val, token, scores = tokens[-1]

        bottle_score = scores["bottle"]
        case_score   = scores["case"]

        # Если больше очков bottle → bottle
        if bottle_score > case_score:
            self.price_bottle = val
            # попытка derive case по BPC
            if self.bottles_per_case:
                self.price_case = round(val * self.bottles_per_case, 2)
                self.state = "derived"
            else:
                self.state = "bottle"
            return

        # Если больше очков case → case
        if case_score > bottle_score:
            self.price_case = val
            if self.bottles_per_case:
                self.price_bottle = round(val / self.bottles_per_case, 4)
                self.state = "derived"
            else:
                self.state = "case"
            return

        # Иначе → нет контекста → ищем BPC
        if self.bottles_per_case:
            # считаем этот токен как case по умолчанию
            self.price_case = val
            self.price_bottle = round(val / self.bottles_per_case, 4)
            self.state = "derived"
            return

        # Нет BPC → default = bottle
        self.price_bottle = val
        self.state = "bottle"

#слова фильтры для доступа
AVAIL_WORDS = {
    "eta", "etd",
    "shipping", "delivery",
    "arriving", "arrival",
    "available", "availability",
    "ready", "landing",
}

BLOCK_WORDS = {
    "deposit", "payment", "valid", "validity", "offer", "invoice"
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
    s_l = s.lower()
    patterns = PATS.ACCESS
    for rx in patterns:
        # collect *all* matches for this regex, not just the first
        for m in rx.finditer(s):
            match_val = m.group(0).strip()
            if match_val and match_val not in parts:
                parts.append(match_val)
        # 2) даты (ETA / shipping / deposit) - отсекаем лишние даты по контексту
        for m in RX_DATE.finditer(s):
            date_val = m.group(0).strip()
            span_start = m.start()

            # смотрим ТОЛЬКО влево от даты
            left_ctx = s_l[max(0, span_start - 50): span_start]

            has_avail = any(w in left_ctx for w in AVAIL_WORDS)
            has_block  = any(w in left_ctx for w in BLOCK_WORDS)

            # availability выигрывает, если она ближе
            if has_avail and not has_block:
                if date_val not in parts:
                    parts.append(date_val)

    if parts:
        # фильтруем перекрытия: убираем более короткие, если входят в длинные
        filtered = []
        for p in parts:
            if not any((p != q and p in q) for q in parts):
                filtered.append(p)

        # deduplicate while preserving order
        seen = set()
        unique = [p for p in filtered if not (p in seen or seen.add(p))]

        val = ", ".join(unique)
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

    
    # предварительная очистка и нормализация
    s = re.sub(r'\s+', ' ', s)
    s = s.replace(",", ", ").replace("  ", " ").strip()

    # ищем incoterm (возможен любой вариант из словаря)
    incoterm = None
    for key, val in INCOTERM_ALIASES.items():
        if re.search(rf'\b{re.escape(key)}\b', s, re.I):
            incoterm = val.upper()
            break

    # если нет инкотерма
    if not incoterm:
        # 1️⃣ пробуем city через in/at/from
        m = re.search(r'\b(?:in|at|from)\s+([A-ZА-Я][A-Za-zА-Яа-я\-]+)\b', s, re.I)
        if m:
            city = m.group(1)
            if re.search(r'\b(not\s+for\s+sales?|sales?|sale)\b', s, re.I):
                return None
            expanded = CITY_ALIASES.get(city.lower()[:4], city)
            location_logger.debug(
                f"extract_location: no incoterm, city found → {expanded!r}"
            )
            return expanded

        # 2️⃣ FALLBACK: warehouse без incoterm
        tail = s[-100:]
        for alias, wh in WAREHOUSE_ALIASES.items():
            if re.search(rf'\b{re.escape(alias)}\b', tail, re.I):
                location_logger.debug(
                    f"extract_location: no incoterm, fallback to warehouse → {wh}"
                )
                return wh   # ← ВАЖНО: без incoterm

        location_logger.debug(
            f"extract_location: no incoterm, no city, no warehouse → {s!r}"
        )
        # 2.5 — EXTRA: detect standalone city when shipping context (ETA/ETD)
        if re.search(r'\b(eta|etd|arrival|arrive|reach|departure)\b', s, re.I):
            for alias, canonical in CITY_ALIASES.items():
                if re.search(rf'\b{re.escape(alias)}\b', s, re.I):
                    location_logger.debug(
                        f"extract_location: no incoterm, but shipping-context city found → {canonical!r}"
                    )
                    return canonical

        return None   

    # выделяем часть ближе к концу строки
    tail = s[-100:]  # последние 100 символов чаще всего содержат локацию

    # ищем все потенциальные города/страны
    found_cities = []
    for alias, canonical in CITY_ALIASES.items():
        if re.search(rf'\b{re.escape(alias)}\b', tail, re.I):
            if canonical not in found_cities:
                found_cities.append(canonical)
    # ✅ дополнительно ищем склад в tail (после city-скана)
    found_wh = []
    for alias, wh in WAREHOUSE_ALIASES.items():
        if re.search(rf'\b{re.escape(alias)}\b', tail, re.I):
            if wh not in found_wh:
                found_wh.append(wh)
    if not found_cities:
        # ✅ если город не нашли — пробуем склад (incoterm уже есть)
        if found_wh:
            val = f"{incoterm} {found_wh[0]}".strip()
            location_logger.debug(f"extract_location: no city, warehouse fallback → {val!r}")
            return val
        location_logger.debug(f"extract_location: нет городов в '{tail}'")
        return None
    # нормализуем написание: соединяем города через " or " / "/" / "and"
    clean_parts = []
    for p in found_cities:
        p_clean = re.sub(r'\b(or|and|s)\b$', '', p, flags=re.I).strip(",. ")
        clean_parts.append(p_clean)
    # ✅ если есть и города, и склад — добавляем склад в конец
    for wh in found_wh:
        if wh not in clean_parts:
            clean_parts.append(wh)
    joined = re.sub(r'\s+', ' ', ' or '.join(clean_parts)).strip()
    # финальная сборка
    val = f"{incoterm} {joined}".strip()

    # финальная постпроверка — только если Incoterm + город известен
    if not any(alias.lower() in val.lower() for alias in CITY_ALIASES.values()):
        location_logger.debug(f"extract_location: финальная проверка не прошла → {val!r}")
        return None

    location_logger.debug(f"extract_location: успешно → {val!r}")
    return val
