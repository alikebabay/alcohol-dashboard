# utils/regular_expressions.py
import re

RX_CURRENCY_MARKER = re.compile(
    r'(?:\b(?:eur|euro|euros|usd|gbp|chf|aed)\b'   # normal currency words
    r'|[¥₽£€\$]'                             # currency symbols
    r'|\bE(?=\s*\d))',                       # NEW: "E" only if followed by a number (E 52.00 / E52.00)
    re.I,
)

#валюта без цен
RX_CURRENCY = re.compile(
    r"(?i)(?:€|\$|£|\b(?:eur|euro|usd|gbp)\b)"
)


# Цена за бутылку
RX_BOTTLE = [
    re.compile(r'price\s+per\s*bottle\s+([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|euros|€|usd|gbp)\b', re.I),
    # 👇 новый универсальный вариант, чтобы ловить 'at 37.15 USD'
    re.compile(r'at\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|euros|€|usd|gbp)\b', re.I),
    # Handles '@ €121.94/btl' or 'at €121.94/btl' | €26.50 /btl | 26,50€ /btl | 26.50 eur/btl | 
    re.compile(
    r'[@\s-]*(?:at\s*)?(?:€|eur|euro|euros|usd|gbp)?\s*-?\s*([0-9]+(?:[.,][0-9]+)?)\s*'
    r'(?:€|eur|euro|euros|usd|gbp)?\s*(?:/|per\s+)(?:btl|bottle)\b',
    re.I,),

]

# Цена за кейс
RX_CASE = [
        #per case
        re.compile(r'(?:eur|euro|euros|€|usd|gbp)\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:per\s*case|case|cs)\b', re.I),
        re.compile(r'([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|euros|€|usd|gbp)\s*(?:per\s*case|case|cs)\b', re.I),
        re.compile(r'price\s+per\s*case\s+([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|euros|€|usd|gbp)\b', re.I),
        # 👇 новый универсальный вариант, чтобы ловить 'at 37.15 USD'
        re.compile(r'at\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|euros|€|usd|gbp)\b', re.I),
        # 👇 короткие варианты вроде "— $131.95" или "€307.34"
        re.compile(r'[$€£]\s*([0-9]+(?:[.,][0-9]+)?)\b', re.I),
        re.compile(r'[$€£]\s*([0-9]{1,3}(?:[,.\s][0-9]{3})*(?:[.,][0-9]+)?)\b', re.I),
        # 👇 Price(USD)/Box или Price(EUR)/Case
        re.compile(r'price\s*\(?(usd|eur|euro|euros|€|gbp)?\)?\s*/\s*(?:box|case)\b', re.I),
        ]

# контекстные регексы лексические
RX_BOTTLE_LEFT = [
    re.compile(r'(?:/|per\s+)?btl\b', re.I),
    re.compile(r'\bper\s+bottle\b', re.I),
    re.compile(r'\bbottle\b', re.I),
]

RX_BOTTLE_RIGHT = [
    re.compile(r'\b(?:/|per\s+)?btl\b', re.I),
    re.compile(r'\bper\s+bottle\b', re.I),
    re.compile(r'\bbottle\b', re.I),
]

RX_CASE_LEFT = [
    re.compile(r'\bcase\b', re.I),
    re.compile(r'\bcs\b', re.I),
    re.compile(r'\bbox\b', re.I),
    re.compile(r'\bper\s+case\b', re.I),
]

RX_CASE_RIGHT = [
    re.compile(r'\bcase\b', re.I),
    re.compile(r'\bcs\b', re.I),
    re.compile(r'\bbox\b', re.I),
    re.compile(r'\bper\s+case\b', re.I),
]

#pattern for prices in float format
RX_NUMBER = re.compile(
    r"""
    \d{1,3}                # первая группа (1–3 цифры)
    (?:[.,\s]\d{3})*       # группы тысяч (,048 .048  048)
    (?:[.,]\d+)?           # дробная часть
    """,
    re.X
)


# Bottles-per-case (6x75, 12×70 и т.п.)
RX_BPC = re.compile(r'(\d{1,2})\s*[x×]\s*\d{1,3}', re.I)
# Star-style variant:  cs*6 btl, *12 btl, cs * 6 bottles
RX_BPC_STAR = re.compile(
    r'(?i)(?:\bcs\s*\*|\*)\s*(?P<cases>\d{1,2})\s*(?:btl|btls|bottle)s?\b'
)
RX_BPC_DASH = re.compile(r'(?i)[—\-–]\s*(?P<cases>\d{1,2})\s*[—\-–]')

#6/70/43
RX_BPC_TRIPLE = re.compile(
    r'(?P<bpc>\d{1,2})\s*[x×/]\s*\d{2,3}\s*[x×/]\s*\d{1,2}'
)

#---------------------------------
# --- регексы для признаков продукта ---
#---------------------------------



# Объём вида 50ml, 75cl, 1L, 37.5cl
# Теперь после ml|cl|l может быть конец строки, пробел, запятая, %, или буква x
RX_VOLUME = re.compile(
    r'(?i)(\d{1,4}(?:[.,]\d{1,2})?\s?(?:ml|cl|l))(?=\b|[x% ,]|$)'
)
# NxVol (12x75cl, 06x1L, 120x5cl) — разрешаем слепленные варианты
_RX_CASEVOL = re.compile(
    r'(?i)\b(\d{1,3})\s*[x×]\s*(\d{1,4}(?:[.,]\d{1,3})?)\s*(ml|cl|l)(?:\b|(?=[x%]))'
)
#особый случай: NxVolxABV (6x100x40%)
_RX_CASEVOL_ABV = re.compile(
    r'(?i)\b\d{1,3}\s*[x×]\s*(\d{1,4}(?:[.,]\d{1,2})?)\s*[x×]\s*\d{1,2}\s*%'
)
# /slash CASE COUNT / VOLUME(CL) / ABV(%)

_RX_SLASH_CASEVOL = re.compile(
    r'(?i)\b\d{1,3}\s*/\s*(\d{1,4})\s*/\s*\d{1,2}\b'
)

# shortening for imports
class CL:
    VOL   = RX_VOLUME
    CASE  = _RX_CASEVOL
    CASE_ABV = _RX_CASEVOL_ABV
    SLASH = _RX_SLASH_CASEVOL



# ABV: 40%, 46.3%, можно слепленные (70clx40%)
RX_ABV = re.compile(
    r'(?i)\b(\d{1,2}(?:[.,]\d)?)\s?%(?:\s*abv)?'
)
RX_AGE      = re.compile(r'(?i)\b(\d{1,2})\s?(yo|years?|лет)\b')
RX_VINTAGE  = re.compile(r'\b(19\d{2}|20(0\d|1\d|2[0-6]))\b')



# извлечение количества бутылок из паттернов вида 6x75cl, 12x0.7l, 24x200ml
RX_PACK_CASES_FLEX = re.compile(
    r'(?i)\b(?P<cases>\d{1,2})\s*[x×]\s*\d{1,4}(?:[.,]\d{1,2})?\s?(?:ml|cl|l)'
)
# извлечение количества бутылок из паттернов вида 6 pcs, 12шт
RX_PACK_PCS = re.compile(r'(?i)\(?\b(?P<cases>\d{1,3})\s*(?:pcs|шт)\b\)?')

# --- Gift box / gift pack detection ---
# Matches any positive indicator of boxed/gift packaging
RX_GBX_MARKER = re.compile(
    r"""(?ix)
    (?<![a-z])
    (?:
        gbx? |
        g\.?b\.?x?\.? |
        g\s*/\s*b |                     # G/B variant
        gbox |
        gift\s*(?:box(?:ed)?|pack)\b |  # Gift Box / Gift Pack
        giftbox(?=\s*$) |               # Giftbox only if it's at end of string
        gpack|gpac |
        \+glass(?:es)? |
        \+hip\s*flask |
        twin\s*pack |
        boxed\s*(?:set|gift)\b          # Boxed Set / Boxed Gift
    )
    (?![a-z])
    """,
    re.IGNORECASE,
)




# Negative markers — explicitly "no gift box", "without box", etc.
RX_GBX_NEGATIVE = re.compile(
    r"""(?ix)
    (?<![a-z])
    (?:no\s*(gbx?|box|gift)|
       non[-\s\.]*gbx?|
       n\.?\s*gbx?|
       without\s*box)
    (?![a-z])
    """,
    re.IGNORECASE,
)

