# verifier.py
import pandas as pd
import re

class Verifier:
    def __init__(self):
        self.rules = []
        self.messages = []

    def register(self, func):
        """Регистрирует функцию-проверку"""
        self.rules.append(func)
        return func

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """Запускает все проверки по очереди"""
        for rule in self.rules:
            try:
                df = rule(df, self.messages)
            except Exception as e:
                self.messages.append(f"[ERROR] Rule {rule.__name__} failed: {e}")
        return df

    def report(self):
        return "\n".join(self.messages) if self.messages else "[Verifier] No issues detected"


# --- конкретные правила ---
verifier = Verifier()

@verifier.register
def check_location_columns(df: pd.DataFrame, messages: list):
    """
    Проверка: колонки location не должны содержать в основном числа.
    Если более 70% значений числовые → колонка не location, а ошибка.
    """
    for col in df.columns:
        if "Место загрузки" in col or "location" in col.lower():
            non_null = df[col].dropna().astype(str)
            if not non_null.empty:
                numeric_ratio = non_null.str.replace(",", ".").str.match(r"^[0-9.]+$").mean()
                if numeric_ratio > 0.7:
                    messages.append(f"[WARN] Column {col} looks numeric ({numeric_ratio:.2%}). Clearing as non-location.")
                    df[col] = None
    return df
