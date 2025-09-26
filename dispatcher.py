#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

from parser import parse_excel
from writer import save_to_excel
from pathlib import Path
from gsheets_integration import update_master_to_gsheets

def dispatch_excel(file_path: Path):
    print(f"[DEBUG dispatcher] Входной файл: {file_path}")
    df_norm, mapping = parse_excel(file_path)
    print(f"[DEBUG dispatcher] parse_excel вернул df shape={df_norm.shape}, mapping={mapping}")

    out_path, df_out = save_to_excel(df_norm, file_path.name)
    print(f"[DEBUG dispatcher] save_to_excel вернул: {out_path}")

    # обновляем Google Sheets ИЗ ТОГО ЖЕ df
    try:
        update_master_to_gsheets(df_out)
    except Exception as e:
        print(f"[ERROR dispatcher] Не удалось обновить Google Sheets: {e}")

    return out_path
