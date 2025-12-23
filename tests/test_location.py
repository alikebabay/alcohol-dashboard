import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.location_assistant import LocationAssistant
from utils.text_extractors import extract_location

text = """
Magners cider bottle 24x330ml
Locatie: van der Mark | Cases: 2160cs | BBD: fresh | Prijs: €20.25

Estrella damm bottle 24x330ml
Locatie: van der Mark | Cases: 1728cs | BBD: fresh | Prijs: €12.30

Stella artois can 24x500ml
Locatie: van der Mark | Cases: 1840cs | BBD: fresh | Prijs: €13.75

Grolsch bottle 24x330ml
Locatie: van der Mark | Cases: 1872cs | BBD: fresh | Prijs: €13.99

Pilsner urquell bottle 24x330ml
Locatie: van der Mark | Cases: 1728cs | BBD: fresh | Prijs: €13.50

Staropramen bottle 24x330ml
Locatie: van der Mark | Cases: 1728cs | BBD: fresh | Prijs: €13.15

Staropramen can 24x500ml
Locatie: van der Mark | Cases: 1890cs | BBD: fresh | Prijs: €15.05

Coors bottle 24x330ml
Locatie: van der Mark | Cases: 1728cs | BBD: fresh | Prijs: €13.10

Coors can 24x500ml
Locatie: van der Mark | Cases: 2016cs | BBD: fresh | Prijs: €14.90

Strongbow cider British dry bottle 24x330ml
Locatie: van der Mark | Cases: 2016cs | BBD: fresh | Prijs: €16.10

Strongbow cider British dry can 24x500ml
Locatie: van der Mark | Cases: 2060cs | BBD: fresh | Prijs: €14.00

John smiths extra smooth can 24x500ml
Locatie: van der Mark | Cases: 1890cs | BBD: fresh | Prijs: €14.10

Paulaner hefen weizen can 24x500ml
Locatie: van der Mark | Cases: 1890cs | BBD: fresh | Prijs: €16.50
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
