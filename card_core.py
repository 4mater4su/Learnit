#!/usr/bin/env python3
"""
card_core.py

"""

import json
import os
import sys
from typing import Any, Dict, List, Tuple

# ─────────────────────────── CONFIG ───────────────────────────

PROGRESS_PATH = "progress.json"  # stores all batches’ progress

# ───────────────────────── FLASHCARD REVIEW + PROGRESS ─────────────────────────

def load_flashcard_data(json_path: str) -> Dict[str, Any]:
    if not os.path.exists(json_path):
        print(f"ERROR: Could not find {json_path}", file=sys.stderr)
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    flashcards = data.get("flashcards")
    if not isinstance(flashcards, list) or not flashcards:
        print("ERROR: JSON must contain a non-empty 'flashcards' list.", file=sys.stderr)
        sys.exit(1)
    return data


def _load_progress(path: str = PROGRESS_PATH) -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_progress(progress: dict, path: str = PROGRESS_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def update_progress(
    batch_key: str,
    session_results: List[Dict[str, Any]],
    *,
    timestamp: str | None = None,
    path: str = PROGRESS_PATH
) -> None:
    """
    Merge one quiz session into the persistent progress file.
    Each batch_key is something like "Mein Lernziel (Seiten 5–7)".
    """
    progress = _load_progress(path)
    goal_block = progress.setdefault(batch_key, {})

    for entry in session_results:
        q, a, r = entry["question"], entry["answer"], entry["rating"]
        stats = goal_block.setdefault(q, {
            "answer": a, "repetitions": 0, "ratings": []
        })
        stats["repetitions"] += 1
        stats["ratings"].append(r)
        stats["avg_rating"] = round(sum(stats["ratings"]) / len(stats["ratings"]), 2)

    if timestamp:
        goal_block.setdefault("_sessions", []).append(timestamp)

    _save_progress(progress, path)


def remove_batch_progress(batch_key: str, path: str = PROGRESS_PATH):
    """Remove all progress entries for a batch_key."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        progress = json.load(f)
    if batch_key in progress:
        del progress[batch_key]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)


def remove_card_progress(batch_key: str, question: str, path: str = PROGRESS_PATH):
    """Remove progress for a specific question in a batch."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        progress = json.load(f)
    block = progress.get(batch_key)
    if block and question in block:
        del block[question]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)
