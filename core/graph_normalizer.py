# core/graph_normalizer.py
import re, json, unicodedata

import pandas as pd
import logging

from utils.logger import setup_logging
from core.canonical_rules import apply_canonical_rules
from utils.normalize import normalize as _normalize
from utils.wine_guard import looks_like_new_wine
from core.patterns import valid_numerical, short_series_whitelist


# импортируем уже сконфигурированный драйвер и MODE
from config import driver, MODE

# инициализация общего логгера
setup_logging()
logger = logging.getLogger(__name__)

#separate logging for canonical lookups
canon_logger = logging.getLogger("core.graph_normalizer.canonical")

# ==========================================================
# 🕸 Neo4j driver (из config)
# ==========================================================
logger.info(f"[Neo4j] Using shared driver (mode={MODE})")


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

    # Merge dotted abbreviations: V.S.O.P → VSOP, X.O. → XO
    raw = re.sub(r"\b([A-Z])(?:\.([A-Z]))+(?:\.)?", lambda m: m.group(0).replace(".", ""), raw)

    # Extract tokens, keeping apostrophes and dots inside
    return re.findall(r"[A-Za-z0-9.'&%+]+", raw)


# ==========================================================
# BRAND LIST
# ==========================================================
def load_brands(path="tests/multiword_brands.json"):
    """Load all known brands (with normalization map)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    brands = []
    for k in ["one_word", "two_word", "three_word", "more"]:
        brands += data.get(k, [])
    # key = просто нижний регистр без удаления символов
    normalized = {b.lower().strip(): b for b in brands}
    logger.info(f"[INIT] Loaded {len(normalized)} brands")
    return normalized

BRANDS = load_brands()

# ==========================================================
# Глобальный справочник (все бренды + серии)
# ==========================================================
def load_all_brand_series(driver):
    """
    Загружаем все пары (brand, series) и default_series один раз — для быстрой валидации.
    Возвращает кортеж:
      • all_series (set[str]) — нормализованные серии всех брендов;
      • default_series_map (dict[str, str]) — brand_norm → default_series_norm
    """
    all_series = set()
    default_series_map = {}
    with driver.session() as s:
        rows = s.run("""
            MATCH (b:Brand)
            OPTIONAL MATCH (b)-[:HAS_SERIES|HAS_VARIANT]->(s:Series)
            RETURN DISTINCT b.name AS brand, s.name AS series, b.default_series AS default
        """).values()

    for brand, series, default in rows:
        if not brand:
            continue
        if series:
            all_series.add(_normalize(series))
        if default:
            default_series_map[_normalize(brand)] = _normalize(default)
            # добавим дефолт в общий список, чтобы он тоже проходил валидацию
            all_series.add(_normalize(default))

    logger.info(
        f"[INIT] Global series dict loaded: {len(all_series)} items, defaults: {len(default_series_map)}"
    )
    return all_series, default_series_map


ALL_SERIES_SET, DEFAULT_SERIES_MAP = load_all_brand_series(driver)




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
        elif token in brand_norm and len(token) >= 4:
            score += 0.75

        # prefix/suffix partials
        if brand_norm.startswith(token):
            score += 0.25

    # 2️⃣ multi-token sequence
    joined = " ".join(tokens[:3])
    if brand_norm in joined:
        score += 1.5

    # 3️⃣ numeric brand bonus
    if re.search(r"\b\d{3,4}\b", raw) and re.search(r"\d", brand_norm):
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
# GRAPH SERIES RESOLVER (упрощённая)
# ==========================================================
def build_series_resolver(driver):
    """
    Возвращает функцию resolve(brand)->list[str].
    Ищет серии, связанные с брендом, в графе.
    Если ничего не найдено — возвращает None и пишет предупреждение.
    """
    def resolve(brand: str):
        if not brand:
            return None
        bnorm = _normalize(brand)
        with driver.session() as s:
            rows = s.run("""
                // ⚙️ исправлено: убран депрекейтнутый синтаксис ':HAS_SERIES|:HAS_VARIANT'
                MATCH (b:Brand)-[:HAS_SERIES|HAS_VARIANT]->(s:Series)
                WHERE toLower(b.name) CONTAINS $bn
                RETURN DISTINCT s.name AS name
                ORDER BY s.name ASC
            """, bn=bnorm).values()
        if not rows:
            logger.debug(f"[GRAPH] no series found for brand: {brand}")
            return None
        series = [r[0] for r in rows if r and len(r[0]) > 1]
        logger.debug(f"[GRAPH] found {len(series)} series for brand: {brand}")
        return series
    return resolve


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
        self.series_resolver = series_resolver
        self._series_cache = {}  # cache: norm_brand -> list[str]
        # 🔁 pre-warm cache so known brand series (Apple, Honey, etc.) are available
        if self.series_resolver:
            for b in self.brands.values():
                try:
                    s_list = self.series_resolver(b) or []
                    if s_list:
                        self._series_cache[_normalize(b)] = [(s, _normalize(s)) for s in s_list]
                except Exception:
                    continue

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
            if category in ("beer", "wine"):
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

        # 3️⃣ бренд не найден → сбрасываем контекст
        
        logger.debug("[BEER] no brand in line → reset INIT")
        self.state = "INIT"
        self.last_brand = None
        self.context_type = "common"
        return None, None

    
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
            default_series = DEFAULT_SERIES_MAP.get(bnorm)
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
        #    но сначала проверим костыль: не выглядит ли это как самостоятельное вино
        if looks_like_new_wine(raw_norm):
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

        if not self.series_resolver or not brand:
            
            return None
        bkey = _normalize(brand)
        if bkey not in self._series_cache:
            try:
                series_list = self.series_resolver(brand) or []
            except Exception as e:
                logger.warning(f"[WARN] series_resolver failed for '{brand}': {e}")
                series_list = []
            # храним нормализованные фразы, но и оригиналы тоже, чтобы вернуть красиво
            self._series_cache[bkey] = [(s, _normalize(s)) for s in series_list if s and len(s) > 1]
            logger.debug(f"[GRAPH SERIES] cached series for '{brand}': {[s for s, _ in self._series_cache[bkey]]}")

        raw_norm = _normalize(raw)
        # выбираем самое длинное совпадение по нормализованной подстроке
        logger.debug(f"[GRAPH SERIES] raw_norm='{raw_norm}'")
        matches = []
        for s_original, s_norm in self._series_cache[bkey]:
            if not s_norm:
                continue
            logger.debug(f"[GRAPH SERIES] compare '{s_norm}' in '{raw_norm}'")
            if s_norm in raw_norm:
                logger.debug(f"[GRAPH SERIES] MATCH '{s_norm}' ⊂ '{raw_norm}' → {s_original}")
                matches.append((len(s_norm), s_original))
            
        if not matches:
            logger.debug(f"[GRAPH SERIES] no matches for brand='{brand}' raw='{raw_norm}'")
            return None
        # берём наиболее «длинную» серию (чаще всего наиболее специфичная)
        matches.sort(key=lambda x: -x[0])
        return matches[0][1]

    # ==========================================================
    # Базовая логика извлечения бренда/серии (как раньше)
    # ==========================================================
    
    def _extract_brand_series(self, raw: str):
        """Оригинальная версия без FSM-ограничений (мягкий скоринг, полное сканирование)."""
        tokens = [t for t in tokenize(raw)]
        logger.debug(f"[TOKENS] {tokens}")
        scores = {}
        logger.debug(f"[SCORES] {scores}")
        for token in tokens[:6]:  # ограничиваем первые токены
            t_norm = _normalize(token)
            if len(t_norm) < 3 or t_norm.isdigit():
                continue

            for b_norm, b_orig in self.brands.items():
                sc = score_brand_series(raw, b_norm)
                b_tokens = b_norm.split()
                # ✅ quick boost if brand literally appears in normalized raw
                if b_norm in _normalize(raw):
                    sc += 1.0

                # прямые совпадения
                if t_norm in b_tokens or t_norm == b_norm:
                    sc += 1
                    
                elif len(t_norm) >= 4 and any(t_norm in bt for bt in b_tokens):
                    sc += 0.25                    

                # ✅ исправленный plural-fix
                for bt in b_tokens:
                    if t_norm.rstrip("s") == bt or bt.rstrip("s") == t_norm:
                        sc += 0.6
                        
                    elif t_norm.endswith("es") and t_norm[:-2] == bt:
                        sc += 0.5
                        
                    elif t_norm.endswith("ies") and bt.endswith("y") and t_norm[:-3] + "y" == bt:
                        sc += 0.5                        

                if sc > 0:
                    scores[b_orig] = scores.get(b_orig, 0) + sc

        if not scores:
            logger.debug(f"[DETECT] no brand candidates found in: {raw}")
            return None, None
        #debug    
        
        top = sorted(scores.items(), key=lambda x: (-x[1], -len(x[0])))[0]
        logger.debug(f"[DEBUG SCORES] top={top}, all={list(scores.keys())[:10]}")
        #debug

        brand = top[0]            

        # выбираем лучший по скору, при равенстве — по длине
        brand = sorted(scores.items(), key=lambda x: (-x[1], -len(x[0])))[0][0]

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

                # 2️⃣ если нет совпадения, разрешаем только whitelisted короткие серии
                if not match:
                    after_tokens = tokenize(after)
                    for t in after_tokens:
                        t_norm = _normalize(t)
                        if t_norm in short_series_whitelist:
                            match = t
                            break
                        # 🚫 проверяем строгое совпадение числа в серии, а не подстроку
                        if t.isdigit():
                            for s in valid_numerical["series"]:
                                s_tokens = _normalize(s).split()
                                # серия может содержать число как отдельное слово, например "Macallan 18"
                                if t in s_tokens:
                                    match = t
                                    break
                            if match:
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

        # 🧠 собираем все нормализованные серии, где бренд совпадает или не важен
        possible_series = list(ALL_SERIES_SET)

        # фильтруем токены — оставляем только те, которые реально входят в серии
        series_tokens = []
        for t in tokens:
            t_norm = _normalize(t)
            if any(t_norm in s for s in possible_series):
                series_tokens.append(t)

        if not series_tokens:
            logger.debug(f"[AFTER] no series tokens matched for raw='{raw}'")
            return None

        candidate = " ".join(series_tokens)
        # ищем точное совпадение с одной из серий
        match = None
        for s in possible_series:
            if _normalize(s) in _normalize(candidate):
                match = s
                break

        logger.debug(f"[AFTER] candidate='{candidate}', matched={match}")
        return match or candidate

# ==========================================================
# NEO4J LOOKUPS
# ==========================================================
def find_canonical(tx, brand, series, raw):
    """Finds the best canonical name from Neo4j with penalty for overreach."""
    # ⚙️ добавлен DISTINCT для устранения дубликатов Canonical с одинаковыми именами
    rows = [r[0] for r in tx.run("MATCH (c:Canonical) RETURN DISTINCT c.name AS name").values()]
    canon_logger.debug(f"[CANON CANDIDATES] total={len(rows)} for brand={brand!r}, series={series!r}")
    if len(rows) > 10:
        canon_logger.debug(f"[CANON CANDIDATES SAMPLE] {rows[:10]}")
    bnorm = _normalize(brand or "")
    snorm = _normalize(series or "")
    rnorm = _normalize(raw)

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
            f"[CANON DEBUG DEFAULT] bnorm={bnorm!r}, snorm={snorm!r}, def_series={DEFAULT_SERIES_MAP.get(bnorm)!r}"
        )

        # ✅ NEW: if no explicit series detected, gently prefer the brand's default
        # using the already loaded DEFAULT_SERIES_MAP (bnorm is normalized brand)
        if not snorm and bnorm:
            def_series = DEFAULT_SERIES_MAP.get(bnorm)
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
            m = re.search(r"(\d{1,2})\s*(?:yo|year|years?)", s.lower())
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

        # 🧩 применяем доменные правила (штраф за Magnum и др.)
        try:            
            delta = apply_canonical_rules(raw, cname)
            if delta != 0:
                logging.getLogger(__name__).debug(
                    f"[CANON RULE] {cname}: delta={delta:+.2f}"
                )
            score += delta
        except Exception as e:
            logging.getLogger(__name__).warning(f"[CANON RULE] failed for {cname}: {e}")
        
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
        from core.graph_normalizer import load_brands_meta_from_graph
        meta = load_brands_meta_from_graph().get(brand, {})
        default_series = (meta.get("default_series") or "").lower()
        for candidate in tied:
            if default_series and default_series in candidate.lower():
                canon_logger.debug(f"[CANON TIE-BREAK] picked default_series '{default_series}' → {candidate!r}")
                return candidate

    
    return best

def load_brands_meta_from_graph():
    with driver.session() as s:
        rows = s.run("""
            MATCH (b:Brand)-[:BELONGS_TO]->(c:Category)
            RETURN b.name AS brand,
                   c.name AS category,
                   b.default_series AS default_series
        """).data()
    return {
        r["brand"]: {
            "category": r["category"],
            "default_series": r.get("default_series")
        }
        for r in rows
    }

# ==========================================================
# MAIN NORMALIZER
# ==========================================================
def normalize_dataframe(df: pd.DataFrame, col_name: str = "Наименование") -> pd.DataFrame:
    col = col_name  # back-compat alias
    if col not in df.columns:
        logger.warning(f"[WARN] no '{col}' column")
        return df
    brands_meta = load_brands_meta_from_graph()
    series_resolver = build_series_resolver(driver)
    extractor = BrandSeriesExtractor(BRANDS, series_resolver, brands_meta)

    with driver.session() as s:
        for i, raw in enumerate(df[col_name].fillna("").astype(str)):
            if not raw.strip():
                continue

            brand, series = extractor.extract(raw)

            if not brand:
                continue
            canon_logger.debug(
                f"[LOOKUP START] raw={raw!r} → brand={brand!r}, series={series!r}"
            )
            found = s.execute_read(find_canonical, brand, series, raw)
            canon_logger.debug(f"[LOOKUP END] raw={raw!r} → canonical={found!r}")
            if found:
                df.at[i, col_name] = found
                logger.debug(f"[CANON] → {found}")
            else:
                logger.debug(f"[CANON] no match for {raw}")

    return df