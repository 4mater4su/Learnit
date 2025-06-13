from openai import OpenAI
from pydantic import BaseModel
from typing import List

# 1. Define flashcard schema for strict output
class Flashcard(BaseModel):
    question: str
    answer: str

class FlashcardBatch(BaseModel):
    flashcards: List[Flashcard]

CLIENT = OpenAI()

def extract_and_clean(pdf_path, learning_goal):
    # 1. Upload PDF to OpenAI Files
    with open(pdf_path, "rb") as f:
        uploaded = CLIENT.files.create(file=f, purpose="user_data")

    # 2. Build your cleaning prompt
    cleaning_prompt = (
        f"Hier ist eine PDF-Datei. Dein Lernziel lautet:\n\n"
        f"\"{learning_goal}\"\n\n"
        "Bitte lies die Datei, finde den Abschnitt, der am meisten zum Lernziel passt, "
        "und entferne Einleitung und Ende, die nicht direkt dazu gehören. "
        "Gib NUR den relevanten Ausschnitt als Klartext zurück. Und sonst nichts."
    )

    # 3. Call GPT with file and prompt (using responses.create for file input)
    response = CLIENT.responses.create(
        model="gpt-4.1",  # or your preferred model
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "file_id": uploaded.id,
                    },
                    {
                        "type": "input_text",
                        "text": cleaning_prompt,
                    },
                ]
            }
        ]
    )

    # 4. Extract result
    return response.output_text.strip()

def generate_flashcards_structured(relevant_text: str, learning_goal: str) -> List[Flashcard]:
    """
    Given relevant text and a learning goal, uses OpenAI structured output to create flashcards.
    Returns: List[Flashcard]
    """
    response = CLIENT.responses.parse(
        model="gpt-4o-2024-08-06",
        input=[
            {
                "role": "system",
                "content": (
                    "Du bist ein hilfreicher Tutor. "
                    "Erstelle 3 bis 5 Lernkarteikarten (jede mit 'question' und 'answer') zum angegebenen Lernziel, "
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
        text_format=FlashcardBatch,  # Enforces the schema!
    )
    return response.output_parsed.flashcards

if __name__ == "__main__":
    # ----- Set your PDF path and learning goal -----
    pdf_path = "/Users/robing/Desktop/projects/Learnit/archive/die_Wirkung_der_kleinen_Glutealmuskeln_auf_das_H_ftgelenk_und_ihre_Rolle_in_der_Standbeinphase_als_B/M10_komplett_S2-4.pdf"
    learning_goal = (
        "die Wirkung der kleinen Glutealmuskeln auf das Hüftgelenk und ihre Rolle in der Standbeinphase "
        "als Beispiel für die gelenksstabilisierende Wirkung von Muskeln beschreiben können."
    )

    print("Extrahiere relevanten Text aus PDF ...")
    relevant_text = extract_and_clean(pdf_path, learning_goal)
    print("Relevanter Abschnitt gefunden:\n")
    print(relevant_text)
    print("\nGeneriere Karteikarten ...\n")

    flashcards = generate_flashcards_structured(relevant_text, learning_goal)
    for i, fc in enumerate(flashcards, 1):
        print(f"Karte {i}:")
        print(f"Frage: {fc.question}")
        print(f"Antwort: {fc.answer}")
        print()