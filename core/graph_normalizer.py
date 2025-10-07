# core/graph_normalizer.py
import re, json, unicodedata
from pathlib import Path
from neo4j import GraphDatabase
import pandas as pd

# ==========================================================
# NEO4J CONFIG
# ==========================================================
URI  = "bolt://localhost:7687"
USER = "neo4j"
PASS = "testing123"
driver = GraphDatabase.driver(URI, auth=(USER, PASS))

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
    print(f"[INIT] Loaded {len(normalized)} brands")
    return normalized

BRANDS = load_brands()

# ==========================================================
# HELPERS
# ==========================================================
def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower().replace("&", "and")
    # collapse apostrophes (e.g. "grant's" -> "grants")
    s = re.sub(r"(\w)'s\b", r"\1s", s)
    s = re.sub(r"'", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()



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
# BRAND + SERIES DETECTION
# ==========================================================
def extract_brand_series(raw: str):
    tokens = [t for t in re.findall(r"[A-Za-z0-9%+]+", raw)]
    print(f"[TOKENS] {tokens}")

   # score brands
    scores = {}
    for token in tokens[:6]:  # limit to first 6 tokens for sanity
        t_norm = _normalize(token)
        # skip meaningless tokens (short, numeric)
        if len(t_norm) < 3 or t_norm.isdigit():
            continue

        for b_norm, b_orig in BRANDS.items():
            sc = score_brand_series(raw, b_norm)
            if sc > 0:
                scores[b_orig] = sc
            b_tokens = b_norm.split()
            # prefer exact token matches
            if t_norm in b_tokens or t_norm == b_norm:
                scores[b_orig] = scores.get(b_orig, 0) + 1
            # allow weak partial matches (for fuzzy names like glenfiddich / glen)
            elif len(t_norm) >= 4 and t_norm in b_norm:
                scores[b_orig] = scores.get(b_orig, 0) + 0.25

    if not scores:
        print(f"[DETECT] no brand candidates found in: {raw}")
        return None, None

    # pick highest score, tie-breaker by brand length
    brand = sorted(scores.items(), key=lambda x: (-x[1], -len(x[0])))[0][0]

    # extract series
    idx = _normalize(raw).find(_normalize(brand))
    series = None
    if idx != -1:
        after = raw[idx + len(brand):].strip()
        if after:
            # tokenize what follows brand
            after_tokens = re.findall(r"[A-Za-z0-9%+]+", after)
            # keep only plausible series words (exclude pure numbers or very short junk)
            valid = [t for t in after_tokens if not t.isdigit() and len(t) > 2]
            # join top 1–3 tokens max
            if valid:
                series = " ".join(valid[:3])

    print(f"[DETECT] raw={raw!r} → brand={brand!r} (score={scores[brand]}), series={series!r}")
    return brand, series

# ==========================================================
# NEO4J LOOKUPS
# ==========================================================
def find_canonical(tx, brand, series, raw):
    """Finds the best canonical name from Neo4j with penalty for overreach."""
    rows = [r[0] for r in tx.run("MATCH (c:Canonical) RETURN c.name AS name").values()]
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

        return score

    # compute scores for all candidates
    scored = [(c, canonical_score(c)) for c in rows]
    scored = [x for x in scored if x[1] > 0]

    if not scored:
        return None

    best = sorted(scored, key=lambda x: (-x[1], len(x[0])))[0][0]
    print(f"[MATCH] best canonical → {best}")
    return best


# ==========================================================
# MAIN NORMALIZER
# ==========================================================
def normalize_dataframe(df: pd.DataFrame, col_name: str = "Наименование") -> pd.DataFrame:
    col = col_name  # back-compat alias
    if col not in df.columns:
        print(f"[WARN] no '{col}' column")
        return df

    with driver.session() as s:
        for i, raw in enumerate(df[col].fillna("").astype(str)):
            if not raw.strip():
                continue
            print(f"\n[CANON] start: {raw}")
            brand, series = extract_brand_series(raw)
            found = s.execute_read(find_canonical, brand, series, raw)
            if found:
                df.at[i, col] = found
                print(f"[CANON] → {found}")
            else:
                print(f"[CANON] no match for {raw}")
    return df