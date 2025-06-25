#!/usr/bin/env python3
"""
card_create.py

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
class card_creator(Protocol):
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
class OneShotCardCreator(card_creator, ABC):
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
            model="gpt-4.1",
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
        model="gpt-4.1",
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
        model="gpt-4.1",
        input=[
            {
                "role": "system",
                "content": (
                    "Du bist ein hilfreicher Tutor. Verwandle ALLE Informationen in Fragen; "
                    "nichts darf verloren gehen. Gib ein Array von Objekten "
                    "{question, answer} zurück."
                    """
Few shot examples:
1. Welche Wirkung hat eine erhöhte Sympathikusaktivität auf die Plasmakonzentration von Angiotensin II?
   a) Senkend
   b) Keine
   c) Erhöhend

2. Mit welchen Rezeptoren präsentieren Langerhans-Zellen Antigene hauptsächlich?
   a) Toll-Like Rezeptor
   b) MHC-II
   c) CD3
   d) CD4
   e) CD19

3. Was ist eine typische Wirkung von Cholezystokinin?
   a) Es induziert eine Kontraktion der Gallenblase.
   b) Es induziert ein Hungergefühl.
   c) Es reduziert den Enzymgehalt des Pankreassaftes.
   d) Es reduziert die glomeruläre Filtrationsrate in der Niere.
   e) Es reduziert die Insulinsekretion im Pankreas.

4. Welche der folgenden Nagelveränderungen ist typisch für die Psoriasis vulgaris?
   a) Onychomykose
   b) Ölfleck
   c) Tüpfelnagelphänomen
   d) Längsrillen
   e) Uhrglasnägel

5. Eine 75-jährige Frau stellt sich in Ihrer Praxis wegen progredienter Belastungsdyspnoe vor. Welcher Befund spricht für das Vorliegen einer Aortenklappenstenose?
   a) Hohe Blutdruckamplitude (140/40 mmHg)
   b) Peripheres Pulsdefizit
   c) Vorhofflimmern im EKG
   d) Spindelförmiges Systolikum mit Fortleitung in die Karotiden

6. Was ist ein Kennzeichen einer hyperphagen Essstörung?
   a) Essen von einer großen Mahlzeit am Tag
   b) Essen über den kalorischen Bedarf hinaus
   c) Essen im Rahmen von Essattacken
   d) Regelmäßiges Erbrechen nach dem Essen

7. Worin unterscheiden sich die de-novo-Synthese und der Wiederverwertungsstoffwechsel von Purinbasen?
   a) In ihrer zellulären Lokalisation
   b) In ihren Endprodukten
   c) In ihren Ausgangssubstanzen

8. Wie wird Staphylococcus epidermidis laut morphologisch-physiologischer Bakteriensystematik bezeichnet?
   a) Gram-positiv, aerob
   b) Gram-negativ, aerob
   c) Gram-negativ, anaerob
   d) Gram-positiv, sporenbildend
   e) Gram-negativ, nicht-sporenbildend

9. Wie lang darf der QRS-Komplex bei einem unauffälligen EKG maximal dauern?
   a) 10 ms
   b) 60 ms
   c) 120 ms
   d) 180 ms
   e) Es gibt keinen Grenzwert für die Dauer des QRS-Komplexes.

10. Welche hormonellen Veränderungen sind nach einem deutlichen Gewichtsverlust am wahrscheinlichsten?
    a) Abfall von Leptin
    b) Abfall von Ghrelin
    c) Abfall von GLP-1
    d) Anstieg von Insulin
    e) Anstieg von TSH

11. Welche Hautveränderung ist eine Primäreffloreszenz?
    a) Squama
    b) Vesicula
    c) Cicatrix
    d) Ulkus
    e) Nodus

12. Von welchem Typ sind die Rezeptoren des Parasympathikus am Erfolgsorgan?
    a) Muskarinerge Acetylcholinrezeptoren
    b) Nikotinerge Acetylcholinrezeptoren
    c) Adrenerge alpha-Rezeptoren
    d) Adrenerge beta-Rezeptoren
    e) Glutaminrezeptoren vom Typ NMDA

13. Für die Beteiligung welcher Wurzel spricht der einseitige Ausfall des Patellar-Sehnen-Reflexes bei einer Lumboischialgie bei ansonsten seitengleichen lebhaften Muskeleigenreflexen?
    a) L4
    b) L5
    c) S1
    d) S2

14. Was bewirkt die laterale Hemmung auf der Ebene des Rückenmarks?
    a) Eine Unterdrückung irrelevanter taktiler Reize (Habituation)
    b) Eine Unterdrückung nozizeptiver Reizweiterleitung durch mechanische Reize (gate theory)
    c) Eine Blockade der Sensibilisierung nozizeptiver C-Fasern
    d) Eine Abnahme der Zwei-Punkt-Unterschiedsschwelle für taktile Reize
    e) Eine Abnahme der Empfindlichkeit der mechanosensitiven A-β-Fasern

15. Wofür werden definitionsgemäß die Abbauprodukte einer rein glucoplastischen Aminosäure im Körper genutzt?
    a) Für die Bildung von Ketonkörpern
    b) Für die anaplerotische Supplementierung des Citratzyklus
    c) Für die Proteinsynthese
    d) Für die Bildung von Cholesterol

16. Wie kann der Glykogenabbau im arbeitenden Muskel verstärkt werden?
    a) Aktivierung der Phosphorylasekinase durch Bindung von Mg²⁺
    b) Aktivierung der Phosphorylasekinase durch Bindung von Ca²⁺
    c) Aktivierung der Phosphorylase b durch Bindung von cAMP
    d) Aktivierung der Phosphorylase b durch Bindung von ADP
    e) Aktivierung der Phosphorylase b durch Bindung von Ca²⁺

17. Welche Struktur hat die Funktion der Bildung einer wasserdichten Diffusionsbarriere?
    a) Melanozyten
    b) Meissner-Körperchen
    c) Stratum corneum
    d) Stratum basale
    e) Stratum spinosum
    f) Plexus superficialis

18. Welches der folgenden Medikamente wird bei der Behandlung von Erkrankten mit dilatativer Kardiomyopathie grundsätzlich empfohlen?
    a) Digitoxin
    b) Digoxin
    c) ACE-Hemmer
    d) Phenprocoumon

19. In welchem Hautbereich manifestieren sich Infektionen mit dem Herpes-Simplex-Virus vom Typ 2 (HSV-2) überwiegend?
    a) Hinter den Ohren
    b) An der Genitalschleimhaut
    c) Am Rumpf
    d) Im Lippenbereich
    e) An den Extremitäten

20. Bei welcher Erkrankung kann das sogenannte Cullen-Zeichen auftreten?
    a) Ulcus duodeni
    b) Leberzirrhose
    c) Leberzellkarzinom
    d) Pankreatitis
    e) Appendizitis
"""
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
class ChainedCardCreator(card_creator, ABC):
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

    creator: card_creator = ChainedCardCreator()

    print("== PDF DEMO ==")
    pdf_cards = creator.generate_flashcards(DEMO_PDF, (1, 2), GOAL)
    for i, c in enumerate(pdf_cards, 1):
        print(f"{i}. Q: {c.question}\n   A: {c.answer}\n")

    print("== TXT DEMO ==")
    with open(DEMO_TXT, encoding="utf-8") as fh:
        txt_cards = creator.generate_flashcards_from_text(fh.read(), GOAL)
    for i, c in enumerate(txt_cards, 1):
        print(f"{i}. Q: {c.question}\n   A: {c.answer}\n")
