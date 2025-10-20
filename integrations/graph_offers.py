# integrations/graph_offers.py
import logging
import pandas as pd
from state_machine import AlcoholStateMachine
from utils.logger import setup_logging

from config import driver, MODE

# активируем общий логгер (matrix_debug.txt)
setup_logging()
logger = logging.getLogger(__name__)

# ==========================================================
# 🕸 Neo4j driver (из config)
# ==========================================================
logger.info(f"[Neo4j] Using shared driver (mode={MODE})")

# ───────────────────────────────────────────────
# 1️⃣ Загрузка офферов в граф
# ───────────────────────────────────────────────
def push_offers_to_graph(df: pd.DataFrame, supplier_name: str = None):
    """
    Сохраняет df_out в Neo4j:
      (Supplier)-[:HAS_OFFER]->(Offer)
    Если supplier_name не передан — берёт активный из FSM.
    """
    if df is None or df.empty:
        logger.warning("[GRAPH] push_offers_to_graph получил пустой DataFrame")
        return

    # 🧩 Получаем активного supplier из FSM (если не передан явно)
    if not supplier_name:
        fsm = AlcoholStateMachine.get_active()
        if not fsm or not getattr(fsm, "name", None):
            raise RuntimeError("Нет активного AlcoholStateMachine — невозможно определить supplier.")
        supplier_name = fsm.name.strip()
    logger.info(f"[GRAPH] Active supplier: {supplier_name!r}")

    with driver.session() as session:
        # создаём/находим поставщика
        session.run(
            "MERGE (s:Supplier {name:$name}) RETURN s",
            name=supplier_name
        )
        inserted, skipped = 0, 0
        for _, row in df.iterrows():
            offer_name = str(row.get("Наименование", "")).strip()
            if not offer_name:
                continue

            props = {
                "supplier": supplier_name,
                "Тип": row.get("Тип", ""),
                "Наименование": offer_name,
                "cl": row.get("cl", ""),
                "шт_кор": row.get("шт / кор", ""),
                "crc32_hash": str(row.get("crc32_hash", "")),
                "b64": str(row.get("b64", "")),
                "date_int": int(row.get("date_int", 0)) if str(row.get("date_int", "")).isdigit() else 0,
            }

            # добавляем динамические колонки (все supplier-специфичные поля)
            supplier_prefixes = [
                f"цена за бутылку",
                f"цена за кейс",
                f"Доступ",
                f"Место загрузки",
                f"currency",
            ]

            for col in df.columns:
                val = str(row.get(col, "")).strip()
                if not val:
                    continue

                # 💡 включаем все supplier-специфичные колонки (например, "Доступ we offer")
                if any(prefix in col for prefix in supplier_prefixes):
                    props[col] = val
                # остальное — только если это не базовые поля
                elif col not in ["Тип", "Наименование", "cl", "шт / кор", "crc32_hash", "b64", "date_int"]:
                    props[col] = val

            # 🧠 двухуровневая проверка дубликатов как в MatrixMerger: crc32 → b64
            existing = session.run("""
                MATCH (s:Supplier {name:$supplier})-[:HAS_OFFER]->(o:Offer)
                WHERE o.crc32_hash = $crc32
                RETURN o.b64 AS b64
            """, supplier=supplier_name, crc32=props["crc32_hash"]).value()

            if existing:
                # crc32 совпал → сверяем b64
                if any(x == props["b64"] for x in existing):
                    skipped += 1
                    logger.debug(f"[GRAPH] duplicate skipped: {props['crc32_hash']} / {props['b64']}")
                    continue

            # 🆕 если дубликата нет — вставляем
            session.run("""
                MERGE (o:Offer {crc32_hash:$crc32, supplier:$supplier, b64:$b64})
                SET o += $props
                WITH o
                MERGE (s:Supplier {name:$supplier})
                MERGE (s)-[:HAS_OFFER]->(o)
            """,
            supplier=supplier_name,
            crc32=props["crc32_hash"],
            b64=props["b64"],
            props=props)

            inserted += 1

        logger.info(f"[GRAPH] добавлены={inserted}, пропущены={skipped}, всего={inserted+skipped}")

# ───────────────────────────────────────────────
# 2️⃣ Формирование финального df
# ───────────────────────────────────────────────
def get_final_dataframe(limit_suppliers: int = 10) -> pd.DataFrame:
    """
    Собирает все офферы из графа и возвращает объединённый DataFrame.
    limit_suppliers — ограничение по количеству поставщиков.
    """
    query = f"""
    MATCH (s:Supplier)-[:HAS_OFFER]->(o:Offer)
    RETURN s.name AS supplier,
           o.Тип AS type,
           o.Наименование AS name,
           o.cl AS cl,
           o.шт_кор AS bottles_per_case,
           o.crc32_hash AS crc32_hash,
           o.b64 AS b64,
           o.date_int AS date_int,
           o.`цена за бутылку {s.name}` AS price_bottle,
           o.`цена за кейс {s.name}` AS price_case,
           o.`Место загрузки {s.name}` AS location,
           o.`Доступ {s.name}` AS access
    ORDER BY s.name, o.Наименование
    LIMIT {limit_suppliers * 200}
    """

    with driver.session() as session:
        records = session.run(query).data()

    if not records:
        logger.warning("[GRAPH] нет данных для финального df")
        return pd.DataFrame()

    df = pd.DataFrame(records)
    logger.info(f"[GRAPH] собран df_final: {df.shape[0]} строк, {df.shape[1]} колонок")
    return df
