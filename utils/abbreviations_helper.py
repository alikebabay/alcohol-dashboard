import re

abbreviations = {
        "yl": "Yellow Label",
        "Moët": "Moet & Chandon",
        "imperial brut": "Brut Imperial",
        "XO": "X.O",
        "YO": "Year Old",
        "yo": "Year Old",
    }

def convert_abbreviation(text) -> str:
    "Отделяет yo из чисел, чтобы не сливалось, например 12yo -> 12 yo"
    text = re.sub(r'(?<=\d)(?=yo\b|YO\b)', ' ', text)
    """Convert brand abbreviations to their full forms."""
    for abbrev, full_form in abbreviations.items():
            text = re.sub(r'\b' + re.escape(abbrev) + r'\b', full_form, text, flags=re.IGNORECASE)
    return text