import pandas as pd
from datetime import datetime
import logging
import numpy as np
import os
from pathlib import Path

from state_machine import AlcoholStateMachine
from utils.logger import setup_logging

# инициализируем общий логгер (один раз в рантайме)
setup_logging()
logger = logging.getLogger(__name__)

class MatrixMerger:
    """
    Матрица сопоставления офферов.
    Объединяет старую и новую таблицы, сравнивая позиции по "генетике" и отпечаткам.
    """

    def __init__(self, debug: bool = True):
        self.debug = debug
        
        self.logger = logger

    def _log(self, msg: str):
        """
        Централизованный лог: печатает и пишет в файл через logging.
        """
        if self.debug:
            self.logger.debug(msg)
        else:
            self.logger.info(msg)

    def _same_genetics(self, row_a, row_b) -> bool:
        return (
            str(row_a.get("Наименование")) == str(row_b.get("Наименование"))
            and str(row_a.get("cl")) == str(row_b.get("cl"))
            and str(row_a.get("шт / кор")) == str(row_b.get("шт / кор"))
        )

    def _is_duplicate(self, old_row, new_row) -> bool:
        if old_row.get("crc32_hash") == new_row.get("crc32_hash"):
            if old_row.get("b64") == new_row.get("b64"):
                return True
        return False

    # ──────────────────────────────
    def merge(self, old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
        # очистка старого лога (используем централизованный файл логгера)
        for h in logging.getLogger().handlers:
            if isinstance(h, logging.FileHandler):
                try:
                    open(h.baseFilename, "w", encoding="utf-8").close()
                    self._log(f"🧹 Cleared log file: {h.baseFilename}")
                except Exception as e:
                    self._log(f"[WARN] Cannot clear log file: {e}")
                break

        old = old.copy()
        self._log(f"[DEBUG] len={len(old)}, shape={old.shape}, index_valid={old.index.notna().all()}")
        self._log(f"[DEBUG] values.size={old.values.size}")
        self._log(f"[DEBUG] head:\n{old.head().to_string(index=False)}")
        new = new.copy()

        # 🧩 Получаем активного supplier из FSM
        fsm = AlcoholStateMachine.get_active()
        if not fsm or not getattr(fsm, "name", None):
            raise RuntimeError("Нет активного AlcoholStateMachine — невозможно определить supplier.")
        supplier = fsm.name.strip()
        self._log(f"Active supplier: {supplier!r}")

        today = int(datetime.now().strftime("%Y%m%d"))
        added, updated, skipped = 0, 0, 0

        base_cols = ["Тип", "Наименование", "cl", "шт / кор"]

        key_aliases = {
            "Поставщик": ["Поставщик", f"Поставщик {supplier}"],
            "цена за бутылку": ["цена за бутылку", f"цена за бутылку {supplier}"],
            "цена за кейс": ["цена за кейс", f"цена за кейс {supplier}"],
            "Валюта": ["Валюта", f"currency {supplier}"],
            "Место загрузки": ["Место загрузки", f"Место загрузки {supplier}"],
            "Доступ": ["Доступ", f"Доступ {supplier}"],
            "crc32_hash": ["crc32_hash"],
            "b64": ["b64"],
            "date_int": ["date_int"],
        }

        if old.empty:
            self._log("Old master is empty — initializing structure with key/value pairs")
            for col in base_cols:
                old[col] = None
            for i in range(1, len(key_aliases) + 1):
                old[f"ключ_{i}"] = None
                old[f"значение_{i}"] = None
            self._log(f"Initialized columns: {old.columns.tolist()}")

        self._log(f"Starting merge: {len(new)} new rows, {len(old)} old rows")
                # 🧩 двухуровневая фильтрация дубликатов по crc32_hash → b64
        if "crc32_hash" in old.columns and "crc32_hash" in new.columns:
            before = len(new)

            def is_duplicate_row(r):
                # фильтрация по crc32
                same_crc = old["crc32_hash"].astype(str) == str(r.get("crc32_hash"))
                if not same_crc.any():
                    return False
                # если есть колонка b64 — проверяем вторым уровнем
                if "b64" in old.columns and "b64" in new.columns:
                    same_b64 = old.loc[same_crc, "b64"].astype(str) == str(r.get("b64"))
                    return same_b64.any()
                return True

            # применяем построчно; axis=1 обязателен
            mask = new.apply(is_duplicate_row, axis=1)
            new = new.loc[~mask].reset_index(drop=True)

            self._log(
                f"Filtered duplicates: {before - len(new)} removed, "
                f"{len(new)} remain after crc32+b64 check"
            )
        else:
            self._log("⚠️ crc32_hash column missing — skip duplicate filtering")


        for idx, new_row in new.iterrows():
            name = new_row.get("Наименование")
            cl = new_row.get("cl")
            bpc = new_row.get("шт / кор")

            if not name or not cl or not bpc:
                self._log(f"⚠️ Skipping row {idx}: missing genetics {name=}, {cl=}, {bpc=}")
                continue

            mask = (
                (old["Наименование"] == name)
                & (old["cl"] == cl)
                & (old["шт / кор"] == bpc)
            )
            subset = old[mask]

            self._log(f"Row {idx}: genetics ({name}, {cl}, {bpc}) found {len(subset)} matches")

            def collect_pairs(row):
                pairs = []
                for key, aliases in key_aliases.items():
                    val = None
                    for alias in aliases:
                        if alias in row and pd.notna(row[alias]):
                            val = row[alias]
                            break
                    if val not in ("", None, "NaN", "nan"):
                        pairs.append(f"{key}/{val}")
                return pairs

            pairs = collect_pairs(new_row)

            if subset.empty:
                self._log(f"🆕 New product: {name} — pairs={len(pairs)}")
            else:
                self._log(f"🔁 Variant: {name} — pairs={len(pairs)}")

            row_dict = {col: new_row.get(col, "") for col in base_cols}
            for i, p in enumerate(pairs, 1):
                key, val = (p.split("/", 1) + [""])[:2]
                row_dict[f"ключ_{i}"] = key
                row_dict[f"значение_{i}"] = val
            for i in range(len(pairs) + 1, len(key_aliases) + 1):
                row_dict[f"ключ_{i}"] = None
                row_dict[f"значение_{i}"] = None

            old = pd.concat([old, pd.DataFrame([row_dict])], ignore_index=True)
            if subset.empty:
                added += 1
            else:
                updated += 1

        self._log(f"merge complete: added={added}, updated={updated}, skipped={skipped}, total={len(old)}")

        ordered = base_cols + [
            x
            for i in range(1, len(key_aliases) + 1)
            for x in (f"ключ_{i}", f"значение_{i}")
        ]
        tail = [c for c in old.columns if c not in ordered]
        df_sorted = old.reindex(columns=ordered + tail)

        sort_cols = [c for c in ["Тип", "Наименование", "cl"] if c in df_sorted.columns]
        if sort_cols:
            df_sorted = df_sorted.sort_values(by=sort_cols, ascending=[True] * len(sort_cols))
        
        # --- диагностика на inf/NaN ---
        try:
            inf_cols, nan_cols = [], []

            # логируем типы колонок для наглядности
            dtypes_info = {c: str(df_sorted[c].dtype) for c in df_sorted.columns}
            self._log(f"[DIAG] column types: {dtypes_info}")

            for c in df_sorted.columns:
                col = df_sorted[c]
                if pd.api.types.is_numeric_dtype(col):
                   if np.isinf(col.to_numpy(copy=False)).any():
                        inf_cols.append(c)
                if col.isna().any():
                    nan_cols.append(c)

            if inf_cols or nan_cols:
                self._log(f"[DIAG] detected anomalies: inf_cols={inf_cols}, nan_cols={nan_cols}")
                for col in inf_cols:
                    mask = np.isinf(df_sorted[col].to_numpy(copy=False))
                    vals = df_sorted.loc[mask, col]
                    self._log(f"[DIAG] {col}: {len(vals)} inf values → {vals.head(10).tolist()}")
            else:
                self._log("[DIAG] no inf/NaN detected before return")
        except Exception as e:
            self._log(f"[DIAG ERROR] inf check failed: {e}")

        # 🔥 финальный отчёт
        self._log("─" * 80)
        self._log(f"FINAL DATAFRAME SHAPE: {df_sorted.shape}")
        self._log(f"FINAL COLUMNS: {df_sorted.columns.tolist()}")
        self._log("HEAD (5 rows):")
        self._log(df_sorted.head().to_string(index=False))
        self._log("FULL CONTENT:")
        self._log(df_sorted.to_string(index=False))
        self._log("─" * 80)
        # показываем, куда писался лог
        for h in logging.getLogger().handlers:
            if isinstance(h, logging.FileHandler):
                self._log(f"✅ Exported to {h.baseFilename}")
                break

        return df_sorted.reset_index(drop=True)
