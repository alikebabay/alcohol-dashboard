import difflib
import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel
from pathlib import Path
import logging
import io

from core.graph_normalizer import normalize_dataframe
from utils.abbreviations_helper import convert_abbreviation

router = APIRouter()


class TestRequest(BaseModel):
    text: str


@router.post("/test/graph")
async def test_graph(req: TestRequest):
    """
    Test graph_normalizer on pasted text.
    Returns line-by-line diff.
    """
    text = req.text or ""
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    if not lines:
        return {"ok": False, "error": "No input lines"}

    df = pd.DataFrame({"Наименование": lines})

    # copy stages
    df_raw = df.copy()
    df_abbr = df.copy()
    df_abbr["Наименование"] = df_abbr["Наименование"].apply(convert_abbreviation)

    # --- BEGIN LOG CAPTURE ---
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)

    canonical_logger = logging.getLogger("core.graph_normalizer.canonical")
    canonical_logger.addHandler(handler)
    normalize_dataframe_logger = logging.getLogger("core.graph_normalizer")
    normalize_dataframe_logger.addHandler(handler)

    try:
        df_norm = normalize_dataframe(df_abbr, col_name="Наименование")
        logs_text = log_stream.getvalue()
    finally:
        canonical_logger.removeHandler(handler)
        normalize_dataframe_logger.removeHandler(handler)
    # --- END LOG CAPTURE ---

    out = []

    for raw, norm in zip(df_raw["Наименование"], df_norm["Наименование"]):
        if raw != norm:
            out.append({
                "raw": raw,
                "norm": norm,
                "changed": True
            })
        else:
            out.append({
                "raw": raw,
                "norm": norm,
                "changed": False
            })
    
    return {
        "ok": True,
        "rows": len(out),
        "data": out,
        "logs": logs_text
    }
