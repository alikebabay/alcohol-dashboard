#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

import logging
from config import MODE, driver, POLICY

#code integrations
from writer import save_to_excel
from core.organizer import attach_categories, order_by_category
from state_machine import AlcoholStateMachine
from integrations.input_loader import load
from utils.verifier import verifier
from integrations.graph_offers import push_offers_to_graph
from integrations.graph_to_sheets import get_all_offers, make_master_sheet, upload_to_gsheets
from integrations.raw_to_graph import persist_raw_blob
from workers.event_bus import publish
from integrations.reference_to_graph import reference_to_graph
from utils.logger import setup_logging
from integrations.df_raw_to_graph import df_raw_to_graph

setup_logging()
logger = logging.getLogger(__name__)


async def dispatch_excel(update, context, supplier_choice=None):
    # 1. загружаем файл или текст через input_loader
    file_src, file_name = await load(update, context)

    # chat_id может отсутствовать (regression / DummyUpdate)
    chat_id = getattr(getattr(update, "effective_chat", None), "id", None)    
    
    # Создаём state machine и определяем состояние
    supplier_sm = AlcoholStateMachine(file_name, supplier_choice)
    state = supplier_sm.decide_state(file_src)    

    # FSM вызывает соответствующий метод обработки
    df_distilled = supplier_sm.handle_state(state, file_src)

    # 💾 Детерминированный сброс сырья в граф
    raw_id = persist_raw_blob(driver, file_src, file_name)
    await publish("raw_blob_ready", {"supplier": supplier_sm.name, "raw_id": raw_id})

    # 💾 сброс спарсенной таблицы в граф
    df_raw_id = df_raw_to_graph(driver, supplier_sm.df_raw)
    # уведомляем воркера, чтобы он связал (Supplier)-[:HAS_BLOB]->(RawBlob)-[:HAS_DFRAW]->(DfRaw)
    await publish("df_raw_ready", {
        "supplier": supplier_sm.name,
        "raw_id": raw_id,
        "df_raw_id": df_raw_id
    })
    logger.debug(
        f"[DISPATCH] Event 'df_raw_ready' published: "
        f"supplier={supplier_sm.name}, raw_id={raw_id}, df_raw_id={df_raw_id}"
    )
    
    # уведомляем воркера об окончании парсинга текста
    mapping = getattr(supplier_sm, "mapping", None) or {}
    
    await publish("parse_finished", {
        "chat_id": chat_id,
        "mapping": mapping,
    })

    # 3.1 Категоризация + порядок
    df_distilled = attach_categories(df_distilled, name_col="name", out_col="Тип")
    df_distilled = order_by_category(df_distilled, category_col="Тип")

    # ⚡️ теперь говорим state machine, что поставщик готов
    supplier_sm.ready()
    supplier_name = supplier_sm.get_name()

    # проверка логики перед отдачей пользователю
    try:
        verifier.set_state("logic")
        df_distilled = verifier.run(df_distilled)        
    except ValueError as e:
        if str(e) == "NO_PRICE_COLUMNS":
            await publish("ingest.failed", {
                "chat_id": chat_id,
                "reason": "NO_PRICE",
            })
            return None

        if str(e) == "NO_PRICE_VALUES":
            await publish("ingest.failed", {
                "chat_id": chat_id,
                "reason": "NO_PRICE",
            })
            return None

        raise
    # ⚡️ финальная типизация теперь всегда
    verifier.set_state("typing")
    verifier.run(df_distilled)
    print(verifier.report())
    
    df_out = save_to_excel(df_distilled, supplier_name)

    # файл для отдачи пользователю телеграм. сохраним в state machine
    supplier_sm.set_df_out(df_out)

    # пуш сборника офферов в граф
    df_id = reference_to_graph(df_out)
    await publish("df_out_ready", {"supplier": supplier_name, "df_id": df_id})
    if POLICY.allow_graph_writes:
        push_offers_to_graph(df_out, supplier_name)

    # 5. Обновляем Google Sheets на основе графа
    try:
        df_all = get_all_offers()
        master_view = make_master_sheet(df_all, max_pairs=12)
        upload_to_gsheets(master_view)
        logger.debug(f"[OK dispatcher] Pivot обновлён: {len(master_view)} строк загружено в Google Sheets")
    except Exception as e:
        logger.error(f"[ERROR dispatcher] Не удалось обновить Pivot из графа: {e}")

    

    result = supplier_sm.get_df_out()

    supplier_sm.reset()
    supplier_sm = None  # 💥 уничтожаем ссылку на объект FSM
    verifier.reset()  # 💥 сбрасываем глобальный верифаер

    return result
