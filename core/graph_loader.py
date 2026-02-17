

import logging
import time

from config import driver, MODE
from utils.normalize import normalize as _normalize

logger = logging.getLogger(__name__)
loader_logger = logging.getLogger("core.graph_loader")
logger.info(f"[Neo4j] Using shared driver (mode={MODE})")

CACHE_LOADED_AT = None


# ==========================================================
# LOAD DATA FROM GRAPH
# ==========================================================
def load_graph_data(driver):
    with driver.session() as s:
        loader_logger.debug (f"starting load")
        # 1) brands
        brands_rows = s.run("""
            MATCH (b:Brand)
            RETURN b.name AS name
        """).values()
        brands = [r[0] for r in brands_rows if r and r[0]]
        # 🔥 create unified BRAND_KEYMAP: normalized → original
        brand_keymap = {}
        for b in brands:
            bn = _normalize(b)
            brand_keymap[bn] = b

        # 2) series + default_series + aliases
        series_rows = s.run("""
            MATCH (b:Brand)
            OPTIONAL MATCH (b)-[:HAS_SERIES|HAS_VARIANT]->(s:Series)
            RETURN b.name AS brand, 
                   s.name AS series,
                   s.alias AS alias,
                   b.default_series AS default
        """).values()
        all_series = set()
        default_series = {}
        brand_series = {}
        brand_series_full = {}

        for brand, series, alias, default in series_rows:
            if not brand:
                continue
            # 🔥 use normalized key everywhere
            bnorm = _normalize(brand)
            if series:
                s_norm = _normalize(series)
                all_series.add(s_norm)
                # store original series under normalized brand key
                brand_series.setdefault(bnorm, []).append(series)
                # формируем ключи для матчинга серии (сама серия + alias)
                alias_keys = {s_norm}
                if alias:
                    if isinstance(alias, dict):
                        alias_iter = alias.keys()  # or .values()
                    elif isinstance(alias, (list, tuple)):
                        alias_iter = alias
                    else:
                        alias_iter = [alias]

                    for a in alias_iter:
                        if a:
                            alias_keys.add(_normalize(a))


                brand_series_full.setdefault(bnorm, []).append({
                    "series": series,
                    "series_norm": s_norm,
                    "alias": list(alias_keys),
                })
            if default:
                dnorm = _normalize(default)
                default_series[bnorm] = dnorm
                all_series.add(dnorm)

        
        # 3) brand metadata
        meta_rows = s.run("""
            MATCH (b:Brand)-[:BELONGS_TO]->(c:Category)
            RETURN b.name AS brand,
                   c.name AS category,
                   b.default_series AS default_series,
                   b.brand_alias AS brand_alias
        """).data()
        brands_meta = {}
        for r in meta_rows:
             b = r["brand"]
             brands_meta[b] = {
                 "category": r["category"],
                 "default_series": r.get("default_series"),
                 "brand_alias": r.get("brand_alias") or []
             }

        # =======================================================
        # 3a) Add BRAND ALIASES → map alias_norm → brand_name
        # =======================================================
        for brand, meta in brands_meta.items():
            aliases = meta.get("brand_alias") or []
            for alias in aliases:
                alias_norm = _normalize(alias)
                if alias_norm not in brand_keymap:
                    loader_logger.debug(
                        f"[ALIAS→KEYMAP] inserting alias_norm='{alias_norm}' → brand='{brand}'"
                    )
                    brand_keymap[alias_norm] = brand
                else:
                    loader_logger.debug(
                        f"[ALIAS→KEYMAP] alias_norm='{alias_norm}' already exists"
                    )
                    
        # 4) canonical names
        canon_rows = s.run("""
            MATCH (c:Canonical)
            RETURN DISTINCT c.name AS name
        """).values()
        canonical_names = [r[0] for r in canon_rows if r and r[0]]

    return {
        "brands": brand_keymap,   # normalized → original
        "all_series": all_series,
        "default_series": default_series,
        "brand_series": brand_series,
        "brand_series_full": brand_series_full,
        "brands_meta": brands_meta,
        "canonical": canonical_names,
        "brand_keymap": brand_keymap,
    }
GRAPH = load_graph_data(driver)
BRAND_KEYMAP = GRAPH["brand_keymap"]   # normalized → original
BRANDS = BRAND_KEYMAP                  # alias for compatibility
ALL_SERIES_SET = GRAPH["all_series"]
DEFAULT_SERIES_MAP = GRAPH["default_series"]
BRAND_SERIES_MAP = GRAPH["brand_series"]
BRAND_SERIES_FULL = GRAPH["brand_series_full"]
BRANDS_META = GRAPH["brands_meta"]
CANONICAL_NAMES = GRAPH["canonical"]

# =====================================================================
# UNIVERSAL GRAPH DATA DEBUG DUMP – complete coverage of all loaded data
# =====================================================================

def _cp(s):
    """Return unicode code points for every character."""
    return " ".join(hex(ord(ch)) for ch in s)

loader_logger.debug("===== GRAPH DEBUG DUMP: BEGIN =====")

# ---------------------------------------------------------
# BRANDS
# ---------------------------------------------------------
loader_logger.debug(f"→ TOTAL BRANDS: {len(BRANDS)}")

for norm, orig in sorted(BRANDS.items(), key=lambda x: x[0]):
    loader_logger.debug(
        f"[BRAND] norm='{norm}' | orig='{orig}' | codepoints={_cp(orig)}"
    )

# ---------------------------------------------------------
# BRAND META
# ---------------------------------------------------------
loader_logger.debug(f"→ TOTAL BRAND META ENTRIES: {len(BRANDS_META)}")

for brand, meta in sorted(BRANDS_META.items(), key=lambda x: x[0]):
    loader_logger.debug(
        f"[META] brand='{brand}' | category='{meta.get('category')}' | "
        f"default_series='{meta.get('default_series')}' | "
        f"brand_alias={meta.get('brand_alias')}"
    )

# ---------------------------------------------------------
# SERIES
# ---------------------------------------------------------
loader_logger.debug(f"→ TOTAL UNIQUE SERIES: {len(ALL_SERIES_SET)}")

for brand_norm, series_list in sorted(BRAND_SERIES_MAP.items(), key=lambda x: x[0]):
    loader_logger.debug(f"[SERIES] brand_norm='{brand_norm}' → {series_list}")

# ---------------------------------------------------------
# SERIES FULL (with alias)
# ---------------------------------------------------------
loader_logger.debug(f"→ SERIES FULL (with alias): {len(BRAND_SERIES_FULL)} brands")

for bn, entries in sorted(BRAND_SERIES_FULL.items(), key=lambda x: x[0]):
    loader_logger.debug(f"[SERIES FULL] brand_norm='{bn}'")
    for entry in entries:
        loader_logger.debug(
            f"    series='{entry['series']}' "
            f"series_norm='{entry['series_norm']}' "
            f"alias={entry['alias']}"
        )

# ---------------------------------------------------------
# DEFAULT SERIES
# ---------------------------------------------------------
loader_logger.debug(f"→ DEFAULT SERIES MAP size: {len(DEFAULT_SERIES_MAP)}")

for bn, ds in sorted(DEFAULT_SERIES_MAP.items(), key=lambda x: x[0]):
    loader_logger.debug(f"[DEFAULT SERIES] brand_norm='{bn}' → '{ds}'")

# ---------------------------------------------------------
# CANONICAL NAMES
# ---------------------------------------------------------
loader_logger.debug(f"→ TOTAL CANONICAL NAMES: {len(CANONICAL_NAMES)}")

for c in sorted(CANONICAL_NAMES):
    loader_logger.debug(f"[CANONICAL] '{c}' | codepoints={_cp(c)}")

# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------
loader_logger.debug("===== GRAPH DEBUG SUMMARY =====")
loader_logger.debug(f"Brands:           {len(BRANDS)}")
loader_logger.debug(f"Brand meta:       {len(BRANDS_META)}")
loader_logger.debug(f"Series sets:      {len(BRAND_SERIES_MAP)} brands")
loader_logger.debug(f"Series entries:   {sum(len(v) for v in BRAND_SERIES_MAP.values())}")
loader_logger.debug(f"Series full map:  {len(BRAND_SERIES_FULL)} brands")
loader_logger.debug(f"Default series:   {len(DEFAULT_SERIES_MAP)}")
loader_logger.debug(f"All series uniq:  {len(ALL_SERIES_SET)}")
loader_logger.debug(f"Canonical total:  {len(CANONICAL_NAMES)}")

loader_logger.debug("===== GRAPH DEBUG DUMP: END =====")

# ---------------------------------------------------------
# BRAND_KEYMAP DEBUG (normalized_key → original brand)
# ---------------------------------------------------------
loader_logger.debug("===== BRAND_KEYMAP DUMP BEGIN =====")
for norm_key, original in sorted(BRAND_KEYMAP.items(), key=lambda x: x[0]):
    loader_logger.debug(f"[KEYMAP] norm='{norm_key}'  →  brand='{original}'")
loader_logger.debug("===== BRAND_KEYMAP DUMP END =====")

# ---------------------------------------------------------
# BRAND ALIASES CHECK (ensure aliases appear in BRAND_KEYMAP)
# ---------------------------------------------------------
loader_logger.debug("===== BRAND ALIAS → KEYMAP CHECK BEGIN =====")
for brand, meta in sorted(BRANDS_META.items(), key=lambda x: x[0]):
    aliases = meta.get("brand_alias") or []
    for alias in aliases:
        alias_norm = _normalize(alias)
        exists = alias_norm in BRAND_KEYMAP
        loader_logger.debug(
            f"[ALIAS CHECK] brand='{brand}', alias='{alias}', "
            f"alias_norm='{alias_norm}', in_keymap={exists}"
        )
loader_logger.debug("===== BRAND ALIAS → KEYMAP CHECK END =====")

def reload_graph_cache():
    global GRAPH, CACHE_LOADED_AT

    GRAPH = load_graph_data(driver)

    BRAND_KEYMAP.clear()
    BRAND_KEYMAP.update(GRAPH["brand_keymap"])

    BRANDS.clear()
    BRANDS.update(GRAPH["brand_keymap"])

    ALL_SERIES_SET.clear()
    ALL_SERIES_SET.update(GRAPH["all_series"])

    DEFAULT_SERIES_MAP.clear()
    DEFAULT_SERIES_MAP.update(GRAPH["default_series"])

    BRAND_SERIES_MAP.clear()
    BRAND_SERIES_MAP.update(GRAPH["brand_series"])

    BRAND_SERIES_FULL.clear()
    BRAND_SERIES_FULL.update(GRAPH["brand_series_full"])

    BRANDS_META.clear()
    BRANDS_META.update(GRAPH["brands_meta"])

    CANONICAL_NAMES.clear()
    CANONICAL_NAMES.extend(GRAPH["canonical"])
    CACHE_LOADED_AT = time.strftime("%H:%M:%S")
    print(f"[CACHE] reloaded at {CACHE_LOADED_AT}")
