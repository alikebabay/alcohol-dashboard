#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

from io import BytesIO

from utils.resolve_supplier_name import resolve_supplier_name
from text_state import TextState
from core.parser import parse_excel
from core.normalizer import normalize_alcohol_df
from core.name_enricher import filter_and_enrich

class AlcoholStateMachine:
    def __init__(self, file_name: str, supplier_choice: str = None):
        self.name = resolve_supplier_name(file_name, supplier_choice)

        self.state = "INIT"
        self.df_out = None  # здесь будем хранить выходной датафрейм

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
        ts = TextState(file_src)
        return ts.run()

    def handle_file(self, file_src: BytesIO):
        df_raw, _ = parse_excel(file_src)
        df_norm, _ = normalize_alcohol_df(df_raw)
        return filter_and_enrich(df_norm, col_name="name")

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
