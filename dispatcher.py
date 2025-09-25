from parser import parse_excel
from writer import save_to_excel
from pathlib import Path

def dispatch_excel(file_path: Path):
    print(f"[DEBUG dispatcher] Входной файл: {file_path}")
    df_norm, mapping = parse_excel(file_path)
    print(f"[DEBUG dispatcher] parse_excel вернул df shape={df_norm.shape}, mapping={mapping}")

    out_path = save_to_excel(df_norm, file_path.name)
    print(f"[DEBUG dispatcher] save_to_excel вернул: {out_path}")
    return out_path
