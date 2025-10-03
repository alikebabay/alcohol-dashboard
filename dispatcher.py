#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")


from typing import Union
from io import BytesIO
from pathlib import Path
import os


#code integrations
from parser import parse_excel
from writer import save_to_excel, normalize_alcohol_df, merge_with_master
from gsheets_integration import update_master_to_gsheets, load_master_from_gsheets
from name_enricher import filter_and_enrich
from organizer import attach_categories, order_by_category
from state_machine import AlcoholStateMachine
from text_state import TextState
from input_loader import load

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

    print(f"[DEBUG dispatcher] Входной файл: {file_name}, supplier_choice={supplier_choice}")

    # Создаём state machine для поставщика (само решает: имя файла или выбор пользователя)
    supplier_sm = AlcoholStateMachine(file_name, supplier_choice)
       
    if isinstance(file_src, str):
        # если это сырой текст → TextState
        ts = TextState(file_src)
        df_distilled = ts.run()
    else:
        # Excel путь
        df_raw, _ = parse_excel(file_src)
        df_norm, mapping = normalize_alcohol_df(df_raw)
        df_distilled = filter_and_enrich(df_norm, col_name="name")

    # 3.1 Категоризация + порядок
    df_distilled = attach_categories(df_distilled, name_col="name", out_col="Тип")
    df_distilled = order_by_category(df_distilled, category_col="Тип")

    # ⚡️ теперь говорим state machine, что поставщик готов
    supplier_sm.ready()
    supplier_name = supplier_sm.get_name()
    
    df_out = save_to_excel(df_distilled, supplier_name)

    # файл для отдачи пользователю телеграм. сохраним в state machine
    supplier_sm.set_df_out(df_out)
    print(f"[DEBUG dispatcher] df_out saved to state machine, shape={df_out.shape}")

    
    # 5. работа с мастером в Google Sheets
    try:
        old_master = load_master_from_gsheets()
        if old_master.empty:
            df_final = df_out
        else:
            df_final = merge_with_master(old_master, df_out, supplier_name)

        update_master_to_gsheets(df_final)
        print(f"[OK dispatcher] Master обновлён в Google Sheets, всего строк: {df_final.shape[0]}")
    except Exception as e:
        print(f"[ERROR dispatcher] Не удалось обновить Google Sheets: {e}")
        df_final = df_out  # fallback

    return supplier_sm.get_df_out()

