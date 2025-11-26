# tests/test_normalizer.py
import sys
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import json
import pandas as pd
from neo4j import GraphDatabase
from utils.logger import setup_logging

# инициализация общего логгера
setup_logging()

# импортируем нормализатор
from core.normalizer import normalize_alcohol_df


# --- Neo4j локальный ---
LOCAL_URI = "bolt://localhost:7687"
LOCAL_USER = "neo4j"
LOCAL_PASS = "testing123"

driver = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASS))


def load_dfraw_from_graph(df_raw_id: str) -> pd.DataFrame:
    """Грузит JSON из узла (:DfRaw) и возвращает DataFrame."""
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

    # JSON в orient="split"
    df = pd.read_json(json_text, orient="split")
    return df


def main(df_raw_id: str):
    df_raw = load_dfraw_from_graph(df_raw_id)
    df_norm, mapping = normalize_alcohol_df(df_raw)
    return df_norm, mapping


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(1)

    df_raw_id = sys.argv[1]
    df_norm, mapping = main(df_raw_id)
