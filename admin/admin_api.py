#admin_api.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse, Response
from fastapi.responses import JSONResponse
from io import BytesIO

from neo4j import AsyncGraphDatabase
import logging
from utils.logger import setup_logging
import os
from pydantic import BaseModel

from config import MODE, USER, PASS, URI
from config import (
    SPREADSHEET_DEV,
    SPREADSHEET_PROD,
)

from admin.sheets_export import rebuild_master_sheet
from admin.supplier_state import (
    list_suppliers as list_suppliers_state,
    set_excluded as set_supplier_excluded,
)
from admin.test_graph import router as test_graph_router
from admin.editor import attach_editor_routes



#requests for user input
class SupplierName(BaseModel):
    name: str

class SupplierRequest(BaseModel):
    supplier: str

class CanonicalRequest(BaseModel):
    id: str


setup_logging()
logger = logging.getLogger(__name__)

logger.info(f"[Neo4j] Using shared driver (mode={MODE})")

app = FastAPI()
app.include_router(test_graph_router, prefix="/admin")

#logging events for admin user
EVENT_LOG = []
MAX_LOG = 200   # keep last 200 events

def log_event(text: str):
    EVENT_LOG.append(text)
    if len(EVENT_LOG) > MAX_LOG:
        EVENT_LOG.pop(0)
    logger.info("[ADMIN EVENT] " + text)



#FastAPI route for admin.html
@app.get("/admin")
async def admin_page():
    return FileResponse(os.path.join("frontend-miniapp", "admin.html"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from config import USER, PASS
# 🟢 NEW: Shared ASYNC driver (used by admin API / FastAPI)

async_driver = AsyncGraphDatabase.driver(URI, auth=(USER, PASS))
logger.debug(f"[Neo4j] driver object type: {type(async_driver)}")

#communication with graph returns dict
async def run_query(query: str, params: dict):
    async with async_driver.session() as session:
        result = await session.run(query, params)
        out = []
        async for record in result:
           out.append(record.data())   # ← convert to dict
        return out



#offer editor
app.include_router(
    attach_editor_routes(run_query),
    prefix="/admin"
)

#function to download blobs
async def load_node_for_download(node_id: str):
    query = """
    MATCH (n)
    WHERE elementId(n) = $id OR n.id = $id
    RETURN labels(n) AS labels,
           n.blob AS blob,
           n.json AS json,
           n.fileName AS fileName,
           n.ext AS ext,
           n.type AS type,
           n.supplier AS supplier
    LIMIT 1
    """
    rows = await run_query(query, {"id": node_id})
    return rows[0] if rows else None


#mounting styles for admin
app.mount("/static", StaticFiles(directory="frontend-miniapp/static"), name="static")

#admin endpoint for url
@app.get("/admin/config")
async def admin_config():    
    return {"mode": MODE, "api_base": "/admin"}


#normalisation of node data
def normalize_node(node_props: dict, labels: list):
    # choose type from labels
    node_type = labels[0] if labels else "Node"

    # actual properties
    props = node_props

    # choose user-friendly name
    name = (
        props.get("Наименование") or
        props.get("name") or
        props.get("fileName") or
        None
    )

    # fallback for DfRaw
    if node_type == "DfRaw" and not name:
        json = props.get("json")
        if isinstance(json, dict):
            rows = len(json.get("data", []))
        else:
            rows = "?"
        name = f"DfRaw ({rows} rows)"

    return {
        "id": props.get("id"),
        "type": node_type,
        "name": name,
        "price_bottle": props.get("price_bottle"),
        "price_case": props.get("price_case"),
        "currency": props.get("currency"),
        "location": props.get("location"),
        "access": props.get("access"),
    }


#helper functions
async def load_canonicals():
    query = """
    MATCH (n)
    WHERE n.canonical = true
    RETURN n.id AS id, n.supplier AS supplier
    """
    rows = await run_query(query, {})
    return {row["id"] for row in rows}


# ============================================================
# Admin Endpoints (for your buttons)
# ============================================================
# ============================================================
# 🔍 BUTTON: List all suppliers
# ============================================================
@app.get("/admin/list_suppliers")
async def list_suppliers():
    return await list_suppliers_state(run_query)

class SupplierExcludeRequest(BaseModel):
    supplier: str
    excluded: bool

@app.post("/admin/set_supplier_excluded")
async def set_supplier_excluded_api(req: SupplierExcludeRequest):
    log_event(
        f"Supplier '{req.supplier}' admin_excluded={req.excluded}"
    )
    return await set_supplier_excluded(
        run_query,
        supplier=req.supplier,
        excluded=req.excluded,
    )

# ❌ Remove Supplier + all its offers
@app.post("/admin/remove_supplier")
async def remove_supplier(req: SupplierName):
    log_event(f"Removed supplier: {req.name}")
    query = """
    MATCH (s:Supplier {name: $name})-[r:HAS_OFFER]-(o)
    DETACH DELETE s, o
    RETURN 'OK' AS status
    """
    return await run_query(query, {"name": req.name})


# 🔍 Find nodes for supplier
@app.get("/admin/find_nodes")
async def find_nodes(supplier: str):
    query = """
    MATCH (c)
    WHERE c.supplier = $supplier
    AND (
        c:DfRaw
        OR c:DfOut
        OR c:RawBlob
    )
    RETURN c, labels(c) AS labels
    LIMIT 200

    """
    raw = await run_query(query, {"supplier": supplier})

    canonical_ids = await load_canonicals()

    result = []
    for row in raw:
        node_props = row.get("c")
        labels = row.get("labels") or []

        if not node_props:
            continue

        node = normalize_node(node_props, labels)

        # ⭐ backend marks canonical
        if node["type"] == "DfOut":
            node["isCanonical"] = node["id"] in canonical_ids

        result.append(node)

    return result

#find offers for supplier
@app.get("/admin/list_offers")
async def list_offers(supplier: str):
    query = """
    MATCH (o:Offer)
    WHERE o.supplier = $supplier
    RETURN
        elementId(o) AS id,
        labels(o) AS labels,
        properties(o) AS props
    LIMIT 200
    """
    rows = await run_query(query, {"supplier": supplier})
    out = []
    for r in rows:
        p = r["props"]
        out.append({
            "id": r["id"],
            "type": r["labels"][0] if r["labels"] else "Offer",
            "name": p.get("Наименование"),
            "cl": p.get("cl"),
            # support BOTH schemas: "шт / кор" and "шт_кор"
            "bottles_per_case": (
                p.get("шт / кор")
                if p.get("шт / кор") not in (None, "")
                else p.get("шт_кор")
            ),
            "price_bottle": p.get(f"цена за бутылку {supplier}"),
            "price_case": p.get(f"цена за кейс {supplier}"),
            "currency": p.get(f"currency {supplier}"),
            "location": p.get(f"Место загрузки {supplier}"),
            "access": p.get(f"Доступ {supplier}"),
            "date_int": p.get("date_int"),
        })

    return out


#find canonical nodes
@app.get("/admin/list_canonicals")
async def list_canonicals():
    query = """
    MATCH (n)
    WHERE n.canonical = true
    RETURN n.id AS id
    """
    rows = await run_query(query, {})
    return [r["id"] for r in rows]


# 🗑 Delete all DfOut for supplier
@app.post("/admin/delete_dfout")
async def delete_dfout(req: SupplierRequest):
    log_event(f"Deleted all DfOut for supplier: {req.supplier}")
    query = """
    MATCH (d:DfOut)
    WHERE d.supplier = $supplier
    DETACH DELETE d
    RETURN count(d) AS deleted
    """
    return await run_query(query, {"supplier": req.supplier})


#delete node by id
class DeleteByIdRequest(BaseModel):
    id: str


@app.post("/admin/delete_node")
async def delete_node(req: DeleteByIdRequest):
    log_event(f"Deleted node: {req.id}")
    query = """
    MATCH (n)
    WHERE elementId(n) = $id OR n.id = $id
    WITH collect(n) AS nodes
    FOREACH (x IN nodes | DETACH DELETE x)
    RETURN size(nodes) AS deleted
    """
    return await run_query(query, {"id": req.id})



# Mark DfOut as canonical
@app.post("/admin/mark_canonical")
async def mark_canonical(req: CanonicalRequest):
    log_event(f"Marked DfOut as canonical: {req.id}")
    query = """
    MATCH (d:DfOut {id: $id})
    SET d.canonical = true
    RETURN true AS ok
    """
    return await run_query(query, {"id": req.id})



#manage pivot table
@app.post("/admin/rebuild_sheets")
async def rebuild_sheets():
    log_event("Rebuilding Google Sheets master...")
    try:
        result = rebuild_master_sheet(max_pairs=12)
        log_event(f"Sheets rebuild OK: {result['rows']} rows")
        return result
    except Exception as e:
        log_event(f"Sheets rebuild FAILED: {repr(e)}")
        raise

#download endpoint
@app.get("/admin/download/{node_id}")
async def download_node(node_id: str):
    node = await load_node_for_download(node_id)
    if not node:
        return Response("Node not found", status_code=404)

    labels = node["labels"]
    file_name = node.get("fileName") or f"node_{node_id}"
    ext = node.get("ext") or ""

    # 🟣 DfOut / RawBlob (binary)
    if node.get("blob") is not None:
        data = node["blob"]
        if ext and not file_name.endswith(ext):
            file_name += ext

        return StreamingResponse(
            BytesIO(data),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{file_name}"'
            }
        )

    # 🟡 DfRaw (JSON stored as text)
    if "DfRaw" in labels and node.get("json"):
        supplier = node.get("supplier") or "dfraw"
        safe_supplier = supplier.replace("/", "_").replace("\\", "_")
        file_name = f"{safe_supplier}.json"

        text = node["json"]
        if isinstance(text, dict):
            import json
            text = json.dumps(text, ensure_ascii=False, indent=2)

        return StreamingResponse(
            BytesIO(text.encode("utf-8")),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{file_name}"'
            }
        )

    return Response("Unsupported node type", status_code=400)


#event log
@app.get("/admin/event_log")
async def event_log():
    return {"events": EVENT_LOG[-50:]}  # latest 50 events

#open pivot
@app.get("/admin/pivot")
async def get_pivot_url():
    """
    Return Google Sheets pivot URL depending on MODE
    """
    if MODE == "prod":
        sheet_id = SPREADSHEET_PROD
    else:
        sheet_id = SPREADSHEET_DEV

    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"

    return {
        "mode": MODE,
        "url": url,
    }