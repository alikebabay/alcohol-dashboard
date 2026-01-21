# admin/editor.py
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
import json

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


class CanonicalCreate(BaseModel):
    brand: str
    series: str | None = None
    category: str | None = None
    canonical_name: str   
    brand_alias: list[str] | None = None
    series_alias: list[str] | None = None



# ============================================================
# Brand helpers
# ============================================================

async def _find_brand(run_query, name: str):
    rows = await run_query(
        """
        MATCH (b:Brand)
        WHERE toLower(b.name) CONTAINS toLower($name)
           OR ANY(a IN coalesce(b.brand_alias, [])
                  WHERE toLower(a) CONTAINS toLower($name))
        RETURN
            b.name        AS name,
            b.brand_alias AS brand_alias
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

    return {
        "found": True,
        "brands": rows
    }




# ============================================================
# Attach routes
# ============================================================

def attach_editor_routes(run_query) -> APIRouter:

    # --------------------------------------------------------
    # FIND BRAND (ADMIN)
    # --------------------------------------------------------
    @router.get("/find_brand")
    async def find_brand(name: str):
        return await _find_brand(run_query, name)


    # --------------------------------------------------------
    # LOAD ORIGINAL ROWS (DfRaw ±3 rows, FUZZY by name)
    # --------------------------------------------------------
    @router.get("/editor/original_rows")
    async def load_original_rows(offer_id: str = Query(...)):

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

    # --------------------------------------------------------
    # UPDATE OFFER PRICE
    # --------------------------------------------------------
    @router.post("/offer")
    async def update_offer(req: OfferEdit):
        query = """
        MATCH (o:Offer)
        WHERE elementId(o) = $id
        WITH o,
            o.supplier AS supplier,
            'цена за бутылку ' + o.supplier AS k_btl,
            'цена за кейс ' + o.supplier   AS k_case,
            'currency ' + o.supplier       AS k_curr,
            'шт_кор ' + o.supplier         AS k_bpc
        SET
            // 🆕 NAME (GLOBAL)
            o.`Наименование` =
                COALESCE($name, o.`Наименование`),

            // 💰 SUPPLIER-SCOPED FIELDS
            o[k_btl]  = COALESCE($price_bottle, o[k_btl]),
            o[k_case] = COALESCE($price_case,   o[k_case]),
            o[k_curr] = COALESCE($currency,     o[k_curr]),
            o[k_bpc]  = COALESCE($bpc,          o[k_bpc])
        RETURN true AS ok


        """
        await run_query(query, req.dict())
        return {"ok": True}
    # --------------------------------------------------------
    # ADD CANONICAL
    # --------------------------------------------------------
    @router.post("/editor/addcanonical")
    async def add_canonical(req: CanonicalCreate):

        query = """
        // ---- CANONICAL ----
        MERGE (c:Canonical {name: $canonical_name})
        SET c.updatedAt = timestamp()
        WITH c

        // ---- BRAND ----
        MERGE (b:Brand {name: $brand})
        SET b.updatedAt = timestamp()

        FOREACH (_ IN CASE WHEN $brand_alias IS NULL THEN [] ELSE [1] END |
            SET b.alias = $brand_alias
        )

        // ---- CATEGORY ----
        FOREACH (_ IN CASE WHEN $category IS NULL THEN [] ELSE [1] END |
            MERGE (cat:Category {name: $category})
            MERGE (b)-[:BELONGS_TO]->(cat)
        )

        MERGE (b)-[:HAS_CANONICAL]->(c)

        // ---- SERIES (OPTIONAL) ----
        FOREACH (s IN CASE WHEN $series IS NULL THEN [] ELSE [$series] END |
            MERGE (ser:Series {name: s})
            SET ser.updatedAt = timestamp()

            FOREACH (_ IN CASE WHEN $series_alias IS NULL THEN [] ELSE [1] END |
                SET ser.alias = $series_alias
            )

            MERGE (b)-[:HAS_SERIES]->(ser)
            MERGE (ser)-[:HAS_CANONICAL]->(c)
        )

        RETURN c.name AS canonical
        """

        await run_query(query, req.dict())
        return {"ok": True}


    return router
