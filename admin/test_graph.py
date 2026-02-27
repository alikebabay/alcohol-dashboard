import difflib
import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel
from pathlib import Path


from core.graph_normalizer import normalize_dataframe
from utils.abbreviations_helper import convert_abbreviation

router = APIRouter()

LOG_FILES = [
    "graph_normalizer_debug.txt",
    "canonical_debug.txt",
    "brand_debug.txt",
]


def read_logs():
    logs_dir = Path("logs")
    collected = []

    for fname in LOG_FILES:
        path = logs_dir / fname
        if path.exists():
            collected.append(f"\n===== {fname} =====\n")
            collected.append(path.read_text(encoding="utf-8"))

    return "\n".join(collected)

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
    logs_text = read_logs()

    return {
        "ok": True,
        "rows": len(out),
        "data": out,
        "logs": logs_text
    }
