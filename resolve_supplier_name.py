from pathlib import Path

def resolve_supplier_name(file_name: str | None, supplier_choice: str | None) -> str:
    """
    Определяет имя поставщика:
    1. Если выбран из списка (кнопка) → берём его.
    2. Если "Из файла" или None → берём stem(file_name).
    3. Если файла нет, но есть текст → возвращаем "manual".
    4. В остальных случаях → берём то, что передано.
    """
    match supplier_choice:
        case "Поставщик 1" | "Поставщик 2" | "Поставщик 3":
            return supplier_choice
        case "Из файла" | None:
            if file_name:
                return Path(file_name).stem or "unknown"
            return "manual"
        case _:
            return supplier_choice or "unknown"
