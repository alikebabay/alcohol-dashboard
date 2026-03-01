# core/graph_normalizer.py
import re, json, unicodedata

import pandas as pd
import logging

from utils.logger import setup_logging
from utils.normalize import normalize as _normalize
from utils.wine_guard import looks_like_new_wine
from libraries.patterns import valid_numerical
from utils.series_number_extractor import _extract_label_number


import core.graph_loader as gl



# инициализация общего логгера
setup_logging()
logger = logging.getLogger(__name__)

#separate logging for canonical lookups
canon_logger = logging.getLogger("core.graph_normalizer.canonical")
brand_logger = logging.getLogger("core.graph_normalizer.brand")


# ==========================================================
# TOKENIZER
# ==========================================================
def tokenize(raw: str) -> list[str]:
    """
    Splits raw strings into tokens while preserving:
      • apostrophes inside words (L'Orange)
      • dots inside abbreviations (V.S.O.P → VSOP)
    and still filters out most punctuation noise.
    """
    # Merge French-style prefixes like L' or D' (before capital letter)
    raw = re.sub(r"\b([A-Za-z])['’]\s*(?=[A-Z])", r"\1’", raw)

    # Extract tokens, keeping apostrophes and dots inside
    return re.findall(r"[A-Za-z0-9.'&%+]+", raw)



# ==========================================================
# Simple brand detector helper
# ==========================================================
def line_contains_any_brand(raw_norm: str) -> bool:
    """Returns True if the line contains ANY known brand (normalized)."""
    for bnorm in gl.BRAND_KEYMAP.keys():
        if bnorm in raw_norm:
            return True
    return False



# ==========================================================
# SCORING
# ==========================================================
def score_brand(raw, brand_norm):
    tokens = _normalize(raw).split()
    score = 0.0

    # 1️⃣ token matches
    for i, token in enumerate(tokens[:6]):
        if len(token) < 3:
            score -= 1
            continue
        if token == brand_norm:
            score += 1.0
        elif len(token) >= 4 and brand_norm.startswith(token):
           score += 0.75

    # 2️⃣ multi-token sequence
    joined = " ".join(tokens[:3])
    if brand_norm in joined:
        score += 1.5

    # 3️⃣ numeric brand bonus (match only if the same number appears)
    raw_nums = re.findall(r"\d{2,4}", raw)
    brand_nums = re.findall(r"\d{2,4}", brand_norm)
    if any(bn in raw_nums for bn in brand_nums):
        score += 1.0

    # 4️⃣ position bonus
    if _normalize(raw).startswith(brand_norm.split()[0]):
        score += 0.25

    return score

# ==========================================================
# COMBINED BRAND + SERIES SCORING
# ==========================================================
def score_brand_series(raw, brand_norm, series_norm=None):
    """
    Extended scoring that boosts candidates matching both brand and series.
    Does not penalize missing series unless the raw string contains a series fragment.
    """
    base = score_brand(raw, brand_norm)

    if not series_norm:
        return base

    raw_norm = _normalize(raw)
    series_tokens = series_norm.split()

    # detect if raw text even *has* series-like info
    has_series_fragment = any(tok in raw_norm for tok in series_tokens)

    # 1️⃣ bonus for full series presence together with brand
    if has_series_fragment and all(tok in raw_norm for tok in series_tokens):
        base += 1.5

    # 2️⃣ soft bonus for partial overlap
    elif has_series_fragment:
        base += 0.5

    return base



# ==========================================================
# BRAND + SERIES DETECTION
# ==========================================================
class BrandSeriesExtractor:
    """
    Состояние-машина для последовательной обработки строк.
    Управляет контекстом (INIT → BRAND → INIT).
    """
    
    def __init__(self, brands_dict, series_resolver=None, brands_meta=None):
        self.state = "INIT"
        self.last_brand = None
        self.context_type = "common"  # default
        self.brands = brands_dict
        self.brands_meta = brands_meta or {}
        # callback: series_resolver(brand:str) -> list[str] (из графа)
        
        self.series_resolver = None  # unused now
        self._series_cache = {}

        # Warm cache directly from global BRAND_SERIES_MAP
        for b_norm, series_list in gl.BRAND_SERIES_MAP.items():
            self._series_cache[b_norm] = [(s, _normalize(s)) for s in series_list]

    # ==========================================================
    # Публичный метод
    # ==========================================================
    def extract(self, raw: str):
        raw_norm = _normalize(raw)

        if self.state == "INIT":
            return self._handle_init(raw, raw_norm)
        elif self.state == "BRAND":
            return self._handle_brand(raw, raw_norm)
        else:
            raise RuntimeError(f"Unknown state {self.state}")

    # ==========================================================
    # INIT → ищем новый бренд
    # ==========================================================
    def _handle_init(self, raw, raw_norm):
        brand, series = self._extract_brand_series(raw)  
        
        if brand:
            self.last_brand = brand
            # определяем категорию из метаданных
            meta = self.brands_meta.get(brand, {})
            category = meta.get("category", "").lower()
            if category in ("beer", "wine", "cider"):
                self.context_type = "beer"  # используем ту же ветку
            else:
                self.context_type = "common"

            self.state = "BRAND"
            logger.debug(f"[STATE] INIT → BRAND ({brand}) context={self.context_type}")
        else:
            logger.debug(f"[STATE] INIT stays INIT (no brand)")
        return brand, series

    # ==========================================================
    # BRAND → ищем только серии внутри текущего бренда
    # ==========================================================
    def _handle_brand(self, raw, raw_norm):
        
        logger.debug(f"[CTX] handle={self.context_type.upper()} brand={self.last_brand}")
        if self.context_type == "beer":
            return self._handle_beer(raw, raw_norm)
        else:
            return self._handle_common(raw, raw_norm)
        
    def _handle_beer(self, raw, raw_norm):
        brand = self.last_brand
        brand_norm = _normalize(brand)
        detected_brand, detected_series = self._extract_brand_series(raw)
        detected_norm = _normalize(detected_brand) if detected_brand else None

        # 1️⃣ бренд есть в строке → возвращаем его и серию (только прямо после бренда)
        if brand_norm in raw_norm:
            series = self._extract_series_after_brand(raw, brand_norm)
            return brand, series

        # 2️⃣ встретили другой бренд → переключаем контекст
        if detected_brand and detected_norm != brand_norm:
            self.last_brand = detected_brand
            meta = self.brands_meta.get(detected_brand, {})
            category = meta.get("category", "").lower()
            self.context_type = "beer" if category == "beer" else "common"
            
            logger.debug(f"[CTX] beer → {self.context_type} ({detected_brand})")
            return detected_brand, detected_series

        # 3️⃣ бренд не найден → сбрасываем контекст и ПЕРЕПРОБУЕМ INIT на этой же строке
        logger.debug("[BEER] no brand in line → reset INIT + retry init on same line")
        self.state = "INIT"
        self.last_brand = None
        self.context_type = "common"
        return self._handle_init(raw, raw_norm)
    
    def _handle_common(self, raw, raw_norm):
        brand = self.last_brand
        brand_norm = _normalize(brand)
        # 1 проверяем наличие контекстного бренда в строке
        if brand_norm in raw_norm:
            series = self._extract_series_after_brand(raw, brand_norm)
            if series:                
                logger.debug(f"[COMMON] brand present, found series ({series})")
                return brand, series
            
            # 🔁 нет серии — пробуем дефолт сначала из глобального кэша DEFAULT_SERIES_MAP
            bnorm = _normalize(brand)
            default_series = gl.DEFAULT_SERIES_MAP.get(bnorm)
            if default_series:
                logger.debug(f"[FALLBACK→DEFAULT] brand={brand} → default_series='{default_series}'")
                return brand, default_series

            # затем, если что, смотрим локальные метаданные бренда (на случай ручных переопределений)
            meta = self.brands_meta.get(brand, {})
            meta_default = meta.get("default_series")
            if meta_default:
                logger.debug(f"[FALLBACK] using meta.default_series '{meta_default}' for brand={brand}")
                return brand, meta_default

            logger.debug(f"[COMMON] brand present, no series and no default; keep context")
            return brand, None
        
        # 2️⃣ если контекстный бренд не встречается — пробуем искать серии контекстного бренда в строке
        #   но сначала проверим костыль: не выглядит ли это как самостоятельное вино
        # ------------------------------------------
        # DEBUG: brand detection inside this line
        # ------------------------------------------
        detected_brands = []
        for bnorm, borig in gl.BRAND_KEYMAP.items():
            if bnorm in raw_norm:
                detected_brands.append(borig)

        # primary flag (old)
        has_brand_in_line = bool(detected_brands)

        logger.debug(
            f"[COMMON DEBUG] raw={raw!r} | raw_norm={raw_norm!r}\n"
            f"    context_brand={brand!r} ({brand_norm!r})\n"
            f"    detected_brands={detected_brands}\n"
            f"    has_brand_in_line={has_brand_in_line}"
        )


        if has_brand_in_line and looks_like_new_wine(raw_norm):
            logger.debug(f"[WINE GUARD] skip series via graph for {brand}: looks like independent wine ({raw})")
        else:
            series = self._extract_series_for_brand_via_graph(raw, brand)
            if series:
                logger.debug(f"[STATE] BRAND (series via graph; keep {brand})")
                return brand, series

        # 3️⃣ если серии контекстного бренда не нашли — ищем новый бренд 
        new_brand, new_series = self._extract_brand_series(raw) 
        if new_brand:
            logger.debug(f"[STATE] BRAND → BRAND ({brand} → {new_brand})")
            self.last_brand = new_brand
            return new_brand, new_series
        # 4️⃣ если не нашли ни серию, ни бренд — сбрасываем
        logger.debug(f"[STATE] BRAND → INIT (no brand/series context)")
        self.state = "INIT"
        self.last_brand = None
        return None, None

    
    # ==========================================================
    # серии для текущего бренда через граф (Neo4j)
    # ==========================================================
    def _extract_series_for_brand_via_graph(self, raw: str, brand: str):
        """
        Достаём из графа список серий для brand и пытаемся найти их в raw.
        Матчим по нормализованной подстроке (многословные серии поддерживаются).
        Возвращаем найденную серию (как строку), либо None.
        """
        logger.debug(f"[GRAPH SERIES] enter brand='{brand}' raw='{raw}'")

        if not brand:
            return None

        bkey = _normalize(brand)
        entries = gl.BRAND_SERIES_FULL.get(bkey, [])


        raw_norm = _normalize(raw)
        logger.debug(f"[GRAPH SERIES] raw_norm='{raw_norm}'")

        matches = []          # прямые (по series_norm)
        alias_matches = []    # alias fallback

        for entry in entries:
            s_original = entry["series"]
            s_norm = entry["series_norm"]
            alias_list = entry.get("alias", [])   # ← ВАЖНО: используем alias, как в canonical

            # 1) PRIMARY: series_norm — все токены по порядку (допускаем вставки типа "75cl")
            if s_norm:
                tokens = [t for t in s_norm.split() if t]
                pos = 0
                ok = True
                for t in tokens:
                    idx = raw_norm.find(t, pos)
                    if idx == -1:
                        ok = False
                        break
                    pos = idx + len(t)

                if ok:
                    logger.debug(
                        f"[GRAPH SERIES] DIRECT TOKENS MATCH '{s_norm}' → {s_original}"
                    )
                    matches.append((len(s_norm), s_original))
                    continue

            # 2) FALLBACK: alias (также через токены, но после series_norm)
            for a in alias_list:
                if not a:
                    continue
                a_norm = _normalize(a)
                tokens = [t for t in a_norm.split() if t]
                pos = 0
                ok = True
                for t in tokens:
                    idx = raw_norm.find(t, pos)
                    if idx == -1:
                        ok = False
                        break
                    pos = idx + len(t)

                if ok:
                    logger.debug(
                        f"[GRAPH SERIES] ALIAS TOKENS MATCH '{a_norm}' → {s_original}"
                    )
                    alias_matches.append((len(a_norm), s_original))
                    break
            
        # 1) если есть нормальные совпадения → используем их
        if matches:
            matches.sort(key=lambda x: -x[0])
            return matches[0][1]

        # 2) иначе — alias fallback
        if alias_matches:
            alias_matches.sort(key=lambda x: -x[0])
            return alias_matches[0][1]

        logger.debug(f"[GRAPH SERIES] no matches for brand='{brand}' raw='{raw_norm}'")
        return None

    # ==========================================================
    # Базовая логика извлечения бренда/серии (как раньше)
    # ==========================================================
    
    def _extract_brand_series(self, raw: str):
        """Оригинальная версия без FSM-ограничений (мягкий скоринг, полное сканирование)."""        
        tokens = [t for t in tokenize(raw)]
        
        scores = {}
        raw_norm_full = _normalize(raw)
        brand_logger.debug("[BRAND ENTER] raw=%r", raw)
        for token in tokens[:8]:  # ограничиваем первые токены - 8 for cases 
                                  # 2200 cs*6 btl Moët & Chandon Brut без ПУ - 25,80 eur/btl DAP Riga
            
            t_norm = _normalize(token)            
            
            # ✅ allow numeric brands (e.g. 1792, 1800, 19 Crimes, 7 Deadly Zins)
            if len(t_norm) < 3:
                continue
            if t_norm.isdigit():
                if not any(t_norm in _normalize(b) for b in valid_numerical["brands"]):
                    continue

            for b_norm, b_orig in self.brands.items():
                sc = score_brand_series(raw, b_norm)               

                b_tokens = b_norm.split()
                # ----------------------------------------------------
                # BRAND ALIAS SUPPORT (перед обычными матчами)
                # ----------------------------------------------------
                meta = self.brands_meta.get(b_orig, {})
                brand_aliases = meta.get("brand_alias") or []
                variants = [b_norm] + [_normalize(a) for a in brand_aliases if a]

                for v_norm in variants:
                    if not v_norm:
                        continue

                    sc = score_brand_series(raw, v_norm)
                    b_tokens = v_norm.split()

                    # ✅ quick boost если этот вариант буквально есть в raw
                    if v_norm in raw_norm_full:
                        brand_logger.debug(
                            "[BRAND BOOST][LITERAL] brand=%r v_norm=%r +1.0",
                            b_orig, v_norm
                        )
                        sc += 1.0

                    # прямые совпадения
                    if t_norm in b_tokens or t_norm == v_norm:
                        brand_logger.debug(
                            "[BRAND BOOST][TOKEN_EQ] brand=%r token=%r b_tokens=%s +1.0",
                            b_orig, t_norm, b_tokens
                        )
                        sc += 1

                    elif len(t_norm) >= 4 and any(bt.startswith(t_norm) for bt in b_tokens):
                        brand_logger.debug(
                            "[BRAND BOOST][TOKEN_PART] brand=%r token=%r b_tokens=%s +0.25",
                            b_orig, t_norm, b_tokens
                        )
                        sc += 0.25

                    # ✅ исправленный plural-fix
                    for bt in b_tokens:
                        if t_norm.rstrip("s") == bt or bt.rstrip("s") == t_norm:
                            brand_logger.debug(
                                "[BRAND BOOST][PLURAL] brand=%r token=%r bt=%r +0.6",
                                b_orig, t_norm, bt
                            )
                            sc += 0.6

                        elif t_norm.endswith("es") and t_norm[:-2] == bt:
                            brand_logger.debug(
                                "[BRAND BOOST][ES] brand=%r token=%r bt=%r +0.5",
                                b_orig, t_norm, bt
                            )
                            sc += 0.5

                        elif t_norm.endswith("ies") and bt.endswith("y") and t_norm[:-3] + "y" == bt:
                            brand_logger.debug(
                                "[BRAND BOOST][IES] brand=%r token=%r bt=%r +0.5",
                                b_orig, t_norm, bt
                            )
                            sc += 0.5

                    if sc > 0:
                        # 👇 все варианты (бренд + алиасы) копят скор в одном ключе бренда
                        brand_logger.debug(
                            "[BRAND SCORE ADD] brand=%r v_norm=%r token=%r sc=%.3f total_before=%.3f",
                            b_orig,
                            v_norm,
                            t_norm,
                            sc,
                            scores.get(b_orig, 0)
                        )
                        scores[b_orig] = scores.get(b_orig, 0) + sc

        if not scores:
            logger.debug(f"[DETECT] no brand candidates found in: {raw}")
            return None, None
        #debug    
        
        top = sorted(scores.items(), key=lambda x: (-x[1], -len(x[0])))[0]
        logger.debug(f"[DEBUG SCORES] top={top}, all={list(scores.keys())[:10]}")
        #debug

        brand = top[0]  
        brand_logger.debug(
            "[BRAND SCORES FINAL] %s",
            scores
        )          

        # выбираем лучший по скору, при равенстве — по длине
        brand = sorted(scores.items(), key=lambda x: (-x[1], -len(x[0])))[0][0]
        
        brand_logger.debug(
            "[BRAND PICK] brand=%r score=%.3f",
            brand,
            scores.get(brand)
        )


        # извлекаем серию после бренда
        idx = _normalize(raw).find(_normalize(brand))
        series = None
        if idx != -1:
            after = raw[idx + len(brand):].strip()
            if after:
                bkey = _normalize(brand)
                brand_series = [s for s, _ in self._series_cache.get(bkey, [])]
                after_norm = _normalize(after)

                # 1️⃣ ищем совпадение серии бренда в "after"
                match = None
                for s in brand_series:
                    s_norm = _normalize(s)
                    if f" {s_norm} " in f" {after_norm} ":
                        match = s
                        break

                # 2️⃣ если нет совпадения, пробуем извлечь числовую серию, связанную с брендом
                if not match:
                    
                    after_tokens = tokenize(after)
                    # Построим карту (label3 → {numbers}) из серий этого бренда
                    label_to_numbers = {}
                    series_lookup = {}
                    for s in brand_series:
                        lbl, num = _extract_label_number(s)
                        if lbl and num:
                            k = lbl[:3]
                            label_to_numbers.setdefault(k, set()).add(num)
                            series_lookup[(k, num)] = s

                    for i, t in enumerate(after_tokens):
                        t_norm = _normalize(t)                        
                        if t.isdigit() and i > 0:
                            prev = after_tokens[i - 1]
                            lbl = _normalize(prev)[:3]
                            try:
                                t_num = int(t)
                            except ValueError:
                                continue
                            if lbl in label_to_numbers and t_num in label_to_numbers[lbl]:
                                match = series_lookup[(lbl, t_num)]
                                logger.debug(f"[STRICT BRAND NUMERIC] label={lbl} num={t_num} → '{match}'")
                                break

                series = match
                if series:
                    logger.debug(f"[SERIES FOUND STRICT] {series}")
                else:
                    logger.debug(f"[STRICT] no series match found for brand '{brand}' → fallback to default later")              
               
        logger.debug(f"[RETURN DEBUG] returning brand={brand!r}, series={series!r} for raw='{raw}'")
        return brand, series
    
    def _extract_series_after_brand(self, raw, brand_norm):
        """
        Извлекает серию, оставляя только слова, которые встречаются в известных сериях из графа.
        """
        logger.debug(f"[AFTER] start brand_norm='{brand_norm}' raw='{raw}'")
        idx = _normalize(raw).find(brand_norm)
        if idx == -1:
            return None

        after = raw[idx + len(brand_norm):].strip()
        if not after:
            return None

        after_norm = _normalize(after)
        tokens = tokenize(after)
        logger.debug(f"[AFTER] normalized(after)='{after_norm}', tokens={tokens}")

        # ============================================================
        # 🔥 NEW: прямой match по series_norm и alias (НЕ ломает old logic)
        # ============================================================
        bkey = brand_norm
        entries = gl.BRAND_SERIES_FULL.get(bkey, [])

        best = None
        best_len = -1

        for entry in entries:
            s_original = entry["series"]
            s_norm = entry["series_norm"]

            # ---- SERIES MATCH ----
            if all(tok in after_norm for tok in s_norm.split()):
                ln = len(s_norm)
                if ln > best_len:
                    best_len = ln
                    best = s_original

            # ---- ALIAS MATCH ----
            for a in entry.get("alias", []):
                a_norm = _normalize(a)
                if all(tok in after_norm for tok in a_norm.split()):
                    ln = len(a_norm)
                    if ln > best_len:
                        best_len = ln
                        best = s_original

        if best:
            logger.debug(f"[AFTER] series/alias direct match → {best!r}")
            return best

        logger.debug("[AFTER] no alias/series direct match → continue old logic")

        # 🧠 собираем все нормализованные серии, где бренд совпадает или не важен
        bkey = brand_norm
        entries = gl.BRAND_SERIES_FULL.get(bkey, [])
        possible_series = [ _normalize(e["series"]) for e in entries ]


        # фильтруем токены — оставляем только те, которые реально входят в серии
        series_tokens = []
        for t in tokens:
            t_norm = _normalize(t)
            if len(t_norm) >= 3 and any(t_norm in s.split() for s in possible_series):
                series_tokens.append(t)

        if not series_tokens:
            logger.debug(f"[AFTER] no series tokens matched for raw='{raw}'")
            return None

        candidate = " ".join(series_tokens)
        # ищем точное совпадение с одной из серий
        match = None
        cand_norm = _normalize(candidate)
        for s in possible_series:
            s_norm = _normalize(s)
            # exact word or numeric-aware match
            if f" {s_norm} " in f" {cand_norm} ":
                match = s
                break
            # numeric safety: match "Bin 28" but not "Bin 2"
            lbl_s, num_s = _extract_label_number(s)
            lbl_c, num_c = _extract_label_number(candidate)
            if lbl_s and num_s and lbl_c == lbl_s and num_c == num_s:
                match = s
                break

        logger.debug(f"[AFTER] candidate='{candidate}', matched={match}")
        return match or candidate

# ==========================================================
# NEO4J LOOKUPS
# ==========================================================
def find_canonical(brand, series, raw):
    """Finds the best canonical name from Neo4j with penalty for overreach."""
    # ⚙️ добавлен DISTINCT для устранения дубликатов Canonical с одинаковыми именами
    rows = gl.CANONICAL_NAMES
    canon_logger.debug(f"[CANON CANDIDATES] total={len(rows)} for brand={brand!r}, series={series!r}")
    if len(rows) > 10:
        canon_logger.debug(f"[CANON CANDIDATES SAMPLE] {rows[:10]}")
    bnorm = _normalize(brand or "")
    snorm = _normalize(series or "")
    rnorm = _normalize(raw)
    canon_logger.debug(
        f"[ALIAS SERIES] enter brand={brand!r}, series={series!r}, "
        f"bnorm={bnorm!r}, snorm={snorm!r}, raw_norm={rnorm!r}"
    )
    # ---------------------------------------------------------
    # 🔥 Алиасы серий (per brand)
    # Если series == None, пробуем определить серию по alias-ключам
    # ---------------------------------------------------------
    if brand and not series:
        bkey = bnorm
        entries = gl.BRAND_SERIES_FULL.get(bkey, [])
        canon_logger.debug(
            f"[ALIAS SERIES] lookup bkey={bkey!r}, entries={len(entries)}"
        )
        best = None
        best_len = -1
        for entry in entries:
            canon_logger.debug(
                f"[ALIAS SERIES] entry series={entry.get('series')!r}, "
                f"series_norm={entry.get('series_norm')!r}, "
                f"alias={entry.get('alias')!r}"
            )
            for key in entry.get("alias", []):
                if key and key in rnorm:
                    canon_logger.debug(
                        f"[ALIAS SERIES] MATCH key={key!r} ⊂ raw_norm → "
                        f"series={entry.get('series')!r}"
                    )
                    # выбираем самую длинную alias-форму (yl magnum > yl)
                    if len(key) > best_len:
                            best_len = len(key)
                            best = entry["series"]
            canon_logger.debug(
                f"[ALIAS SERIES] best={best!r}, best_len={best_len}, "
                f"before_snorm={snorm!r}"
            )
        if best:
            # конвертируем найденную alias-серию в нормализованную форму
            snorm = _normalize(best)
            canon_logger.debug(
                f"[ALIAS SERIES] resolved via alias → series={best!r}, "
                f"snorm={snorm!r}"
            )
        else:
            canon_logger.debug(
                f"[ALIAS SERIES] no alias match for brand={brand!r} "
                f"in raw_norm={rnorm!r}"
            )

    def canonical_score(cname):
        cn_norm = _normalize(cname)
        score = 0.0

        # base: brand must appear
        if bnorm and bnorm in cn_norm:
            score += 1.0
        else:
            return -1.0  # skip if brand not found

        # reward if series appears and is present in both (series-aware equivalence)
        def _series_key(s: str) -> str:
            # общий ключ серии: убираем только лишние пробелы, оставляем точки для отличия V.S vs V.S.O.P
            return re.sub(r"\s+", "", s)

        if snorm:
            sn_clean = _series_key(snorm)
            cn_clean = _series_key(cn_norm)
            rn_clean = _series_key(rnorm)
            if sn_clean and sn_clean in cn_clean and sn_clean in rn_clean:
                score += 0.6
            
        canon_logger.debug(
            f"[CANON DEBUG DEFAULT] bnorm={bnorm!r}, snorm={snorm!r}, def_series={gl.DEFAULT_SERIES_MAP.get(bnorm)!r}"
        )

        # ✅ NEW: if no explicit series detected, gently prefer the brand's default
        # using the already loaded DEFAULT_SERIES_MAP (bnorm is normalized brand)
        if not snorm and bnorm:
            def_series = gl.DEFAULT_SERIES_MAP.get(bnorm)
            if def_series and def_series in cn_norm:
                score += 0.5
        # --- NEW: token-overlap bonus (brand-agnostic), helps when series is None
        # compare only non-brand tokens
        c_tokens = cn_norm.split()
        b_tokens = set(bnorm.split()) if bnorm else set()
        nb_tokens = [t for t in c_tokens if t not in b_tokens]
        raw_tokens = set(t for t in rnorm.split() if len(t) > 2)
        overlap_cnt = sum(1 for t in nb_tokens if t in raw_tokens)
        if overlap_cnt > 0:
            # only boost if canonical token (e.g. "fire") really appears in raw text
            score += 0.15 * overlap_cnt
        else:
            score -= 0.2  # slight penalty when no overlap at all
        
        # 🧮 NEW: numeric year-aware adjustment (penalize wrong ages, boost exact)
        def _extract_year(s: str):
            m = re.search(
                    r"(\d{1,2})\s*(?:yo|y\.?o\.?|year|years?|yr|y/o)", 
                    s.lower()
                )
            return int(m.group(1)) if m else None

        y_raw = _extract_year(rnorm)
        y_can = _extract_year(cn_norm)
        if y_raw and y_can:
            diff = abs(y_raw - y_can)
            if diff == 0:
                score += 0.3
            elif diff == 1:
                score -= 0.1
            elif diff >= 2:
                score -= 0.3
            canon_logger.debug(f"[CANON YEAR DEBUG] {cname!r}: y_raw={y_raw}, y_can={y_can}, diff={diff}, adj→{score:.2f}")

        # 🔍 substring containment bonus for series name
        if snorm and snorm in cn_norm:
            score += 0.2
        elif snorm and cn_norm in snorm:
            score += 0.1
        

        # small bonus for perfect equality
        if cn_norm == bnorm or cn_norm == rnorm:
            score += 0.3

        
        
        canon_logger.debug(f"[CANON SCORE] {cname!r} → {score:.2f}")
        return score

    # compute scores for all candidates
    scored = [(c, canonical_score(c)) for c in rows]
    scored = [x for x in scored if x[1] > 0]

    if not scored:
        canon_logger.debug("[CANON RESULT] no valid canonical candidates found")
        return None

    sorted_scored = sorted(scored, key=lambda x: (-x[1], len(x[0])))
    canon_logger.debug(
        "[CANON SCORES] top10=" +
        ", ".join(f"{c!r}:{s:.2f}" for c, s in sorted_scored[:10])
    )

    sorted_scored = sorted(scored, key=lambda x: (-x[1], len(x[0])))
    canon_logger.debug("[CANON SCORES] top10=" + ", ".join(f"{c!r}:{s:.2f}" for c, s in sorted_scored[:10]))
    best = sorted_scored[0][0]
    best_score = max(scored, key=lambda x: x[1])[1]
    canon_logger.debug(f"[CANON PICKED] best={best!r} score={best_score:.2f}")

    # ⚙️ если несколько равных — выбираем дефолтную серию бренда (если есть)
    tied = [c for c, s in scored if abs(s - best_score) < 1e-9]
    if len(tied) > 1:
        
        meta = gl.BRANDS_META.get(brand, {})
        default_series = (meta.get("default_series") or "").lower()
        for candidate in tied:
            if default_series and default_series in candidate.lower():
                canon_logger.debug(f"[CANON TIE-BREAK] picked default_series '{default_series}' → {candidate!r}")
                return candidate

    
    return best



# ==========================================================
# MAIN NORMALIZER
# ==========================================================
def normalize_dataframe(df: pd.DataFrame, col_name: str = "Наименование") -> pd.DataFrame:
    col = col_name
    if col not in df.columns:
        logger.warning(f"[WARN] no '{col}' column")
        return df

    extractor = BrandSeriesExtractor(gl.BRANDS, brands_meta=gl.BRANDS_META)
    

    for i, raw in enumerate(df[col].fillna("").astype(str)):
        if not raw.strip():
            continue

        brand, series = extractor.extract(raw)
        canon_logger.debug(
            "[ROW] i=%d raw=%r → brand=%r series=%r state=%s ctx=%s",
            i, raw, brand, series, extractor.state, extractor.context_type
        )
        if not brand:
            canon_logger.debug("[ROW DROP] i=%d reason=no_brand raw=%r", i, raw)
            continue

        canon_logger.debug(f"[LOOKUP START] raw={raw!r} → brand={brand!r}, series={series!r}")

        found = find_canonical(brand, series, raw)

        canon_logger.debug(f"[LOOKUP END] raw={raw!r} → canonical={found!r}")

        if found:
            df.at[i, col] = found
        else:
            logger.debug(f"[CANON] no match for {raw}")

    return df
