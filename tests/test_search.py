from rapidfuzz import fuzz

a = "Glenmorangie Quinta Ruban 14 Year Old"
b1 = "Glenmorangie Quinta Ruban 14YO 75cl GBX "
b2 = "Glenmorangie Nectar 16YO 75cl GBX — 6 — $307.34"
b3 = "glenmorangierer nectar quita ruban 14 year old"
b4 = "Glenmorangie Quinta Ruban 15yo 75cl GBX"
b5 = "Glenmorangie The Infinita 18 Years Old"
b6 = "Glenmorangie Quintar Ruban 14 Year Old"
b7 = "Glenmorangie Quinta Ruban 14 Year Old sdfsdfsdf"
print(fuzz.partial_ratio(a, b1))  
print(fuzz.partial_ratio(a, b2)) 
print(fuzz.partial_ratio(a, b3)) 
print(fuzz.partial_ratio(a, b4)) 
print(fuzz.partial_ratio(a, b5)) 
print(fuzz.partial_ratio(a, b6)) 
print(fuzz.partial_ratio(a, b7)) 