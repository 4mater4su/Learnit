#!/usr/bin/env python3
"""
flashcard_manager.py

"""

import json
import os
import sys
from typing import Any, Dict, List, Tuple

from openai import OpenAI
from PyPDF2 import PdfReader, PdfWriter

# ─────────────────────────── CONFIG ───────────────────────────
CLIENT = OpenAI()  # assumes you have OPENAI_API_KEY set

PROGRESS_PATH = "progress.json"  # stores all batches’ progress

# ──────────────────── PDF EXTRACTION & FLASHCARD GEN ────────────────────

def slice_pdf(input_pdf: str, output_pdf: str, start: int, end: int) -> None:
    """
    Extracts pages [start..end] from input_pdf into output_pdf.
    Page numbers are 1-based inclusive.
    """
    reader = PdfReader(input_pdf)
    writer = PdfWriter()
    total_pages = len(reader.pages)
    if start < 1 or end > total_pages or start > end:
        raise ValueError(f"Invalid page range {start}-{end} for a PDF with {total_pages} pages.")
    for i in range(start - 1, end):
        writer.add_page(reader.pages[i])
    with open(output_pdf, "wb") as f:
        writer.write(f)


def generate_flashcards_from_pdf(
    pdf_path: str,
    page_range: Tuple[int, int],
    learning_goal: str,
    output_json_path: str,
    temp_dir: str = "temp"
) -> List[Dict[str, str]]:
    """
    1) Extracts the specified page range into a small temp PDF.
    2) Uploads that PDF to OpenAI Files.
    3) Asks GPT-4 to return 3-5 Q&A pairs in strict JSON.
    4) Embeds that into a JSON file that also records learning_goal & page_range.

    Returns the list of flashcards (each dict with "question"/"answer").
    """
    start, end = page_range
    os.makedirs(temp_dir, exist_ok=True)
    extracted_pdf = os.path.join(temp_dir, f"extracted_{start}_{end}.pdf")
    slice_pdf(pdf_path, extracted_pdf, start, end)

    # Upload to OpenAI Files
    with open(extracted_pdf, "rb") as f:
        uploaded = CLIENT.files.create(file=f, purpose="user_data")

    prompt = (
        f"Bitte erstelle 3–5 Fragen und Antworten in Verbindung mit dem Lernziel: {learning_goal}"
        f"Gib sie im JSON-Format zurück:\n\n"
        f"{{\n"
        f"  \"flashcards\": [\n"
        f"    {{\"question\": \"...\", \"answer\": \"...\"}},\n"
        f"    …\n"
        f"  ]\n"
        f"}}"
    )

    schema = {
        "type": "object",
        "properties": {
            "flashcards": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "answer": {"type": "string"}
                    },
                    "required": ["question", "answer"],
                    "additionalProperties": False
                },
                "minItems": 1
            }
        },
        "required": ["flashcards"],
        "additionalProperties": False
    }

    response = CLIENT.responses.parse(
        model="gpt-4.1-nano",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_file", "file_id": uploaded.id},
                    {"type": "input_text", "text": prompt}
                ]
            }
        ],
        text={
            "format": {
                "type": "json_schema",
                "strict": True,
                "name": "flashcard_generation",
                "schema": schema
            }
        }
    )

    raw_json = None
    try:
        raw_json = response.output[0].content[0].text
        parsed = json.loads(raw_json)
        flashcards = parsed["flashcards"]
    except Exception as e:
        raise ValueError(f"Fehler beim Parsen der Modellantwort: {e}\n\nRohantwort:\n{raw_json}")

    # Build full batch JSON
    batch = {
        "learning_goal": learning_goal,
        "page_range": f"{start}-{end}",
        "pdf_path": pdf_path,
        "flashcards": flashcards
    }

    # Save to JSON
    with open(output_json_path, "w", encoding="utf-8") as out_f:
        json.dump(batch, out_f, indent=2, ensure_ascii=False)

    return flashcards


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
