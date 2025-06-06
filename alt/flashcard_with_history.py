import os
import json
import glob
import time
from typing import List, Dict, Tuple
from datetime import datetime
from openai import OpenAI
from PyPDF2 import PdfReader, PdfWriter

# ────────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────────────────────────────────────

# Pfad zu deinem PDF (der das ganze Modul enthält)
PDF_PATH = "PDFs/M10_komplett.pdf"

# Excel-Parser o. Ä. liefert dir den Lernziel‐Text; hier als Beispiel:
LEARNING_GOAL = "Beschreibe die Schritte der endogenen Calcitriolsynthese."

# Wo die Berichte der vergangenen Sessions liegen; jede Datei muss gültiges JSON sein:
# - Jede JSON-Datei ist ein Array von { "question": str, "answer": str, "rating": int, "learning_goal": str }.
# - Die Dateien sollten so benannt sein, dass du anhand ihres Zeitstempels sortieren kannst,
#   z.B. "report_Calcitriol_2025-06-06T15-30-00.json".
REPORTS_DIR = "reports"

# Wie viele der letzten Sessions (Reports) pro Lernziel wir heranziehen
N_RECENT = 3

# Wo wir die neu generierten Flashcards speichern
OUTPUT_JSON = "next_session_flashcards.json"

# Welches Modell wir verwenden (Nano)
MODEL_NAME = "gpt-4.1-nano"

# ────────────────────────────────────────────────────────────────────────────────

client = OpenAI()


def extract_pdf_pages(input_pdf: str, output_pdf: str, start: int, end: int):
    """
    Extrahiert Seiten [start, end] (1‐basierter Index) aus input_pdf und speichert in output_pdf.
    """
    reader = PdfReader(input_pdf)
    writer = PdfWriter()
    for i in range(start - 1, end):
        writer.add_page(reader.pages[i])
    with open(output_pdf, "wb") as f:
        writer.write(f)


def load_recent_reports(
    reports_dir: str,
    learning_goal: str,
    n: int
) -> List[Dict]:
    """
    Liest alle JSON-Dateien in reports_dir, filtert nach learning_goal,
    sortiert nach Dateiname (oder Dateizeit) absteigend und gibt die letzten n.
    Jede Datei sollte ein Array von Objekten sein, die mindestens
    { "question":..., "answer":..., "rating":..., "learning_goal":... } enthalten.
    """
    pattern = os.path.join(reports_dir, "*.json")
    candidates = []

    for path in glob.glob(pattern):
        try:
            with open(path, "r", encoding="utf-8") as f:
                arr = json.load(f)
            # Prüfe, ob mindestens eine Karte für das gesuchte Lernziel vorhanden ist
            for entry in arr:
                if entry.get("learning_goal") == learning_goal:
                    candidates.append((path, entry))
                    break
        except Exception:
            continue

    # Sortieren nach Dateinamen (falls das Zeitstempeln im Dateinamen steckt) oder nach modification_time
    # Wir nehmen hier modification_time als Fallback:
    candidates_sorted = sorted(
        {path: None for path, _ in candidates}.items(),
        key=lambda kv: os.path.getmtime(kv[0]),
        reverse=True
    )
    # Die Pfade herausdestillieren
    recent_paths = [path for path, _ in candidates_sorted[:n]]
    recent_reports = []
    for rp in recent_paths:
        try:
            with open(rp, "r", encoding="utf-8") as f:
                arr = json.load(f)
            # Filter nur jene Karten, die zum Lernziel passen
            for entry in arr:
                if entry.get("learning_goal") == learning_goal:
                    recent_reports.append(entry)
        except Exception:
            continue

    return recent_reports


def analyze_strengths_weaknesses(
    reports: List[Dict]
) -> Tuple[List[str], List[str]]:
    """
    Nimmt eine Liste von {question, answer, rating, learning_goal}, aggregiert
    die Ratings nach 'answer' (Konzept), und gibt zwei Listen zurück:
      - weak_answers: Konzepte (answer), deren Durchschnitts‐Rating ≥ 2.0
      - strong_answers: Konzepte (answer), deren Durchschnitts‐Rating ≤ 1.2 (also fast immer 'Easy')
    """
    stats: Dict[str, Dict[str, float]] = {}
    for entry in reports:
        ans = entry["answer"]
        r = entry["rating"]
        if ans not in stats:
            stats[ans] = {"count": 0, "sum_ratings": 0.0}
        stats[ans]["count"] += 1
        stats[ans]["sum_ratings"] += float(r)

    weak_answers = []
    strong_answers = []
    for ans, st in stats.items():
        avg = st["sum_ratings"] / st["count"]
        if avg >= 2.0:
            weak_answers.append(ans)
        elif avg <= 1.2:
            strong_answers.append(ans)

    return weak_answers, strong_answers


def generate_flashcards_with_history(
    pdf_excerpt: str,
    learning_goal: str,
    weak_answers: List[str],
    strong_answers: List[str],
    model: str = MODEL_NAME
) -> List[Dict[str, str]]:
    """
    Fragt das Modell, 3–5 QA-Paare für den gegebenen PDF-Text zu erstellen,
    mit Hinweis auf vergangene Stärken/Schwächen. Gibt eine Liste von
    { "question": ..., "answer": ... } zurück.
    """

    # Baue den Prompt
    prompt = f"""
Du bist ein Tutor für Medizinstudenten und hilfst dabei, Lernziele zu verankern.
Lernziel: "{learning_goal}".

In den letzten Sitzungen gab es folgende Beobachtungen:
- Schwache Konzepte (häufig mittel/hart bewertet): 
  {', '.join(weak_answers) if weak_answers else '– keine'}
- Starke Konzepte (meist leicht bewertet): 
  {', '.join(strong_answers) if strong_answers else '– keine'}

Bitte generiere 3 bis 5 Fragen mit den jeweiligen Antworten basierend auf dem beigefügten PDF-Abschnitt unten.
**Wichtige Anforderungen**:
1. Behandle den PDF-Text so, als wäre es das erste Mal, dass du ihn siehst.
2. Formuliere jede Frage **anders** (Wortwahl, Blickwinkel). 
3. Fokussiere besonders auf die Konzepte, die in den vergangenen Sitzungen als "schwach" identifiziert wurden (falls vorhanden).
4. Vermeide, bereits gestellte Fragen zu wiederholen; decke neue Aspekte und Perspektiven ab.
5. Gib das Ergebnis als JSON‐Schema: 
   {{
     "flashcards": [
       {{"question": "…", "answer": "…"}},
       …
     ]
   }}
- Jede ‘question’ muss den Inhalt des PDF-Abschnitts abfragen.
- Jede ‘answer’ muss kurz und präzise sein.

<PDF-Excerpt>
{pdf_excerpt}
</PDF-Excerpt>
"""

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

    # API-Aufruf
    response = client.responses.parse(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt}
                ]
            }
        ],
        text={
            "format": {
                "type": "json_schema",
                "strict": True,
                "name": "flashcard_with_history",
                "schema": schema
            }
        }
    )

    # Extrahiere die Liste von QA-Paaren:
    flashcards = response.output["flashcards"]  # List[{"question":..., "answer":...}]
    return flashcards


def main():
    # ────────────────────────────────────────────────────────────────────────────
    # Beispielseiten‐Bereich festlegen (z.B. Seiten 13–13)
    START_PAGE = 13
    END_PAGE = 13
    EXTRACTED_PDF = "temp_excerpt.pdf"
    # ────────────────────────────────────────────────────────────────────────────

    # 1) Extrahiere relevante Seite(n) aus dem PDF
    extract_pdf_pages(PDF_PATH, EXTRACTED_PDF, START_PAGE, END_PAGE)

    # 2) Lade die letzten N Reports für dieses Lernziel
    recent_reports = load_recent_reports(REPORTS_DIR, LEARNING_GOAL, N_RECENT)

    # 3) Analysiere Stärken/Schwächen anhand der Ratings
    weak_answers, strong_answers = analyze_strengths_weaknesses(recent_reports)

    # 4) Lese den PDF‐Excerpt‐Text, damit wir ihn im Prompt einbetten
    #    (Wir könnten auch das extrahierte PDF als file input schicken, falls Diagramme relevant sind.)
    with open(EXTRACTED_PDF, "rb") as f:
        # Wir senden das PDF als Base64 für maximale Kontextverfügbarkeit.
        import base64
        b64 = base64.b64encode(f.read()).decode("utf-8")
        pdf_input = f"data:application/pdf;base64,{b64}"

    # Für Einfachheit packen wir hier aber den reinen Text:
    # (wenn es nur Text‐Seiten sind, wäre das ausreichend)
    # Ansonsten kann man das Modell auch mit dem PDF‐file_id füttern,
    # analog zu generate_flashcards_from_pdf(...).
    # Hier: wir verwenden `pdf_input` im prompt, das Modell wird es decodieren.
    #
    # Alternativ: Wir extrahieren den Klartext aller Seiten:
    reader = PdfReader(EXTRACTED_PDF)
    pages_text = "\n\n".join(p.extract_text() or "" for p in reader.pages)

    # 5) Generiere neue Flashcards anhand PDF und History
    new_flashcards = generate_flashcards_with_history(
        pdf_excerpt=pages_text,
        learning_goal=LEARNING_GOAL,
        weak_answers=weak_answers,
        strong_answers=strong_answers,
        model=MODEL_NAME
    )

    # 6) Speichere die neuen QA‐Paare in einer einzigen JSON‐Datei
    out_data = {
        "learning_goal": LEARNING_GOAL,
        "page_range": f"{START_PAGE}-{END_PAGE}",
        "flashcards": new_flashcards
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2, ensure_ascii=False)

    print(f"\n→ {len(new_flashcards)} neue Flashcards in {OUTPUT_JSON} gespeichert.")
    for idx, card in enumerate(new_flashcards, start=1):
        print(f"{idx}. Q: {card['question']}")
        print(f"   A: {card['answer']}\n")


if __name__ == "__main__":
    main()
