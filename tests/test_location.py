import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.location_assistant import LocationAssistant
from utils.text_extractors import extract_location

text = """

600 cs Singleton of Dufftown 12yo 6/70/40 (no GB) @ EUR 74 (12,33 p/btl)
560 cs Glenfiddich 12yo 6/70/40 GB @ EUR 111 (18,50 p/btl)
560 cs Glenfiddich 12yo Triple Oak 6/70/40 GB @ EUR 130 (21,67 p/btl)
80 cs Glenfiddich Orchard 6/70/43 GB @ EUR 159 (26,50 p/btl)
80 cs Glenfiddich Fire and Cane 6/70/43 @ EUR 140 (23,33 p/btl)
EXW Loendersloot, Revera or Newcorp / Lead time is about 2 weeks / T2
We can also assist with shipping to your destination

Looking forward to your comments.


Kind regards,

Daan Hoefman
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
