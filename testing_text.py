from text_state import TextState

raw = "FTL. Glenfiddich 15YO GBX 6x70clx40% @ Euro 28.75 per bottle, T2, 2 weeks"

session = TextState(raw)
df_final = session.run()

print("[DEBUG testing_text] df_final:")
print(df_final)