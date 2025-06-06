# progress_tracker.py
"""
Script: progress_tracker.py

Keeps track of which Lernziele have been processed, persisting state to a JSON file
so that the pipeline can resume where it left off.
"""
import os
import json

DEFAULT_PATH = "progress.json"


def load_progress(path: str = DEFAULT_PATH) -> dict:
    """
    Load the progress JSON file if it exists, or return an empty dict.

    Returns:
        A dict mapping Veranstaltung titles to lists of processed Lernziel strings.
    """
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(progress: dict, path: str = DEFAULT_PATH) -> None:
    """
    Persist the progress dict to a JSON file.
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def is_done(progress: dict, veranstaltung: str, lernziel: str) -> bool:
    """
    Check if a given Lernziel for a Veranstaltung has already been processed.
    """
    return lernziel in progress.get(veranstaltung, [])


def mark_done(progress: dict, veranstaltung: str, lernziel: str) -> None:
    """
    Record that a Lernziel for a Veranstaltung has been processed.
    """
    if veranstaltung not in progress:
        progress[veranstaltung] = []
    if lernziel not in progress[veranstaltung]:
        progress[veranstaltung].append(lernziel)
