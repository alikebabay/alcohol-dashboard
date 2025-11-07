# canon_side_by_side.py
import pandas as pd
from pathlib import Path

# === вставляешь сюда сырой список (до нормализации) ===
raw_text = """
Dom Perignon 75cl GBX
Dom Perignon 75cl
Moet & Chandon Brut 75cl 
Moet & Chandon Rosé 75cl
Moet & Chandon Ice 75cl
Veuve Cliquot Brut Yellow Label 75cl GBX
Veuve Cliquot Brut Yellow Label 75cl 
Ruinart blanc de blanc 75cl
Krug Grand Cuvee 75cl Edition 172 GBX
Jacquesson Cuvee No. 742 75cl
Jacquesson Cuvee No. 743 75cl
Jacquesson Cuvee No. 748 75cl
Jacquesson Avize Champ Cain 75cl
Jacquesson Dizy Corne Bautray 75cl
Jacquesson Dizy Terres Rouges 75cl
Jacquesson Dizy Terres Rouges 75cl
Cava Freixenet Cordon Negro Brut 75cl
Minuty M de Minuty Rosé 150cl
Domaines Ott Chateau Romassan Rosé 75cl
DBR Lafite Les Legendes R Bordeaux Red 75cl
DBR Lafite R Saga Rouge 75cl
Rioja Alta Gran Reserva 890 75cl
Rioja Alta Gran Reserva 904 75cl
Rioja Alta Viña Ardanza 75cl
Aalto 75cl
Aalto blanco 75cl
Aalto blanco 75cl
Aalto 150cl
Aalto 150cl
Aalto 300cl
Aalto 500cl
Aalto PS 75cl
Aalto PS 75cl
Aalto PS 150cl Wooden Case
Aalto PS 150cl Wooden Case
Aalto PS 150cl Wooden Case
Aalto PS 150cl Wooden Case
Aalto PS 3L Wooden Case
Luce Brunello di Montalcino 75cl
Luce della Vite Luce 75cl
Luce Lucente 75cl
Dal Forno Romano Amarone della Valpolicella 75cl (historical box)
Dal Forno Romano della Valpolicella 75cl
Quintarelli Giuseppe Amarone Classico 75cl
Quintarelli Giuseppe Valpolicella Classico 75cl
Sassicaia Tenuta San Guido 75cl
Sassicaia Tenuta San Guido 75cl
Tenuta San Guido Guidalberto 75cl
Tenuta San Guido Guidlaberto 75cl
Tenuta San Guido Guidlaberto 75cl
Tenuta San Guido Le Difese
Tenuta dell'Ornellaia Ornellaia 75cl
Tenuta dell'Ornellaia Le Serre Nuove 75cl
Tenuta dell'Ornellaia Le Volte 75cl
Braida Bricco Dell’Uccelone 75cl
Tenuta di Biserno Biserno 75cl
Tenuta di Biserno Il Pino 75cl
Tenuta di Biserno Il Pino 75cl
Tenuta di Biserno Il Pino 150cl
Tenuta di Biserno Insoglio 150cl
Egon Muller Scharzhof Riesling 75cl
Egon Muller Scharzhofberger Riesling Spätlese 75cl
Egon Muller Scharzhofberger Riesling Auslese 75cl
Egon Muller Scharzhof Riesling 75cl
Egon Muller Scharzhofberger Riesling Kabinett 75cl
Egon Muller Scharzhofberger Riesling Spätlese 75cl
Egon Muller Scharzhofberger Riesling Auslese 75cl
Egon Muller Scharzhofberger Riesling Beerenauslese 75cl
Chocolate Block 75cl
Barista Pinotage 75cl
Opus One 75cl
Opus One 75cl
Los Vascos Sauvignon Blanc 75cl
Los Vascos Cabernet Sauvignon 75cl
Los Vascos Cromas Grand Reserva Carmenere 75cl
Los Vascos Cromas Grand Reserva Carmenere 75cl
Los Vascos Le Dix 75cl
Cloudy Bay Sauvignon Blanc 75cl
Penfolds Koonunga Hill Shiraz Cabernet 75cl
Penfolds Grange 75cl
Penfolds RWT 75cl
Penfolds St. Henri 75cl
Penfolds Bin 707 75cl
Penfolds Bin 407 75cl
Penfolds Bin 389 75cl
Penfolds Bin 128 75cl
Penfolds Bin 28 75cl
Penfolds Bin 2 75cl
Penfolds Bin 8 75cl 
Aultmore 18YO 70cl 46% GBX NRF
Aultmore 21YO 70cl 46% GBX NRF
Aultmore 25YO 70cl 46% GBX NRF
Dalmore 12YO 70cl
Dalmore 15YO 70cl
Dalmore King Alexander III Malt 70cl
Bowmore 10YO dark and intense Single Malt 70cl 40%
The Yamazaki Single Malt 12yo  48%
Monkey Shoulder Whisky 1L 40%
Laphroaig 10YO 1L 40%
Macallan Enigma Box 70cl GBX
Macallan Night on earth 70cl GBX
Macallan The Harmony Edition 3 Amber Meadow 70cl GBX
Macallan Rare Cask Black 70cl GBX
Ballantine's Finest 100cl NRF 40%
Chivas Regal 18YO 75cl NRF 40%
Glenfarclas 35YO 70cl GBX
Glenmorangie The Accord 12Y 1L GBX 43%
Glenmorangie The Elementa 14Y 1L GBX 43%
Glenfiddich 12YO 70cl 40%
Glenfiddich 15YO 70cl 40%
J&B 1L 40% NRF
Teachers highland cream 1L 40% NRF
The Famous Grouse 1L 40% NRF
The Famous Grouse 1L 40% NRF blanco carton
Cutty Sark 1L 40% NRF International Label
Johnnie Walker Black Label 1L 40% NRF
Jim Beam Apple 1L 40%
Jim Beam Honey 1L 40%
Singleton Single Malt Dufftown 12YO 70cl 40%
Kweichow Moutai Chiew 50CL 53%
Boulard Grand Solage 70cl 40%
Roku Select Edition Gin 1L 43%
Hendricks Gin 1L 41,4% REF
Mintis originale Gin 70cl 41,8%
Molinari Extra 1L 40%
Passoa 70cl 17%
Villa Massa Limoncello 70cl
Vecchia Romagna Riserva 18y 70cl 43,8%
Kahlua 1L 20%
Beluga Noble 70cl 40% (Montenegro production)
Absolut Original Vodka 20cl 40% REF
Grey Goose Blue vodka 1L 40%
Aperol 1L 11%
Campari 1L 25%
Select aperitivo 1L 17,5%
Clase Azul Plata 70cl 40%
Clase Azul Gold 70cl 40%
Clase Azul Anejo 70cl 40%
Clase Azul Ultra 70cl 40%
Clase Azul Mezcal Durango 70cl 40%
Clase Azul Mezcal Guerrero 70cl 40%
Clase Azul Mezcal San Luis 70cl 40%
Jose Cuervo 1800 Anejo 75cl 40% REF
Tequila Rose Strawberry 70cl 15%
Disaronno Amaretto 70cl 28%
Disaronno Amaretto 1L 28%
Tia Maria 70cl 20%
Tia Maria 1L 20%
Jagermeister 70cl 35%  REF 
Bols Blue 70cl 21%
Bols Peach 70cl 17%
Bols Lychee 70cl 17%

""".strip().splitlines()

# === вставляешь сюда итоговый список (после нормализации) ===
canon_text = """
Aultmore 18 Year Old GB
Aultmore 21 Year Old GBX
Aultmore 25 Year Old GBX
Ballantine's Finest
Bowmore 10YO Dark And Intense Single Malt
Chivas Regal 18 Year Old
Cutty Sark International Label NRF
Dalmore 12 Years Old
Dalmore 15 Years Old
Dalmore King Alexander III
Glenfarclas 35 Years Old GBX
Glenfiddich 12 Year Old
Glenfiddich 15 Year Old
Glenmorangie The Accord 12Y GBX
Glenmorangie The Elementa 14Y GBX
J&B Rare
Jim Beam Apple
Jim Beam Honey
Johnnie Walker Black Label NRF
Laphroaig 10 Years Old
Macallan Enigma GBX
Macallan Night On Earth GBX
Macallan Rare Cask Black GBX
Macallan The Harmony Collection Amber Meadow GBX
Monkey Shoulder
Singleton 12 Year Old
Teacher's Highland Cream
The Famous Grouse NRF
The Famous Grouse NRF
The Yamazaki Single Malt 12YO
Boulard Grand Solage
Absolut Original Vodka
Beluga Noble (montenegro Production)
Grey Goose
Hendrick's
Mintis Gin Originale
Roku Select Edition Gin
Clase Azul Anejo
Clase Azul Gold
Clase Azul Mezcal Durango
Clase Azul Mezcal Guerrero
Clase Azul Mezcal San Luis
Clase Azul Plata
Clase Azul Ultra
Jose Cuervo 1800 Anejo
Tequila Rose Strawberry
Aperol
Bols Blue
Bols Lychee
Bols Peach
Campari
Disaronno Amaretto
Disaronno Amaretto
Jagermeister
Kahlua
Molinari Extra
Passoa
Select Aperitivo
Tia Maria
Tia Maria
Vecchia Romagna Riserva 18Y
Villa Massa Limoncello
Dom Perignon Vintage 2015
Dom Perignon Vintage 2015
Freixenet Cordon Negro Brut Cava
Jacquesson Avize Champ Cain
Jacquesson Cuvee No. 742
Jacquesson Cuvee No. 748
Jacquesson Cuvée No. 743
Jacquesson Dizy Corne Bautray 2014
Jacquesson Dizy Terres Rouges
Jacquesson Dizy Terres Rouges
Krug Grand Cuvee Edition GBX
Moet & Chandon Brut Imperial
Moet & Chandon Ice Imperial
Moet & Chandon Rose Imperial
Ruinart Blanc De Blancs
Veuve Clicquot Brut Yellow Label
Veuve Clicquot Brut Yellow Label
Aalto
Aalto
Aalto
Aalto
Aalto
Aalto Blanco
Aalto Blanco
Aalto Pagos Seleccionados
Aalto Pagos Seleccionados
Aalto Pagos Seleccionados
Aalto Pagos Seleccionados
Aalto Pagos Seleccionados
Aalto Pagos Seleccionados
Aalto Pagos Seleccionados
Barista Pinotage
Braida Bricco Dell’Uccelone 2019
Cloudy Bay Sauvignon Blanc
DBR Lafite Les Legendes R Bordeaux Red
DBR Lafite R Saga Rouge
Dal Forno Romano Amarone Della Valpolicella
Dal Forno Romano Della Valpolicella
Domaines Ott Chateau Romassan Rose
Egon Muller Scharzhof Riesling
Egon Muller Scharzhof Riesling
Egon Muller Scharzhofberger Riesling Auslese
Egon Muller Scharzhofberger Riesling Auslese
Egon Muller Scharzhofberger Riesling Beerenauslese
Egon Muller Scharzhofberger Riesling Kabinett
Egon Muller Scharzhofberger Riesling Spatlese
Egon Muller Scharzhofberger Riesling Spatlese
Los Vascos Cabernet Sauvignon
Los Vascos Cromas Grand Reserva Carmenere
Los Vascos Cromas Grand Reserva Carmenere
Los Vascos Le Dix
Los Vascos Sauvignon Blanc
Luce Brunello Di Montalcino
Luce Della Vite Luce
Luce Lucente
Minuty M De Minuty Rose
Opus One
Opus One
Penfolds Bin 128
Penfolds Bin 2
Penfolds Bin 28
Penfolds Bin 389
Penfolds Bin 407
Penfolds Bin 707
Penfolds Bin 8
Penfolds Grange
Penfolds Koonunga Hill Shiraz Cabernet
Penfolds RWT Bin 798 Shiraz
Penfolds St. Henri
Quintarelli Giuseppe Amarone Classico
Quintarelli Giuseppe Valpolicella Classico
Rioja Alta Gran Reserva 890
Rioja Alta Gran Reserva 904
Rioja Alta Vina Ardanza
Tenuta Dell'ornellaia Le Serre Nuove
Tenuta Dell'ornellaia Le Volte
Tenuta Dell'ornellaia Ornellaia
Tenuta Di Biserno Biserno
Tenuta Di Biserno Il Pino
Tenuta Di Biserno Il Pino
Tenuta Di Biserno Il Pino
Tenuta Di Biserno Insoglio
Tenuta San Guido Guidalberto
Tenuta San Guido Guidalberto
Tenuta San Guido Guidalberto
Tenuta San Guido Le Difese
Tenuta San Guido Sassicaia
Tenuta San Guido Sassicaia
The Chocolate Block
Kweichow Moutai Chiew
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