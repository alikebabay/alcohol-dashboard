# local_runner.py

from text_state import TextState
from organizer import attach_categories, order_by_category
from writer import save_to_excel

def test_text_pipeline(raw_text: str, supplier_name: str = "TextSupplier"):
    # 1. Получаем df_distilled через TextState
    ts = TextState(raw_text)
    df_distilled = ts.run()
    print("\n[STEP 1] df_distilled:")
    print(df_distilled)

    # 2. Категоризация
    df_distilled = attach_categories(df_distilled, name_col="name", out_col="Тип")
    print("\n[STEP 2] after attach_categories:")
    print(df_distilled)

    # 3. Порядок категорий
    df_distilled = order_by_category(df_distilled, category_col="Тип")
    print("\n[STEP 3] after order_by_category:")
    print(df_distilled)

    # 4. Сохранение в Excel
    df_out = save_to_excel(df_distilled, supplier_name)
    print("\n[STEP 4] df_out saved:")
    print(df_out)

    return df_out


if __name__ == "__main__":
    raw = "FTL. Glenfiddich 15YO GBX 6x70clx40% @ Euro 28.75 per bottle, T2, 2 weeks"
    final_df = test_text_pipeline(raw)
    print("\n[FINAL RESULT]:")
    print(final_df)
