import pandas as pd
from core.text_parser import parse_text
from core.name_enricher import filter_and_enrich
from core.normalizer import normalize_alcohol_df
from utils.verifier import verifier


class TextState:
    def __init__(self, raw_text: str):
        self.raw_text = raw_text
        self.df_raw: pd.DataFrame | None = None
        self.df_distilled: pd.DataFrame | None = None
        self.mapping = {}

    def run(self) -> pd.DataFrame:
        # 1. сырой текст → DataFrame с уже разобранными колонками
        self.df_raw, self.mapping = parse_text(self.raw_text)
        

        #2. Нормализация и очистка данных
        self.df_norm, _ = normalize_alcohol_df(self.df_raw)

        #3. фильтрация и обогащение (этап df_distilled)
        #debug code
        print(f"[DEBUG] df_norm.shape={self.df_norm.shape}")
        print(self.df_norm.head(3))
        #debug code
        self.df_distilled = filter_and_enrich(self.df_norm, col_name="name")
        #debug code
        print(f"[DEBUG] df_distilled={type(self.df_distilled)}, shape={getattr(self.df_distilled, 'shape', None)}")
        #debug code

        verifier.reset()  # сброс состояния дл логики
        print("[TextState] verifier.reset() после enrich — пайплайн завершён")
        
        return self.df_distilled

    def get_distilled(self) -> pd.DataFrame:
        if self.df_distilled is None:
            raise RuntimeError("Call run() before get_distilled()")
        return self.df_distilled
