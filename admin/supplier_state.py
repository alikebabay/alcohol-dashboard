# admin/supplier_state.py
"""
Admin-owned supplier metadata.

IMPORTANT:
- This module does NOT change existing behavior.
- Flags defined here are NOT consumed by exports yet.
- All suppliers continue to be exported as before.

Purpose:
- Provide a place for admin-managed supplier state
- Prepare safe, explicit extension points
"""

from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# default for legacy suppliers
DEFAULT_EXCLUDED = False


Q_LIST_SUPPLIERS = """
MATCH (s:Supplier)-[:HAS_BLOB]->(:RawBlob)-[:HAS_DFOUT]->(d:DfOut)
RETURN
    s.name AS name,
    coalesce(s.admin_excluded, $default) AS admin_excluded,
    max(d.createdAt) AS last_seen
ORDER BY last_seen DESC
"""

Q_SET_EXCLUDED = """
MATCH (s:Supplier {name: $supplier})
SET s.admin_excluded = $excluded
RETURN
    s.name AS name,
    s.admin_excluded AS admin_excluded
"""


async def list_suppliers(run_query) -> List[Dict]:
    """
    List suppliers with admin metadata.
    Does NOT affect exports yet.
    """
    rows = await run_query(Q_LIST_SUPPLIERS, {
        "default": DEFAULT_EXCLUDED
    })
    logger.debug(f"[SupplierState] Loaded {len(rows)} suppliers")
    return rows


async def set_excluded(
    run_query,
    *,
    supplier: str,
    excluded: bool
) -> Dict:
    """
    Admin-only flag. Not used by export yet.
    """
    rows = await run_query(Q_SET_EXCLUDED, {
        "supplier": supplier,
        "excluded": excluded
    })

    if not rows:
        raise ValueError(f"Supplier not found: {supplier}")

    logger.info(
        f"[SupplierState] admin_excluded={excluded} for '{supplier}'"
    )
    return rows[0]
