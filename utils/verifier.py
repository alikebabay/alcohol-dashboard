# verifier.py
import pandas as pd
import logging
import uuid

from integrations.rules_typing import enforce_base_types
from core.graph_normalizer import normalize_dataframe

logger = logging.getLogger(__name__)
VERBOSE_STATE_LOG = False
# ───────────────────────────────────────────────
# 💬 Класс буфера сообщений с управляемым verbose
# ───────────────────────────────────────────────
class MessageBuffer(list):
    """Список сообщений, которые добавляются только если включён verbose."""
    def __init__(self, verbose: bool):
        super().__init__()
        self.verbose = verbose

    def append(self, msg):
        if self.verbose:
            super().append(msg)

    def always(self, msg):
        super().append(msg)

class Verifier:
    def __init__(self):
        # правила разделены по состояниям
        self.rules_by_state = {
            "graph": [],
            "logic": [],
            "typing": [],
            
        }
        self.messages = MessageBuffer(verbose=VERBOSE_STATE_LOG)
        self.state = "logic"  # состояние по умолчанию
        self._graph_runs = 0  # сколько раз отработало состояние graph за текущий пайплайн
        self._graph_executed = False  # ✅ флаг: уже отработал ли граф

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
        """Запускает проверки текущего состояния или указанного явно через аргумент state"""
        target_state = getattr(self, "_explicit_state", None) or self.state
        rules = self.rules_by_state.get(self.state, [])
        # ✅ защита: граф запускается только 1 раз за пайплайн
        if target_state == "graph":
            if self._graph_executed:
                self.messages.append("[GRAPH] skipped (already executed once)")
                return df
            self._graph_executed = True

        self.messages.append(f"[RUN] Executing {len(rules)} rule(s) for state '{target_state}'")
        for rule in rules:
            try:
                df = rule(df, self.messages)
            except Exception as e:
                self.messages.append(f"[ERROR] Rule {rule.__name__} failed: {e}")
        if hasattr(self, "_explicit_state"):
            delattr(self, "_explicit_state")
        return df

    def run_state(self, df: pd.DataFrame, state: str) -> pd.DataFrame:
        """Одноразово запускает проверки для заданного состояния без смены self.state."""
        self._explicit_state = state
        return self.run(df)


    def report(self):
        return "\n".join(self.messages) if self.messages else "[Verifier] No issues detected"
    
    def reset(self):
        """Полный сброс состояния верифаера."""
        self.messages.clear()
        self.state = "logic"
        self._graph_runs = 0
        self._graph_executed = False  # ✅ сброс флага
        print("[Verifier] состояние сброшено → logic")


# --- создаём верифаер ---
verifier = Verifier()


# --- правило для графового состояния ---
@verifier.register(state="graph")
def verify_graph_canonical(df: pd.DataFrame, messages: list):
    """Маппим name → canonical_name через Neo4j, заменяя в той же колонке."""
    run_id = uuid.uuid4().hex[:6]
    messages.append(f"[GRAPH] START verify_graph_canonical run_id={run_id}")

    if "name" not in df.columns:
        messages.append("[GRAPH] No 'name' column. Skipped.")
        return df

    try:
        
        # просто обновляем колонку 'name' внутри того же df
        normalize_dataframe(df, col_name="name")
        messages.append(f"[GRAPH] canonical_name replaced in column 'name' (in-place).")
    except Exception as e:
        messages.append(f"[ERROR] normalize_dataframe failed: {e}")
    
    return df


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
                    
        # --- очистка значений колонки cl ---
        if col.lower() == "cl":
            before = df[col].copy()
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"(?i)\s*cl\b", "", regex=True)
                .str.replace(r"(?i)\s*мл\b", "", regex=True)
                .str.strip()
            )
            diff_count = (before != df[col]).sum()
            if diff_count > 0:
                messages.append(f"[INFO] cleaned {diff_count} values in column '{col}' (removed 'cl'/'мл').")

    return df

# --- правило восстановления цен и согласования логики ---
@verifier.register(state="logic")
def verify_logic(df: pd.DataFrame, messages: list):
    """Проверка согласованности числовых полей и восстановление пропущенных значений."""
    df = df.copy()
    messages.append(f"[VERIFY] started, rows={len(df)}")

    df["bottles_per_case"] = pd.to_numeric(df.get("bottles_per_case"), errors="coerce")
    df["price_per_case"] = pd.to_numeric(df.get("price_per_case"), errors="coerce")
    df["price_per_bottle"] = pd.to_numeric(df.get("price_per_bottle"), errors="coerce")

    cond = df["bottles_per_case"].notna() & df["price_per_case"].notna() & df["price_per_bottle"].isna()
    if cond.any():
        df.loc[cond, "price_per_bottle"] = (df.loc[cond, "price_per_case"] / df.loc[cond, "bottles_per_case"]).round(4)
        messages.append(f"[VERIFY] recalculated price_per_bottle for {cond.sum()} rows")

    cond = df["bottles_per_case"].notna() & df["price_per_bottle"].notna() & df["price_per_case"].isna()
    if cond.any():
        df.loc[cond, "price_per_case"] = (df.loc[cond, "price_per_bottle"] * df.loc[cond, "bottles_per_case"]).round(4)
        messages.append(f"[VERIFY] recalculated price_per_case for {cond.sum()} rows")

    cond = (
        df["bottles_per_case"].notna()
        & df["price_per_case"].notna()
        & df["price_per_bottle"].notna()
    )
    if cond.any():
        diff = (df.loc[cond, "price_per_case"] / df.loc[cond, "bottles_per_case"]) - df.loc[cond, "price_per_bottle"]
        mismatches = (diff.abs() > 0.01).sum()
        if mismatches:
            messages.append(f"[VERIFY] warning: {mismatches} inconsistent rows (case vs bottle mismatch >0.01)")

    messages.append(
        f"[VERIFY] done, non-null price_case={df['price_per_case'].notna().sum()}, "
        f"price_bottle={df['price_per_bottle'].notna().sum()}"
    )
    return df


# --- правило для типизационного состояния ---
@verifier.register(state="typing")
def enforce_types(df: pd.DataFrame, *args):
    """Применяет типизацию (вызывается в отдельном состоянии)"""
    return enforce_base_types(df)
