#!/usr/bin/env python3
"""
flashcard_pdf_with_progress.py

Contains functions to:
  - Extract pages from a PDF
  - Generate initial flashcards (Q&A) from a PDF slice
  - Generate additional, non-overlapping flashcards based on existing progress
  - Persist a long-term progress file tracking repetitions and ratings

Usage examples:
  from this_module import generate_flashcards_from_pdf, generate_additional_flashcards_from_pdf
"""

import json
import os
import shutil
import uuid
from datetime import datetime
from typing import List, Dict, Tuple

from openai import OpenAI
from PyPDF2 import PdfReader, PdfWriter

client = OpenAI()

# ──────────────────────────── PDF extraction ────────────────────────────────

def extract_pdf_pages(input_pdf: str, output_pdf: str, start: int, end: int) -> None:
    """
    Extracts pages [start..end] (1-based inclusive) from input_pdf
    and writes them into output_pdf.
    """
    reader = PdfReader(input_pdf)
    writer = PdfWriter()
    for i in range(start - 1, end):
        writer.add_page(reader.pages[i])
    with open(output_pdf, "wb") as f:
        writer.write(f)


# ─────────────────── Initial flashcard generation ──────────────────────────

def generate_flashcards_from_pdf(
    pdf_path: str,
    page_range: Tuple[int, int],
    learning_goal: str,
    output_json_path: str,
    output_pdf: str = "temp_extracted.pdf"
) -> List[Dict[str, str]]:
    """
    Generates 3–5 flashcards (Q&A) from a selected PDF page range for a given learning goal.
    Saves them in output_json_path and returns the list of cards.

    Args:
        pdf_path: Full PDF document path.
        page_range: Tuple (start_page, end_page), 1-based inclusive.
        learning_goal: The learning objective.
        output_json_path: Path where the flashcards will be saved as JSON.
        output_pdf: (Optional) Intermediate file name for extracted pages.

    Returns:
        List of flashcard dictionaries: [{"question": str, "answer": str}, …]
    """
    start, end = page_range
    extract_pdf_pages(pdf_path, output_pdf, start, end)

    with open(output_pdf, "rb") as f:
        uploaded_file = client.files.create(file=f, purpose="user_data")

    prompt = (
        f"Das folgende PDF enthält Informationen zum Lernziel:\n"
        f"„{learning_goal}“.\n"
        f"Bitte extrahiere daraus 3 bis 5 Fragen mit den passenden Antworten.\n"
        f"Gib sie im folgenden JSON-Format zurück:\n\n"
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
                "minItems": 3,
                "maxItems": 5
            }
        },
        "required": ["flashcards"],
        "additionalProperties": False
    }

    response = client.responses.parse(
        model="gpt-4.1-nano",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_file", "file_id": uploaded_file.id},
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

    try:
        raw_json = response.output[0].content[0].text
        parsed = json.loads(raw_json)
        flashcards = parsed["flashcards"]
    except Exception as e:
        raise ValueError(f"Fehler beim Parsen der Modellantwort: {e}")

    # Save to JSON file
    with open(output_json_path, "w", encoding="utf-8") as json_out:
        json.dump({
            "learning_goal": learning_goal,
            "page_range": f"{start}-{end}",
            "flashcards": flashcards
        }, json_out, indent=2, ensure_ascii=False)

    return flashcards


# ──────────────────────── Safe progress helpers ─────────────────────────────

PROGRESS_PATH = "progress.json"

def _backup_progress(path: str) -> None:
    """
    Make a timestamped backup of the progress file once, the first time we write.
    E.g. progress_20250606T154012_abcd.json
    """
    if not os.path.exists(path):
        return
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    uid = uuid.uuid4().hex[:4]
    backup_name = f"{os.path.splitext(path)[0]}_{ts}_{uid}.json"
    shutil.copy2(path, backup_name)

def _load_progress(path: str = PROGRESS_PATH) -> dict:
    """
    Load the persistent progress JSON, or return an empty dict if none exists.
    """
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_progress(progress: dict, path: str = PROGRESS_PATH) -> None:
    """
    Save the merged progress back to disk. Creates one backup per session.
    """
    if not getattr(_save_progress, "_backed_up", False):
        _backup_progress(path)
        _save_progress._backed_up = True
    with open(path, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)

def _merge_into_progress(
    learning_goal: str,
    new_cards: List[Dict[str, str]],
    *,
    path: str = PROGRESS_PATH,
) -> None:
    """
    Append NEW Q-A pairs into the persistent progress file without overwriting existing entries.
    If a question already exists (exact text match), leave its historical stats intact.
    """
    progress = _load_progress(path)
    goal_block = progress.setdefault(learning_goal, {})

    for card in new_cards:
        q = card["question"]
        a = card["answer"]

        # If this question text already exists, do not modify its stats
        if q in goal_block:
            continue

        goal_block[q] = {
            "answer": a,
            "repetitions": 0,
            "ratings": [],
            "avg_rating": None
        }

    # Record this auto-generation session
    goal_block.setdefault("_sessions", []).append(
        f"auto-generation:{datetime.now().isoformat(timespec='seconds')}"
    )

    _save_progress(progress, path)


# ──────────── Generate additional, non-overlapping flashcards ───────────────

def generate_additional_flashcards_from_pdf(
    pdf_path: str,
    page_range: Tuple[int, int],
    learning_goal: str,
    output_json_path: str,
    *,
    progress_path: str = PROGRESS_PATH,
    output_pdf: str = "temp_extracted.pdf",
    n_cards: int | Tuple[int, int] = (3, 5),
) -> List[Dict[str, str]]:
    """
    Like `generate_flashcards_from_pdf`, but instructs the model to produce Q&A pairs
    that cover aspects not yet quizzed and with distinct phrasing. Also appends
    these new cards into the persistent progress file (without overwriting old data).

    Args:
        pdf_path: Path to the full PDF document.
        page_range: Tuple (start_page, end_page), 1-based inclusive.
        learning_goal: The learning objective string (must match the key in progress).
        output_json_path: Where to write the fresh flashcards JSON.
        progress_path: Path to the long-term progress JSON (default: "progress.json").
        output_pdf: Temporary file name for extracted pages (default: "temp_extracted.pdf").
        n_cards: Either an int or a (min, max) tuple for how many Q&A pairs to generate.

    Returns:
        The list of newly generated flashcards (each a dict with "question" and "answer").
    """
    # 1. Load existing progress to know which Q&A have already been used
    progress = _load_progress(progress_path)
    seen_cards = progress.get(learning_goal, {})
    seen_qas = [
        {"question": q, "answer": v["answer"]}
        for q, v in seen_cards.items()
        if not q.startswith("_")
    ]

    # 2. Extract the specified page range
    start, end = page_range
    extract_pdf_pages(pdf_path, output_pdf, start, end)

    # 3. Build the prompt, embedding the list of already-covered Q&A
    already_covered = json.dumps(seen_qas, ensure_ascii=False, indent=2)
    if isinstance(n_cards, int):
        min_cards = max_cards = n_cards
    else:
        min_cards, max_cards = n_cards

    prompt = f"""
Das folgende PDF enthält Informationen zum Lernziel:
„{learning_goal}“.

Hier sind Fragen & Antworten, die der Lernende bereits bearbeitet hat
(DU DARFST KEINE davon inhaltlich oder wörtlich wiederholen!):

{already_covered}

Bitte extrahiere {min_cards}–{max_cards} NEUE Fragen,
• die Aspekte behandeln, die oben noch nicht vorkommen,
• deren Formulierungen sich klar von allen bisherigen unterscheiden
  (andere Satzstruktur, Synonyme, neue Blickwinkel),
• die dennoch korrekt und prägnant sind.

Gib sie exakt in diesem JSON-Format zurück:

{{
  "flashcards": [
    {{"question": "...", "answer": "..."}},
    …
  ]
}}
""".strip()

    # 4. JSON schema enforcing the card count and keys
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
                "minItems": min_cards,
                "maxItems": max_cards
            }
        },
        "required": ["flashcards"],
        "additionalProperties": False
    }

    # 5. Upload the extracted PDF slice and call the model
    with open(output_pdf, "rb") as f:
        uploaded_file = client.files.create(file=f, purpose="user_data")

    response = client.responses.parse(
        model="gpt-4.1-nano",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_file", "file_id": uploaded_file.id},
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

    try:
        raw_json = response.output[0].content[0].text
        parsed = json.loads(raw_json)
        flashcards = parsed["flashcards"]
    except Exception as e:
        raise ValueError(f"Fehler beim Parsen der Modellantwort: {e}")

    # 6. Persist the newly generated flashcards into a dedicated JSON file
    with open(output_json_path, "w", encoding="utf-8") as out:
        json.dump(
            {
                "learning_goal": learning_goal,
                "page_range": f"{start}-{end}",
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "flashcards": flashcards
            },
            out,
            indent=2,
            ensure_ascii=False
        )

    # 7. Merge these new cards into the long-term progress file (without overwriting existing stats)
    _merge_into_progress(learning_goal, flashcards, path=progress_path)

    return flashcards


# ───────────────────────────────── please ignore below ─────────────────────────
# If you want to test this module directly, you can write a small __main__ block,
# but typically you'd import these functions into another script or REPL.
# ───────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Test sequence using:
      - pdf_path = "PDFs/M10_komplett.pdf"
      - page_range = (13, 13)
      - learning_goal = "Beschreibe die Schritte der endogenen Calcitriolsynthese."
    """

    import sys

    # 1) Define inputs
    pdf_path = "PDFs/M10_komplett.pdf"
    page_range = (13, 13)
    learning_goal = "Beschreibe die Schritte der endogenen Calcitriolsynthese."

    # 2) Paths for output JSON files
    initial_output = "calcitriol_flashcards.json"
    additional_output = "calcitriol_additional_flashcards.json"

    print("\n=== SCHRITT 1: Initiale Flashcard-Generierung ===")
    try:
        initial_cards = generate_flashcards_from_pdf(
            pdf_path=pdf_path,
            page_range=page_range,
            learning_goal=learning_goal,
            output_json_path=initial_output
        )
        print(f"Es wurden {len(initial_cards)} initiale Karten erzeugt. Fragen:")
        for i, c in enumerate(initial_cards, 1):
            print(f"  {i}. {c['question']}")
    except Exception as e:
        print(f"Fehler bei der initialen Generierung: {e}")
        sys.exit(1)

    print("\n=== SCHRITT 2: Zusätzliche Flashcard-Generierung ===")
    try:
        new_cards = generate_additional_flashcards_from_pdf(
            pdf_path=pdf_path,
            page_range=page_range,
            learning_goal=learning_goal,
            output_json_path=additional_output
        )
        print(f"Es wurden {len(new_cards)} zusätzliche Karten erzeugt. Fragen:")
        for i, c in enumerate(new_cards, 1):
            print(f"  {i}. {c['question']}")
    except Exception as e:
        print(f"Fehler bei der zusätzlichen Generierung: {e}")
        sys.exit(1)

    print("\n=== FERTIG. Überprüfe „progress.json“, um den Fortschritt zu sehen. ===\n")
