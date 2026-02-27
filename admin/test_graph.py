import difflib
import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from pathlib import Path
import logging
import io

from core.graph_normalizer import normalize_dataframe
from utils.abbreviations_helper import convert_abbreviation
from utils.logger import temporary_debug

router = APIRouter()


class TestRequest(BaseModel):
    text: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "395 cases Courvoisier VSOP + GB 12x70cl at 196 euro\n"
                        "700 cases Courvoisier VSOP + GB 12x75cl at 196 euro\n"
                        "85 cases Courvoisier VSOP + GB 12x1L at 315 euro\n"
                        "230 cases Courvoisier XO + GB 6x70cl at 362 euro\n"
                        "322 cases Macallan 12 y Double Cask + GB 6x70cl at 252 euro\n"
                        "563 cases Moet Rose + GB 6x75cl at 178.20 euro"
            }
        }
    )

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
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    ))

    canonical_logger = logging.getLogger("core.graph_normalizer.canonical")
    graph_logger = logging.getLogger("core.graph_normalizer")

    # Prevent duplicate logs via propagation
    canonical_logger.propagate = False
    graph_logger.propagate = False

    canonical_logger.addHandler(handler)
    graph_logger.addHandler(handler)

    try:
        with temporary_debug([
            "core.graph_normalizer",
            "core.graph_normalizer.canonical",
            "core.graph_normalizer.brand"
        ]):
            df_norm = normalize_dataframe(df_abbr, col_name="Наименование")
        logs_text = log_stream.getvalue()
        logs_lines = logs_text.splitlines()  # easier for frontend rendering
    finally:
        canonical_logger.removeHandler(handler)
        graph_logger.removeHandler(handler)
        canonical_logger.propagate = True
        graph_logger.propagate = True

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
        "logs": logs_text,
        "logs": logs_lines
    }
