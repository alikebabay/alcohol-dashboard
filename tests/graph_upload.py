import json
from neo4j import GraphDatabase

URI  = "bolt://localhost:7687"
USER = "neo4j"
PASS = "testing123"

driver = GraphDatabase.driver(URI, auth=(USER, PASS))


def upload_json_to_graph(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("❌ JSON должен быть списком объектов.")

    with driver.session(database="neo4j") as session:
        # 1️⃣ Полная очистка графа
        print("🧹 Clearing old nodes...")
        session.run("MATCH (n) DETACH DELETE n")
        print("✅ Database cleared.")

    with driver.session(database="neo4j") as session:
        res = session.run("RETURN 1 AS ok").single()
        print("✅ Connected to Neo4j:", res["ok"])

        for entry in data:
            canonical = entry.get("canonical_name")
            variants = entry.get("raw_examples", [])
            if not canonical:
                continue

            # ❗ сохраняем canonical в оригинальном регистре
            canonical_clean = canonical.strip()

            # создаём canonical node (оригинальный регистр)
            session.run("MERGE (c:Canonical {name:$canonical})", canonical=canonical_clean)

            # привязываем все варианты
            for v in variants:
                variant_clean = v.strip()
                print(f"→ Linking '{variant_clean}' → '{canonical_clean}'")
                session.run("""
                    MERGE (v:Variant {name:$variant})
                    MERGE (c:Canonical {name:$canonical})
                    MERGE (v)-[:SAME_AS]->(c)
                """, variant=variant_clean, canonical=canonical_clean)

    print(f"✅ Uploaded {len(data)} canonical alcohol groups into Neo4j")


if __name__ == "__main__":
    upload_json_to_graph(r"tests\\canonical_mapping_master.json")
