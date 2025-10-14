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

        # 2️⃣ Убедимся, что все типы связей объявлены (во избежание warning'ов)
        print("🧩 Ensuring relationship types exist...")
        session.run("CALL db.createRelationshipType('HAS_SERIES')")
        session.run("CALL db.createRelationshipType('HAS_VARIANT')")
        session.run("CALL db.createRelationshipType('HAS_CANONICAL')")
        session.run("CALL db.createRelationshipType('SAME_AS')")
        print("✅ Relationship types ready.")

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
            # ==========================================================
            # 🧩 Brand / Series связи — теперь берём из JSON напрямую
            # ==========================================================
            brand = entry.get("brand")
            series = entry.get("series")

            if brand:
                session.run("MERGE (b:Brand {name:$brand})", brand=brand)

            if series:
                session.run("""
                    MERGE (s:Series {name:$series})
                    MERGE (b:Brand {name:$brand})
                    MERGE (b)-[:HAS_SERIES]->(s)
                    MERGE (s)-[:HAS_CANONICAL]->(c:Canonical {name:$canonical})
                """, brand=brand, series=series, canonical=canonical_clean)
                print(f"→ Linked Brand '{brand}' → Series '{series}'")
            elif brand:
                # Если серии нет — всё равно связываем бренд напрямую с каноном
                session.run("""
                    MERGE (b:Brand {name:$brand})
                    MERGE (c:Canonical {name:$canonical})
                    MERGE (b)-[:HAS_CANONICAL]->(c)
                """, brand=brand, canonical=canonical_clean)
                print(f"→ Linked Brand '{brand}' → Canonical '{canonical_clean}'")

    print(f"✅ Uploaded {len(data)} canonical alcohol groups into Neo4j")

# ==========================================================
# 🧮 Обновлённые Cypher-запросы (для поиска серий)
# ----------------------------------------------------------
# заменяем ':HAS_SERIES|:HAS_VARIANT' → ':HAS_SERIES|HAS_VARIANT'
# ==========================================================

# Пример использования:
# MATCH (b:Brand)-[:HAS_SERIES|HAS_VARIANT]->(s:Series)
# WHERE toLower(replace(b.name,'&','and')) CONTAINS $bn
# RETURN DISTINCT s.name AS name

if __name__ == "__main__":
    upload_json_to_graph(r"tests\\canonical_mapping_master.json")
