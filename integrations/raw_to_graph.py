from datetime import datetime
from io import BytesIO
import logging
from pathlib import Path

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
    created = datetime.utcnow().isoformat()
    # 🧩 2. Получаем активного поставщика
    fsm = AlcoholStateMachine.get_active()
    if not fsm or not getattr(fsm, "name", None):
        raise RuntimeError("Нет активного AlcoholStateMachine — невозможно определить поставщика.")

    supplier = fsm.name
    logger.debug(f"[RAW] Using supplier={supplier!r}")


    # --- Проверяем дубликат ---
    check = """
    MATCH (r:RawBlob)
    WHERE r.supplier = $supplier AND r.fileName = $file_name AND r.size = $size
    RETURN r.id AS id, r.receivedAt AS receivedAt
    ORDER BY r.receivedAt DESC LIMIT 1
    """
    with driver.session() as session:
        rec = session.run(check, supplier=fsm.name, file_name=file_name, size=size).single()
        if rec:
            logger.info(f"[RAW] duplicate detected: supplier={fsm.name} size={size} file={file_name}")
            return rec["id"]
    # определяем расширение исходного файла
    ext = Path(file_name).suffix or ""

    # --- Если дубля нет — создаём новую ноду ---
    cypher = """
    CREATE (r:RawBlob {
        id: randomUUID(),
        supplier: $supplier,
        fileName: $supplier_filename,
        size: $size,
        type: $ftype,
        receivedAt: $created,
        blob: $blob
    })
    RETURN r.id AS id
    """
    with driver.session() as session:
        rec = session.run(
            cypher,
            supplier=fsm.name,
            supplier_filename=f"{fsm.name}{ext}",
            size=size,
            ftype=ftype,
            created=created,
            blob=raw_bytes,
        ).single()

    rid = rec["id"]
    logger.info(f"[RAW] stored new RawBlob id={rid} supplier={fsm.name} size={size} file={file_name} (mode={MODE})")
    return rid
