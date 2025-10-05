# verifier.py
import pandas as pd

from integrations.rules_typing import enforce_base_types

class Verifier:
    def __init__(self):
        # правила разделены по состояниям
        self.rules_by_state = {
            "logic": [],
            "typing": [],
        }
        self.messages = []
        self.state = "logic"  # состояние по умолчанию

    def register(self, func=None, *, state="logic"):
        """
        Регистрирует функцию-проверку.
        Можно указать состояние: state="logic" или "typing".
        """
        def decorator(f):
            self.rules_by_state.setdefault(state, []).append(f)
            return f
        return decorator(func) if func else decorator
    
    def set_state(self, new_state: str):
        """Переключает текущее состояние верифаера"""
        if new_state not in self.rules_by_state:
            self.rules_by_state[new_state] = []
        self.state = new_state
        self.messages.append(f"[STATE] Switched to: {new_state}")

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """Запускает проверки текущего состояния"""
        rules = self.rules_by_state.get(self.state, [])
        self.messages.append(f"[RUN] Executing {len(rules)} rule(s) for state '{self.state}'")

        for rule in rules:
            try:
                df = rule(df, self.messages)
            except Exception as e:
                self.messages.append(f"[ERROR] Rule {rule.__name__} failed: {e}")
        return df

    def report(self):
        return "\n".join(self.messages) if self.messages else "[Verifier] No issues detected"
    
    def reset(self):
        """Полный сброс состояния верифаера."""
        self.messages.clear()
        self.state = "logic"
        print("[Verifier] состояние сброшено → logic")


# --- создаём верифаер ---
verifier = Verifier()

# --- правила логического состояния ---
@verifier.register(state="logic")
def check_location_columns(df: pd.DataFrame, messages: list):
    """Проверка: колонка location не должна быть числовой"""
    for col in df.columns:
        if "Место загрузки" in col or "location" in col.lower():
            non_null = df[col].dropna().astype(str)
            if not non_null.empty:
                numeric_ratio = non_null.str.replace(",", ".").str.match(r"^[0-9.]+$").mean()
                if numeric_ratio > 0.7:
                    messages.append(f"[WARN] {col} looks numeric ({numeric_ratio:.2%}). Clearing.")
                    df[col] = None
    return df


# --- правило для типизационного состояния ---
@verifier.register(state="typing")
def enforce_types(df: pd.DataFrame, messages: list):
    """Применяет типизацию (вызывается в отдельном состоянии)"""
    return enforce_base_types(df, messages)