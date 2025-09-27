#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

from parser import parse_excel
from writer import save_to_excel, normalize_alcohol_df
from pathlib import Path
from gsheets_integration import update_master_to_gsheets

def dispatch_excel(file_path: Path):
    print(f"[DEBUG dispatcher] Входной файл: {file_path}")
    # 1. читаем Excel
    df_raw, _ = parse_excel(file_path)
    print(f"[DEBUG dispatcher] parse_excel вернул df shape={df_raw.shape}")

    # 2. нормализуем
    df_norm, mapping = normalize_alcohol_df(df_raw)
    print(f"[DEBUG dispatcher] normalize_alcohol_df вернул df shape={df_norm.shape}, mapping={mapping}")

    # 3. сохраняем
    out_path, df_out = save_to_excel(df_norm, file_path.name)
    print(f"[DEBUG dispatcher] save_to_excel вернул: {out_path}")

    # 4. (опционально) обновляем Google Sheets
    try:
        update_master_to_gsheets(df_out)
        print("[DEBUG dispatcher] Google Sheets обновлён")
    except Exception as e:
        print(f"[ERROR dispatcher] Не удалось обновить Google Sheets: {e}")

    return out_path
