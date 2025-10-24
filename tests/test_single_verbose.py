# -*- coding: utf-8 -*-
import os, sys, logging, re
from pprint import pprint

# ---- чтобы импортировать core.* при запуске как файл ----
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import driver
from core.graph_normalizer import (
    BrandSeriesExtractor,
    build_series_resolver,
    load_brands,
    load_brands_meta_from_graph,
    _normalize,  # используем те же нормализаторы
)

# ----------------- НАСТРОЙКА ЛОГОВ -----------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("tests.single_verbose")
logging.getLogger("core.graph_normalizer").setLevel(logging.DEBUG)

# ----------------- СЫРЬЕ -----------------
RAW = "Veuve Clicquot Clicquot YL 75cl N.GBX — 6 — $208.75"

# ----------------- ВСПОМОГАТЕЛЬНОЕ: печать токенов после бренда -----------------
def debug_series_after_brand(raw, brand):
    rn = _normalize(raw)
    bn = _normalize(brand)
    idx = rn.find(bn)
    if idx == -1:
        return None
    after_raw = raw[len(raw) - (len(rn) - (idx + len(bn))):]  # аккуратно сдвигаем по оригиналу
    tokens = re.findall(r"[A-Za-z0-9%+]+", after_raw)
    return after_raw, tokens

# ----------------- ВСПОМОГАТЕЛЬНОЕ: вывод кандидатов canonical со скором (как в find_canonical) -----------------
def score_canonicals_verbose(brand, series, raw):
    bnorm = _normalize(brand or "")
    snorm = _normalize(series or "")
    rnorm = _normalize(raw)

    with driver.session() as s:
        # ограничим кандидатов по бренду, чтобы увидеть релевантное
        rows = s.run("""
            MATCH (c:Canonical)
            WHERE toLower(c.name) CONTAINS toLower($brand)
            RETURN c.name AS name
        """, brand=brand).values()
    candidates = [r[0] for r in rows]

    def canonical_score(cname):
        cn_norm = _normalize(cname)
        score = 0.0

        # 1) бренд обязателен
        if bnorm and bnorm in cn_norm:
            score += 1.0
        else:
            return -1.0

        # 2) серия — если есть и встречается и в candidate, и в raw
        if snorm and snorm in cn_norm and snorm in rnorm:
            score += 0.6

        # 3) бонус за пересечение небрандовых токенов
        c_tokens = cn_norm.split()
        b_tokens = set(bnorm.split()) if bnorm else set()
        nb_tokens = [t for t in c_tokens if t not in b_tokens]
        raw_tokens = set(rnorm.split())
        overlap_cnt = sum(1 for t in nb_tokens if t in raw_tokens)
        if overlap_cnt > 0:
            score += 0.25 * overlap_cnt

        # 4) штраф за «лишние» токены (без учёта простого плюрала)
        extra_tokens = [t for t in c_tokens if t not in rnorm.split() and t.rstrip("s") not in rnorm.split()]
        if extra_tokens:
            score -= len(extra_tokens) * 0.15

        # 5) если серии нет, штраф за «слишком длинный» canonical
        if not snorm and len(c_tokens) > len(bnorm.split()):
            score -= 0.5

        # 6) микро-бонус за точное равенство (вряд ли сработает здесь)
        if cn_norm == bnorm or cn_norm == rnorm:
            score += 0.3

        return score

    scored = [(c, canonical_score(c)) for c in candidates]
    scored = [x for x in scored if x[1] > 0]
    scored.sort(key=lambda x: (-x[1], len(x[0])))

    return scored

# ----------------- ОБОРАЧИВАЕМ series_resolver ДЛЯ ЛУЧШЕГО ЛОГА -----------------
def make_debug_resolver(driver):
    base = build_series_resolver(driver)
    def wrapped(brand: str):
        out = base(brand)
        logger.debug(f"[DEBUG RESOLVER] brand='{brand}' -> series_from_graph={out}")
        return out
    return wrapped

# ----------------- ГЛАВНЫЙ ПРОГОН -----------------
def main():
    logger.info("=== SINGLE LINE VERBOSE RUN ===")
    logger.info("RAW: %s", RAW)

    brands = load_brands()
    brands_meta = load_brands_meta_from_graph()
    series_resolver = make_debug_resolver(driver)

    # ВАЖНО: чтобы увидеть «как выбирается бренд», вставим детальный лог внутрь экстрактора.
    # Лёгкий способ — создать наследника и переопределить _extract_brand_series с доп.логом:
    class DebugExtractor(BrandSeriesExtractor):
        def _extract_brand_series(self, raw: str):
            tokens = [t for t in re.findall(r"[A-Za-z0-9%+]+", raw)]
            logging.getLogger("core.graph_normalizer").debug(f"[TOKENS] {tokens}")
            scores = {}
            logging.getLogger("core.graph_normalizer").debug(f"[SCORES INIT] {scores}")

            # Сузим круг брендов для читаемости: показываем только два кандидата, но логику не ломаем
            interesting_prefixes = ("veuve", "ruinart",)

            for token in tokens[:6]:
                t_norm = _normalize(token)
                if len(t_norm) < 3 or t_norm.isdigit():
                    continue
                logging.getLogger("core.graph_normalizer").debug(f"[TOKEN LOOP] token='{token}' norm='{t_norm}'")

                for b_norm, b_orig in self.brands.items():
                    # печатаем только интересные бренды (но очки копим всем)
                    print_this = b_orig.lower().startswith(interesting_prefixes)

                    sc = 0.0
                    # базовая оценка бренда (как в score_brand / score_brand_series с series=None)
                    # подмешаем основную логику score_brand:
                    tokens_norm = _normalize(raw).split()
                    if t_norm == b_norm:
                        sc += 1.0
                    elif t_norm in b_norm and len(t_norm) >= 4:
                        sc += 0.75
                    if b_norm.startswith(t_norm):
                        sc += 0.25
                    if b_norm in " ".join(tokens_norm[:3]):
                        sc += 1.5
                    if _normalize(raw).startswith(b_norm.split()[0]):
                        sc += 0.25

                    # plural-fix
                    for bt in b_norm.split():
                        if t_norm.rstrip("s") == bt or bt.rstrip("s") == t_norm:
                            sc += 0.6
                        elif t_norm.endswith("es") and t_norm[:-2] == bt:
                            sc += 0.5
                        elif t_norm.endswith("ies") and bt.endswith("y") and t_norm[:-3] + "y" == bt:
                            sc += 0.5

                    if sc > 0:
                        prev = scores.get(b_orig, 0.0)
                        scores[b_orig] = prev + sc
                        if print_this:
                            logging.getLogger("core.graph_normalizer").debug(
                                f"    [UPDATE] '{b_orig}' += {sc:.2f} -> {scores[b_orig]:.2f}"
                            )

            if not scores:
                logging.getLogger("core.graph_normalizer").debug(f"[DETECT] no brand candidates found in: {raw}")
                return None, None

            sorted_scores = sorted(scores.items(), key=lambda x: (-x[1], -len(x[0])))
            top = sorted_scores[0]
            logging.getLogger("core.graph_normalizer").debug(f"[DEBUG SCORES] top={top}, all={sorted_scores[:10]}")
            brand = top[0]

            # серия после бренда (как в оригинале) — покажем токены
            idx = _normalize(raw).find(_normalize(brand))
            series = None
            if idx != -1:
                after = raw[idx + len(brand):].strip()
                if after:
                    after_tokens = re.findall(r"[A-Za-z0-9%+]+", after)
                    valid = [t for t in after_tokens if not t.isdigit() and len(t) > 2]
                    if valid:
                        series = " ".join(valid[:3])
                    logging.getLogger("core.graph_normalizer").debug(
                        f"[SERIES DETECT] after='{after}', valid={valid}, series='{series}'"
                    )

            logging.getLogger("core.graph_normalizer").debug(
                f"[RETURN DEBUG] brand='{brand}', series='{series}', raw='{raw}'"
            )
            return brand, series

    extractor = DebugExtractor(brands, series_resolver, brands_meta)

    # Шаг 1. Извлечь бренд/серию (покажет токены, очки и что взялось «после бренда»)
    brand, series = extractor.extract(RAW)
    print("\n====== EXTRACT RESULT ======")
    print("brand :", brand)
    print("series:", series)

    # Показать реальный список серий из графа для детектированного бренда
    print("\n====== SERIES FROM GRAPH FOR DETECTED BRAND ======")
    series_list = series_resolver(brand) if brand else []
    pprint(series_list)

    # Показать, что именно стоит «после бренда» в этой строке (токены)
    print("\n====== TOKENS AFTER BRAND (to see why 'YL' выпал) ======")
    after = debug_series_after_brand(RAW, brand)
    pprint(after)

    # Шаг 2. Посчитать очки для Canonical (как find_canonical, но с выводом всех кандидатов)
    print("\n====== CANONICAL CANDIDATES & SCORES (brand-scoped) ======")
    scored = score_canonicals_verbose(brand, series, RAW)
    for name, sc in scored[:15]:
        print(f"{sc:5.2f}  {name}")

    # Подсказка: если хочется проверить влияние 'YL' -> 'Yellow Label'
    if series and series.lower().startswith("clicquot"):
        print("\n[HINT] series сейчас 'Clicquot ...'. Если подменить series='Yellow Label', пересчет будет такой:")
        rescored = score_canonicals_verbose(brand, "Yellow Label", RAW)
        for name, sc in rescored[:10]:
            print(f"{sc:5.2f}  {name}")

if __name__ == "__main__":
    main()
