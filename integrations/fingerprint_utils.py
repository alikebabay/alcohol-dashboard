import base64
import zlib
from datetime import datetime
import pandas as pd

from state_machine import AlcoholStateMachine  # 🧩 чтобы тянуть активный supplier

def add_offer_metadata(df: pd.DataFrame, debug: bool = True) -> pd.DataFrame:
    """Добавляет дату и отпечатки (crc32_hash, b64) для каждой строки DataFrame."""

    if debug:
        print(f"[fingerprint] called add_offer_metadata(df.shape={df.shape})")
    
    # 🗓️ 1. Добавляем текущую дату числом
    df["date_int"] = int(datetime.now().strftime("%Y%m%d"))

    # 🧩 2. Получаем активного поставщика
    fsm = AlcoholStateMachine.get_active()
    if not fsm or not getattr(fsm, "name", None):
        raise RuntimeError("Нет активного AlcoholStateMachine — невозможно определить поставщика.")

    supplier = fsm.name
    if debug:
        print(f"[fingerprint] Using supplier={supplier!r}")

    # 🔢 2. Считаем отпечатки
    def offer_fingerprint(row):
        parts = [
            str(row.get("Наименование")),
            str(row.get("cl")),
            str(row.get("шт / кор")),
            str(supplier),
            str(row.get(f"цена за бутылку {supplier}", "")),
            str(row.get(f"цена за кейс {supplier}", "")),
            str(row.get(f"currency {supplier}", "")),
            str(row.get(f"Место загрузки {supplier}", "")),
            str(row.get(f"Доступ {supplier}", "")),
        ]
        canonical = "|".join(parts)
        crc32_hash = format(zlib.crc32(canonical.encode()), "08x")
        b64 = base64.b64encode(canonical.encode()).decode("ascii")
        return crc32_hash, b64

    if debug:
        print("[fingerprint] Generating crc32/b64 for each row...")

    df[["crc32_hash", "b64"]] = df.apply(
        lambda row: pd.Series(offer_fingerprint(row)), axis=1
    )

    if debug:
        unique_hashes = df["crc32_hash"].nunique()
        print(f"[fingerprint] Done. Generated {len(df)} fingerprints ({unique_hashes} unique).")

    return df
