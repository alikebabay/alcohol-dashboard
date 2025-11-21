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
        print("🧹 Starting CLEANUP phase...")

        # -------------------------------------------
        # 1. Collect JSON sets
        # -------------------------------------------
        canonicals_in_json = set()
        brands_in_json = set()
        series_in_json = set()

        for entry in data:
            if entry.get("canonical_name"):
                canonicals_in_json.add(entry["canonical_name"].strip())
            if entry.get("brand"):
                brands_in_json.add(entry["brand"].strip())

            s = entry.get("series")
            if isinstance(s, str) and s.strip():
                series_in_json.add(s.strip())

        print(f"📦 JSON Canonicals: {len(canonicals_in_json)}")
        print(f"📦 JSON Brands:      {len(brands_in_json)}")
        print(f"📦 JSON Series:      {len(series_in_json)}")

        # -------------------------------------------
        # 2. Delete Canonicals not in JSON
        # -------------------------------------------
        print("🗑️  Removing Canonicals not in JSON...")
        result = session.run("""
            MATCH (c:Canonical)
            WHERE NOT c.name IN $canonicals
            WITH c, c.name AS name
            DETACH DELETE c
            RETURN name
        """, canonicals=list(canonicals_in_json))

        deleted = [r["name"] for r in result]
        print(f"   → Deleted Canonicals: {len(deleted)}")
        if deleted:
            for n in deleted:
                print("      -", n)

        # -------------------------------------------
        # 3. Delete Series not in JSON
        # -------------------------------------------
        print("🗑️  Removing Series not in JSON...")
        result = session.run("""
            MATCH (s:Series)
            WHERE NOT s.name IN $series
            WITH s, s.name AS name
            DETACH DELETE s
            RETURN name
        """, series=list(series_in_json))

        deleted = [r["name"] for r in result]
        print(f"   → Deleted Series: {len(deleted)}")
        if deleted:
            for n in deleted:
                print("      -", n)

        # -------------------------------------------
        # 4. Delete Brands not in JSON
        # -------------------------------------------
        print("🗑️  Removing Brands not in JSON...")
        result = session.run("""
            MATCH (b:Brand)
            WHERE NOT b.name IN $brands
            WITH b, b.name AS name
            DETACH DELETE b
            RETURN name
        """, brands=list(brands_in_json))

        deleted = [r["name"] for r in result]
        print(f"   → Deleted Brands: {len(deleted)}")
        if deleted:
            for n in deleted:
                print("      -", n)

        # -------------------------------------------
        # 5. Delete orphan Variants
        # -------------------------------------------
        print("🗑️  Removing orphan Variants...")
        result = session.run("""
            MATCH (v:Variant)
            WHERE NOT (v)-[:SAME_AS]->(:Canonical)
            WITH v, v.name AS name
            DETACH DELETE v
            RETURN name
        """)

        deleted = [r["name"] for r in result]
        print(f"   → Deleted Orphan Variants: {len(deleted)}")
        if deleted:
            for n in deleted:
                print("      -", n)

        print("✨ CLEANUP DONE.")



if __name__ == "__main__":
    upload_json_to_graph(r"tests/canonical_mapping_master.json")
