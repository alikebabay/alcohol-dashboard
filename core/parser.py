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
    logger.debug("=== Чтение всех листов ===")
    # ⚡ Читаем все листы ОДИН раз (без повторных обращений к файлу)
    # dtype=str ускоряет парсинг и устраняет дорогое приведение типов
    sheets = pd.read_excel(src, sheet_name=None, header=None, engine="openpyxl", dtype=str)     
    logger.debug(f"Найдено листов: {len(sheets)} -> {list(sheets.keys())}")

    frames = []
    mappings = {}

    for sheet_name, raw in sheets.items():
        # ищем строку-шапку (там где >=6 непустых значений)
        logger.debug(f"--- Обработка листа: {sheet_name} ---")
        logger.debug(f"Размер листа: {raw.shape[0]} строк × {raw.shape[1]} столбцов")
        header_row = None
        for i, row in raw.iterrows():
            # raw уже str; пустые ячейки — это NaN/None/"" после чтения
            non_empty = row.notna().sum()
            if non_empty >= 4:   # можно менять на 7
                header_row = i
                logger.debug(f"{sheet_name}: заголовок найден на строке {i} (непустых ячеек: {non_empty})")
                break

        if header_row is None:
            logger.warning(f"{sheet_name}: не удалось найти строку с заголовками, пропускаю")
            continue

        # ⚡ Формируем нормальный DataFrame БЕЗ повторного чтения файла
        # 1) строка заголовков
        headers = raw.iloc[header_row].astype(str).tolist()
        # 2) сами данные — все строки после заголовка
        df = raw.iloc[header_row + 1:].copy()
        df.columns = headers
        # 3) чистка полностью пустых строк/столбцов (опционально)
        df.dropna(how="all", inplace=True)
        df = df.loc[:, df.notna().any(axis=0)]
        # 4) сброс индекса для аккуратности
        df.reset_index(drop=True, inplace=True)

        logger.debug(f"{sheet_name}: колонки установлены -> {list(df.columns)}")
        logger.debug(f"{sheet_name}: кол-во строк данных -> {df.shape[0]}")

        frames.append(df)
        mappings[sheet_name] = {"columns": list(df.columns), "header_row": header_row}
        
    if frames:
        df_all = pd.concat(frames, ignore_index=True)
        logger.debug(f"=== Итоговая таблица ===")
        logger.debug(f"Всего строк: {df_all.shape[0]}, столбцов: {df_all.shape[1]}")
    else:
        logger.warning("Не найдено ни одного листа с данными")
        df_all = pd.DataFrame()
    return df_all, mappings