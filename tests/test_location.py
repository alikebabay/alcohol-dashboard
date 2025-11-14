import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.location_assistant import LocationAssistant
from utils.text_extractors import extract_location

text = """2200 cs Moët & Chandon Brut Imp. (no GBX) 6x75cl 12.5% T1 @ €150.00 cs, DAP Loend/PLG, 6–7 weeks
500 cs Moet Chandon Imperial Brut 6x75cl GBX,T2 @ 26,50€ /btl Exwork Van de Mark - Holland, 1 week after deposit
1500cs *12 btl Finlandia 50 cl - 2.75 eur/btl DAP Riga, lead time 2-3 weeks
360 cs *12 btl Glenfiddich 12yo GBX 50 cl - 15.80 eur/btl DAP Riga
12000 btl Hennessy VS GBX 70 cl -18.50 eur/btl DAP Riga, lead time 2-3 weeks
18000 btl JD 70 cl - 8.95 eur/btl DAP Riga, lead time 2 weeks
1800 btl JD 3 L with cradle - 49.5 eur/btl DAP Riga, lead time 3-4 weeks
3150 *6 btl Olmeca Silver 50 cl - 5.05 eur/btl DAP Riga
3125*6 btl Jameson 70 cl - 8.03 eur/btl DAP Riga
2300*12 btl Jameson 50 cl - 6.10 eur/btl DAP Riga
3000 cs *6 btl Jim Beam - 5.20 eur/btl DAP Riga

3125 cs*6 btl Tullamore Dew (Round Bottle) 70 cl - 5.33 eur/btl DAP Riga, lead time 1-2 weeks
2200 cs*6 btl Moët & Chandon Brut без ПУ - 25,80 eur/btl DAP Riga
2200 cs*6 btl Veuve Clicquot без ПУ - 30.90 eur/btl DAP Riga
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
