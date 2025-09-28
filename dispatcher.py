#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

from parser import parse_excel
from writer import save_to_excel, normalize_alcohol_df
from typing import Union
from io import BytesIO
from pathlib import Path
from gsheets_integration import update_master_to_gsheets
from distillator import filter_and_enrich
from organizer import attach_categories, order_by_category



def dispatch_excel(file_src: Union[Path, BytesIO], file_name: str = "unnamed.xlsx"):
    print(f"[DEBUG dispatcher] Входной файл: {file_name}")

# если прилетает BytesIO → пока подсовываем дамми Path (старому коду)
    if isinstance(file_src, BytesIO):
        parse_target = Path(r"C:\Users\alikebabay\Documents\alcohol-dashboard\test_documents") / file_name
    else:
        parse_target = file_src
    
    # 1. читаем Excel
    df_raw, _ = parse_excel(parse_target)
    print(f"[DEBUG dispatcher] parse_excel вернул df shape={df_raw.shape}")

    # 2. нормализуем
    df_norm, mapping = normalize_alcohol_df(df_raw)
    print(f"[DEBUG dispatcher] normalize_alcohol_df вернул df shape={df_norm.shape}, mapping={mapping}")


    # 3. фильтруем и обогащаем
    df_distilled = filter_and_enrich(df_norm, col_name="name")
    print(f"[DEBUG dispatcher] после фильтрации/обогащения shape={df_distilled.shape}")

    # 3.1 Категоризация + порядок
    df_distilled = attach_categories(df_distilled, name_col="name", out_col="Тип")
    df_distilled = order_by_category(df_distilled, category_col="Тип")

    # 4. сохраняем
    out_path, df_out = save_to_excel(df_distilled, file_name)
    print(f"[DEBUG dispatcher] save_to_excel вернул: {out_path}")

    # 5. (опционально) обновляем Google Sheets
    try:
        update_master_to_gsheets(df_out)
        print("[DEBUG dispatcher] Google Sheets обновлён")
    except Exception as e:
        print(f"[ERROR dispatcher] Не удалось обновить Google Sheets: {e}")

    return out_path
