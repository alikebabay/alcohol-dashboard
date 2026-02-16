#test_product_detector.py detects product without price
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.product_detector import detect_product_without_price
from utils.logger import setup_logging
setup_logging()

text = """
Peroni Nastro Azzurro 24/330/5%     161cs   28.2.2025  
Amsterdam NAVIGATOR CAN 24/500/8%   216cs 19.4.2025  
Grolsch NL Can  24/500/5.0%   240cs 2.12.2024 1,99eur
Grolsch NL Can  24/500/5.0%   240cs 18.7.2025 2,20eur
Grolsch NL Can  24/500/5.0%   385cs 12.9.2025 2,50 eur
ASAHI SUPER DRY BOTTLE  24/330/5.0%  1035cs  18.5.2025  
Peroni Nastro Azzurro Bottle 24/330/0%  700 cs 30.7.2025  
Peroni Nastro Azzurro Bottle 24/330/0%  5234cs (3 loads) 1.9.2025 
Peroni Nastro Azzurro Bottle 24/330/0% 1080cs 30.9.2025 

ALL TOGETHER 5-6 LOADS = TAKE ALL PRICE €2.50 CASE EVERY BEER
EXW revera
"""

for i, line in enumerate(text.splitlines(), 1):
    if not line.strip():
        continue

    result = detect_product_without_price(line)
    print(f"[{i:02}] {result}  |  {line}")
