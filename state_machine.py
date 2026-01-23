from __future__ import annotations

#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")
from io import BytesIO
import logging

from utils.resolve_supplier_name import resolve_supplier_name
from text_state import TextState
from core.parser import parse_excel
from core.normalizer import normalize_alcohol_df
from core.name_enricher import filter_and_enrich
from utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

class AlcoholStateMachine:
    _active_instance: "AlcoholStateMachine" | None = None
    def __init__(self, file_name: str, supplier_choice: str = None):
        self.name = resolve_supplier_name(file_name, supplier_choice)

        self.state = "INIT"
        self.df_raw = None  # здесь будем хранить входной (сырый) датафрейм
        self.df_out = None  # здесь будем хранить выходной датафрейм
        self.mapping = {}   # ← mapping из parse_text / TextState

    def ready(self):
        self.state = "READY"

    def decide_state(self, file_src):
        """Определяем состояние: TEXT или FILE"""
        if isinstance(file_src, str):
            self.state = "TEXT"
        else:
            self.state = "FILE"
        return self.state

    def handle_text(self, file_src: str):
        self.activate()  # (1)
        ts = TextState(file_src)  # (2)
        df_out = ts.run()  # (3)

        # (4)
        if ts.df_raw is not None:
            self.df_raw = ts.df_raw.copy()
            logger.debug(f"[FSM] Saved df_raw from TextState, shape={self.df_raw.shape}")
        
        # 💡 сохраняем mapping из text pipeline
        if hasattr(ts, "mapping"):
            self.mapping = ts.mapping or {}
            logger.debug(
                "[FSM] Saved mapping from TextState: keys=%s",
                list(self.mapping.keys())
            )

        return df_out  # (5)
    
    def handle_file(self, file_src: BytesIO):
        self.activate()  # ✅ теперь self доступна глобально как "активная"
        df_raw, _ = parse_excel(file_src)
        self.df_raw = df_raw.copy()  # 💾 сохраняем исходный датафрейм для доп. поиска
        logger.debug(f"[FSM] Saved df_raw from FileState, shape={self.df_raw.shape}")
        try:
            preview = self.df_raw.head(3).to_string(index=True)
            logger.debug(f"[FSM] df_raw preview (first 3 rows):\n{preview}")
        except Exception as e:
            logger.debug(f"[FSM] Could not print df_raw preview: {e}")
        df_norm, _ = normalize_alcohol_df(df_raw)
        return filter_and_enrich(df_norm, col_name="name", df_raw=self.df_raw)


    def handle_state(self, state: str, file_src):
        """Вызывает метод в зависимости от состояния"""
        method = getattr(self, f"handle_{state.lower()}", None)
        if not method:
            raise ValueError(f"No handler for state {state}")
        return method(file_src)
    
    def set_df_out(self, df_out):
        self.df_out = df_out

    def get_df_out(self):
        if self.df_out is None:
            raise RuntimeError("df_out ещё не установлен")
        return self.df_out

    def get_name(self) -> str:
        if self.state != "READY":
            raise RuntimeError(f"Supplier not ready, current state={self.state}")
        return self.name
    
    def reset(self):
        """Полный сброс состояния после завершения обработки"""
        logger.debug(f"[FSM] Сбрасываю состояние для поставщика: {self.name}")
        self.state = "INIT"
        self.df_raw = None
        self.df_out = None
        self.mapping = {}
        self.name = None

    # 👇 Регистрируем активную FSM
    def activate(self):
        AlcoholStateMachine._active_instance = self
        logger.debug(f"[FSM] Activated instance for supplier: {self.name}")
    
    # 👇 Получаем текущую FSM откуда угодно
    @staticmethod
    def get_active() -> "AlcoholStateMachine | None":
        return AlcoholStateMachine._active_instance