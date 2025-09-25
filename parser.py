# parser.py
from pathlib import Path
import pandas as pd

def parse_excel(file_path: Path):
    print(f"[DEBUG parse_excel] Начинаю парсить: {file_path}")
    df = pd.read_excel(file_path)

    # твоя логика нормализации
    # df = normalize(df)

    mapping = {"columns": list(df.columns)}
    print(f"[DEBUG parse_excel] Нормализовал, shape={df.shape}")
    return df, mapping
