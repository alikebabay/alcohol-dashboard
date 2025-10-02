import pandas as pd
from text_parser import parse_text
from name_enricher import filter_and_enrich 

class TextState:
    def __init__(self, raw_text: str):
        self.raw_text = raw_text
        self.df_raw: pd.DataFrame | None = None
        self.df_final: pd.DataFrame | None = None
        self.mapping = {}

    def run(self) -> pd.DataFrame:
        # 1. сырой текст → DataFrame с уже разобранными колонками
        self.df_raw, self.mapping = parse_text(self.raw_text)
        print(f"[DEBUG TextState] df_raw shape={self.df_raw.shape}")
        print(f"[DEBUG TextState] preview:\n{self.df_raw.head()}")

        # 2. общий пайплайн (тот же, что для Excel)
        self.df_final = filter_and_enrich(self.df_raw, col_name="name")
        print(f"[DEBUG TextState] df_final shape={self.df_final.shape}")

        return self.df_final

    def get_final(self) -> pd.DataFrame:
        if self.df_final is None:
            raise RuntimeError("Call run() before get_final()")
        return self.df_final
