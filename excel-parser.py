import pandas as pd

# 1) Load and filter the DataFrame
file_path = "/Users/robing/Desktop/projects/Learnit/M10-LZ.xlsx"
df = pd.read_excel(file_path)
cols = [
    "Modul",
    "akad. Periode",
    "Woche",
    "Veranstaltung: Titel",
    "LZ-Dimension",
    "LZ-Kognitionsdimension",
    "Lernziel"
]
df = df[cols]

# 2) Group into dict of lists of records
vz_dict = {
    veranst: grp.to_dict(orient="records")
    for veranst, grp in df.groupby("Veranstaltung: Titel")
}

# 3) Print, showing Modul/Periode/Woche only once per Veranstaltung
for veranst, records in vz_dict.items():
    # Header
    print(f"Veranstaltung: {veranst}")
    print("=" * (14 + len(veranst)))
    
    # Extract the shared info from the first record
    first = records[0]
    print(f"Modul:           {first['Modul']}")
    print(f"akad. Periode:   {first['akad. Periode']}")
    print(f"Woche:           {first['Woche']}\n")
    
    # Now list each Lernziel with its dimensions
    print("Lernziele:")
    for i, rec in enumerate(records, start=1):
        print(f"  {i}. {rec['Lernziel']}")
        print(f"       – LZ-Dimension:    {rec['LZ-Dimension']}")
        print(f"       – Kogn.-Dimension: {rec['LZ-Kognitionsdimension']}")
    print("\n")  # blank line between Veranstaltungen
