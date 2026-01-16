import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.access_assistant import AccessAssistant
from utils.text_extractors import extract_access

# тестовый текст, как в твоих price-тестах
text = """
1500 cases Hennessy VS 50cl x 12, 40% REF @ 13.5EUR
No gbx 
Shipping schedule: ETA Riga - 22NOV. Deposit we need to have until 26 SEP
"""

print("[TEST] AccessAssistant demo run\n")

assistant = AccessAssistant(extract_access)
assistant.prepare(text)
resolved = assistant.resolve_access()
lines = assistant.lines()

for i, (line, acc) in enumerate(zip(lines, resolved), 1):
    if not line.strip():
        continue
    print(f"[{i:02}] {line.strip()}")
    print(f"    access = {acc!r}")
