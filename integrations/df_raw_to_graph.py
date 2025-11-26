import hashlib
import logging
from datetime import datetime
import pandas as pd

from config import driver as GLOBAL_DRIVER, MODE
from utils.logger import setup_logging
from state_machine import AlcoholStateMachine

setup_logging()
logger = logging.getLogger(__name__)

logger.debug(f"[Neo4j] driver object type: {type(GLOBAL_DRIVER)}")
logger.info(f"[Neo4j] Using shared driver (mode={MODE})")


def df_raw_to_graph(driver, df_raw: pd.DataFrame):
    """
    Создаёт ноду (:DfRaw) — исходная таблица после парсера Excel (до нормализации).
    Хранит JSON-структуру DataFrame и метаданные.

    Возвращает id созданного или найденного узла.
    """

    # Получаем активного поставщика
    fsm = AlcoholStateMachine.get_active()
    if not fsm or not getattr(fsm, "name", None):
        raise RuntimeError("Нет активного AlcoholStateMachine — невозможно определить поставщика.")
    supplier = fsm.name
    logger.debug(f"[DF_RAW] Using supplier={supplier!r}")

    # 1) сериализация таблицы
    df_json = df_raw.to_json(orient="split", default_handler=str)

    # 2) хеширование для дедупликации
    digest = hashlib.sha256(df_json.encode("utf-8")).hexdigest()

    # 3) проверка на дубликат
    check = """
    MATCH (d:DfRaw)
    WHERE d.supplier = $supplier AND d.hash = $hash
    RETURN d.id AS id
    ORDER BY d.createdAt DESC LIMIT 1
    """

    with driver.session() as session:
        rec = session.run(check, supplier=supplier, hash=digest).single()
        if rec:
            logger.info(f"[DF_RAW] duplicate detected: supplier={supplier} hash={digest[:8]}")
            return rec["id"]

    # 4) создаём новую ноду (:DfRaw)
    create = """
    CREATE (d:DfRaw {
        id: randomUUID(),
        supplier: $supplier,
        createdAt: $created,
        rows: $rows,
        cols: $cols,
        hash: $hash,
        json: $json
    })
    RETURN d.id AS id
    """

    created = datetime.utcnow().isoformat()

    with driver.session() as session:
        rec = session.run(
            create,
            supplier=supplier,
            created=created,
            rows=len(df_raw),
            cols=len(df_raw.columns),
            hash=digest,
            json=df_json,
        ).single()

    did = rec["id"]

    logger.info(
        f"[DF_RAW] stored DfRaw id={did} supplier={supplier} "
        f"rows={len(df_raw)} cols={len(df_raw.columns)} (mode={MODE})"
    )

    return did