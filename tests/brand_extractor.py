import json, re

with open("canonical_mapping_master.json", "r", encoding="utf-8") as f:
    data = json.load(f)

brands = {item["brand"] for item in data if "brand" in item}
multi_word = [b for b in brands if len(b.split()) >= 2]

# split by word count
by_length = {
    "one_word": [b for b in brands if len(b.split()) == 1],
    "two_word": [b for b in brands if len(b.split()) == 2],
    "three_word": [b for b in brands if len(b.split()) == 3],
    "more": [b for b in brands if len(b.split()) > 3]
}

with open("multiword_brands.json", "w", encoding="utf-8") as out:
    json.dump(by_length, out, ensure_ascii=False, indent=2)
