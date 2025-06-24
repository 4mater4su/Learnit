#!/usr/bin/env python3
"""
flashcard_generation.py

Pluggable flash-card generation back-ends for PDF **and plain-text** pipelines.

Key additions
-------------
* **generate_flashcards_from_text(...)** is now part of the public interface.
* Both One-Shot and Chained generators implement it.
* Everything uses the new OpenAI Python SDK (v1) `responses.*` endpoints.
"""

from __future__ import annotations

import os
from typing import List, Tuple, Protocol
from abc import ABC, abstractmethod

from openai import OpenAI
from pydantic import BaseModel

from utils.slice_pdf import slice_pdf

# --------------------------------------------------------------------------- #
#  Configuration / globals
# --------------------------------------------------------------------------- #
CLIENT = OpenAI()          # assumes `OPENAI_API_KEY` env var is present
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# --------------------------------------------------------------------------- #
#  Core data models
# --------------------------------------------------------------------------- #
class Flashcard(BaseModel):
    question: str
    answer: str


class FlashcardBatch(BaseModel):
    flashcards: List[Flashcard]


# --------------------------------------------------------------------------- #
#  Generator interface
# --------------------------------------------------------------------------- #
class FlashcardGenerator(Protocol):
    """
    Abstract interface – supports BOTH PDF and raw-text sources.
    """

    # ---------- PDF ----------
    @abstractmethod
    def generate_flashcards(
        self,
        pdf_path: str,
        page_range: Tuple[int, int],
        learning_goal: str,
    ) -> List[Flashcard]:
        """
        Convert the indicated PDF page range to flashcards.
        """

    # ---------- Plain-text ----------
    @abstractmethod
    def generate_flashcards_from_text(
        self,
        text_content: str,
        learning_goal: str,
    ) -> List[Flashcard]:
        """
        Convert an arbitrary text snippet to flashcards.
        """

# --------------------------------------------------------------------------- #
#  JSON schema for one-shot calls
# --------------------------------------------------------------------------- #
_JSON_SCHEMA_FLASHCARDS = {
    "type": "object",
    "properties": {
        "flashcards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                },
                "required": ["question", "answer"],
                "additionalProperties": False,
            },
            "minItems": 1,
        }
    },
    "required": ["flashcards"],
    "additionalProperties": False,
}


def _schema_prompt(learning_goal: str) -> str:
    return (
        f"Bitte erstelle Fragen und Antworten in Verbindung mit dem Lernziel:\n"
        f"{learning_goal}\n\n"
        "Liefere das Ergebnis NUR im folgenden JSON-Format zurück:\n"
        "{\n"
        '  "flashcards": [\n'
        '    {"question": "...", "answer": "..."},\n'
        "    ...\n"
        "  ]\n"
        "}"
    )


# --------------------------------------------------------------------------- #
#  One-Shot back-end
# --------------------------------------------------------------------------- #
class OneShotFlashcardGenerator(FlashcardGenerator, ABC):
    """
    Upload once → model returns the finished flashcards (validated via JSON schema).
    """

    # ----- PDF ------------------------------------------------------------- #
    def generate_flashcards(
        self,
        pdf_path: str,
        page_range: Tuple[int, int],
        learning_goal: str,
    ) -> List[Flashcard]:
        start, end = page_range
        tmp_pdf = os.path.join(TEMP_DIR, f"oneshot_{start}_{end}.pdf")
        slice_pdf(pdf_path, tmp_pdf, start, end)

        with open(tmp_pdf, "rb") as fh:
            file_obj = CLIENT.files.create(file=fh, purpose="user_data")

        resp = CLIENT.responses.parse(
            model="gpt-4.1",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_file", "file_id": file_obj.id},
                        {"type": "input_text", "text": _schema_prompt(learning_goal)},
                    ],
                }
            ],
            text={"format": {"type": "json_schema", "schema": _JSON_SCHEMA_FLASHCARDS}},
        )
        return self._parse_flashcards(resp.output[0].content[0].text)

    # ----- TXT ------------------------------------------------------------- #
    def generate_flashcards_from_text(
        self,
        text_content: str,
        learning_goal: str,
    ) -> List[Flashcard]:
        # Text goes directly into the prompt
        full_prompt = (
            _schema_prompt(learning_goal)
            + "\n\n--- BEGIN TEXT ---\n"
            + text_content
            + "\n--- END TEXT ---"
        )

        resp = CLIENT.responses.parse(
            model="gpt-4o-mini",
            input=[{"role": "user", "content": full_prompt}],
            text={"format": {"type": "json_schema", "schema": _JSON_SCHEMA_FLASHCARDS}},
        )
        return self._parse_flashcards(resp.output[0].content[0].text)

    # --------------------------------------------------------------------- #
    @staticmethod
    def _parse_flashcards(raw_json: str) -> List[Flashcard]:
        import json

        try:
            parsed = json.loads(raw_json)
            return [Flashcard(**fc) for fc in parsed["flashcards"]]
        except Exception as exc:
            raise ValueError(f"Fehler beim Parsen der Modellantwort: {exc}\n{raw_json}") from exc


# --------------------------------------------------------------------------- #
#  Helper chain for the “chained” approach
# --------------------------------------------------------------------------- #
def _extract_relevant_text(pdf_path: str, learning_goal: str) -> str:
    """
    Let the LLM trim everything unrelated to the learning goal.
    """
    with open(pdf_path, "rb") as fh:
        uploaded = CLIENT.files.create(file=fh, purpose="user_data")

    prompt = (
        f"Laie bitte den Inhalt der Datei. Dein Lernziel lautet:\n«{learning_goal}»\n\n"
        "Finde den Abschnitt, der AM BESTEN zum Lernziel passt, "
        "und gib ihn ohne Einleitung und Schluss zurück, ausschließlich als Klartext."
    )

    resp = CLIENT.responses.create(
        model="gpt-4o-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_file", "file_id": uploaded.id},
                    {"type": "input_text", "text": prompt},
                ],
            }
        ],
    )
    return resp.output_text.strip()


def _flashcards_from_text_llm(text: str, learning_goal: str) -> List[Flashcard]:
    """
    Ask the LLM to transform *all* information from text into Q/A pairs.
    """

    resp = CLIENT.responses.parse(
        model="gpt-4o-2024-08-06",
        input=[
            {
                "role": "system",
                "content": (
                    "Du bist ein hilfreicher Tutor. Verwandle ALLE Informationen in Fragen; "
                    "nichts darf verloren gehen. Gib ein Array von Objekten "
                    "{question, answer} zurück."
                ),
            },
            {
                "role": "user",
                "content": f"Lernziel: {learning_goal}\n\nTEXT:\n{text}",
            },
        ],
        text_format=FlashcardBatch,
    )
    # The SDK auto-validated against FlashcardBatch
    return resp.output_parsed.flashcards


# --------------------------------------------------------------------------- #
#  Chained back-end
# --------------------------------------------------------------------------- #
class ChainedFlashcardGenerator(FlashcardGenerator, ABC):
    """
    1. Trim the PDF (or text) to what's relevant, 2. Feed trimmed text to a second prompt.
    """

    # ---------- PDF ----------
    def generate_flashcards(
        self,
        pdf_path: str,
        page_range: Tuple[int, int],
        learning_goal: str,
    ) -> List[Flashcard]:
        start, end = page_range
        tmp_pdf = os.path.join(TEMP_DIR, f"chain_{start}_{end}.pdf")
        slice_pdf(pdf_path, tmp_pdf, start, end)

        relevant_text = _extract_relevant_text(tmp_pdf, learning_goal)
        return _flashcards_from_text_llm(relevant_text, learning_goal)

    # ---------- TXT ----------
    def generate_flashcards_from_text(
        self,
        text_content: str,
        learning_goal: str,
    ) -> List[Flashcard]:
        # skip extract-step; go straight to Q/A generation
        return _flashcards_from_text_llm(text_content, learning_goal)


# --------------------------------------------------------------------------- #
#  Demo (remove or protect with __main__ in production)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    DEMO_PDF = "/path/to/your.pdf"
    DEMO_TXT = "/path/to/your.txt"
    GOAL = "Beispiel-Lernziel"

    generator: FlashcardGenerator = ChainedFlashcardGenerator()

    print("== PDF DEMO ==")
    pdf_cards = generator.generate_flashcards(DEMO_PDF, (1, 2), GOAL)
    for i, c in enumerate(pdf_cards, 1):
        print(f"{i}. Q: {c.question}\n   A: {c.answer}\n")

    print("== TXT DEMO ==")
    with open(DEMO_TXT, encoding="utf-8") as fh:
        txt_cards = generator.generate_flashcards_from_text(fh.read(), GOAL)
    for i, c in enumerate(txt_cards, 1):
        print(f"{i}. Q: {c.question}\n   A: {c.answer}\n")
