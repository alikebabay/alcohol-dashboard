import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.access_assistant import AccessAssistant
from utils.text_extractors import extract_access

# тестовый текст, как в твоих price-тестах
text = """
WHISKY STOCK OFFER EX LOENDERSLOOT

40CS BOWMORE 15YRS GOLDEN & ELEGANT 6/100/43 @ EURO 190.00
T2 / CODED / REFILL / GBX / EAN CODE 5010496004548

40CS BOWMORE 18YRS DEEP & COMPLEX 6/70/43 @ EURO 340.00
T2 / CODED / REFILL / GBX / EAN CODE 5010496004555

100CS AUCHENTOSHAN AMERICAN OAK 12/100/40 @ EURO 204.00
T2 / CODED / REFILL / EAN CODE 5010496005378

36CS DEWAR’S 12YRS 6/70/40 @ EURO 75.00
T2 / CODED / REFILL / GBX / EAN CODE 5000277002450

39CS GLEN SCOTIA DOUBLE CASK CLASSIC CAMPBELTOWN 6/70/46 @ EURO 120.00
T2 / CODED / REFILL / GBX / EAN CODE 5016840151210

94CS LONGMORN 16YRS 3/70/48 @ EURO 244.00
T2 / CODED / REFILL / GBX / EAN CODE 5000299607152
EX LOENDERSLOOT

For larger orders, prices can be discussed

140CS BALLANTINE’S 12/100/40 @ EURO 86.00
T2 / CODED / REFILL / EAN CODE 5010106111956 / ON THE FLOOR

600CS BEEFEATER 12/50/40 @ E 52.00
T2 / CODED / REFILL / EAN CODE 5000299605981 / ON THE FLOOR

486CS ABSOLUT 24/20/40 @ E 54.00
T2 / CODED / REFILL / EAN CODE 7312040017201 / 2 WEEKS LEADTIME

120CS ABSOLUT 6/70/40 @ EURO 32.00
T2 / CODED / REFILL / EAN CODE 7312040017683 / ON THE FLOOR

1000CS ABSOLUT 24/35/40 @ EURO 84.00
T2 / CODED / REFILL / EAN CODE 7312040017355 / ON THE FLOOR

1000CS ABSOLUT 12/35/40 @ EURO 42.00
T2 / CODED / REFILL / EAN CODE 7312040017355 / ON THE FLOOR

500CS GLENLIVET FOUNDERS RESERVE 6/70/40 @ E 95.00
T2 / CODED / REFILL / GBX / EAN CODE 500299609347 / ON THE FLOOR

1686CS JAMESON 6/100/40 @ EURO 61.00
T2 / CODED / REFILL / EAN CODE 5011007003227 / ON THE FLOOR

40CS ABERLOUR 16YRS DOUBLE CASK MATURED 3/70/40 @ EURO 134.00
T2 / CODED / REFILL / GBX / EAN CODE 500299298022 / ON THE FLOOR

244CS ABERLOUR 14YRS DOUBLE CASK MATURED 3/70/40 @ EURO 90.00
T2 / CODED / REFILL / EAN CODE 500299620915 / ON THE FLOOR
If intrested we can also send you our full stock offer ex Loendersloot / Newcorp
We can offer many more items on request (Spirits/Waters/Wines/Beers)
Based on your request we can offer ex warehouse Holland or CNF port of destination
+31 6 29701510
wilfred@liquidsupply.nl
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
