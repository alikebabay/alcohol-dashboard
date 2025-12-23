import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.location_assistant import LocationAssistant
from utils.text_extractors import extract_location

text = """
Pilsner urquell 50cl cans on floor loendersloot at 13.90 euro
"""

print("[TEST] LocationAssistant demo run\n")

assistant = LocationAssistant(extract_location)
assistant.prepare(text)
resolved = assistant.resolve_locations()
lines = assistant.lines()

for i, (line, loc) in enumerate(zip(lines, resolved), 1):
    if not line.strip():
        continue
    print(f"[{i:02}] {line.strip()}")
    print(f"    location = {loc!r}")
