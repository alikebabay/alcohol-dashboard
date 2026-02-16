# admin/editor.py
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
import json

from core.graph_loader import reload_graph_cache, BRAND_KEYMAP

router = APIRouter()


# ============================================================
# Models
# ============================================================

class OfferEdit(BaseModel):
    id: str
    name: str | None = None 
    price_bottle: float | None = None
    price_case: float | None = None
    currency: str | None = None
    bpc: int | None = None
    cl: str | None = None
    access: str | None = None          # → "Доступ <supplier>"
    location: str | None = None        # → "Место загрузки <supplier>"

class OfferCreate(BaseModel):
    supplier: str          # ← приходит с фронта
    name: str | None = None 
    price_bottle: float | None = None
    price_case: float | None = None
    currency: str | None = None
    bpc: int | None = None
    cl: str | None = None
    access: str | None = None          # → "Доступ <supplier>"
    location: str | None = None        # → "Место загрузки <supplier>"


class CanonicalCreate(BaseModel):
    brand: str
    series: str | None = None
    category: str | None = None
    canonical_name: str   
    brand_alias: list[str] | None = None
    series_alias: list[str] | None = None

class DeleteBrand(BaseModel):
    name: str

class DeleteSeries(BaseModel):
    brand: str
    series: str

class DeleteCanonical(BaseModel):
    name: str


class DefaultSeriesCreate(BaseModel):
    brand: str
    series: str



# ============================================================
# Brand helper
# ============================================================

async def _find_brand(run_query, name: str):    
    rows = await run_query(
        """
        MATCH (b:Brand)
        WHERE toLower(b.name) CONTAINS toLower($name)
           OR ANY(a IN coalesce(b.brand_alias, [])
                  WHERE toLower(a) CONTAINS toLower($name))

        // ---- canonicals
        CALL {
          WITH b
          OPTIONAL MATCH (b)-[:HAS_CANONICAL]->(c:Canonical)
          RETURN collect(DISTINCT c.name) AS canonicals
        }

        // ---- series + alias
        CALL {
          WITH b
          OPTIONAL MATCH (b)-[:HAS_SERIES]->(s:Series)
          RETURN collect(
            DISTINCT {
              name: s.name,
              alias: s.alias
            }
          ) AS series
        }

        RETURN
            b.name        AS name,
            b.brand_alias AS brand_alias,
            canonicals,
            series
        ORDER BY b.name
        LIMIT 20
        """,
        {"name": name}
    )

    if not rows:
        return {
            "found": False,
            "message": "brand not found",
            "brands": []
        }
    reload_graph_cache()
    return {
        "found": True,
        "brands": [
            {
                "name": r["name"],
                "brand_alias": r.get("brand_alias"),
                "series": [
                    {
                        "name": s.get("name"),
                        "alias": s.get("alias")
                    }
                    for s in (r.get("series") or [])
                    if s and s.get("name")
                ],
                "canonicals": [
                    {"name": c}
                    for c in (r.get("canonicals") or [])
                    if c
                ],
            }
            for r in rows
        ],
    }


# ============================================================
# Default series helper
# ============================================================

async def _get_default_series(run_query):
    rows = await run_query(
        """
        MATCH (b:Brand)
        WHERE b.default_series IS NOT NULL
        RETURN b.name AS name, b.default_series AS series
        ORDER BY b.name
        """,
        {}
    )
    reload_graph_cache()
    return {
        "brands": [
            {
                "name": r["name"],
                "series": r["series"] if isinstance(r["series"], list) else [r["series"]]
            }
            for r in rows
        ]
    }

async def _set_default_series(run_query, req: DefaultSeriesCreate):
    
    query = """
        MATCH (b:Brand {name: $brand})
        SET b.default_series = $series
        RETURN b.name AS name, b.default_series AS series
        """
    rows = await run_query(query, req.model_dump())
    reload_graph_cache()
    return {"ok": True, "name": rows[0]["name"], "series": rows[0]["series"]}

async def _remove_default_series(run_query, req: DefaultSeriesCreate):
    
    query = """
    MATCH (b:Brand {name: $brand})
    WITH b, [s IN b.default_series WHERE s <> $series] AS newSeries
    FOREACH (_ IN CASE WHEN size(newSeries) = 0 THEN [1] ELSE [] END |
        REMOVE b.default_series
    )
    FOREACH (_ IN CASE WHEN size(newSeries) > 0 THEN [1] ELSE [] END |
        SET b.default_series = newSeries
    )
    RETURN b.name AS name, coalesce(b.default_series, []) AS series
    """
    rows = await run_query(query, req.model_dump())
    reload_graph_cache()
    return {"ok": True, "name": rows[0]["name"], "series": rows[0]["series"]}

#delete brands, series,canonicals
async def delete_brand_handler(run_query, req: DeleteBrand):
    
    query = """
    MATCH (b:Brand {name:$name})
    WITH b
    LIMIT 1
    DETACH DELETE b
    RETURN count(b) AS deleted;
    """
    rows = await run_query(query, req.model_dump())
    if not rows or rows[0]["deleted"] == 0:
        return {"ok": False, "error": "brand not found"}
    reload_graph_cache()
    print("bells" in BRAND_KEYMAP)
    return {"ok": True}


async def delete_series_handler(run_query, req: DeleteSeries):
    query = """
    MATCH (b:Brand {name:$brand})-[r:HAS_SERIES]->(s:Series {name:$series})
    WITH b, r, s
    LIMIT 1
    DELETE r
    WITH s
    WHERE NOT (s)<-[:HAS_SERIES]-(:Brand)
    DETACH DELETE s
    RETURN 1 AS deleted
    """

    rows = await run_query(query, req.model_dump())

    if not rows:
        return {"ok": False, "error": "series not found"}
    reload_graph_cache()
    return {"ok": True}

async def delete_canonical_handler(run_query, req: DeleteCanonical):
    
    query = """
    MATCH (c:Canonical {name:$name})
    WITH c
    LIMIT 1
    DETACH DELETE c
    RETURN 1 AS deleted
    """

    rows = await run_query(query, req.model_dump())

    if not rows:
        return {"ok": False, "error": "canonical not found"}
    reload_graph_cache()
    return {"ok": True}

#load original rows
async def load_original_rows_handler(run_query, offer_id: str):

        # 1️⃣ Load Offer (only what we need)
        q_offer = """
        MATCH (o:Offer)
        WHERE elementId(o) = $id
        RETURN
            o.supplier AS supplier,
            o.`Наименование` AS name,
            o.date_int AS date_int
        LIMIT 1
        """
        rows = await run_query(q_offer, {"id": offer_id})
        if not rows:
            return {"error": "Offer not found"}

        offer = rows[0]
        offer_name = (offer.get("name") or "").lower().strip()
        if not offer_name:
            return {"error": "Offer has no name"}

        # 2️⃣ Nearest DfRaw by date
        q_dfraw = """
        MATCH (r:DfRaw)
        WHERE r.supplier = $supplier
          AND r.json IS NOT NULL
        RETURN r.json AS json
        ORDER BY abs(r.date_int - $date_int) ASC
        LIMIT 1
        """
        dfraw_rows = await run_query(q_dfraw, offer)
        if not dfraw_rows:
            return {"error": "DfRaw not found"}

        raw_json = dfraw_rows[0]["json"]
        if isinstance(raw_json, str):
            raw_json = json.loads(raw_json)

        # TEXT dfraw → raw only
        if isinstance(raw_json, dict) and raw_json.get("raw"):
            return {"rows": [{"raw": raw_json["raw"]}]}

        # TABLE dfraw
        if not isinstance(raw_json, dict):
            return {"error": "Unsupported DfRaw format"}

        cols = raw_json.get("columns") or []
        rows_raw = raw_json.get("data") or []

        def build_raw(row):
            return " | ".join(
                str(row[i])
                for i in range(min(len(row), len(cols)))
                if row[i] not in (None, "", "nan")
            )

        data = [{"raw": build_raw(r)} for r in rows_raw]
        header = (
            {"raw": " | ".join(str(c) for c in cols if c not in (None, "", "nan"))}
            if cols else None
        )

        # 4️⃣ FUZZY MATCH BY NAME первое точное совпадение
        idx = None
        offer_words = offer_name.split()
        offer_tokens = set(offer_words)
        first_token = offer_words[0] if offer_words else None

        for i, row in enumerate(data):
            text = row["raw"].lower()
            if not text:
                continue

            # 1️⃣ exact first-token match (brand anchor)
            if first_token and text.startswith(first_token):
                idx = i
                break

            # contains OR token overlap
            if offer_name in text:
                idx = i
                break

            tokens = set(text.split())
            if len(tokens & offer_tokens) >= 2:
                idx = i
                break

        # 5️⃣ Slice ±3
        if idx is None:
            # table → return full rows
            rows = data[:6]
            if header:
                rows = rows + [header]
            return {"rows": rows}

        start = max(0, idx - 3)
        end = min(len(data), idx + 4)

        rows = data[start:end]
        if header:
            rows = rows + [header]
        return {"rows": rows}

#update offer
async def update_offer_handler(run_query, req: OfferEdit):
    # --------------------------------------------------
    # build dynamic props (supplier-scoped)
    # --------------------------------------------------
    props = {}

    supplier = None

    # load supplier once (cheap & safe)
    q_supplier = """
    MATCH (o:Offer)
    WHERE elementId(o) = $id
    RETURN o.supplier AS supplier
    LIMIT 1
    """
    rows = await run_query(q_supplier, {"id": req.id})
    if not rows:
        return {"error": "Offer not found"}

    supplier = rows[0]["supplier"]

    removes = []

    if req.price_bottle is not None:
        props[f"цена за бутылку {supplier}"] = req.price_bottle
    elif req.price_bottle is None:
        removes.append(f"o.`цена за бутылку {supplier}`")

    if req.price_case is not None:
        props[f"цена за кейс {supplier}"] = req.price_case
    elif req.price_case is None:
        removes.append(f"o.`цена за кейс {supplier}`")

    if req.currency is not None:
        props[f"currency {supplier}"] = req.currency
    elif req.currency is None:
        removes.append(f"o.`currency {supplier}`")

    if req.access is not None:
        props[f"Доступ {supplier}"] = req.access
    elif req.access is None:
        removes.append(f"o.`Доступ {supplier}`")

    if req.location is not None:
        props[f"Место загрузки {supplier}"] = req.location
    elif req.location is None:
        removes.append(f"o.`Место загрузки {supplier}`")

    if req.bpc is not None:
        props["шт_кор"] = req.bpc
    elif req.bpc is None:
        removes.append("o.`шт_кор`")


    # --------------------------------------------------
    # update offer
    # --------------------------------------------------
    remove_clause = ""
    if removes:
        remove_clause = "REMOVE " + ", ".join(removes)

    query = f"""
    MATCH (o:Offer)
    WHERE elementId(o) = $id
    SET
        o.`Наименование` = COALESCE($name, o.`Наименование`),
        o.`cl`           = COALESCE($cl,   o.`cl`)
    SET o += $props
    {remove_clause}
    RETURN true AS ok
    """

    await run_query(query, {
        "id": req.id,
        "name": req.name,
        "cl": req.cl,
        "props": props,
    })

    return {"ok": True}

async def add_offer_handler(run_query, req: OfferCreate):
    supplier = req.supplier
    props = {
        "supplier": supplier
    }

    if req.name is not None:
        props["Наименование"] = req.name

    if req.cl is not None:
        props["cl"] = req.cl

    if req.bpc is not None:
        props["шт_кор"] = req.bpc

    # supplier-scoped поля
    if req.price_bottle is not None:
        props[f"цена за бутылку {supplier}"] = req.price_bottle

    if req.price_case is not None:
        props[f"цена за кейс {supplier}"] = req.price_case

    if req.currency is not None:
        props[f"currency {supplier}"] = req.currency

    if req.access is not None:
        props[f"Доступ {supplier}"] = req.access

    if req.location is not None:
        props[f"Место загрузки {supplier}"] = req.location

    query = """
    MERGE (s:Supplier {name:$supplier})
    CREATE (o:Offer)
    SET o += $props
    MERGE (s)-[:HAS_OFFER]->(o)
    RETURN elementId(o) AS id
    """

    rows = await run_query(query, {
        "supplier": supplier,
        "props": props
    })

    return {"ok": True}



#add canonical
async def add_canonical_handler(run_query, req: CanonicalCreate):
        
        query = """
        // ---- CANONICAL ----
        MERGE (c:Canonical {name: $canonical_name})
        SET c.updatedAt = timestamp()
        WITH c

        // ---- BRAND ----
        MERGE (b:Brand {name: $brand})
        SET b.updatedAt = timestamp()

        FOREACH (_ IN CASE WHEN $brand_alias IS NULL THEN [] ELSE [1] END |
            SET b.brand_alias =
                CASE
                    WHEN b.brand_alias IS NULL THEN $brand_alias
                    ELSE b.brand_alias + [x IN $brand_alias WHERE NOT x IN b.brand_alias]
                END

        )

        // ---- CATEGORY ----
        FOREACH (_ IN CASE WHEN $category IS NULL THEN [] ELSE [1] END |
            MERGE (cat:Category {name: $category})
            MERGE (b)-[:BELONGS_TO]->(cat)
        )

        MERGE (b)-[:HAS_CANONICAL]->(c)

        // ---- SERIES (OPTIONAL) ----
        FOREACH (s IN CASE WHEN $series IS NULL THEN [] ELSE [$series] END |
            MERGE (b)-[:HAS_SERIES]->(ser:Series {name: s})
            SET ser.updatedAt = timestamp()

            FOREACH (_ IN CASE WHEN $series_alias IS NULL THEN [] ELSE [1] END |
                SET ser.alias =
                    CASE
                        WHEN ser.alias IS NULL THEN $series_alias
                        ELSE ser.alias + [x IN $series_alias WHERE NOT x IN ser.alias]
                    END

            )
            MERGE (ser)-[:HAS_CANONICAL]->(c)
        )

        RETURN c.name AS canonical
        """

        await run_query(query, req.model_dump())
        reload_graph_cache()
        return {"ok": True}

# ============================================================
# Attach routes - maps several admin routes together
# ============================================================

def attach_editor_routes(run_query) -> APIRouter:

    # --------------------------------------------------------
    # FIND BRAND (ADMIN)
    # --------------------------------------------------------
    @router.get("/find_brand")
    async def find_brand(name: str):
        return await _find_brand(run_query, name)
    
    # --------------------------------------------------------
    # FIND DEFAULT SERIES
    # --------------------------------------------------------
    
    @router.get("/default_series")
    async def get_default_series():
        return await _get_default_series(run_query)
    
    # --------------------------------------------------------
    # SET ADN REMOVE DEFAULT SERIES
    # --------------------------------------------------------

    @router.post("/default_series/add")
    async def set_default_series(req: DefaultSeriesCreate):
        return await _set_default_series(run_query, req)
    
    @router.post("/default_series/remove")
    async def remove_default_series(req: DefaultSeriesCreate):
        return await _remove_default_series(run_query, req)

    # --------------------------------------------------------
    # LOAD ORIGINAL ROWS (DfRaw ±3 rows, FUZZY by name)
    # --------------------------------------------------------
    @router.get("/editor/original_rows")
    async def load_original_rows(offer_id: str = Query(...)):
        return await load_original_rows_handler(run_query, offer_id)

    # --------------------------------------------------------
    # ADD AND UPDATE OFFER PRICE
    # --------------------------------------------------------
    @router.post("/offer/update")
    async def update_offer(req: OfferEdit):
        return await update_offer_handler(run_query, req)
    
    @router.post("/offer/add")
    async def add_offer(req: OfferCreate):
        return await add_offer_handler(run_query, req)
    # --------------------------------------------------------
    # ADD CANONICAL
    # --------------------------------------------------------
    @router.post("/editor/addcanonical")
    async def add_canonical(req: CanonicalCreate):
        return await add_canonical_handler (run_query, req)
    
    # --------------------------------------------------------
    # DELETE BRAND,SERIES,CANONICAL
    # --------------------------------------------------------
    
    @router.post("/delete/brand")
    async def delete_brand(req: DeleteBrand):
        return await delete_brand_handler(run_query, req)

    @router.post("/delete/series")
    async def delete_series(req: DeleteSeries):
        return await delete_series_handler(run_query, req)

    @router.post("/delete/canonical")
    async def delete_canonical(req: DeleteCanonical):
        return await delete_canonical_handler(run_query, req)


    return router
