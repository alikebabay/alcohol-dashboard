#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

from pathlib import Path

class SupplierStateMachine:
    def __init__(self, file_name: str):
        self.name = Path(file_name).stem or "unknown"
        self.state = "INIT"

    def ready(self):
        self.state = "READY"

    def get_name(self) -> str:
        if self.state != "READY":
            raise RuntimeError(f"Supplier not ready, current state={self.state}")
        return self.name
