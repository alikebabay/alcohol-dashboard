# workers/excel_worker.py - connects df_raw to supplier
import logging
from workers.event_bus import subscribe
from config import driver

logger = logging.getLogger(__name__)


async def handle_df_raw_ready(payload):
    """
    payload:
      {
        "supplier": <supplier_name>,
        "raw_id": <RawBlob.id>,
        "df_raw_id": <DfRaw.id>
      }
    """
    supplier = payload["supplier"]
    raw_id   = payload["raw_id"]
    df_raw_id = payload["df_raw_id"]

    logger.info(f"[EXCEL_WORKER] Received df_raw_ready: "
                f"supplier={supplier}, raw={raw_id}, df_raw={df_raw_id}")

    cypher = """
    MATCH (s:Supplier {name:$supplier})
    MATCH (r:RawBlob {id:$raw_id})
    MATCH (d:DfRaw {id:$df_raw_id})

    MERGE (s)-[:HAS_BLOB]->(r)
    MERGE (r)-[:HAS_DFRAW]->(d)

    RETURN s.name AS supplier, r.id AS raw, d.id AS df_raw
    """

    try:
        with driver.session() as sess:
            rec = sess.run(
                cypher,
                supplier=supplier,
                raw_id=raw_id,
                df_raw_id=df_raw_id,
            ).single()

        if rec:
            logger.info(f"[EXCEL_WORKER] Linked Supplier → RawBlob → DfRaw: "
                        f"{rec['supplier']} → {rec['raw']} → {rec['df_raw']}")
        else:
            logger.warning("[EXCEL_WORKER] No records returned from merge")

    except Exception as e:
        logger.error(f"[EXCEL_WORKER] Error while linking df_raw: {e}")


def init_worker():
    subscribe("df_raw_ready", handle_df_raw_ready)
