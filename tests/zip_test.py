import os, zipfile

path = "processed/Stock offer Wines Spirits & Champagne 200825.xlsx"

print(os.path.getsize(path), "байт")
with open(path, "rb") as f:
    print(f.read(2))  # должно быть b'PK'

try:
    with zipfile.ZipFile(path) as zf:
        print("OK:", zf.namelist()[:5])
except Exception as e:
    print("Ошибка zip:", e)
