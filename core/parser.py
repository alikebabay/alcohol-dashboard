#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

# parser.py
from io import BytesIO
import pandas as pd
import re
import logging
from collections import Counter

from utils.logger import setup_logging
from libraries.patterns import PATS

logger = logging.getLogger("core.parser")


def parse_excel(src: BytesIO):
    # -------------------------------------------------------------
    # 🚀 Новый FSM-парсер: четыре состояния
    # 1) LOAD_SHEETS
    # 2) DETECT_HEADER_TYPE
    # 3) PARSE_SINGLE_HEADER  (если 1-я строка полноценная)
    # 4) PARSE_DOUBLE_HEADER  (если header вертикальный)
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    #  SEMANTIC HEADER DETECTION
    # -------------------------------------------------------------
    # --- helper: строка похожа на header? ---
    
    def _semantic_hits(row: list[str]) -> dict:
        """Проверяем обязательные паттерны для однострочного хэдера."""
        cells = [str(x or "").strip().lower() for x in row]
        def hit(patterns):
            return any(re.search(p, c) for c in cells for p in patterns)
        return {
            "price_case": hit(PATS.PRICE_CASE)
        }

    REQUIRED_KEYS = ("price_case")


    class ExcelParserFSM:
        def __init__(self, src_bytes):
            self.src = src_bytes
            self.sheets = None
            self.frames = []
            self.mappings = {}
            self.sheet_name = None
            self.raw = None
            self.header_row = None            
            self.header_type = None  # "single" / "double"
            self.state = "LOAD_SHEETS"
            self.headers_fixed = None   # храним хэдер с добавленным name
            self.detected_name_col = None      # индекс колонки с брендом
            self.detected_name_row = None    # индекс ряда с брендом
            self.detected_name_sample = None   # само значение первой найденной name-like (брендовой) ячейки
            

       # --------------------------
        def run(self):
            while self.state:
                method = getattr(self, f"state_{self.state}")
                self.state = method()
            return self.frames, self.mappings

        # --------------------------
        def state_LOAD_SHEETS(self):
            logger.debug("=== FSM: LOAD_SHEETS ===")
            self.sheets = pd.read_excel(
               self.src, sheet_name=None, header=None, engine="openpyxl", dtype=str
            )
            logger.debug(f"Найдено листов: {len(self.sheets)} → {list(self.sheets.keys())}")
            return "DETECT_HEADER_TYPE"

        # --------------------------
        def state_DETECT_HEADER_TYPE(self):
            for name, raw in self.sheets.items():
                self.sheet_name = name
                self.raw = raw
                logger.debug(f"--- FSM: Обработка листа: {name} ---")
                # ------------------------------------------------------------
                # 🔍 NEW HEADER & DATA ROW DETECTION (correct structural logic)
                # ------------------------------------------------------------

                def _is_numeric_strict(v):
                    s = str(v).strip().lower()
                    # 🔥 Critical fix: these must NOT count as numeric
                    if s in ("", "nan", "none", "null", "-", "--"):
                        return False
                    try:
                        float(s)
                        return True
                    except:
                        return False
                    
                #  Skip preamble / titles like "Connexion ... Offer"
                def is_noise_row(vals):
                    strs = [v for v in vals if v and not _is_numeric_strict(v)]
                    nums = [v for v in vals if _is_numeric_strict(v)]
                    # one long string, no numbers → garbage title row
                    return (len(strs) == 1 and len(nums) == 0)

                #detect header row
                def is_header_row(vals):
                    string_cells = 0
                    numeric_cells = 0

                    for v in vals:
                        v = str(v).strip().lower()

                        if v in ("", "nan", "none", "null", "-"):
                            continue  # <- FIX: don't count as string

                        if _is_numeric_strict(v):
                            numeric_cells += 1
                        else:
                            string_cells += 1

                    return numeric_cells == 0 and string_cells >= 4

                #detect data row
                def is_data_row(vals):
                    numeric_cells = 0
                    non_empty = 0

                    for v in vals:
                        v = str(v).strip()
                        if v:
                            non_empty += 1
                        if _is_numeric_strict(v):
                            numeric_cells += 1

                    return numeric_cells >= 1 and non_empty >= 3

                header_rows = []
                
                first_data_row = None
                logger.debug(
                        f"[HEADER-DETECT] header_rows={header_rows}, "
                        f"header_row={self.header_row}, first_data_row={first_data_row}"
                    )

                for idx, row in raw.iterrows():
                    vals = [
                        "" if (x is None or (isinstance(x, float) and pd.isna(x))) else str(x).strip()
                        for x in row.tolist()
                    ]
                    logger.debug(f"[ROW RAW] idx={idx} | {row.tolist()}")
                    logger.debug(f"[ROW CLEAN] idx={idx} | {vals}")
                    logger.debug(f"[ROW NONEMPTY COUNT] {sum(1 for v in vals if v)}")
                    logger.debug(f"[ROW STRING COUNT] {sum(1 for v in vals if v and not _is_numeric_strict(v))}")
                    logger.debug(f"[ROW NUMERIC COUNT] {sum(1 for v in vals if _is_numeric_strict(v))}")
                    # 🔥 Skip noisy rows BEFORE header/data logic
                    if is_noise_row(vals):
                        logger.debug(f"[ROW SKIP] idx={idx} classified as noise/preamble")
                        continue

                    if is_header_row(vals):
                        header_rows.append(idx)
                        continue

                    if is_data_row(vals):
                        first_data_row = idx
                        break

                if first_data_row is None:
                    logger.debug(f"{self.sheet_name}: SKIP — no data rows found")
                    continue

                # 🔥 TRUE HEADER ROW = LAST string-only row before data
                self.header_row = header_rows[-1] if header_rows else 0
                logger.debug(
                    f"[HEADER-DETECT] header_rows={header_rows}, "
                    f"header_row={self.header_row}, first_data_row={first_data_row}"
                )

                logger.debug(
                    f"[HEADER-DETECT] header_rows={header_rows}, "
                    f"header_row={self.header_row}, first_data_row={first_data_row}"
                )
                # 🔍 PREVIEW DETECTED HEADER ROW
                header_raw = self.raw.iloc[self.header_row].tolist()
                header_clean = (
                    self.raw.iloc[self.header_row]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .tolist()
                )

                logger.debug(f"[HEADER PREVIEW RAW]   idx={self.header_row} | {header_raw}")
                logger.debug(f"[HEADER PREVIEW CLEAN] idx={self.header_row} | {header_clean}")


                # --- ПРОСТАЯ ЛОГИКА ОПРЕДЕЛЕНИЯ TYPE ---
                r0 = raw.iloc[self.header_row].fillna("").astype(str).tolist()
            
                # ----------------------------------------------------
                # 🔍 Находим колонку с наименованиями алкоголя
                # ----------------------------------------------------
                r0 = raw.iloc[self.header_row].fillna("").astype(str).tolist()
                clean_r0 = [str(h or "").strip().lower() for h in r0]

                # Если в хэдере уже есть name — ничего не делаем
                has_name = any(any(re.search(p, h) for p in PATS.NAME) for h in clean_r0)

                # NEW: Structural NAME column detection (simple + robust)
                if not has_name:
                    for c in raw.columns:
                        vals = raw[c].astype(str).fillna("").tolist()

                        # skip header cell if it already has text
                        if r0[c].strip():
                            continue

                        # must NOT contain numeric anywhere
                        if any(_is_numeric_strict(v) for v in vals[1:]):
                            continue

                        # collect non-empty strings
                        non_empty = [v.strip() for v in vals if v.strip()]
                        if len(non_empty) < 3:
                            continue

                        # frequency analysis
                        
                        cnt = Counter(non_empty)
                        most_common = cnt.most_common(1)[0][1]
                        total = len(non_empty)
                        freq = most_common / total  # dominant repetition share

                        # YOUR RULE:
                        # if ≥10% identical → NOT name
                        if freq >= 0.10:
                            continue

                        # Also: must have at least 3 different products
                        if len(cnt) < 3:
                            continue

                        # FOUND NAME COLUMN
                        r0[c] = "name"
                        has_name = True
                        logger.debug(
                            f"[HEADER_FIX][NAME] selected column={c} | unique={len(cnt)} | freq={freq:.3f}"
                        )
                        break


                # Если после этого name всё ещё нет → пропускаем лист (страховка)
                if not has_name:
                    logger.debug(f"{self.sheet_name}: SKIP — header still has no NAME")
                    continue

                self.headers_fixed = r0
                logger.debug(f"{self.sheet_name}: FIXED r0 = {self.headers_fixed}")                

                # ------------------------------------------------------------
                # 🔍 NEW HEADER TYPE DETECTION (single vs double)
                # ------------------------------------------------------------
                # if previous row is string-only → this is a double header
                if self.header_row > 0:
                    prev = raw.iloc[self.header_row - 1].astype(str).fillna("").tolist()
                    prev_has_numbers = any(_is_numeric_strict(v) for v in prev)
                    if not prev_has_numbers:      # previous row is string-only
                        self.header_type = "double"
                    else:
                        self.header_type = "single"
                else:
                    self.header_type = "single"

                logger.debug(f"{name}: header_type={self.header_type}")

                # дальше пошло состояние parse
                if len(header_rows) == 1:
                    self._parse_single_header(self.headers_fixed)
                else:
                    self._parse_double_header(header_rows)


            return "FINISH"

        # --------------------------
        def _parse_single_header(self, headers_fixed):
            raw = self.raw
            hr = self.header_row

            headers = list(headers_fixed)   # <-- используем уже фиксированный header

            # Данные
            df = raw.iloc[hr + 1 :].copy()
            df.columns = headers
            df.dropna(how="all", inplace=True)
            df = df.loc[:, df.notna().any(axis=0)]
            df.reset_index(drop=True, inplace=True)

            self.frames.append(df)
            self.mappings[self.sheet_name] = {"columns": list(df.columns), "header_row": hr}

        # --------------------------
        def _parse_double_header(self, header_rows):
            """
            Merge all detected header rows into a single header by vertical concatenation.
            """
            raw = self.raw

            # collect header rows in VISUAL top→bottom order
            header_rows_sorted = sorted(header_rows)

            rows = []
            for r in header_rows_sorted:
                if r == self.header_row:
                    # use FIXED header row ("name", etc.)
                    rows.append(list(self.headers_fixed))
                else:
                    rows.append(
                        raw.iloc[r].fillna("").astype(str).str.strip().tolist()
                    )

            # --- vertical merge preserving top→bottom order ---
            num_cols = len(rows[0])
            merged = []

            for col_idx in range(num_cols):
                parts = []
                for row in rows:
                    val = re.sub(r"\s+", " ", row[col_idx]).strip()            
                    if val:
                        parts.append(val)
                merged.append(" ".join(parts))

            logger.debug(f"[HEADER MERGED] cols={num_cols} | {merged}")

            # data begins AFTER the last header row
            data_start = header_rows_sorted[-1] + 1

            df = raw.iloc[data_start:].copy()
            df.columns = merged
            df.dropna(how="all", inplace=True)
            df = df.loc[:, df.notna().any(axis=0)]
            df.reset_index(drop=True, inplace=True)

            self.frames.append(df)
            self.mappings[self.sheet_name] = {
                "columns": list(df.columns),
                "header_row": header_rows
            }

        def state_FINISH(self):
            return None

    # -------------------------------------------------------------
    # 🚀 Запуск FSM
    # -------------------------------------------------------------
    frames, mappings = ExcelParserFSM(src).run()

    if frames:
        df_all = pd.concat(frames, ignore_index=True)
        # 🔐 стабильная идентичность строки
        df_all["raw_idx"] = df_all.index

        logger.debug(f"[RAW_IDX] created raw_idx 0..{len(df_all)-1}")

        with pd.option_context("display.max_columns", None, "display.width", 1000):
            logger.debug(
                f"=== ИТОГОВАЯ ТАБЛИЦА (HEAD 15) ===\n{df_all.head(15).to_string(index=True)}"
            )
    else:
        logger.warning("Не найдено ни одного листа с данными")
        df_all = pd.DataFrame()

    return df_all, mappings