# parser.py
from pathlib import Path
import pandas as pd

import numpy as np

def parse_excel(file_path: Path):
    print(f"[DEBUG parse_excel] Начинаю парсить: {file_path}")
    # читаем всё как есть, без заголовков
    raw = pd.read_excel(file_path, header=None)
    
    # ищем строку-шапку (там где >=6 непустых значений)
    header_row = None
    for i, row in raw.iterrows():
        non_empty = row.dropna().shape[0]
        if non_empty >= 4:   # можно менять на 7
            header_row = i
            break

    if header_row is None:
        raise ValueError("Не удалось найти строку с заголовками")

    # формируем нормальный DataFrame
    df = pd.read_excel(file_path, header=header_row)

    mapping = {"columns": list(df.columns)}
    print(f"[DEBUG parse_excel] Нормализовал, shape={df.shape}, header_row={header_row}")
    return df, mapping