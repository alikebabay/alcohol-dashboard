import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import difflib
import pandas as pd
from colorama import Fore, Style


from core.graph_normalizer import normalize_dataframe
from utils.abbreviations_helper import convert_abbreviation

# 🧾 Just paste your text here — no need for quotes or commas
text = """

Ballantines Finest 12x75cl 40%
Ballantines Finest 12x1L 40% NRF
Ballantines 17yo 6x75cl 40% GB
Ballantines 21yo 6x70cl 40% GB
Ballantines 30yo 6x70cl 40% GB
Chivas Regal 12yo minis 120x5cl 40% glass
Chivas Regal 12yo 24x20cl 40%
Chivas Regal 12yo 12x37.5cl 40% 
Chivas Regal 12yo 12x75cl 40% NRF GB
Chivas Regal 12yo 12x1L 40%
Chivas Regal 12yo 12x1L 40% NRF
Chivas Regal 18yo minis 120x5cl 40% glass
Chivas Regal 18yo 6x75cl 40% GB
Chivas Regal 18yo 6x1L 40% GB
Chivas Royal Salute 21yo 6x70cl 40% GB
Grants 1x4.5L 40%
J&B Rare 12x1L 40% NRF
Johnnie Walker Red 12x1L 40% NRF
Johnnie Walker Black 12x70cl 40% NRF
Johnnie Walker Black 12x75cl 40% NRF
Johnnie Walker Island Green 6x1L 43% GB *
Old Parr 12yo 12x1L 40% NRF 
Johnnie Walker Gold Reserve 6x1L 40% GB
Johnnie Walker Red minis 192x5cl 40% pet
Johnnie Walker Red 12x75cl 40% NRF
Johnnie Walker Blue 6x75cl 40% GB
Johnnie Walker Blue 6x1L 40% GB
Old Parr 18yo 12x75cl 40% NRF GB
Buchanan's 18yo 6x75cl 40% NRF GB
Grants Triple Wood 12x1L 40% NRF GB
Johnnie Walker Red 24x20cl 40% 
Famous Grouse 12x1L 40% NRF

Malt Whisky 
Aultmore 18yo 6x70cl 46% GB
Glen Grant Cask Heaven 6x1L 46% GB
Dalmore Quartet 6x1L 41.5% GB
Glenfiddich 12yo 12x70cl 40% GB
Glenfiddich 18yo 12x70cl 40% GB
Macallan 18yo Double Cask 6x70cl 43% GB
Macallan 18yo Sherry Oak 6x70cl 43% GB
Monkey Shoulder minis 96x5cl 40% glass
Monkey Shoulder 6x70cl 40%
Old Pulteney 15yo 6x70cl 46% GB
Laphroaig PX Cask 6x1L 48% GB
Monkey Shoulder 6x1L 40%
Glenfiddich 12yo 12x70cl 40% GB

Bourbon - Canadian - Irish - Japanese Whisky 
1792 Small Batch 6x75cl 46.85%
Bakers 7yo Kentucky Straight 6x75cl 53.5%
Basil Hayden 12x1L 40%
Bushmills Original 12x50cl 40%
Bushmills Black Bush 6x70cl 40%
Bushmills 12yo 6x70cl 40% GB
Bushmills 16yo 6x70cl 40% GB
Canadian Club minis 120x5cl 40%
Gentleman Jack 6x1L 40%
Jack Daniels 24x20cl 40%
Jack Daniels Honey 24x20cl 35%
Jack Daniels Fire 12x1L 35%
Jack Daniels Honey 12x1L 35%
Jack Daniels Single Barrel 6x75cl 47%
Jameson minis 120x5cl 40% Glass
Jameson 12x20cl 40%
Jameson 12x75cl 40% 
Knob Creek 9yo 6x1L 50%
Makers Mark 46 6x1L 47%
Nikka Session 12x70cl 43%
Russell's Reserve 10yo 6x75cl 45%
Suntory Special Reserve 12x70cl 40%
Suntory World Whisky Ao 12x70cl 43% separate GB
Wild Turkey 81 12x75cl 40.5%
Wild Turkey Long Branch 6x1L 43%
Wild Turkey Single Barrel 6x1L 50.5% GB
Woodford Reserve Distillers Select 6x1L 43.2%
Blantons Original Single Barrel 6x75cl 40% GB

Cognac - Brandy 
Hennessy Pure White 6x70cl 40%
Hennessy VS 12x35cl 40%
Hennessy VS 12x1L 40% GB
Hennessy XO 12x70cl 40% GB
Remy Martin VSOP 12x1L 40%
Martell Cordon Bleu 12x70cl 40% GB
Martell XO 12x70cl 40% GB

Vodka 
Absolut Blue 12x75cl 40% 
Absolut Blue 6x1.75L 40%
Absolut Blue 1x4.5L 40%
Absolut Citron 12x75cl 40%
Absolut Citron 12x1L 40%
Absolut Mandarin 12x75cl 40%
Absolut Mandarin 12x1L 40%
Absolut Mango 12x75cl 38%
Absolut Mango 12x1L 38%
Absolut Pears 12x75cl 38%
Absolut Pears 12x1L 38%
Absolut Raspberry 12x75cl 38%
Absolut Raspberri 12x1L 38%
Absolut Vanilla 12x75cl 40%
Absolut Vanilla 12x1L 38%
Ciroc Pineapple 12x1L 35%
Ciroc Red Berry 12x1L 35%
Grey Goose minis aluminum 144x5cl 40%
Grey Goose minis aluminum 96x5cl 40%
Grey Goose 6x1L 40% 
Grey Goose L'Orange 6x1L 40%
Grey Goose 6x1.75L 40% 
Ketel One 12x1L 40%
Stolichnaya minis 120x5cl 40%
Stolichnaya 24x20cl 40%
Beluga Gold 6x1L 40% GB
Beluga Noble 6x1L 40%

Gin 
Beefeater minis 120x5cl 40%
Beefeater 12x1L 40% NRF
Bombay Sapphire minis 120x5cl 40%
The Botanist 6x70cl 46%
Ungava 6x1L 43.1%
Hendrick's 12x1L 44%

Rum 
Havana Club Anejo 3yo 12x70cl 37.5% NRF
Havana Club Anejo Especial 12x70cl 37.5% NRF
Havana Club 7yo 12x1L 40% NRF
Havana Club Seleccion de Maestros 6x70cl 45% GB
Mount Gay Silver 12x1L 40%
Pusser's Gunpowder Proof 6x70cl 54.5%
Pusser's 15yo 6x70cl 40% GB
Pyrat XO Reserve 6x70cl 40%
Zacapa XO 6x75cl 40% GB
Havana Club 7yo 12x70cl 40% NRF

Liqueur
Aperol 6x1L 11%
Baileys Irish Cream 12x1L 17% [28/02/2027]
Campari minis 200x5cl 25% glass
Cointreau 12x70cl 40% 
Dekuyper Amaretto Liqueur 12x1L
Dekuyper Blackberry Brandy 12x1L 30%
Dekuyper Creme de Cassis 12x1L 15%
Dekuyper Watermelon 12x1L 35%
Drambuie 6x1L 40%
Jagermeister 6x50cl 35%
Jagermeister 6x70cl 35% NRF
Jagermeister 6x1L 35% NRF
Kahlua 12x75cl 16%
Kahlua 12x1L 16%
Malibu 12x75cl 21%
Patron XO Cafe 6x75cl 35% GB
Southern Comfort 12x1L 40%

Tequila
1800 Reserva Coconut 12x75cl 35%
1800 Reserva Blanco 12x75cl 40%
1800 Reserva Reposado 12x75cl 40%
1800 Reserva Cristalino Anejo 6x75cl 40% 
Clase Azul Anejo 3x75cl 40% GB
Corazon Blanco 6x75cl 40%
Espolon Anejo 6x1L 40%
Jose Cuervo Especial Gold minis 120x5cl 40%
Jose Cuervo Especial Reposado 12x70cl 38%
Jose Cuervo Especial Reposado 12x75cl 40%
Jose Cuervo Especial Reposado 12x1L 40%
Jose Cuervo Tradicional Cristalino 6x75cl 40% GB
Olmeca Gold 12x1L 35%
Patron Silver minis 60x5cl 40% GB
Teremana Reposado 6x1L 40%
Teremana Anejo 6x1L 40%
Cazadores Anejo 6x1L 40%
Don Julio 1942 6x75cl 38% GB

Champagnes
Barons de Rothschild Brut 6x75cl 12%
Dom Perignon Rose 2009 3x75cl 12.5% GB
Moet & Chandon Brut 6x75cl 12.5% 
Veuve Clicquot Brut 6x75cl 12.5%
Moet & Chandon Nectar 6x75cl 12% GB
Moet & Chandon Ice 6x75cl 12.5%

Wines
Cheval de los Andes Blanc 6x75cl 14.5% 2009 wooden case
Robert Mondavi Private Selection Cab. Sauv. 2023 12x75cl 12.5%
Terrazas Reserva Syrah 6x75cl 14.5% 2014

"""

# 🧩 Convert each non-empty line into a row
raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
df = pd.DataFrame({"Наименование": raw_lines})


def color_diff(a: str, b: str) -> str:
    """Word-level diff with color output (always visible)."""
    a_words, b_words = a.split(), b.split()
    sm = difflib.SequenceMatcher(None, a_words, b_words)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.extend(b_words[j1:j2])
        elif tag == "replace":
            out.append(Fore.YELLOW + " ".join(b_words[j1:j2]) + Style.RESET_ALL)
        elif tag == "insert":
            out.append(Fore.GREEN + " ".join(b_words[j1:j2]) + Style.RESET_ALL)
        elif tag == "delete":
            out.append(Fore.RED + " ".join(b_words[j1:j2]) + Style.RESET_ALL)
    return " ".join(out)



try:
    # 1️⃣ Make a copy of the original data
    df_raw = df.copy()

    # 2️⃣ Apply abbreviation conversion FIRST (for graph_normalizer input)
    df_abbr = df.copy()
    df_abbr["Наименование"] = df_abbr["Наименование"].apply(convert_abbreviation)

    # 3️⃣ Then normalize using graph_normalizer on the ABBREVIATED text
    df_norm = normalize_dataframe(df_abbr, col_name="Наименование")

    # 4️⃣ Now show how the raw text changed after both stages
    print("\n[OUTPUT: RAW vs PROCESSED (diff view)]\n")
    for raw, norm in zip(df_raw["Наименование"], df_norm["Наименование"]):
        if raw.strip() == norm.strip():
            continue
        diff = color_diff(raw, norm)
        print(f"{raw}\n→ {diff}\n")

except Exception as e:
    print(f"[ERROR] normalize_dataframe() failed: {e}")
