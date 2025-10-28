#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")


# parser.py
from io import BytesIO
import pandas as pd

def parse_excel(src: BytesIO):
    
    # читаем все листы сразу
    sheets = pd.read_excel(src, sheet_name=None, header=None, engine="openpyxl")
    

    frames = []
    mappings = {}

    for sheet_name, raw in sheets.items():
        # ищем строку-шапку (там где >=6 непустых значений)
        header_row = None
        for i, row in raw.iterrows():
            non_empty = row.dropna().shape[0]
            if non_empty >= 4:   # можно менять на 7
                header_row = i
                break

        if header_row is None:
            print(f"[WARN] {sheet_name}: не удалось найти строку с заголовками, пропускаю")
            continue

        # формируем нормальный DataFrame
        df = pd.read_excel(src, sheet_name=sheet_name, header=header_row, engine="openpyxl")
        frames.append(df)
        mappings[sheet_name] = {"columns": list(df.columns), "header_row": header_row}
        
    if frames:
        df_all = pd.concat(frames, ignore_index=True)
    else:
        df_all = pd.DataFrame()
    return df_all, mappings