#!/usr/bin/env python3
"""
Module: excel_parser.py

Provides functionality to load the Excel sheet and return a DataFrame
filtered to the required columns, preserving the original row order.
"""
import pandas as pd


def load_data(file_path: str) -> pd.DataFrame:
    """
    Load the Excel file and filter to the required columns, preserving row order.

    Args:
        file_path: Path to the input Excel file.

    Returns:
        A pandas DataFrame with the columns:
        Modul, akad. Periode, Woche, Veranstaltung: Titel,
        LZ-Dimension, LZ-Kognitionsdimension, Lernziel
    """
    cols = [
        "Modul",
        "akad. Periode",
        "Woche",
        "Veranstaltung: Titel",
        "LZ-Dimension",
        "LZ-Kognitionsdimension",
        "Lernziel"
    ]
    # Read only the needed columns, preserving their order
    df = pd.read_excel(file_path, usecols=cols)
    return df
