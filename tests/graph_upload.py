import json
from neo4j import GraphDatabase

URI = "bolt://46.62.240.187"
USER = "neo4j"
PASS = "testing123"

driver = GraphDatabase.driver(URI, auth=(USER, PASS))


def upload_json_to_graph(path):
    """Загрузка JSON в локальную Neo4j базу (копия онлайн-логики)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("❌ JSON должен быть списком объектов.")

    with driver.session(database="neo4j") as session:
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

            variants_clean = [v.strip() for v in variants if v.strip()]

            session.run("""
                MERGE (c:Canonical {name:$canonical})
                WITH c
                UNWIND $variants AS vname
                    MERGE (v:Variant {name:vname})
                    MERGE (v)-[:SAME_AS]->(c)
                WITH c
                CALL {
                    WITH c
                    MERGE (b:Brand {name:$brand})
                    MERGE (cat:Category {name:$category})
                    MERGE (b)-[:BELONGS_TO]->(cat)
                    MERGE (b)-[:HAS_CANONICAL]->(c)
                    FOREACH (s IN CASE WHEN $series IS NULL THEN [] ELSE [$series] END |
                        MERGE (ser:Series {name:s})
                        MERGE (b)-[:HAS_SERIES]->(ser)
                        MERGE (ser)-[:HAS_CANONICAL]->(c)
                    )
                }
            """, canonical=canonical_clean, variants=variants_clean,
                 brand=brand, series=series, category=category)

        print(f"✅ Upserted {len(data)} canonical groups into LOCAL Neo4j")
        # 🧹 Remove Canonicals that no longer exist in JSON
        canonicals_in_json = [
            entry["canonical_name"].strip()
            for entry in data
            if entry.get("canonical_name")
        ]

        session.run("""
            MATCH (c:Canonical)
            WHERE NOT c.name IN $canonicals
            DETACH DELETE c
        """, canonicals=canonicals_in_json)

        print("🗑️  Removed Canonicals not found in JSON")


if __name__ == "__main__":
    upload_json_to_graph(r"tests/canonical_mapping_master.json")
