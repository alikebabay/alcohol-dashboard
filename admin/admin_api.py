#admin_api.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from neo4j import AsyncGraphDatabase
import logging
from utils.logger import setup_logging
import os

from pydantic import BaseModel

from config import async_driver as GLOBAL_DRIVER, MODE, ADMIN_API_BASE


#requests for user input
class SupplierName(BaseModel):
    name: str

class SupplierRequest(BaseModel):
    supplier: str

class CanonicalRequest(BaseModel):
    id: str


setup_logging()
logger = logging.getLogger(__name__)


logger.debug(f"[Neo4j] driver object type: {type(GLOBAL_DRIVER)}")
logger.info(f"[Neo4j] Using shared driver (mode={MODE})")

app = FastAPI()

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

#communication with graph returns dict
async def run_query(query: str, params: dict):
    async with GLOBAL_DRIVER.session() as session:
        result = await session.run(query, params)
        out = []
        async for record in result:
           out.append(record.data())   # ← convert to dict
        return out

#mounting styles for admin
app.mount("/static", StaticFiles(directory="frontend-miniapp/static"), name="static")

#admin endpoint for url
@app.get("/admin/config")
async def admin_config():    
    return {"mode": MODE, "api_base": ADMIN_API_BASE}


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
    }



# ============================================================
# Admin Endpoints (for your buttons)
# ============================================================
# ============================================================
# 🔍 BUTTON: List all suppliers
# ============================================================
@app.get("/admin/list_suppliers")
async def list_suppliers():
    query = """
    MATCH (s:Supplier)
    RETURN s.name AS name
    ORDER BY name
    """
    return await run_query(query, {})


# ❌ Remove Supplier + all its offers
@app.post("/admin/remove_supplier")
async def remove_supplier(req: SupplierName):
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
    RETURN c, labels(c) AS labels
    LIMIT 200
    """
    raw = await run_query(query, {"supplier": supplier})

    result = []
    for row in raw:
        node_props = row.get("c")
        labels = row.get("labels") or []
        if node_props:
            result.append(normalize_node(node_props, labels))

    return result


# 🗑 Delete all DfOut for supplier
@app.post("/admin/delete_dfout")
async def delete_dfout(req: SupplierRequest):
    query = """
    MATCH (d:DfOut)
    WHERE d.supplier = $supplier
    DETACH DELETE d
    RETURN count(d) AS deleted
    """
    return await run_query(query, {"supplier": req.supplier})


# ⭐ Mark DfOut as canonical
@app.post("/admin/mark_canonical")
async def mark_canonical(req: CanonicalRequest):
    query = """
    MATCH (d:DfOut {id: $id})
    SET d.canonical = true
    RETURN true AS ok
    """
    return await run_query(query, {"id": req.id})

# 🔍 Find Brand by name
@app.get("/admin/find_brand")
async def find_brand(name: str):
    query = """
    MATCH (b:Brand {name: $name})
    RETURN b
    """
    return await run_query(query, {"name": name})