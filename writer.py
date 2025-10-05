
from __future__ import annotations
import pandas as pd
from utils.verifier import verifier

# --- создание матрицы ------------------------------------------------------------

def merge_with_master(old: pd.DataFrame, new: pd.DataFrame, supplier: str) -> pd.DataFrame:
    """
    Ключ: Наименование + шт / кор.
    Обновляем/добавляем поля поставщика:
      цена за бутылку {supplier}, цена за кейс {supplier} (если есть), Доступ {supplier}, Место загрузки {supplier}.
    """
    # 0) гарантируем наличие нужных колонок поставщика
    need_cols = [
        f"цена за бутылку {supplier}",
        f"Доступ {supplier}",
        f"Место загрузки {supplier}",
        f"цена за кейс {supplier}",
    ]
    for c in need_cols:
        if c not in old.columns:
            old[c] = None

    for _, row in new.iterrows():
        name = row.get("Наименование")
        bpc  = row.get("шт / кор")

        price_bottle = row.get(f"цена за бутылку {supplier}") or row.get("price_per_bottle")
        price_case   = row.get(f"цена за кейс {supplier}")   or row.get("price_per_case")
        access       = row.get(f"Доступ {supplier}")         or row.get("Доступ")   or row.get("access")
        location     = row.get(f"Место загрузки {supplier}") or row.get("Место загрузки") or row.get("location")

        if name is None or bpc is None:
            continue  # защитимся от мусорных строк

        mask = (old["Наименование"] == name) & (old["шт / кор"] == bpc)

        if mask.any():
            # обновляем только если реально изменилось
            if price_case is not None:
                col = f"цена за кейс {supplier}"
                if pd.isna(old.loc[mask, col]).all() or not (old.loc[mask, col] == price_case).all():
                    old.loc[mask, col] = price_case

            if price_bottle is not None:
                col = f"цена за бутылку {supplier}"
                if pd.isna(old.loc[mask, col]).all() or not (old.loc[mask, col] == price_bottle).all():
                    old.loc[mask, col] = price_bottle

            if access not in (None, ""):
                col = f"Доступ {supplier}"
                if pd.isna(old.loc[mask, col]).all() or not (old.loc[mask, col].astype(str) == str(access)).all():
                    old.loc[mask, col] = access

            if location not in (None, ""):
                col = f"Место загрузки {supplier}"
                if pd.isna(old.loc[mask, col]).all() or not (old.loc[mask, col].astype(str) == str(location)).all():
                    old.loc[mask, col] = location

        else:
            # новой строки нет → создаём
            new_row = {
                "Тип": row.get("Тип", ""),
                "Наименование": name,
                "cl": row.get("cl", ""),
                "шт / кор": bpc,
                f"цена за бутылку {supplier}": price_bottle,
                f"цена за кейс {supplier}": price_case,
                f"Доступ {supplier}": access,
                f"Место загрузки {supplier}": location,
            }
            # добьём отсутствующие базовые колонки, если вдруг нет
            for base in ["Тип", "Наименование", "cl", "шт / кор"]:
                new_row.setdefault(base, "")
            old = pd.concat([old, pd.DataFrame([new_row])], ignore_index=True)

    
    # базовые → для каждого поставщика: цена/Доступ/Место загрузки
    base_cols = ["Тип", "Наименование", "cl", "шт / кор"]
    suppliers = sorted({
        c.replace("цена за бутылку ", "")
        for c in old.columns if c.startswith("цена за бутылку ")
    })
    ordered = base_cols[:]
    for s in suppliers:
        ordered += [f"цена за бутылку {s}", f"Доступ {s}", f"Место загрузки {s}", f"цена за кейс {s}"]
    # добрособираем хвост
    tail = [c for c in old.columns if c not in ordered]
    old = old.reindex(columns=ordered + tail)
    return old



# --- сохранение ------------------------------------------------------------

def save_to_excel(df: pd.DataFrame, supplier: str) -> pd.DataFrame:
    """
    Фиксируем базовые колонки товара, а цены/доступ/место — в колонках конкретного поставщика.
    Формат:
      Тип | Наименование | cl | шт / кор |
      цена за бутылку {supplier} | Доступ {supplier} | Место загрузки {supplier}
    """
    # 1) базовые маппинги товара
    column_map = {
        "name": "Наименование",
        "bottles_per_case": "шт / кор",
        "cl": "cl",
        "Тип": "Тип",
    }

    base_cols = ["Тип", "Наименование", "cl", "шт / кор"]
    df_out = pd.DataFrame(index=range(len(df)), columns=base_cols)

    for raw_col, target_col in column_map.items():
        if raw_col in df.columns:
            df_out[target_col] = df[raw_col]

    # 2) поставщик-специфичные колонки
    col_price_bottle = f"цена за бутылку {supplier}"
    col_price_case   = f"цена за кейс {supplier}"
    col_access       = f"Доступ {supplier}"
    col_location     = f"Место загрузки {supplier}"

    # цена за бутылку (из нормализатора)
    if "price_per_bottle" in df.columns:
        df_out[col_price_bottle] = df["price_per_bottle"]

    # цена за кейс (если вдруг уже есть в df)
    if "price_per_case" in df.columns:
        df_out[col_price_case] = df["price_per_case"]

    # доступ и место загрузки: принимаем и en/ru варианты источников
    access_src   = df.get("Доступ", df.get("access"))
    location_src = df.get("Место загрузки", df.get("location"))

    if access_src is not None:
        df_out[col_access] = access_src
    if location_src is not None:
        df_out[col_location] = location_src

    # 3) минимальная чистка
    return df_out.fillna("")




