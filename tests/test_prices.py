import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.text_extractors import PriceExtractor

text = """
We can offer:
1044 cases Jose Cuervo 12x70cl @ Euro 72.5 per case, on floor, Ex Loendersloot
4979 bottles Grants Triple Wood 12YO 40% 100cl+GBX @ Euro 8.15 per bottle, Ex PLG on floor
FTL Ron Zacapa Solera Rum 70clx40% @ Euro 24 per bottle, 2 weeks, T2, DAP Loendersloot
750 cases Macallan 12YO Sherry Oak 6x70cl RF GBX @ USD 395 per case, 8 weeks, CFR any port
FTL Cointreau RF 6x70cl @ Euro 6.5 per bottle, 3 weeks, Ex Loendersloot
3000 cases Jameson 6x70cl @ Euro 7.8 per bottle, on floor, Ex New Corp
2000 cases (MOQ) Glenfiddich 12YO 6x70cl GBX @ Euro 17.75 per bottle, 1 week, Ex Loendersloot
FTL Ron Zacapa Solera Rum 1L GBX @ Euro 28.25 per bottle, 2 weeks, T2, DAP Loendersloot
19200 bottles Gordons 70cl @ Euro 3.95 per bottle, T2, DAP Top Logistics, 1 week
800 cases Gin Mare 6x1L @ Euro 18 per bottle, on floor, Ex New Corp
"""

extractor = PriceExtractor()
for i, line in enumerate(text.splitlines(), 1):
    if not line.strip():
        continue
    print(f"\n[{i:02}] {line}")
    print(extractor.extract(line))