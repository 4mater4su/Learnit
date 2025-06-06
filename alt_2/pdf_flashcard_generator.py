import json
from typing import List, Dict, Tuple
from openai import OpenAI
from PyPDF2 import PdfReader, PdfWriter

client = OpenAI()

def extract_pdf_pages(input_pdf: str, output_pdf: str, start: int, end: int):
    """
    Extracts pages from a PDF and saves them as a new PDF.
    """
    reader = PdfReader(input_pdf)
    writer = PdfWriter()
    for i in range(start - 1, end):
        writer.add_page(reader.pages[i])
    with open(output_pdf, "wb") as f:
        writer.write(f)

def generate_flashcards_from_pdf(
    pdf_path: str,
    page_range: Tuple[int, int],
    learning_goal: str,
    output_json_path: str,
    output_pdf: str = "temp_extracted.pdf"
) -> List[Dict[str, str]]:
    """
    Generates flashcards (Q&A) from a selected PDF page range for a given learning goal
    and writes the result to a JSON file.

    Args:
        pdf_path: Full PDF document path.
        page_range: Tuple (start_page, end_page), 1-based inclusive.
        learning_goal: The learning objective.
        output_json_path: Path where the flashcards will be saved as JSON.
        output_pdf: (Optional) Intermediate file name for extracted pages.

    Returns:
        List of flashcard dictionaries.
    """
    start, end = page_range
    extract_pdf_pages(pdf_path, output_pdf, start, end)

    with open(output_pdf, "rb") as f:
        uploaded_file = client.files.create(file=f, purpose="user_data")

    prompt = (
        #f"Das folgende PDF enthält Informationen zum Lernziel:\n"
        #f"„{learning_goal}“.\n"
        #f"Bitte extrahiere daraus 3 bis 5 Fragen mit den passenden Antworten.\n"
        f"Bitte erstelle 3-5 Fragen und Antworten basierend auf dem Inhalt.\n"
        f"Gib sie im folgenden JSON-Format zurück:\n\n"
        f"{{\n"
        f"  \"flashcards\": [\n"
        f"    {{\"question\": \"...\", \"answer\": \"...\"}},\n"
        f"    ...\n"
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

    # Extract raw JSON string from model output
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

if __name__ == "__main__":
    flashcards = generate_flashcards_from_pdf(
        pdf_path="PDFs/M10_komplett.pdf",
        page_range=(13, 13),
        learning_goal="Die Schritte der endogenen Calcitriolsynthese (1,25(OH)2 Cholecalciferol), deren Lokalisation (Gewebe) und deren Regulation beschreiben können",
        output_json_path="flashcards/calcitriol_flashcards.json"
    )

    for card in flashcards:
        print("Q:", card["question"])
        print("A:", card["answer"])
        print("—" * 30)
