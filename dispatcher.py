#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")


from typing import Union
from io import BytesIO
from pathlib import Path
import os

#code integrations
from parser import parse_excel
from writer import save_to_excel, normalize_alcohol_df
from gsheets_integration import update_master_to_gsheets
from distillator import filter_and_enrich
from organizer import attach_categories, order_by_category
from parser_fsm import SupplierStateMachine

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
def dispatch_excel(file_src: Union[Path, BytesIO], file_name: str = "unnamed.xlsx"):
    print(f"[DEBUG dispatcher] Входной файл: {file_name}")

    # Создаём state machine для поставщика
    supplier_sm = SupplierStateMachine(file_name)
       
    # 1. читаем Excel
    df_raw, _ = parse_excel(file_src)
    

    # 2. нормализуем
    df_norm, mapping = normalize_alcohol_df(df_raw)  


    # 3. фильтруем и обогащаем
    df_distilled = filter_and_enrich(df_norm, col_name="name")

    # 3.1 Категоризация + порядок
    df_distilled = attach_categories(df_distilled, name_col="name", out_col="Тип")
    df_distilled = order_by_category(df_distilled, category_col="Тип")

    # ⚡️ теперь говорим state machine, что поставщик готов
    supplier_sm.ready()
    supplier_name = supplier_sm.get_name()
    
    df_out = save_to_excel(df_distilled, supplier_name)

    
    

    # 5. Обновляем Google Sheets
    try:
        update_master_to_gsheets(df_out)
        print("[DEBUG dispatcher] Google Sheets обновлён")
    except Exception as e:
        print(f"[ERROR dispatcher] Не удалось обновить Google Sheets: {e}")
    
    

    return df_out

