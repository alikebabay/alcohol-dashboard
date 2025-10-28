# core/graph_normalizer.py
import re, json, unicodedata
from pathlib import Path
import pandas as pd
import logging
from utils.logger import setup_logging
from core.canonical_rules import apply_canonical_rules
from utils.normalize import normalize as _normalize

# импортируем уже сконфигурированный драйвер и MODE
from config import driver, MODE

# инициализация общего логгера
setup_logging()
logger = logging.getLogger(__name__)

# ==========================================================
# 🕸 Neo4j driver (из config)
# ==========================================================
logger.info(f"[Neo4j] Using shared driver (mode={MODE})")

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
    normalized = {
        re.sub(r"[^a-z0-9 ]", "", b.lower().replace("&", "and")).strip(): b
        for b in brands
    }
    logger.info(f"[INIT] Loaded {len(normalized)} brands")
    return normalized

BRANDS = load_brands()





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
                WHERE toLower(replace(b.name,'&','and')) CONTAINS $bn
                RETURN DISTINCT s.name AS name
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
            self.context_type = "beer" if category == "beer" else "common"

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

        if brand_norm in raw_norm:
            series = self._extract_series_after_brand(raw, brand_norm)
            if series:
                
                logger.debug(f"[COMMON] brand present, found series ({series})")
                return brand, series
            
            logger.debug(f"[COMMON] brand present, no series; keep context")
            return brand, None
        # 2️⃣ если бренд не встречается — пробуем искать серии этого бренда в строке 
        # # (например, "Rose Imperial" для "Moet & Chandon") 
        series = self._extract_series_for_brand_via_graph(raw, brand) 
        if series: 
            logger.debug(f"[STATE] BRAND (series via graph; keep {brand})") 
            return brand, series 
        # 3️⃣ если серии текущего бренда не нашли — ищем новый бренд 
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
        tokens = [t for t in re.findall(r"[A-Za-z0-9&%+]+", raw)]
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
                after_tokens = re.findall(r"[A-Za-z0-9%+]+", after)
                valid = [t for t in after_tokens if not t.isdigit() and len(t) > 2]
                if valid:
                    series = " ".join(valid[:3])

        logger.debug(f"[RETURN DEBUG] returning brand={brand!r}, series={series!r} for raw='{raw}'")
        return brand, series
    
    def _extract_series_after_brand(self, raw, brand_norm):
        logger.debug(f"[AFTER] start brand_norm='{brand_norm}' raw='{raw}'")
        idx = _normalize(raw).find(brand_norm)        
        logger.debug(f"[AFTER] normalized(raw)='{_normalize(raw)}', idx={idx}")
        if idx == -1:
            return None
        after = raw[idx + len(brand_norm):]
        tokens = re.findall(r"[A-Za-z0-9%+]+", after)
        valid = [t for t in tokens if not t.isdigit() and len(t) > 2]

       
        logger.debug(f"[AFTER] after='{after}', tokens={tokens}, valid={valid}")

        return " ".join(valid[:3]) if valid else None
    
    



# ==========================================================
# NEO4J LOOKUPS
# ==========================================================
def find_canonical(tx, brand, series, raw):
    """Finds the best canonical name from Neo4j with penalty for overreach."""
    # ⚙️ добавлен DISTINCT для устранения дубликатов Canonical с одинаковыми именами
    rows = [r[0] for r in tx.run("MATCH (c:Canonical) RETURN DISTINCT c.name AS name").values()]
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

        # reward if series appears and is present in both
        if snorm and snorm in cn_norm and snorm in rnorm:
            score += 0.6
        # --- NEW: token-overlap bonus (brand-agnostic), helps when series is None
        # compare only non-brand tokens
        c_tokens = cn_norm.split()
        b_tokens = set(bnorm.split()) if bnorm else set()
        nb_tokens = [t for t in c_tokens if t not in b_tokens]  # non-brand tokens of candidate
        raw_tokens = set(rnorm.split())
        overlap_cnt = sum(1 for t in nb_tokens if t in raw_tokens)
        if overlap_cnt > 0:
            # small bonus per matching non-brand token
            score += 0.25 * overlap_cnt

        # penalty if canonical contains tokens not present in raw
        extra_tokens = [t for t in cn_norm.split() if t not in rnorm.split()]
        if extra_tokens:
            score -= len(extra_tokens) * 0.15

        # penalty if canonical longer but series absent
        if not snorm and len(cn_norm.split()) > len(bnorm.split()):
            score -= 0.5

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

        return score

    # compute scores for all candidates
    scored = [(c, canonical_score(c)) for c in rows]
    scored = [x for x in scored if x[1] > 0]

    if not scored:
        return None

    best = sorted(scored, key=lambda x: (-x[1], len(x[0])))[0][0]
    
    return best

def load_brands_meta_from_graph():
    with driver.session() as s:
        rows = s.run("""
            MATCH (b:Brand)-[:BELONGS_TO]->(c:Category)
            RETURN b.name AS brand, c.name AS category
        """).data()
    return {r["brand"]: {"category": r["category"]} for r in rows}

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

            found = s.execute_read(find_canonical, brand, series, raw)
            if found:
                df.at[i, col_name] = found
                logger.debug(f"[CANON] → {found}")
            else:
                logger.debug(f"[CANON] no match for {raw}")

    return df