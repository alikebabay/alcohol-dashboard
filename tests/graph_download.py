from neo4j import GraphDatabase
import argparse


# 🔹 Локальное подключение (отдельно от онлайн)
URI = "bolt://65.108.49.93:7687"
USER = "neo4j"
PASS = "testing123"

local_driver = GraphDatabase.driver(URI, auth=(USER, PASS))

def export_raw_blob(record_id: str):
    """Скачивает RawBlob из Neo4j и сохраняет как текст или бинарный файл."""
    with local_driver.session() as sess:
        rec = sess.run("""
            MATCH (r:RawBlob {id:$id})
            RETURN r.blob AS blob, r.fileName AS fileName, r.type AS type
        """, id=record_id).single()

    if not rec:
        print("❌ Нода не найдена")
        return

    blob = rec["blob"]
    file_name = rec["fileName"]
    ftype = rec["type"]

    if ftype == "text":
        text = blob.decode("utf-8", errors="ignore")
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"✅ Текст сохранён: {file_name}")
    else:
        with open(file_name, "wb") as f:
           f.write(blob)
        print(f"✅ Файл сохранён: {file_name} ({len(blob)} байт)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Скачать RawBlob из Neo4j")
    parser.add_argument("id", help="UUID ноды RawBlob")
    args = parser.parse_args()

    try:
        export_raw_blob(args.id)
    except Exception as e:
        print(f"❌ Ошибка: {e}")