"""
Script: excel_parser.py
"""
import pandas as pd


def load_data(file_path: str) -> dict:
    """
    Load the Excel file, filter to the required columns, group the rows by
    "Veranstaltung: Titel", and return a dictionary mapping each Veranstaltung
    title to a list of its record dictionaries.

    Args:
        file_path: Path to the input Excel file.

    Returns:
        A dict where keys are Veranstaltung titles and values are lists of
        dicts, each containing the columns:
        Modul, akad. Periode, Woche, LZ-Dimension, LZ-Kognitionsdimension, Lernziel.
    """
    # Read the Excel file
    df = pd.read_excel(file_path)

    # Keep only the needed columns
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

    # Group by Veranstaltung title and convert sub-DataFrames to list of records
    grouped = {
        veranst: group.to_dict(orient="records")
        for veranst, group in df.groupby("Veranstaltung: Titel")
    }

    return grouped
