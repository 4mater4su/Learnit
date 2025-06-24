#!/usr/bin/env python3
"""batch_pagefinder.py: Batch PageFinder runner.

Perform semantic search and copy for every learning goal in an Excel file across a specified vector store (or all stores if none is set).
Saves pages into <outdir>/<sanitized_goal>/. Configure paths below by editing the variables."""

import re
from pathlib import Path

from learnit import LearnIt
from utils.excel_parser import load_data

# === Configuration: edit these paths ===
EXCEL_PATH = "/Users/robing/Desktop/projects/Learnit/lernziele/M10-LZ.xlsx"  # Path to your Excel file with 'Lernziel' column
OUTDIR = "archive"                                                     # Root directory to save pages
VECSTORE_ID_DIR = ".vector_store_ids"                                 # Directory holding .id files
# To run only for one store, set this to the store name (without .id). Leave as None to run on all stores.
SINGLE_STORE: str | None = "Silbernagl_Taschenatlas_Physiologie_8_Aufl_2012_VS.id"
# ======================================

def sanitize_dirname(name: str) -> str:
    """Keep letters, numbers, dash/underscore. Replace spaces and other chars with underscores."""
    sanitized = re.sub(r'[^A-Za-z0-9_\-]', '_', name.replace(' ', '_'))
    return sanitized[:100]


def get_vector_stores(id_dir: str = VECSTORE_ID_DIR) -> list[str]:
    """Return either the single specified store or discover all vector store names by listing *.id files."""
    if SINGLE_STORE:
        print(f"Using specified vector store: {SINGLE_STORE}")
        return [SINGLE_STORE]
    id_path = Path(id_dir)
    if not id_path.exists():
        raise FileNotFoundError(f"Vector ID directory not found: {id_dir}")
    stores = [p.stem for p in id_path.glob("*.id")]
    print(f"Discovered vector stores: {stores}")
    return stores


def load_goals_from_excel(path: str) -> list[str]:
    """Load 'Lernziel' column from the given Excel file."""
    print(f"Loading learning goals from Excel: {path}")
    df = load_data(path)
    if "Lernziel" not in df.columns:
        raise ValueError("Excel file must have a 'Lernziel' column")
    goals = df["Lernziel"].astype(str).tolist()
    print(f"Loaded {len(goals)} learning goals.")
    return goals


def main():
    print("Starting batch PageFinder...")
    # Load all goals
    goals = load_goals_from_excel(EXCEL_PATH)

    # Determine stores to use
    stores = get_vector_stores()

    root_out = Path(OUTDIR)
    root_out.mkdir(parents=True, exist_ok=True)
    print(f"Ensured output directory exists: {root_out.resolve()}")

    total_tasks = len(stores) * len(goals)
    print(f"Processing {total_tasks} tasks ({len(stores)} stores x {len(goals)} goals)\n")

    # Iterate stores and goals
    for i, store in enumerate(stores, start=1):
        print(f"[{i}/{len(stores)}] Using store: {store}")
        li = LearnIt(store_name=store)
        for j, goal in enumerate(goals, start=1):
            sanitized = sanitize_dirname(goal)
            dest_dir = root_out / sanitized
            dest_dir.mkdir(parents=True, exist_ok=True)
            print(f"  -> [{j}/{len(goals)}] Goal: '{sanitized}'", end=" ")
            copied = li.search_and_copy_pages(query=goal, dest_dir=dest_dir)
            print(f"=> {len(copied)} pages copied.")
    print("\nBatch PageFinder completed successfully.")


if __name__ == "__main__":
    main()
