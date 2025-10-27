# integrations/reference_to_graph.py
from datetime import datetime
from pathlib import Path
import logging
from io import BytesIO
import pandas as pd
import hashlib

from config import driver, MODE
from utils.logger import setup_logging
from state_machine import AlcoholStateMachine

setup_logging()
logger = logging.getLogger(__name__)

logger.debug(f"[Neo4j] driver object type: {type(driver)}")
logger.info(f"[Neo4j] Using shared driver (mode={MODE})")


def reference_to_graph(df: pd.DataFrame, supplier_name: str = None):
    """
    Создаёт ноду (:DfOut) и сохраняет бинарь Excel-файла в граф.
    Связывание с RawBlob выполняет воркер.
    """

    fsm = AlcoholStateMachine.get_active()
    if not fsm or not getattr(fsm, "name", None):
        raise RuntimeError("Нет активного AlcoholStateMachine — невозможно определить поставщика.")
    supplier = fsm.name

    # 🧮 Детерминированный хэш по содержимому DataFrame
    df_serialized = df.to_json(orient="split", date_format="iso", default_handler=str)
    digest = hashlib.sha256(df_serialized.encode("utf-8")).hexdigest()

    # Конвертируем DataFrame в Excel (в памяти)
    bio_out = BytesIO()
    df.to_excel(bio_out, index=False)
    bio_out.seek(0)
    raw_bytes = bio_out.getvalue()
    bio_out.close()

    # Метаданные
    size = len(raw_bytes)
    created = datetime.utcnow().isoformat()
    file_name = f"{supplier}.xlsx"
    ext = Path(file_name).suffix

    # Проверяем дубликат по хэшу датафрейма
    check = """
    MATCH (d:DfOut)
    WHERE d.supplier = $supplier AND d.hash = $hash
    RETURN d.id AS id, d.createdAt AS createdAt
    ORDER BY d.createdAt DESC LIMIT 1
    """
    with driver.session() as session:
        rec = session.run(check, supplier=supplier, hash=digest).single()
        if rec:
            logger.info(f"[DF_OUT] duplicate detected: supplier={supplier} hash={digest[:8]} file={file_name}")
            return rec["id"]

    # Создаём ноду
    cypher = """
    CREATE (d:DfOut {
        id: randomUUID(),
        supplier: $supplier,
        fileName: $file_name,
        ext: $ext,
        size: $size,
        hash: $hash,
        format: 'excel',
        createdAt: $created,
        blob: $blob
    })
    RETURN d.id AS id
    """
    with driver.session() as session:
        rec = session.run(
            cypher,
            supplier=supplier,
            file_name=file_name,
            ext=ext,
            size=size,
            hash=digest,
            created=created,
            blob=raw_bytes,
        ).single()

    did = rec["id"]
    logger.info(
        f"[DF_OUT] stored DfOut id={did} supplier={supplier} rows={len(df)} cols={len(df.columns)} size={size} file={file_name} (mode={MODE})"
    )
    return did

