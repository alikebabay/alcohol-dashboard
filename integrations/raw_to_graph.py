from datetime import datetime
from io import BytesIO
import logging
from pathlib import Path
import hashlib

from config import driver, MODE
from utils.logger import setup_logging
from state_machine import AlcoholStateMachine  # 🧩 чтобы тянуть активный supplier

# активируем общий логгер (matrix_debug.txt)
setup_logging()
logger = logging.getLogger(__name__)

# ==========================================================
# 🕸 Neo4j driver (из config)
# ==========================================================
logger.debug(f"[Neo4j] driver object type: {type(driver)}")
logger.info(f"[Neo4j] Using shared driver (mode={MODE})")

def persist_raw_blob(driver, file_src, file_name: str):
    """
    Создаёт ноду (:RawBlob) если нет дубля по (supplier, fileName, size).
    Сравнение по размеру файла/текста.
    """
    

    # --- Получаем байты и тип ---
    if isinstance(file_src, str):
        raw_bytes = file_src.encode("utf-8")
        ftype = "text"
    elif isinstance(file_src, BytesIO):
        raw_bytes = file_src.getvalue()
        ftype = "file"
    else:
        raise TypeError(f"Unsupported file_src type: {type(file_src)}")

    size = len(raw_bytes)
    digest = hashlib.sha256(raw_bytes).hexdigest()
    created = datetime.utcnow().isoformat()
    # 🧩 2. Получаем активного поставщика
    fsm = AlcoholStateMachine.get_active()
    if not fsm or not getattr(fsm, "name", None):
        raise RuntimeError("Нет активного AlcoholStateMachine — невозможно определить поставщика.")

    supplier = fsm.name
    logger.debug(f"[RAW] Using supplier={supplier!r}")
    logger.debug(f"[RAW-DEBUG] supplier=<{supplier}>, file_name=<{file_name}>, size={size}, hash={digest}")


    # --- Проверяем дубликат hash ---
    check = """
    MATCH (r:RawBlob)
    WHERE r.supplier = $supplier AND r.hash = $hash
    RETURN r.id AS id, r.receivedAt AS receivedAt
    ORDER BY r.receivedAt DESC LIMIT 1
    """
    with driver.session() as session:        
        rec = session.run(check, supplier=supplier, hash=digest).single()
        if rec:
            logger.info(f"[RAW] duplicate detected: supplier={supplier} hash={digest[:8]} file={file_name}")
            return rec["id"]
    # определяем расширение исходного файла
    ext = Path(file_name).suffix or ""

    # --- Если дубля нет — создаём новую ноду ---
    cypher = """
    CREATE (r:RawBlob {
        id: randomUUID(),
        supplier: $supplier,
        fileName: $supplier_filename,
        hash: $hash,
        size: toInteger($size),
        type: $ftype,
        receivedAt: $created,
        blob: $blob
    })
    RETURN r.id AS id
    """
    with driver.session() as session:
        logger.debug(f"[RAW-DEBUG] creating new node for {supplier} hash={digest[:8]} file={file_name}")
        rec = session.run(
            cypher,
            supplier=supplier,
            supplier_filename=f"{supplier}{ext}",
            hash=digest,
            size=int(size),
            ftype=ftype,
            created=created,
            blob=raw_bytes,
        ).single()

    rid = rec["id"]
    logger.info(f"[RAW] stored new RawBlob id={rid} supplier={supplier} hash={digest[:8]} size={size} file={file_name} (mode={MODE})")
    return rid
