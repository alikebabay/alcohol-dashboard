import re
# core/valid_numerical.py
valid_numerical = {
    "brands": [
        "19 Crimes", "7 Deadly Zins", "14 Hands", "90+ Cellars", "1792",
        "Seagram’s 7 Crown", "Vat 69", "Kronenbourg 1664", "Colt 45",
        "Miller64", "Goose Island 312", "42 Below", "360 Vodka", "Hangar 1",
        "1800 Tequila", "Código 1530", "818 Tequila", "123 Organic Tequila",
        "No.3 London Dry Gin", "Distillery No. 209", "Monkey 47",
        "Licor 43", "99 Brand"
    ],
    "series": [
        "Bin 707", "Bin 389", "Bin 407", "Bin 128", "Gran Reserva 904",
        "Rochefort 10", "Rochefort 8", "Rochefort 6", "Brugal 1888",
        "Mount Gay 1703", "Ron Zacapa 23", "Bacardi 151", "Stroh 80",
        "Stroh 60", "Southern Comfort 100", "Absolut 100", "Smirnoff No.21",
        "Jack Daniel’s Old No. 7", "Maker’s 46", "Beefeater 24",
        "Tanqueray No. Ten", "Don Julio 1942", "Sauza 901",
        "The Macallan 12", "The Macallan 18", "Glenfiddich 12",
        "Glenfiddich 15", "Glenfiddich 18", "Lagavulin 16", "Lagavulin 12",
        "Aberlour 12", "Aberlour 16", "Aberlour 18", "The Yamazaki 12",
        "The Yamazaki 18", "Hakushu 12", "Hakushu 18"
    ]
}

#availability
ACCESS_PATS = [
        re.compile(r'\b(T[12]|TBO)\b', re.I),
        re.compile(r'\b(on\s*(?:stock|floor)|in\s*stock|available|ready)\b', re.I),
        re.compile(r'\blead\s*time\s*\d+\s*(?:d|day|days|w|wk|wks|week|weeks)\b', re.I),
        re.compile(r'\b\d+(?:[/-]\d+)?\s*(?:d|day|days|w|wk|wks|week|weeks)\b(?:\s*after\s*deposit(?:\s*\w+)?)?', re.I),
        # Availability ETA phrases (verb) [optional helper] (time indicator)
        # like "Stock arriving end Oct", "delivery mid Nov", "ETA week 42"
        re.compile(
            r'\b(?:arriving|expected|delivery|shipping|ready|landing|ETA)\b'
            r'(?:\s+(?:in|on|at|around|about|towards|by))?\s*'
            r'(?:end|mid|early)?\s*'
            r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
            r'Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|week\s*\d{1,2})',
            re.I,
        ),
    ]