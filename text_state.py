import pandas as pd
import logging

from core.text_parser import parse_text
from core.name_enricher import filter_and_enrich
from core.normalizer import normalize_alcohol_df
from utils.verifier import verifier
from utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class TextState:
    def __init__(self, raw_text: str):
        self.raw_text = raw_text
        self.df_raw: pd.DataFrame | None = None
        self.df_distilled: pd.DataFrame | None = None
        self.mapping = {}

    def run(self) -> pd.DataFrame:
        # 1. сырой текст → DataFrame с уже разобранными колонками
        self.df_raw, self.mapping = parse_text(self.raw_text)
        logger.debug(
            "[TextState] parse_text mapping keys=%s",
            list(self.mapping.keys()) if self.mapping else []
        )

        if "noprice_lines" in self.mapping:
            logger.debug(
                "[TextState] noprice_lines=%d",
                len(self.mapping.get("noprice_lines") or [])
            )        

        #2. Нормализация и очистка данных
        self.df_norm, _ = normalize_alcohol_df(self.df_raw)

        #3. фильтрация и обогащение (этап df_distilled)
        
        self.df_distilled = filter_and_enrich(
            self.df_norm,
            col_name="name",
            df_raw=self.df_raw )
       

        verifier.reset()  # сброс состояния дл логики
        logger.debug("[TextState] verifier.reset() после enrich — пайплайн завершён")
        
        return self.df_distilled

    def get_distilled(self) -> pd.DataFrame:
        if self.df_distilled is None:
            raise RuntimeError("Call run() before get_distilled()")
        return self.df_distilled
