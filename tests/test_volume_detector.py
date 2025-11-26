# tests/test_normalizer.py

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import json
import pandas as pd
from neo4j import GraphDatabase
from utils.logger import setup_logging

setup_logging()

from core.volume_detector import detect_volume_column, normalize_volume_num_to_cl

# Neo4j локальный
LOCAL_URI = "bolt://localhost:7687"
LOCAL_USER = "neo4j"
LOCAL_PASS = "testing123"

driver = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASS))


def load_dfraw_from_graph(df_raw_id: str) -> pd.DataFrame:
    with driver.session() as sess:
        rec = sess.run("""
            MATCH (d:DfRaw {id:$id})
            RETURN d.json AS json_text
        """, id=df_raw_id).single()

    if not rec:
        raise RuntimeError("DfRaw not found")

    json_text = rec["json_text"]
    if not json_text:
        raise RuntimeError("DfRaw JSON is empty")

    df = pd.read_json(json_text, orient="split")
    return df


def main(df_raw_id: str):
    df_raw = load_dfraw_from_graph(df_raw_id)

    volcol = detect_volume_column(df_raw)

    if volcol is None:
        print("❌ volume column NOT detected")
        return None

    print(f"✅ detected volume column: {volcol}")

    # создаём нормализованную колонку cl
    df_raw["cl"] = df_raw[volcol].map(normalize_volume_num_to_cl)

    print("=== FIRST THREE NORMALIZED VALUES (column: cl) ===")
    print(df_raw["cl"].head(3).to_string())

    return volcol, df_raw["cl"]



if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(1)

    df_raw_id = sys.argv[1]
    main(df_raw_id)
