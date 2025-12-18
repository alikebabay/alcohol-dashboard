import difflib
import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel

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

    df_norm = normalize_dataframe(df_abbr, col_name="Наименование")

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
        "data": out
    }
