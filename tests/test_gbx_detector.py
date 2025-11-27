# tests/test_gbx_detector_from_graph.py
import sys
import os
import pandas as pd
from neo4j import GraphDatabase

# ================= PROJECT ROOT =================
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(ROOT)

# ================= LOGGING ======================
from utils.logger import setup_logging
setup_logging()    # ensures DEBUG from gbx_detector prints

# ================= GBX DETECTOR =================
from core.gbx_detector import detect_gbx


# ================= CONFIG =======================
LOCAL_URI = "bolt://localhost:7687"
LOCAL_USER = "neo4j"
LOCAL_PASS = "testing123"

# ← ← ←  ВСТАВЛЯЕШЬ ОДИН РАЗ
DFRAW_ID = "a7cc23ed-9659-4ef1-aa30-4cecdac84053"
# ================================================


driver = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASS))


def load_dfraw_from_graph(df_raw_id: str) -> pd.DataFrame:
    """Load df_raw JSON from Neo4j (:DfRaw)."""
    with driver.session() as sess:
        rec = sess.run("""
            MATCH (d:DfRaw {id:$id})
            RETURN d.json AS json_text
        """, id=df_raw_id).single()

    if not rec:
        raise RuntimeError(f"[ERROR] DfRaw node {df_raw_id!r} not found")

    json_text = rec["json_text"]
    if not json_text:
        raise RuntimeError(f"[ERROR] DfRaw node {df_raw_id!r} contains empty JSON")

    # parse orient="split"
    df_raw = pd.read_json(json_text, orient="split")
    return df_raw


def main():
    print(f"[TEST] Loading df_raw from graph id={DFRAW_ID}")

    df_raw = load_dfraw_from_graph(DFRAW_ID)
    print(f"[TEST] df_raw loaded: shape={df_raw.shape}")
    print(df_raw.head(10))

    print("\n[TEST] Running detect_gbx(df_raw)...\n")

    gbx = detect_gbx(df_raw)

    print("\n[TEST] GBX DETECTOR RESULT — first rows:")
    print(gbx.head(20))

    print("\n[TEST] Total GBX detected:", int(gbx["gb_flag"].sum()))

    # merge for human debugging
    merged = pd.concat([df_raw, gbx], axis=1)

    print("\n[TEST] MERGED (first 30 rows):")
    print(merged.head(30).to_string())

    # Example: show rows with any GBX detected
    print("\n[TEST] GBX ROWS:")
    print(merged[merged["gb_flag"] == True].to_string())

    print("\n[TEST] DONE")


if __name__ == "__main__":
    main()
