from integrations.gsheets_integration import load_master_from_gsheets
df = load_master_from_gsheets()
print(df.head())
print(df.shape)