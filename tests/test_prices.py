import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.text_extractors import PriceExtractor

text = """
Grolsch NL Can  24/500/5.0%   240cs 2.12.2024 1,99eur
Grolsch NL Can  24/500/5.0%   240cs 18.7.2025 2,20eur
Grolsch NL Can  24/500/5.0%   385cs 12.9.2025 2,50 eur
"""

extractor = PriceExtractor()
for i, line in enumerate(text.splitlines(), 1):
    if not line.strip():
        continue
    print(f"\n[{i:02}] {line}")
    print(extractor.extract(line))