#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

from pathlib import Path
from resolve_supplier_name import resolve_supplier_name

class AlcoholStateMachine:
    def __init__(self, file_name: str, supplier_choice: str = None):
        self.name = resolve_supplier_name(file_name, supplier_choice)

        self.state = "INIT"
        self.df_out = None  # здесь будем хранить выходной датафрейм

    def ready(self):
        self.state = "READY"
    
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
