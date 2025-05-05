import pandas as pd

# 1) Load the Excel file into a DataFrame
file_path = "/Users/robing/Desktop/projects/Learnit/M10-LZ.xlsx"
df = pd.read_excel(file_path)       # by default reads the first sheet

# 2) Quick sanity checks
print("Columns:", df.columns.tolist())
print("First 5 rows:\n", df.head(), sep="\n")

# 3) Iterate through every row
#    - Using iterrows (gives you an index and a Series per row)
for idx, row in df.iterrows():
    # Example: access a cell by column name
    #   some_val = row["YourColumnName"]
    #print(f"Row {idx} data:", row.to_dict())
    pass


# This builds a dict: { veranstaltung_1: [ziel1, ziel2, …], veranstaltung_2: […], … }
vz_series = df.groupby("Veranstaltung: Titel")["Lernziel"].apply(list)
vz_dict   = vz_series.to_dict()

for veranstaltung, lernziele in vz_dict.items():
    print(f"{veranstaltung}:")
    print("  Lernziele:")
    for idx, ziel in enumerate(lernziele, start=1):
        print(f"    {idx}. {ziel}")
    print()


