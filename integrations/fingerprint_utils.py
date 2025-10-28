import base64
import zlib
from datetime import datetime
import pandas as pd
import logging

from state_machine import AlcoholStateMachine  # 🧩 чтобы тянуть активный supplier
from utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

def add_offer_metadata(df: pd.DataFrame, debug: bool = True) -> pd.DataFrame:
    """Добавляет дату и отпечатки (crc32_hash, b64) для каждой строки DataFrame."""

    logger.debug(f"[fingerprint] called add_offer_metadata(df.shape={df.shape})")
    
    # 🗓️ 1. Добавляем текущую дату числом
    df["date_int"] = int(datetime.now().strftime("%Y%m%d"))

    # 🧩 2. Получаем активного поставщика
    fsm = AlcoholStateMachine.get_active()
    if not fsm or not getattr(fsm, "name", None):
        raise RuntimeError("Нет активного AlcoholStateMachine — невозможно определить поставщика.")

    supplier = fsm.name
    logger.debug(f"[fingerprint] supplier={supplier!r}")

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

    logger.debug("[fingerprint] generating crc32/b64 for each row...")

    df[["crc32_hash", "b64"]] = df.apply(
        lambda row: pd.Series(offer_fingerprint(row)), axis=1
    )

    unique_hashes = df["crc32_hash"].nunique()
    logger.info(f"[fingerprint] ✅ done: {len(df)} fingerprints ({unique_hashes} unique)")

    return df
