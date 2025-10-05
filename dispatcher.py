#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")


from typing import Union
from io import BytesIO
from pathlib import Path
import os


#code integrations

from writer import save_to_excel, merge_with_master
from integrations.gsheets_integration import update_master_to_gsheets, load_master_from_gsheets
from core.organizer import attach_categories, order_by_category
from state_machine import AlcoholStateMachine
from integrations.input_loader import load
from utils.verifier import verifier

from functools import wraps

def timed(func):
    """Декоратор для замера времени работы функции."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"[TIMER] {func.__name__}: {elapsed:.2f} sec")
        return result
    return wrapper


@timed
async def dispatch_excel(update, context, supplier_choice=None):
        # 1. загружаем файл или текст через input_loader
    file_src, file_name = await load(update, context)
    

    # Создаём state machine и определяем состояние
    supplier_sm = AlcoholStateMachine(file_name, supplier_choice)
    state = supplier_sm.decide_state(file_src)

    # FSM вызывает соответствующий метод обработки
    df_distilled = supplier_sm.handle_state(state, file_src)

    # 3.1 Категоризация + порядок
    df_distilled = attach_categories(df_distilled, name_col="name", out_col="Тип")
    df_distilled = order_by_category(df_distilled, category_col="Тип")

    # ⚡️ теперь говорим state machine, что поставщик готов
    supplier_sm.ready()
    supplier_name = supplier_sm.get_name()

    # проверка перед отдачей пользователю
    df_distilled = verifier.run(df_distilled)
    print(verifier.report())
    
    df_out = save_to_excel(df_distilled, supplier_name)

    # файл для отдачи пользователю телеграм. сохраним в state machine
    supplier_sm.set_df_out(df_out)

    
    # 5. работа с мастером в Google Sheets
    try:
        old_master = load_master_from_gsheets()
        # 💡 страховка: если вернул None — создаём пустой DataFrame
        if old_master is None:
            print("[WARN] load_master_from_gsheets() вернул None — создаю пустой DataFrame")
            old_master = pd.DataFrame()

        if old_master.empty:
            print("[INFO] Master пустой — создаю новый из df_out")
            df_final = df_out
        else:
            # обычное слияние
            df_final = merge_with_master(old_master, df_out, supplier_name)
        
        # ⚡️ финальная типизация теперь всегда
        verifier.set_state("typing")
        verifier.run(df_final)
        print(verifier.report())


        update_master_to_gsheets(df_final)
        print(f"[OK dispatcher] Master обновлён в Google Sheets, всего строк: {df_final.shape[0]}")
    except Exception as e:
        print(f"[ERROR dispatcher] Не удалось обновить Google Sheets: {e}")
        df_final = df_out  # fallback

    result = supplier_sm.get_df_out()

    supplier_sm.reset()
    supplier_sm = None  # 💥 уничтожаем ссылку на объект FSM
    verifier.reset()  # 💥 сбрасываем глобальный верифаер
    print("[DEBUG dispatcher] FSM и Verifier полностью обнулены после завершения цикла")

    return result
