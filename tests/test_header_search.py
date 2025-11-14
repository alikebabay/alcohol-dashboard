import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import sys, os, traceback
from io import BytesIO, StringIO
from pathlib import Path
import pandas as pd

# make sure core package is visible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core import parser  # ✅ we keep this import intact


def _sanitize_headers(row, ncols):
    """Local shim to prevent Pandas mismatch without touching parser code."""
    headers = []
    for i, val in enumerate(row):
        if pd.isna(val):
            headers.append(f"col_{i}")
        else:
            headers.append(str(val).strip())
    # pad if needed (safety)
    while len(headers) < ncols:
        headers.append(f"col_pad_{len(headers)}")
    return headers


def test_header_trace():
    base = Path("/home/alikebabay/Projects/alcohol-dashboard")
    src = base / "test_documents/Connexion Offer List Week 38 -2025.xlsx"
    out = base / "processed/Connexion_trace.txt"
    out.parent.mkdir(parents=True, exist_ok=True)

    buf = StringIO()
    buf.write(f"=== HEADER TRACE ===\nInput: {src}\n\n")

    try:
        # --- Step 1: inspect sheet manually ---
        sheets = pd.read_excel(src, sheet_name=None, header=None, dtype=str, engine="openpyxl")

        for name, raw in sheets.items():
            buf.write(f"\n--- Sheet: {name} ---\n")
            buf.write(f"Shape: {raw.shape[0]} × {raw.shape[1]}\n")
            filled = raw.notna().sum(axis=1)
            header_row = None
            for i, c in filled.items():
                if c >= 4:
                    header_row = i
                    break
            buf.write(f"Candidate header_row={header_row}\n")
            # --- deep analysis of the actual header row ---
            row = raw.iloc[header_row]

            buf.write("\n=== HEADER ROW DEEP ANALYSIS ===\n")
            buf.write(f"Total cells: {len(row)}\n")

            for i, val in enumerate(row):
                typ = type(val).__name__
                is_nan = pd.isna(val)
                buf.write(f"[{i:02d}] {repr(val):<50}  type={typ:<10}  is_nan={is_nan}\n")
            buf.write("\n")


            # sanitize headers here without modifying parser
            headers = _sanitize_headers(raw.iloc[header_row], raw.shape[1])
            buf.write(f"Sanitized header ({len(headers)}): {headers}\n")

        # --- Step 2: call original parser (unmodified) ---
        with open(src, "rb") as f:
            data = BytesIO(f.read())
        df, mapping = parser.parse_excel(data)

        buf.write("\n=== PARSE RESULT ===\n")
        buf.write(f"df shape: {df.shape}\n")
        for s, m in mapping.items():
            buf.write(f"{s}: header_row={m['header_row']}, columns={m['columns']}\n")
        buf.write(f"\nHEAD(5):\n{df.head().to_string(index=False)}\n")

    except Exception as e:
        buf.write("\n💥 EXCEPTION OCCURRED 💥\n")
        buf.write(f"{type(e).__name__}: {e}\n")
        buf.write("TRACEBACK:\n")
        buf.write("".join(traceback.format_exc()))

    out.write_text(buf.getvalue(), encoding="utf-8")
    print(buf.getvalue())
    print(f"\n✅ Saved trace to {out}")


if __name__ == "__main__":
    test_header_trace()
