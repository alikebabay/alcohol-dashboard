# worker_dfout.py
import asyncio
import logging
from neo4j import AsyncGraphDatabase

from workers.event_bus import subscribe
from config import MODE, USER, PASS, URI

logger = logging.getLogger(__name__)

async_driver = AsyncGraphDatabase.driver(URI, auth=(USER, PASS))

async def handle_df_out(payload):
    supplier = payload["supplier"]
    df_id = payload["df_id"]
    logger.info(f"[WORKER_DF] получил DfOut: supplier={supplier}, df_id={df_id}")
            
    # проверяем, что DfOut связан с поставщиком и RawBlob
    check_link = """
    MATCH (s:Supplier {name: $supplier})-[:HAS_BLOB]->(r:RawBlob)-[:HAS_DFOUT]->(d:DfOut {id: $df_id})
    RETURN count(d) AS rel_exists
    """
    create_link = """
    MATCH (s:Supplier {name: $supplier})-[:HAS_BLOB]->(r:RawBlob)
    MATCH (d:DfOut {id: $df_id})
    MERGE (r)-[:HAS_DFOUT]->(d)
    RETURN s.name AS supplier, r.id AS raw_id, d.id AS df_id
    """

    try:
        async with async_driver.session() as session:
            result = await session.run(check_link, supplier=supplier, df_id=df_id)
            record = await result.single()
            rel_exists = record["rel_exists"] if record else 0

            if rel_exists and rel_exists > 0:
                logger.info(f"[WORKER_DF] связь с DfOut уже существует для {supplier}")
            else:
                result2 = await session.run(create_link, supplier=supplier, df_id=df_id)
                rec2 = await result2.single()
                logger.info(
                    f"[WORKER_DF] создана связь Supplier → RawBlob → DfOut: "
                    f"{rec2['supplier']} → {rec2['raw_id']} → {rec2['df_id']}"
                )

    except Exception as e:
        logger.error(f"[WORKER_DF] ошибка при создании связи: {e}")

    logger.info(f"[WORKER_DF] обработка DfOut {df_id} завершена.")

def init_worker():
    subscribe("df_out_ready", handle_df_out)
