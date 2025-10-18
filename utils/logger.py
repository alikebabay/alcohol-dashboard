# core/logger.py
import logging
from pathlib import Path

def setup_logging(global_level=logging.INFO):
    """
    Централизованная настройка логгирования для всего проекта.
    Здесь можно задавать уровни для отдельных модулей.
    """
    log_path = Path("matrix_debug.txt")

    # форматтер
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(global_level)

    # очистим старые хэндлеры, чтобы не дублировались
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    # консоль
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    sh.setLevel(global_level)
    root_logger.addHandler(sh)

    # файл
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(logging.DEBUG)
    root_logger.addHandler(fh)

    # 🔧 индивидуальные уровни
    per_module_levels = {
        # "matrix_merger" можно временно выключить, поставив WARNING или ERROR
        "integrations.matrix_merger": logging.ERROR,
        # а если захочешь включить — просто logging.DEBUG
        # "fingerprint_utils": logging.INFO,
        "core.graph_normalizer": logging.ERROR,   # 🔇 полностью выключить, только ошибки
        "integrations.rules_typing": logging.ERROR,
        "integrations.graph_offers": logging.DEBUG,  # 🧩 включаем логи для нового модуля
    }

    for module_name, level in per_module_levels.items():
        logging.getLogger(module_name).setLevel(level)

    # --- отдельные файлы для подмодулей ---
    # --- typing ---
    typing_log_path = Path("typing_debug.txt")
    typing_fh = logging.FileHandler(typing_log_path, encoding="utf-8")
    typing_fh.setFormatter(fmt)
    typing_fh.setLevel(logging.DEBUG)
    logging.getLogger("integrations.rules_typing").addHandler(typing_fh)
    
    # graph_offers
    graph_log_path = Path("graph_offers_debug.txt")
    graph_fh = logging.FileHandler(graph_log_path, encoding="utf-8")
    graph_fh.setFormatter(fmt)
    graph_fh.setLevel(logging.DEBUG)
    logging.getLogger("integrations.graph_offers").addHandler(graph_fh)

    logging.info("✅ Logging initialized (matrix + typing + graph_offers split)")