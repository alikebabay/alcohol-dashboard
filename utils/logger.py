# core/logger.py
import logging
from pathlib import Path


def setup_logging(global_level=logging.INFO):
    """
    Глобальная централизованная настройка логгирования для всего проекта.
    Каждый модуль может писать свои DEBUG/INFO/ERROR-сообщения.
    Отдельные файлы создаются для ключевых подсистем.
    """

    root_logger = logging.getLogger()

    # 🧠 не инициализируем повторно
    if getattr(root_logger, "_global_initialized", False):
        return
    root_logger._global_initialized = True

    # === Формат ===
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # === Корневой логгер ===
    root_logger.setLevel(global_level)

    # Консоль
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    sh.setLevel(global_level)
    root_logger.addHandler(sh)

    # Общий файл для всех модулей
    main_log_path = Path("project_debug.txt")
    fh = logging.FileHandler(main_log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(logging.DEBUG)
    root_logger.addHandler(fh)

    # === Уровни для конкретных модулей ===
    per_module_levels = {
        # инфраструктура
        "integrations.matrix_merger": logging.INFO,
        "core.graph_normalizer": logging.ERROR,
        "integrations.rules_typing": logging.INFO,
        "integrations.graph_offers": logging.ERROR,
        # утилиты и извлекатели
        "utils.text_extractors": logging.ERROR,
        "utils.text_extractors.prices": logging.ERROR,
        "utils.text_extractors.access": logging.DEBUG,
        "utils.text_extractors.location": logging.DEBUG,
        "core.normalizer": logging.ERROR,
        "core.text_parser": logging.ERROR,
    }

    for name, level in per_module_levels.items():
        logging.getLogger(name).setLevel(level)

    # === Отдельные файлы для ключевых подсистем ===
    special_logs = {
        "integrations.matrix_merger": "matrix_debug.txt",
        "integrations.rules_typing": "typing_debug.txt",
        "integrations.graph_offers": "graph_offers_debug.txt",
        "utils.text_extractors": "text_extractors_debug.txt",
        "core.normalizer": "normalizer_debug.txt",
        "core.text_parser": "text_parser_debug.txt",
        "core.graph_normalizer": "graph_normalizer_debug.txt",
        "utils.text_extractors.prices": "prices_debug.txt",
        "utils.text_extractors.access": "access_debug.txt",
        "utils.text_extractors.location": "location_debug.txt",
    }

    # --- Silence noisy external libraries ---
    for noisy in [
        "neo4j",
        "httpx",
        "httpcore",
        "urllib3",
        "telegram",
    ]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    for module, filename in special_logs.items():
        path = Path(filename)
        fh = logging.FileHandler(path, encoding="utf-8")
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG)
        logging.getLogger(module).addHandler(fh)

    logging.getLogger(__name__).info("✅ Global logging initialized")


# Для локального теста
if __name__ == "__main__":
    setup_logging(logging.DEBUG)
    log = logging.getLogger("utils.text_extractors")
    log.debug("Тестовый DEBUG из text_extractors")
