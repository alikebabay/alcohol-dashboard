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
        res = session.run("RETURN 1 AS ok").single()
        print("✅ Connected to Neo4j:", res["ok"])

        # создаём типы связей (на всякий случай)
        print("🧩 Ensuring relationship types exist...")
        for rel in ["HAS_SERIES", "HAS_VARIANT", "HAS_CANONICAL", "SAME_AS", "BELONGS_TO"]:
            session.run(f"CALL db.createRelationshipType('{rel}')")
        print("✅ Relationship types ready.")

        for entry in data:
            canonical = entry.get("canonical_name")
            variants = entry.get("raw_examples", [])
            brand = entry.get("brand")
            series = entry.get("series")
            category = entry.get("category") or "Без категории"

            if not canonical:
                continue

            canonical_clean = canonical.strip()

            # Canonical
            session.run("MERGE (c:Canonical {name:$canonical})",
                        canonical=canonical_clean)

            # Variants
            for v in variants:
                variant_clean = v.strip()
                session.run("""
                    MERGE (v:Variant {name:$variant})
                    MERGE (v)-[:SAME_AS]->(c:Canonical {name:$canonical})
                """, variant=variant_clean, canonical=canonical_clean)

            # Brand
            if brand:
                session.run("""
                    MERGE (b:Brand {name:$brand})
                    MERGE (cat:Category {name:$category})
                    MERGE (b)-[:BELONGS_TO]->(cat)
                    SET b.category = $category
                """, brand=brand, category=category)

            # Series + Canonical
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

        print(f"✅ Upserted {len(data)} canonical alcohol groups into Neo4j")


if __name__ == "__main__":
    upload_json_to_graph(r"tests\\canonical_mapping_master.json")
