import json
from neo4j import GraphDatabase



# 🔹 Локальное подключение (отдельно от онлайн)
LOCAL_URI = "bolt://localhost:7687"
LOCAL_USER = "neo4j"
LOCAL_PASS = "testing123"

local_driver = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASS))


def upload_json_to_graph_local(path):
    """Загрузка JSON в локальную Neo4j базу (копия онлайн-логики)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("❌ JSON должен быть списком объектов.")

    with local_driver.session(database="neo4j") as session:
        res = session.run("RETURN 1 AS ok").single()
        print("✅ Connected to LOCAL Neo4j:", res["ok"])

        print("🧩 Ensuring relationship types exist...")
        for rel in ["HAS_SERIES", "HAS_VARIANT", "HAS_CANONICAL", "SAME_AS", "BELONGS_TO"]:
            session.run(f"CALL db.createRelationshipType('{rel}')")

        for entry in data:
            canonical = entry.get("canonical_name")
            variants = entry.get("raw_examples", [])
            brand = entry.get("brand")
            series = entry.get("series")
            category = entry.get("category") or "Без категории"

            if not canonical:
                continue

            canonical_clean = canonical.strip()

            session.run("MERGE (c:Canonical {name:$canonical})", canonical=canonical_clean)

            for v in variants:
                variant_clean = v.strip()
                session.run("""
                    MERGE (v:Variant {name:$variant})
                    MERGE (v)-[:SAME_AS]->(c:Canonical {name:$canonical})
                """, variant=variant_clean, canonical=canonical_clean)

            if brand:
                session.run("""
                    MERGE (b:Brand {name:$brand})
                    MERGE (cat:Category {name:$category})
                    MERGE (b)-[:BELONGS_TO]->(cat)
                    SET b.category = $category
                """, brand=brand, category=category)

            if series:
                session.run("""
                    MERGE (s:Series {name:$series})
                    MERGE (b:Brand {name:$brand})
                    MERGE (b)-[:HAS_SERIES]->(s)
                    MERGE (s)-[:HAS_CANONICAL]->(c:Canonical {name:$canonical})
                """, brand=brand, series=series, canonical=canonical_clean)
            elif brand:
                session.run("""
                    MERGE (b:Brand {name:$brand})
                    MERGE (b)-[:HAS_CANONICAL]->(c:Canonical {name:$canonical})
                """, brand=brand, canonical=canonical_clean)

        print(f"✅ Upserted {len(data)} canonical groups into LOCAL Neo4j")


if __name__ == "__main__":
    upload_json_to_graph_local(r"tests\\canonical_mapping_master.json")
