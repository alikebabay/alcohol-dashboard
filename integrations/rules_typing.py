import pandas as pd

def enforce_base_types(df: pd.DataFrame, messages: list) -> pd.DataFrame:
    df = df.copy()

    # --- базовые типы ---
    base_types = {
        "Тип": "string",
        "Наименование": "string",
        "cl": "string",
        "шт / кор": "Int64",
    }

    # --- динамические колонки по поставщикам ---
    float_cols = [c for c in df.columns if c.startswith("цена за бутылку") or c.startswith("цена за кейс")]
    str_cols   = [c for c in df.columns if c.startswith("Доступ") or c.startswith("Место загрузки")]

    # применяем базовые типы
    for col, dtype in base_types.items():
        if col in df.columns:
            try:
                if dtype == "Int64":
                    df[col] = (
                        df[col]
                        .replace("", pd.NA)
                        .replace(" ", pd.NA)
                        .replace("-", pd.NA)
                        .pipe(pd.to_numeric, errors="coerce")
                        .astype("Int64")
                    )
                else:
                    df[col] = df[col].astype("string")
            except Exception as e:
                messages.append(f"[WARN] {col}: cannot convert to {dtype} ({e})")

    # цена = float
    for col in float_cols:
        try:
            df[col] = (
                df[col]
                .replace("", pd.NA)
                .replace(" ", pd.NA)
                .pipe(pd.to_numeric, errors="coerce")
                .astype("float64")
            )
        except Exception as e:
            messages.append(f"[WARN] {col}: cannot convert to float ({e})")

    # доступ/место = string
    for col in str_cols:
        try:
            df[col] = df[col].astype("string")
        except Exception as e:
            messages.append(f"[WARN] {col}: cannot convert to string ({e})")

    dtype_groups = {
    "float": [c for c, t in df.dtypes.items() if "float" in str(t)],
    "int":   [c for c, t in df.dtypes.items() if "int" in str(t)],
    "str":   [c for c, t in df.dtypes.items() if "string" in str(t) or "object" in str(t)],
}

    messages.append(
        f"[TYPE] enforced: float→{dtype_groups['float']}, int→{dtype_groups['int']}, str→{dtype_groups['str']}"
    )
