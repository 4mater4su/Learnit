#!/usr/bin/env python3
"""
flashcard_generation.py

Pluggable flashcard generation backends for PDF-to-flashcard pipelines.
"""

import os
from typing import List, Tuple
from abc import ABC, abstractmethod

from openai import OpenAI
from PyPDF2 import PdfReader, PdfWriter
from pydantic import BaseModel

# ---------- Config ----------
CLIENT = OpenAI()
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# ---------- Flashcard Schema ----------
class Flashcard(BaseModel):
    question: str
    answer: str

class FlashcardBatch(BaseModel):
    flashcards: List[Flashcard]

# ---------- Interface ----------
class FlashcardGenerator(ABC):
    @abstractmethod
    def generate_flashcards(
        self, pdf_path: str, page_range: Tuple[int, int], learning_goal: str
    ) -> List[Flashcard]:
        """Generate a batch of flashcards from PDF, page range, and learning goal."""
        pass

# ---------- Utility ----------
def slice_pdf(input_pdf: str, output_pdf: str, start: int, end: int) -> None:
    """
    Extracts pages [start..end] from input_pdf into output_pdf (1-based, inclusive).
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

# ---------- One-Shot Generator ----------
class OneShotFlashcardGenerator(FlashcardGenerator):
    """
    Single-step: Upload PDF, prompt LLM to make flashcards (JSON schema output).
    """
    def generate_flashcards(
        self, pdf_path: str, page_range: Tuple[int, int], learning_goal: str
    ) -> List[Flashcard]:
        start, end = page_range
        temp_pdf = os.path.join(TEMP_DIR, f"oneshot_{start}_{end}.pdf")
        slice_pdf(pdf_path, temp_pdf, start, end)

        with open(temp_pdf, "rb") as f:
            uploaded = CLIENT.files.create(file=f, purpose="user_data")
        prompt = (
            f"Bitte erstelle Fragen und Antworten in Verbindung mit dem Lernziel: {learning_goal}\n"
            "Gib sie im JSON-Format zurück:\n"
            "{\n"
            "  \"flashcards\": [\n"
            "    {\"question\": \"...\", \"answer\": \"...\"},\n"
            "    ...\n"
            "  ]\n"
            "}"
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
            import json
            parsed = json.loads(raw_json)
            flashcards = parsed["flashcards"]
        except Exception as e:
            raise ValueError(f"Fehler beim Parsen der Modellantwort: {e}\n\nRohantwort:\n{raw_json}")

        # Convert to Pydantic Flashcard list
        return [Flashcard(**fc) for fc in flashcards]

# ---------- Chained/Multistep Generator ----------
def extract_and_clean(pdf_path: str, learning_goal: str) -> str:
    with open(pdf_path, "rb") as f:
        uploaded = CLIENT.files.create(file=f, purpose="user_data")
    cleaning_prompt = (
        f"Hier ist eine PDF-Datei. Dein Lernziel lautet:\n\n"
        f"\"{learning_goal}\"\n\n"
        "Bitte lies die Datei, finde den Abschnitt, der am meisten zum Lernziel passt, "
        "und entferne Einleitung und Ende, die nicht direkt dazu gehören. "
        "Gib NUR den relevanten Ausschnitt als Klartext zurück. Und sonst nichts."
    )
    response = CLIENT.responses.create(
        model="gpt-4.1",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_file", "file_id": uploaded.id},
                    {"type": "input_text", "text": cleaning_prompt}
                ]
            }
        ]
    )
    return response.output_text.strip()

def generate_flashcards_structured(relevant_text: str, learning_goal: str) -> List[Flashcard]:
    response = CLIENT.responses.parse(
        model="gpt-4o-2024-08-06",
        input=[
            {
                "role": "system",
                "content": (
                    "Du bist ein hilfreicher Tutor. "
                    "Erstelle eine komplette Liste, sodass alle information in fragen transformiert werden. Keine information darf verloren gehen. (jede mit 'question' und 'answer') zum angegebenen Lernziel, "
                    "verwende ausschließlich den bereitgestellten Text."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Lernziel: {learning_goal}\n"
                    f"Text:\n{relevant_text}"
                )
            }
        ],
        text_format=FlashcardBatch,
    )
    return response.output_parsed.flashcards

class ChainedFlashcardGenerator(FlashcardGenerator):
    """
    Multi-step: 1) Extract/clean relevant text from PDF, 2) prompt LLM to make flashcards from text.
    """
    def generate_flashcards(
        self, pdf_path: str, page_range: Tuple[int, int], learning_goal: str
    ) -> List[Flashcard]:
        start, end = page_range
        temp_pdf = os.path.join(TEMP_DIR, f"chain_{start}_{end}.pdf")
        slice_pdf(pdf_path, temp_pdf, start, end)
        relevant_text = extract_and_clean(temp_pdf, learning_goal)
        flashcards = generate_flashcards_structured(relevant_text, learning_goal)
        return flashcards

# ---------- Example usage (remove for production) ----------
if __name__ == "__main__":
    pdf_path = "/path/to/your.pdf"
    page_range = (2, 4)
    learning_goal = "Beispiel-Lernziel"
    generator = ChainedFlashcardGenerator()
    # generator = OneShotFlashcardGenerator()  # <- switch as needed
    flashcards = generator.generate_flashcards(pdf_path, page_range, learning_goal)
    for i, fc in enumerate(flashcards, 1):
        print(f"Karte {i}:\nFrage: {fc.question}\nAntwort: {fc.answer}\n")