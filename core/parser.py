#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

# parser.py
from io import BytesIO
import pandas as pd
import logging

from utils.logger import setup_logging

logger = logging.getLogger("core.parser")


def parse_excel(src: BytesIO):
    logger.info("=== Чтение всех листов ===")
    # читаем все листы сразу
    sheets = pd.read_excel(src, sheet_name=None, header=None, engine="openpyxl")
    logger.info(f"Найдено листов: {len(sheets)} -> {list(sheets.keys())}")

    frames = []
    mappings = {}

    for sheet_name, raw in sheets.items():
        # ищем строку-шапку (там где >=6 непустых значений)
        logger.info(f"--- Обработка листа: {sheet_name} ---")
        logger.debug(f"Размер листа: {raw.shape[0]} строк × {raw.shape[1]} столбцов")
        header_row = None
        for i, row in raw.iterrows():
            non_empty = row.dropna().shape[0]
            if non_empty >= 4:   # можно менять на 7
                header_row = i
                logger.info(f"{sheet_name}: заголовок найден на строке {i} (непустых ячеек: {non_empty})")
                break

        if header_row is None:
            logger.warning(f"{sheet_name}: не удалось найти строку с заголовками, пропускаю")
            continue

        # формируем нормальный DataFrame
        df = pd.read_excel(src, sheet_name=sheet_name, header=header_row, engine="openpyxl")
        logger.debug(f"{sheet_name}: колонки установлены -> {list(df.columns)}")
        logger.debug(f"{sheet_name}: кол-во строк данных -> {df.shape[0]}")

        frames.append(df)
        mappings[sheet_name] = {"columns": list(df.columns), "header_row": header_row}
        
    if frames:
        df_all = pd.concat(frames, ignore_index=True)
        logger.info(f"=== Итоговая таблица ===")
        logger.info(f"Всего строк: {df_all.shape[0]}, столбцов: {df_all.shape[1]}")
    else:
        logger.warning("Не найдено ни одного листа с данными")
        df_all = pd.DataFrame()
    return df_all, mappings