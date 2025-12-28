# core/logger.py
import logging
from pathlib import Path
import os

def _get_level(env_name: str, default=logging.ERROR):
    """Читает уровень логирования из переменной окружения."""
    val = os.getenv(env_name)
    if not val:
        return default
    val = val.upper()
    return getattr(logging, val, default)


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
    modules = {
        #оркестрация
        "dispatcher": logging.ERROR,
        # инфраструктура
        "integrations.matrix_merger": logging.ERROR,
        "core.graph_normalizer": logging.ERROR,
        "core.graph_normalizer.canonical": logging.DEBUG,
        "core.graph_normalizer.loader": logging.ERROR,
        "core.graph_normalizer.brand": logging.ERROR,
        "core.normalizer": logging.ERROR,
        "integrations.rules_typing": logging.ERROR,
        "integrations.graph_offers": logging.ERROR,
        "integrations.graph_to_sheets": logging.ERROR,
        "core.parser": logging.ERROR,
        "core.name_enricher": logging.ERROR,
        "state_machine": logging.ERROR,
        "text_state": logging.ERROR,
        "currency": logging.ERROR,
        "save_to_excel": logging.ERROR,
        "integrations.df_raw_to_graph": logging.ERROR,
        "core.gbx_detector": logging.ERROR,              
        "core.text_parser": logging.ERROR,
        #workers
        "workers.excel_worker": logging.ERROR,
        # утилиты и извлекатели
        "utils.text_extractors": logging.ERROR,
        "utils.text_extractors.prices": logging.ERROR,
        "utils.text_extractors.access": logging.ERROR,
        "utils.text_extractors.location": logging.DEBUG,
        "core.access_assistant": logging.ERROR,
        "core.location_assistant": logging.DEBUG,  
        "integrations.raw_to_graph": logging.ERROR,
        "workers.blob_worker": logging.ERROR,
        "integrations.reference_to_graph": logging.ERROR,
        "workers.reference_worker": logging.ERROR,
        "main": logging.ERROR,
        "integrations.fingerprint_utils": logging.ERROR,
        "core.distillator": logging.ERROR,
        "core.normalizer.access_location": logging.ERROR,
        "utils.verifier": logging.ERROR,
        "utils.verify_cols": logging.ERROR,
        "core.volume_detector": logging.ERROR,
        "utils.wine_guard": logging.ERROR,
        "core.header_detector": logging.ERROR,
        "core.product_detector": logging.DEBUG,
        "merge_headers": logging.ERROR,
        # админка
        "admin.admin_api": logging.ERROR

    }

    # читаем переопределения из ENV
    for name, default_level in modules.items():
        env_key = f"LOG_{name}"
        env_level = _get_level(env_key, default_level)
        logging.getLogger(name).setLevel(env_level)
        if os.getenv(env_key):
            print(f"[LOGGER] {name} level overridden via {env_key}={os.getenv(env_key)}")

    # === Отдельные файлы для ключевых подсистем ===
    special_logs = {
        "integrations.matrix_merger": "matrix_debug.txt",
        "integrations.rules_typing": "typing_debug.txt",
        "integrations.graph_offers": "graph_offers_debug.txt",
        "utils.text_extractors": "text_extractors_debug.txt",
        "core.normalizer": "normalizer_debug.txt",
        "core.text_parser": "text_parser_debug.txt",
        "core.graph_normalizer": "graph_normalizer_debug.txt",
        "core.graph_normalizer.canonical": "canonical_debug.txt",
        "utils.text_extractors.prices": "prices_debug.txt",
        "utils.text_extractors.access": "access_debug.txt",
        "utils.text_extractors.location": "location_debug.txt",
        "core.normalizer.access_location": "access_location_debug.txt",
        "core.parser": "parser_debug.txt",
        "core.distillator": "distillator_debug.txt",
        "core.name_enricher": "name_enricher_debug.txt",
        "core.access_assistant": "access_assistant_debug.txt",
        "state_machine": "state_machine_debug.txt",
        "utils.verifier": "verifier_debug.txt",
        "text_state": "text_state_debug.txt",
        "core.location_assistant": "location_assistant_debug.txt",
        "currency": "currency_debug.txt",
        "save_to_excel": "save_to_excel_debug.txt",
        "df_raw_to_graph": "df_raw_to_graph_debug.txt",
        "dispatcher": "dispatcher_debug.txt",
        "workers.excel_worker": "excel_worker_debug.txt",
        "utils.verify_cols": "verify_cols_debug.txt",
        "core.volume_detector": "volume_detector_debug.txt",
        "core.gbx_detector": "gbx_detector_debug.txt",
        "core.graph_normalizer.loader": "graph_loader_debug.txt",
        "admin.admin_api": "admin_api_debug.txt",
        "utils.wine_guard": "wine_guard_debug.txt",
        "core.header_detector": "header_detector_debug.txt",
        "core.product_detector": "product_detector_debug.txt",
        "merge_headers": "merge_headers_debug.txt",
        "core.graph_normalizer.brand": "brand_debug.txt",
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
