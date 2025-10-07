import json
with open("tests/canonical_mapping_master.json", encoding="utf-8") as f:
    data = json.load(f)
for i, entry in enumerate(data):
    if not isinstance(entry, dict):
        print(i, type(entry), entry)
        break
