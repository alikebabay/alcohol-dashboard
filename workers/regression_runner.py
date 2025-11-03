# regression_runner.py
import asyncio
import logging
import os
from config import driver
from dispatcher import dispatch_excel
from integrations import input_loader
from tests.graph_download_local import export_node  # ← используем готовую функцию


# ───────────────────────────────────────────────
# 🧩 Заглушка publish, чтобы dispatcher не падал при регрессионном запуске
# ───────────────────────────────────────────────
import dispatcher

async def dummy_publish(event_name, payload=None):
    logger.debug(f"[REG STUB publish] event={event_name}, payload={payload}")
    return None

# подменяем глобал в dispatcher напрямую
dispatcher.publish = dummy_publish

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


Q_GET_RAW_WITH_CANON = """
MATCH (s:Supplier)-[:HAS_BLOB]->(r:RawBlob)-[:HAS_DFOUT]->(d:DfOut)
WHERE d.canonical = true
RETURN s.name AS supplier,
       r.id AS raw_id,
       r.fileName AS raw_file,
       d.id AS canon_id,
       d.fileName AS canon_file
ORDER BY s.name
"""

# Заглушка загрузчика (чтобы dispatch_excel не ходил в Telegram)
async def local_loader(update, context):
    return context.file_src, os.path.basename(context.file_src)


async def run_pipeline_for_raw(supplier: str, raw_path: str, raw_type: str):
    input_loader.load = local_loader  # заменяем загрузчик на локальный

    class DummyDocument:
        def __init__(self, file_name):
            self.file_name = file_name
            self.file_id = f"local_{file_name}"  # 💡 подставляем фиктивный file_id

    class DummyMessage:
        def __init__(self, text=None, document=None):
            self.text = text
            self.document = document

        async def reply_text(self, text):
            logger.debug(f"[TG SIM reply_text] {text}")

        async def reply_document(self, **kwargs):
            logger.debug(f"[TG SIM reply_document] {kwargs.get('filename')}")

    class DummyUpdate:
        def __init__(self, message):
            self.message = message

    class DummyContext:
        chat_data = {"supplier_choice": supplier}
        file_src = raw_path

        class DummyBot:
            async def get_file(self, file_id):                

                class DummyFile:
                    async def download_to_drive(self, path):
                        local_name = os.path.join("processed", file_id.replace("local_", ""))


                        try:
                            with open(local_name, "rb") as src, open(path, "wb") as dst:
                                data = src.read()
                                dst.write(data)

                            dest_size = os.path.getsize(path)
                            

                        except Exception as e:
                            logger.exception(f"[TG SIM download_to_drive] COPY FAILED: {e}")

                    async def download_as_bytearray(self):
                        local_name = os.path.join("processed", file_id.replace("local_", ""))

                        logger.debug(f"[TG SIM download_as_bytearray] reading '{local_name}'")

                        try:
                            with open(local_name, "rb") as f:
                                content = bytearray(f.read())
                            logger.debug(
                                f"[TG SIM download_as_bytearray] returning {len(content)} bytes"
                            )
                            return content
                        except Exception as e:
                            logger.exception(f"[TG SIM download_as_bytearray] READ FAILED: {e}")
                            return bytearray()
                return DummyFile()
        bot = DummyBot()

    # 🧩 Определяем тип входных данных по расширению файла
    if raw_path.lower().endswith(".txt"):
        try:
            with open(raw_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            message = DummyMessage(text=text)
           # logger.debug(f"[REG] Loaded text offer ({len(text)} chars)")
        except Exception as e:
            #logger.error(f"[REG] Failed to read {raw_path}: {e}")
            message = DummyMessage(text=None)
    else:
        # Excel-файл (.xlsx, .xls и т.п.)
        message = DummyMessage(document=DummyDocument(os.path.basename(raw_path)))
        #logger.debug(f"[REG] Loaded Excel offer {raw_path}")

    update, context = DummyUpdate(message), DummyContext()

    #logger.info(f"[REG] ▶ Прогоняем {supplier}, файл {raw_path}")
    df_out = await dispatch_excel(update, context, supplier_choice=supplier)

    out_path = f"processed/{supplier}_out.xlsx"
    df_out.to_excel(out_path, index=False)
    #logger.info(f"[REG] ✅ Сохранено: {out_path}")
    return out_path



async def run_regression():
    """Основной цикл регрессионного теста."""
    with driver.session() as session:
        raws = session.run(Q_GET_RAW_WITH_CANON).data()

    if not raws:
        #logger.warning("[REG] Не найдено RawBlob с каноничными DfOut")
        return

    #logger.info(f"[REG] Найдено {len(raws)} RawBlob для регрессии")

    for rec in raws:
        supplier = rec["supplier"]
        raw_id = rec["raw_id"]
        file_name = rec.get("raw_file") or f"{supplier}.txt"
        raw_type = rec.get("raw_type") or ""
        try:
            # Этап 1️⃣ — скачиваем RawBlob с графа
            #logger.info(f"[REG] 📥 Скачиваем RawBlob {raw_id} ({supplier}) → processed/")
            export_node(raw_id)
            raw_path = os.path.join("processed", file_name)

            # Этап 2️⃣ — прогоняем пайплайн
            out_path = await run_pipeline_for_raw(supplier, raw_path, raw_type)

            # Этап 3️⃣ — сверяем с каноническим DfOut
            logger.debug(f"[REG] ⚖️ Сверяем результат с каноном {rec['canon_id']}")
            try:
                # скачиваем канон
                export_node(rec["canon_id"])
                canon_file = rec.get("canon_file") or f"{supplier}_canon.xlsx"
                canon_path = os.path.join("processed", canon_file)

                import pandas as pd
                df_new = pd.read_excel(out_path)
                df_canon = pd.read_excel(canon_path)

                if "b64" not in df_new.columns or "b64" not in df_canon.columns:
                    logger.warning("[REG] В одном из файлов нет колонки b64 — сравнение невозможно")
                    continue

                set_new = set(df_new["b64"].dropna())
                set_canon = set(df_canon["b64"].dropna())
                added = set_new - set_canon
                removed = set_canon - set_new

                if not added and not removed:
                    logger.info(f"[REG] ✅ {supplier}: совпадает ({len(set_new)} строк)")
                else:
                    if added or removed:
                        logger.warning(f"[REG] ❌ {supplier}: различия найдены (+{len(added)} / -{len(removed)})")
                        import base64
                        if added:
                            logger.warning("[REG][ADDED decoded]")
                            for b in list(added)[:10]:
                                try:
                                    decoded = base64.b64decode(b).decode("utf-8", errors="ignore")
                                    logger.warning(f"  + {decoded}")
                                except Exception as e:
                                    logger.warning(f"  + [decode error] {b[:40]}... ({e})")
    
                        if removed:
                            logger.warning("[REG][REMOVED decoded]")
                            for b in list(removed)[:10]:
                                try:
                                    decoded = base64.b64decode(b).decode("utf-8", errors="ignore")
                                    logger.warning(f"  - {decoded}")
                                except Exception as e:
                                    logger.warning(f"  - [decode error] {b[:40]}... ({e})")


            except Exception as e:
                logger.error(f"[REG] Ошибка при сравнении с каноном: {e}")

        except Exception as e:
            logger.error(f"[REG] Ошибка при прогоне {supplier}: {e}")

        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_regression())
