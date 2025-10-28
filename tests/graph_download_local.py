from neo4j import GraphDatabase
import argparse
import os

# 🔹 Локальное подключение (отдельно от онлайн)
LOCAL_URI = "bolt://localhost:7687"
LOCAL_USER = "neo4j"
LOCAL_PASS = "testing123"

local_driver = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASS))

# 📂 Папка, куда всё будет сохраняться
PROCESSED_DIR = os.path.join(os.getcwd(), "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

def export_node(record_id: str):
    """
    Универсальный экспортер: автоматически определяет тип ноды (RawBlob или DfOut)
    и сохраняет соответствующий файл локально.
    """
    with local_driver.session() as sess:
        rec = sess.run("""
            MATCH (n)
            WHERE n.id = $id
            RETURN labels(n) AS labels, n.blob AS blob,
                   n.fileName AS fileName,
                   n.type AS type,
                   n.ext AS ext,
                   n.format AS format
        """, id=record_id).single()

    if not rec:
        print("❌ Нода не найдена")
        return

    labels = rec["labels"]
    blob = rec["blob"]
    file_name = rec.get("fileName") or f"node_{record_id}"
    ftype = rec.get("type")
    ext = rec.get("ext") or ""
    fmt = rec.get("format")

    out_path = os.path.join(PROCESSED_DIR, file_name)
    if ext and not out_path.endswith(ext):
        out_path += ext

    # 🟢 RawBlob (текст или бинарь)
    if "RawBlob" in labels:
        if ftype == "text":
            text = blob.decode("utf-8", errors="ignore")
            out_path = os.path.join(PROCESSED_DIR, file_name)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"✅ Текст сохранён: {out_path}")
        else:
            if not file_name.endswith(ext):
                file_name = f"{file_name}{ext}"
            out_path = os.path.join(PROCESSED_DIR, file_name)
            with open(out_path, "wb") as f:
                f.write(blob)
            print(f"✅ Файл RawBlob сохранён: {out_path} ({len(blob)} байт)")

    # 🟣 DfOut (обычно Excel)
    elif "DfOut" in labels:
        ext = ext or ".xlsx"
        if not file_name.endswith(ext):
            file_name = f"{file_name}{ext}"
        out_path = os.path.join(PROCESSED_DIR, file_name)
        with open(out_path, "wb") as f:
            f.write(blob)
        print(f"✅ DfOut сохранён: {out_path} ({len(blob)} байт, формат={fmt or 'excel'})")

    else:
        print(f"⚠️ Неизвестный тип ноды: {labels}")
        out_path = os.path.join(PROCESSED_DIR, f"{file_name}.bin")
        with open(out_path, "wb") as f:
            f.write(blob)
        print(f"💾 Содержимое сохранено в {out_path} (сырой бинарь)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Скачать RawBlob или DfOut из Neo4j")
    parser.add_argument("id", help="UUID ноды RawBlob или DfOut")
    args = parser.parse_args()

    try:
        export_node(args.id)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
