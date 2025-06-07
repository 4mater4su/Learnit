#!/usr/bin/env python3
"""
flashcard_manager.py

A single script to:
  - add  → generate + save a new flashcard batch (PDF + pages + learning goal)
  - list → show all existing batches
  - review → quiz yourself on a chosen batch, with per-batch progress tracking

Usage:
  python flashcard_manager.py add    --pdf "PDFs/M10_komplett.pdf" \
                                     --pages 25 25 \
                                     --goal "Das gestörte Gangmuster bei einer Coxa valga und Coxa vara beschreiben können." \
                                     --outdir flashcards

  python flashcard_manager.py list   --outdir flashcards

  python flashcard_manager.py review --json flashcards/coxa_valga_vara_flashcards.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Tuple

from openai import OpenAI
from PyPDF2 import PdfReader, PdfWriter

# ─────────────────────────── CONFIG ───────────────────────────
CLIENT = OpenAI()  # assumes you have OPENAI_API_KEY set

PROGRESS_PATH = "progress.json"  # stores all batches’ progress

# ──────────────────── PDF EXTRACTION & FLASHCARD GEN ────────────────────

def extract_pdf_pages(input_pdf: str, output_pdf: str, start: int, end: int) -> None:
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
    extract_pdf_pages(pdf_path, extracted_pdf, start, end)

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


def run_console_flashcards(flashcards: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    For each card:
      1) Show Q
      2) Wait ENTER
      3) Show A
      4) Ask for rating [1=Easy, 2=Medium, 3=Hard]
    Returns a list of {"question", "answer", "rating"}.
    """
    studied_cards: List[Dict[str, Any]] = []
    total = len(flashcards)

    print("\n=== Flashcard Review ===\n")
    print("Anleitung:")
    print("  1) Frage lesen.")
    print("  2) ENTER drücken, um Antwort zu zeigen.")
    print("  3) Karte bewerten [1=Einfach, 2= Mittel, 3= Schwer].")
    print("  4) ENTER drücken, um weiterzumachen.\n")

    for idx, card in enumerate(flashcards, start=1):
        question = card["question"]
        answer = card["answer"]

        print(f"Karte {idx}/{total}")
        print("-" * 40)
        print("Q:", question)
        input("\nENTER drücken, um Antwort zu zeigen…")

        print("\nA:", answer)
        while True:
            rating_str = input("\nBewertung [1=Einfach,2=Mittel,3=Schwer]: ").strip()
            if rating_str in {"1", "2", "3"}:
                rating = int(rating_str)
                break
            print("Ungültige Eingabe – bitte 1, 2 oder 3 eingeben.")

        studied_cards.append({
            "question": question,
            "answer": answer,
            "rating": rating
        })
        print("\n" + ("=" * 40) + "\n")

    return studied_cards


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


def print_goal_progress(batch_key: str, path: str = PROGRESS_PATH) -> None:
    """
    Print aggregated stats for one batch_key from progress.json.
    """
    progress = _load_progress(path)
    goal_block = progress.get(batch_key)
    if not goal_block:
        print("\n(Keine vorherigen Fortschritte aufgezeichnet.)")
        return

    print(f"\n=== Fortschritt – {batch_key} ===")
    idx = 1
    for q, stats in goal_block.items():
        if q.startswith("_"):
            continue
        print(f"{idx}. Q: {q}")
        print(f"   A: {stats['answer']}")
        print(f"   Wiederholungen: {stats['repetitions']}")
        print(f"   Bewertungen: {stats['ratings']}")
        print(f"   Durchschnittliche Bewertung: {stats['avg_rating']}")
        print("-" * 40)
        idx += 1


def review_batch(json_path: str) -> None:
    """
    1) Load the batch JSON.
    2) Run the console quiz.
    3) Merge progress into progress.json under a composite key.
    4) Print session’s results + aggregated progress.
    """
    data = load_flashcard_data(json_path)
    flashcards = data["flashcards"]
    learning_goal = data.get("learning_goal", "Kein Lernziel")
    page_range = data.get("page_range", "")
    batch_key = f"{learning_goal} (Seiten {page_range})"

    print(f"\nLernziel: {learning_goal}")
    print(f"Seiten: {page_range}\n")

    results = run_console_flashcards(flashcards)
    timestamp = datetime.now().isoformat(timespec="seconds")
    update_progress(batch_key, results, timestamp=timestamp)

    print("\n=== Sitzung abgeschlossen ===\n")
    for i, entry in enumerate(results, 1):
        print(f"{i}. Q: {entry['question']}")
        print(f"   A: {entry['answer']}")
        print(f"   Bewertung: {entry['rating']}")
        print("-" * 40)

    print_goal_progress(batch_key)


# ─────────────────────────── Utility: LIST BATCHES ───────────────────────────

def list_batches(flashcards_dir: str) -> None:
    """
    Look in flashcards_dir for all .json files and print their filenames + a summary line.
    """
    if not os.path.isdir(flashcards_dir):
        print(f"Fehler: Verzeichnis '{flashcards_dir}' existiert nicht.")
        return

    files = sorted([f for f in os.listdir(flashcards_dir) if f.endswith(".json")])
    if not files:
        print(f"(Keine JSON-Dateien in '{flashcards_dir}' gefunden.)")
        return

    print(f"\nVerfügbare Flashcard-Batches in '{flashcards_dir}':\n")
    for fn in files:
        path = os.path.join(flashcards_dir, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            goal = data.get("learning_goal", "<kein Lernziel>")
            pages = data.get("page_range", "")
            print(f" • {fn:30}  →  {goal} [Seiten {pages}]")
        except Exception:
            print(f" • {fn:30}  →  (Fehler beim Einlesen)")
    print()


# ────────────────────────────────── MAIN ────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Flashcard Manager: add | list | review"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # --- add subcommand ---
    add_p = sub.add_parser("add", help="Neues Flashcard-Batch aus PDF erzeugen")
    add_p.add_argument(
        "--pdf", "-p", required=True,
        help="Pfad zur PDF-Datei"
    )
    add_p.add_argument(
        "--pages", "-g", nargs=2, type=int, required=True,
        metavar=("START", "END"),
        help="Seitenbereich (1-basiert, inklusive), z.B. --pages 13 13"
    )
    add_p.add_argument(
        "--goal", "-l", required=True,
        help="Lernziel (z.B. \"Schritte der endogenen Calcitriolsynthese...\")"
    )
    add_p.add_argument(
        "--outdir", "-o", default="flashcards",
        help="Verzeichnis, in dem JSON gespeichert wird"
    )

    # --- list subcommand ---
    list_p = sub.add_parser("list", help="Alle vorhandenen Flashcard-Batches auflisten")
    list_p.add_argument(
        "--outdir", "-o", default="flashcards",
        help="Verzeichnis, in dem Batch-JSON-Dateien liegen"
    )

    # --- review subcommand ---
    rev_p = sub.add_parser("review", help="Ein bestehendes Batch-JSON quizzen")
    rev_p.add_argument(
        "--json", "-j", required=True,
        help="Pfad zu einer Batch-JSON-Datei (aus dem 'add'-Schritt)"
    )

    args = parser.parse_args()

    if args.cmd == "add":
        pdf_path = args.pdf
        start, end = args.pages
        learning_goal = args.goal
        outdir = args.outdir
        os.makedirs(outdir, exist_ok=True)

        # Build a filename from goal + pages, slugified
        safe_goal = learning_goal.strip().replace(" ", "_")[:30]
        filename = f"{safe_goal}_{start}_{end}.json"
        output_json = os.path.join(outdir, filename)

        if os.path.exists(output_json):
            print(f"Fehler: '{output_json}' existiert bereits. Wählen Sie einen anderen Namen oder löschen Sie die alte Datei.")
            sys.exit(1)

        print(f"Erzeuge Flashcards für '{learning_goal}' (Seiten {start}–{end})...")
        try:
            flashcards = generate_flashcards_from_pdf(
                pdf_path=pdf_path,
                page_range=(start, end),
                learning_goal=learning_goal,
                output_json_path=output_json
            )
            print(f"→ Flashcards gespeichert in: {output_json}")
            print(f"   ({len(flashcards)} Karten generiert.)")
        except Exception as e:
            print(f"FEHLER beim Generieren: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.cmd == "list":
        list_batches(args.outdir)

    elif args.cmd == "review":
        review_batch(args.json)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
