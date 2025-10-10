# utils/regular_expressions.py
import re

# Цена за бутылку
RX_BOTTLE = [
    re.compile(r'(?:eur|euro|€|usd|gbp)\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:per\s*bottle|btl)\b', re.I),
    re.compile(r'([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\s*(?:per\s*bottle|btl)\b', re.I),
    re.compile(r'price\s+per\s*bottle\s+([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\b', re.I),
]

# Цена за кейс
RX_CASE = [
    re.compile(r'(?:eur|euro|€|usd|gbp)\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:per\s*case|case|cs)\b', re.I),
    re.compile(r'([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\s*(?:per\s*case|case|cs)\b', re.I),
    re.compile(r'price\s+per\s*case\s+([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\b', re.I),
]

# Bottles-per-case (6x75, 12×70 и т.п.)
RX_BPC = re.compile(r'(\d{1,2})\s*[x×]\s*\d{1,3}', re.I)
