# worker_rawblob.py
import asyncio
import logging

from workers.event_bus import subscribe
from config import driver, MODE


logger = logging.getLogger(__name__)

async def handle_raw_blob(payload):
    supplier = payload["supplier"]
    raw_id = payload["raw_id"]
    logger.info(f"[WORKER] обработка RawBlob: {raw_id} от поставщика {supplier}")   
        
    # проверяем, что RawBlob связан с поставщиком
    check_link = """
    MATCH (s:Supplier {name: $supplier})-[:HAS_BLOB]->(r:RawBlob {id: $raw_id})
    MATCH (RawBlob {id: $raw_id})
    RETURN count(r) AS rel_exists
    """
    create_link = """
    MATCH (s:Supplier {name: $supplier})
    MATCH (r:RawBlob {id: $raw_id})
    MERGE (s)-[:HAS_BLOB]->(r)
    RETURN s.name AS supplier, r.id AS raw_id
    """
    try:
        with driver.session() as session:
            rec = session.run(check_link, supplier=supplier, raw_id=raw_id).single()
            rel_exists = rec["rel_exists"]

            if rel_exists and rel_exists > 0:
                logger.info(f"[WORKER] RawBlob {raw_id} уже связан с поставщиком {supplier}")
            else:
                rec2 = session.run(create_link, supplier=supplier, raw_id=raw_id).single()
                logger.info(f"[WORKER] создана связь RawBlob {raw_id} с поставщиком {supplier}")
    except Exception as e:
        logger.error(f"[WORKER] ошибка при создании RawBlob ноды: {e}")

    logger.info(f"[WORKER] обработка RawBlob {raw_id} завершена.")

def init_worker():
    # при старте приложения регистрируем подписку
    subscribe("raw_blob_ready", handle_raw_blob)
