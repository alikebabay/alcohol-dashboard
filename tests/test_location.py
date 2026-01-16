import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.location_assistant import LocationAssistant
from utils.text_extractors import extract_location

text = """
1500 cases Hennessy VS 50cl x 12, 40% REF @ 13.5EUR
No gbx 
Shipping schedule: ETA Riga - 22NOV. Deposit we need to have until 26 SEP
"""


assistant = LocationAssistant(extract_location)
assistant.prepare(text)
resolved = assistant.resolve_locations()
lines = assistant.lines()

for i, (line, loc) in enumerate(zip(lines, resolved), 1):
    if not line.strip():
        continue
    print(f"[{i:02}] {line.strip()}")
    print(f"    location = {loc!r}")
