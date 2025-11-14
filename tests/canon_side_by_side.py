# canon_side_by_side.py
import pandas as pd
from pathlib import Path

# === вставляешь сюда сырой список (до нормализации) ===
raw_text = """
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
""".strip().splitlines()

# === вставляешь сюда итоговый список (после нормализации) ===
canon_text = """
1792 Small Batch
Aultmore 18 Year Old GBX
Bakers 7YO Kentucky Straight
Ballantine's 17 Year Old GBX
Ballantine's 21 Year Old GBX
Ballantine's 30 Year Old GBX
Ballantine's Finest
Ballantine's Finest
Basil Hayden
Blanton's The Original Single Barrel Bourbon Whiskey GBX
Buchanan's 18 Year Old GBX
Bushmills 12 Year Old GBX
Bushmills 16 Year Old GBX
Bushmills Black Bush
Bushmills Original
Canadian Club MINIS
Chivas Regal 12 Year Old
Chivas Regal 12 Year Old
Chivas Regal 12 Year Old
Chivas Regal 12 Year Old
Chivas Regal 12 Year Old
Chivas Regal 12 Year Old GBX
Chivas Regal 18 Year Old
Chivas Regal 18 Year Old GBX
Chivas Regal 18 Year Old GBX
Dalmore The Quartet GB GBX
Famous Grouse
Glen Grant Rothes Chronicles Cask Haven GBX
Glenfiddich 12 Year Old GBX
Glenfiddich 12 Year Old GBX
Glenfiddich 18 Year Old GBX
Grant's Triple Wood
Grant's Triple Wood GBX
J&B Rare
Jack Daniel's Fire
Jack Daniel's Gentleman Jack
Jack Daniel's Honey
Jack Daniel's Honey
Jack Daniel's Old No. 7
Jack Daniel's Single Barrel
Jameson
Jameson
Jameson MINIS GLASS
Johnnie Walker Black Label
Johnnie Walker Black Label
Johnnie Walker Blue Label GBX
Johnnie Walker Blue Label GBX
Johnnie Walker Gold Reserve GBX
Johnnie Walker Island Green GBX
Johnnie Walker Red Label
Johnnie Walker Red Label
Johnnie Walker Red Label
Johnnie Walker Red Label
Knob Creek 9 Year Old
Laphroaig Px Cask GBX
Macallan 18 Year Old Double Cask GBX
Macallan 18 Year Old Sherry Oak GBX
Monkey Shoulder
Monkey Shoulder
Monkey Shoulder MINIS GLASS
Nikka Session
Old Parr 12 Year Old
Old Parr 18 Year Old GBX
Old Pulteney 15 Year Old GBX
Russell's Reserve 10 Year Old
Suntory Special Reserve
Suntory World Whisky GBX
Wild Turkey 81
Wild Turkey Long Branch
Wild Turkey Single Barrel GBX
Woodford Reserve Distillers Select
Hennessy Pure White
Hennessy V.S
Hennessy V.S GBX
Hennessy X.O GBX
Martell Cordon Bleu GBX
Martell XO GBX
Remy Martin VSOP
Absolut Blue
Absolut Blue
Absolut Blue
Absolut Citron
Absolut Citron
Absolut Mandarin
Absolut Mandarin
Absolut Mango
Absolut Mango
Absolut Pears
Absolut Pears
Absolut Raspberry
Absolut Raspberry
Absolut Vanilla 38%
Absolut Vanilla 40%
Beluga Gold GBX
Beluga Noble
Ciroc Pineapple
Ciroc Red Berry
Grey Goose
Grey Goose
Grey Goose L'Orange
Grey Goose MINIS ALUMINUM
Grey Goose MINIS ALUMINUM
Ketel One
Stolichnaya
Stolichnaya MINIS
Beefeater
Beefeater MINIS
Bombay Sapphire MINIS
Hendrick's
The Botanist Islay Dry Gin
Ungava
Havana Club 7 Year Old
Havana Club 7 Year Old
Havana Club Anejo 3 Anos
Havana Club Anejo Especial
Havana Club Seleccion De Maestros GBX
Mount Gay Silver
Pusser's 15 Year Old GBX
Pusser's Gunpowder Proof
Pyrat XO Reserve
Zacapa XO GBX
1800 Reserva Blanco 40%
1800 Reserva Coconut 35%
1800 Reserva Cristalino Anejo 40%
1800 Reserva Reposado 40%
Cazadores Anejo
Clase Azul Anejo GBX
Corazon Blanco
Don Julio 1942 GBX
Espolon Anejo
Jose Cuervo Especial Gold MINIS
Jose Cuervo Especial Reposado
Jose Cuervo Especial Reposado
Jose Cuervo Especial Reposado
Jose Cuervo Tradicional Cristalino GBX
Olmeca Gold
Patron Silver GBX
Patron XO Cafe GBX
Teremana Anejo
Teremana Reposado
Aperol
Baileys Original Irish Cream [28/02/2027]
Campari MINIS
Cointreau
Dekuyper Amaretto Liqueur
Dekuyper Blackberry Brandy 30%
Dekuyper Creme de Cassis 15%
Dekuyper Watermelon 35%
Drambuie
Jagermeister
Jagermeister
Jagermeister
Kahlua
Kahlua
Malibu
Southern Comfort
Barons De Rothschild Brut
Dom Perignon Rose GBX
Moet & Chandon Brut Imperial
Moet & Chandon Ice Imperial
Moet & Chandon Nectar Imperial GBX
Veuve Clicquot Brut Yellow Label
Cheval De Los Andes Blanc
Maker's Mark 46
Robert Mondavi Private Selection Cab. Sauv.
Royal Salute 21 Year Old GBX
Terrazas Reserva Syrah
""".strip().splitlines()


# === Сортируем оба списка по алфавиту ===
raw_sorted = sorted(raw_text, key=lambda x: x.lower())
canon_sorted = sorted(canon_text, key=lambda x: x.lower())

# === Проверяем количество ===
n_raw = len(raw_sorted)
n_canon = len(canon_sorted)
max_len = max(n_raw, n_canon)

# === Формируем таблицу ===
rows = []
for i in range(max_len):
    raw = raw_sorted[i] if i < n_raw else ""
    canon = canon_sorted[i] if i < n_canon else ""
    rows.append({"RAW": raw, "CANON": canon})

df = pd.DataFrame(rows)

# === Вывод статистики ===
print(f"Входных строк: {n_raw}")
print(f"Выходных строк: {n_canon}")
print(f"⚖️  {'Совпадает ✅' if n_raw == n_canon else '❌ Кол-во не совпадает!'}\n")

# === Настройки отображения ===
pd.set_option('display.max_rows', None)
pd.set_option('display.max_colwidth', 120)

# === Сохраняем результат в Excel ===
out_path = Path("processed") / "canon_check.xlsx"
out_path.parent.mkdir(parents=True, exist_ok=True)
df.to_excel(out_path, index=False)
print(f"\n📁 Результат сохранён: {out_path.resolve()}")