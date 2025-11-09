# utils/regular_expressions.py
import re

# Цена за бутылку
RX_BOTTLE = [
    re.compile(r'price\s+per\s*bottle\s+([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\b', re.I),
    # 👇 новый универсальный вариант, чтобы ловить 'at 37.15 USD'
    re.compile(r'at\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\b', re.I),
    # Handles '@ €121.94/btl' or 'at €121.94/btl' | €26.50 /btl | 26,50€ /btl | 26.50 eur/btl | 
    re.compile(
    r'[@\s-]*(?:at\s*)?(?:€|eur|euro|usd|gbp)?\s*-?\s*([0-9]+(?:[.,][0-9]+)?)\s*'
    r'(?:€|eur|euro|usd|gbp)?\s*(?:/|per\s+)(?:btl|bottle)\b',
    re.I,),

]

# Цена за кейс
RX_CASE = [
        re.compile(r'(?:eur|euro|€|usd|gbp)\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:per\s*case|case|cs)\b', re.I),
    re.compile(r'([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\s*(?:per\s*case|case|cs)\b', re.I),
    re.compile(r'price\s+per\s*case\s+([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\b', re.I),
    # 👇 новый универсальный вариант, чтобы ловить 'at 37.15 USD'
    re.compile(r'at\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|euro|€|usd|gbp)\b', re.I),
    # 👇 короткие варианты вроде "— $131.95" или "€307.34"
    re.compile(r'[$€]\s*([0-9]+(?:[.,][0-9]+)?)\b', re.I),
    re.compile(r'[$€]\s*([0-9]{1,3}(?:[,.\s][0-9]{3})*(?:[.,][0-9]+)?)\b', re.I),
    # 👇 Price(USD)/Box или Price(EUR)/Case
    re.compile(r'price\s*\(?(usd|eur|euro|€|gbp)?\)?\s*/\s*(?:box|case)\b', re.I),


]

# Bottles-per-case (6x75, 12×70 и т.п.)
RX_BPC = re.compile(r'(\d{1,2})\s*[x×]\s*\d{1,3}', re.I)
# Star-style variant:  cs*6 btl, *12 btl, cs * 6 bottles
RX_BPC_STAR = re.compile(
    r'(?i)(?:\bcs\s*\*|\*)\s*(?P<cases>\d{1,2})\s*(?:btl|btls|bottle)s?\b'
)

# --- регексы для признаков продукта ---
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
