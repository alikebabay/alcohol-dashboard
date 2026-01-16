import re
# core/valid_numerical.py
valid_numerical = {
    "brands": [
        "19 Crimes", "7 Deadly Zins", "14 Hands", "90+ Cellars", "1792",
        "Seagram's 7 Crown", "Vat 69", "Kronenbourg 1664", "Colt 45",
        "Miller64", "Goose Island 312", "42 Below", "360 Vodka", "Hangar 1",
        "1800 Tequila", "Código 1530", "818 Tequila", "123 Organic Tequila",
        "No.3 London Dry Gin", "Distillery No. 209", "Monkey 47",
        "Licor 43", "99 Brand",
    ],
    "series": [
        "Bin 707", "Bin 389", "Bin 407", "Bin 128", "Bin 2", "Bin 8",
        "Bin 28", "Gran Reserva 904",
        "Rochefort 10", "Rochefort 8", "Rochefort 6", "Brugal 1888",
        "Mount Gay 1703", "Ron Zacapa 23", "Bacardi 151", "Stroh 80",
        "Stroh 60", "Southern Comfort 100", "Absolut 100", "Smirnoff No.21",
        "Jack Daniel's Old No. 7", "Maker's Mark 46", "Maker's Mark 101", "Beefeater 24",
        "Tanqueray No. Ten", "Don Julio 1942", "Sauza 901",
        "The Macallan 12", "The Macallan 18", "Glenfiddich 12",
        "Glenfiddich 15", "Glenfiddich 18", "Lagavulin 16", "Lagavulin 12",
        "Aberlour 12", "Aberlour 16", "Aberlour 18", "The Yamazaki 12",
        "The Yamazaki 18", "Hakushu 12", "Hakushu 18", 
    ]
}

class _PATS:
    pass

PATS = _PATS()


#availability
RX_MONTH = (
    r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
)

PATS.ACCESS = [
        re.compile(r'\b(T[12]|TBO)\b', re.I),
        # strict ON-THE-FLOOR + safe ON FLOOR (no digits after) + stock/available/ready
        re.compile(
            r"(?:\bon[\s\-_]*the[\s\-_]*floor\b)"
            r"|(?:\bon[\s\-_]*floor\b(?!\s*\d))"
            r"|\bon\s*stock\b|\bin\s*stock\b|\bavailable\b|\bready\b",
            re.I,
        ),
        re.compile(
            r'\b\d+(?:[.,]\d+)?(?:[\/\-–]\d+(?:[.,]\d+)?)?\s*'
            r'(?:d|day|days|w|wk|wks|week|weeks)\b'
            r'(?:\s*after\s*deposit(?:\s*\w+)?)?',
            re.I,
        ),
        # Availability ETA phrases (verb) [optional helper] (time indicator)
        # like "Stock arriving end Oct", "delivery mid Nov", "ETA week 42"
        re.compile(
            rf'\b(?:arriving|expected|delivery|shipping|ready|landing|ETA)\b'
            rf'(?:\s+(?:in|on|at|around|about|towards|by))?\s*'
            rf'(?:end|mid|early)?\s*'
            rf'(?:{RX_MONTH}|\bweek\s*\d{{1,2}}\b)'
            rf'(?:\s*\d{{4}})?\b',
            re.I,
        ),

    ]

#ловит даты в формате 22 NOV
RX_DATE = re.compile(
    r'\b(?:'
    r'\d{1,2}\s*(?:\.|/|-|\s)?\s*'
    r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)'
    r'(?:\.|ember|uary|ch|il|ust)?'
    r'|'
    r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)'
    r'(?:\.|ember|uary|ch|il|ust)?\s*'
    r'\d{1,2}'
    r')\b',
    re.I
)


RX_FLOOR = re.compile(
    r"(?:(?:\bon[\s\-_]*the[\s\-_]*floor\b)|(?:\bon[\s\-_]*floor\b(?!\s*\d)))",
    re.I,
)


# --- Паттерны для excel пайплайна - поиск в названиях колонок-

PATS.NAME = [
    r"^name", r"^наимен", r"^descr", r"описан", r"товар", r"product", r"бренд|марка", r"item"
]

# паттерн для винтажей
PATS.VINTAGE = [r"vintage", r"\bгод\b", r"\byear\b"]

PATS.BOTTLES_PER_CASE = [
    r"bottles_per_case",
    r"^\s*bt\s*/?\s*cs\s*$",
    r"bt.?/?cs", r"btl.?/?case",
    r"bottl.?/case",
    r"шт.*[/ ]*кор", r"шт.*в.*кор", r"шт.*в.*ящ",
    r"pcs.*[/ ]*case", r"qty.*case",
    r"size(?!.*price)",   # исключаем Price/Size
    r"规格"
]

PATS.PRICE_CASE = [
    r"(?:price|цена).*(?:case|cs|ctn|carton)",
    r"(?:usd|eur|\$|€)\s*(?:/|per)?\s*(?:case|cs|ctn|carton)",
    r"usd.?/?cs", r"eur.?/?cs",
    r"\b\$\s*/?\s*cs\b", r"\b€\s*/?\s*cs\b",
    # 👇 поддержка Price(USD)/Box и подобных вариантов
    r"price\s*\(?(?:usd|eur|euro|€|gbp)?\)?\s*/\s*(?:box|case|carton|ctn)\b",
]


PATS.AVAILABILITY = [
    r"stock", r"lead\s*time", r"availability", r"status", r"eta", 
    r"ready", r"t1", r"t2", r"tbo", r"доступ", r"наличи", r"access",
]

PATS.LOCATION = [
    r"ware",       # ← ловит все ware-, warehouse, ware house
    r"склад", r"origin", r"отгруз", r"exw", r"dap", r"fob", r"cif",
    r"место\s*загруз", r"location", r"incoterm", r"ETA\s*Rdam",
]


CURRENCY_PATTERNS = {
    "EUR": [
        (r"\beur\b", True),
        (r"\beuro(s)?\b", True),
        (r"€", False),
    ],
    "USD": [
        (r"\busd\b", True),
        (r"\$", False),
    ],
    "KZT": [
        (r"\bkzt\b", True),
        (r"₸", False),
    ],
    "RUB": [
        (r"\brub\b", True),
        (r"₽", False),
    ],
    "GBP": [
    (r"\bgbp\b", True),
    (r"\bpound(s)?\b", True),
    (r"£", False),
    ],

}