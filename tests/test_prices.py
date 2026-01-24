import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.text_extractors import PriceExtractor

text = """
Leffe Blonde 330ml Bottles Price - 14.55 euro/case
"""

extractor = PriceExtractor()
for i, line in enumerate(text.splitlines(), 1):
    if not line.strip():
        continue
    print(f"\n[{i:02}] {line}")
    print(extractor.extract(line))