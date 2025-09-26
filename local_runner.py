#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

from pathlib import Path
import traceback
from dispatcher import dispatch_excel

# Папка с тестовыми документами
TEST_DIR = Path(r"C:\Users\alikebabay\Documents\alcohol-dashboard\test_documents")

def main():
    files = list(TEST_DIR.glob("*.xls*"))  # и .xls, и .xlsx
    if not files:
        print(f"[INFO] Нет Excel файлов в {TEST_DIR}")
        return

    print(f"[INIT] Найдено файлов: {len(files)}")

    for f in files:
        print(f"\n[DEBUG local_runner] Запуск для: {f.name}")
        try:
            dispatch_excel(f)
            print(f"[OK] Завершено: {f.name}")
        except Exception as e:
            print(f"[ERROR] {f.name}: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    main()
