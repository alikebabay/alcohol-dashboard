import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.location_assistant import LocationAssistant
from utils.text_extractors import extract_location

text = """
1848 cs Finlandia 12/50/40 REF @ EUR 30,60 (EUR 2,55 p/btl) — T2
2400 cs Finlandia 6/70/40 REF @ EUR 22,44 (EUR 3,74 p/btl) —T2
850 cs Finlandia 12/100/40 NRF @ EUR 53,28 (EUR 4,44 p/btl) — T1 not for sales in EU/EEA
EXW Loendersloot, Revera or Newcorp / Lead time about 2-3 weeks / Final quantities may vary
132 Dom Perignon Brut 2015 6/75/12,5 GB @ EUR 726 (121 p/btl)
EXW Newcorp / In stock / T1

100 cs Dom Perignon Brut 2013 6/75/12,5 NGB @ EUR 726 (121 p/btl)
EXW Loenderloot / In stock / T2

115 cs Auchentoshan Three Wood 6/70/43 REF GB @ EUR 117,60 (19,60 p/btl)
EXW Loendersloot / About 1,5 week lead time / T2
40 cs Bowmore 15yo Golden & Elegant 6/100/43 @ EUR 205 (34,17 p/btl)
40 cs Bowmore 18yo Deep & Complex 6/70/43 @ EUR 365 (60,83 p/btl)
200 cs Bulleit Rye 6/70/45 REF UKDS @ EUR 79,75 (13,29 p/btl)
2584 cs Bushmills Original 6/70/40 REF @ EUR 33,50 (5,58 p/btl) – for a smaller QTY we may have to adjust the price
150 cs Hakushu Distiller's Reserve 6/70/43 REF GB @ EUR 356 (59,33 p/btl)
75 cs Longmorn 16yo 3/70/48 @ EUR 263 (87,67 p/btl)
EXW Loendersloot / T2 / In stock / No need to take the full offered quantities per line

1200 cs William Lawson's 12/100/40 NRF @ EUR 56 (4,66 p/btl)
EXW Loendersloot / T1 not for EU/EEA / 6 weeks lead time
At a similar price we can also ship straight to sea ports.
187 cs Glenfarclas 10yo 6/70/40 GB @ EUR 100,00 (p/btl EUR 16,67)
1 cs Glenfarclas Heritage 6/70/40 GB @ EUR 51,00 (p/btl EUR 8,50)
112 cs Glengoyne 10yo 6/70/40 GB @ EUR 101,75 (p/btl EUR 16,96)
EXW Loendersloot / T2 / In stock

400 cs Hibiki Japanese Harmony 6/70/43 REF GB @ EUR 305 (50,83 p/btl)
EXW Loendersloot / T2 / About 3 weeks lead time

Daan
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
