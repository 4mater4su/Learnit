from openai import OpenAI
from PyPDF2 import PdfReader, PdfWriter

def extract_pages(input_path: str, output_path: str, start_page: int, end_page: int) -> None:
    """
    Extract a range of pages (inclusive) from a PDF and save to a new file.
    """
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for i in range(start_page - 1, end_page):  # 1-based to 0-based
        writer.add_page(reader.pages[i])

    with open(output_path, "wb") as out_f:
        writer.write(out_f)

def ask_pdf_question(
    pdf_path: str,
    start_page: int,
    end_page: int,
    question: str,
    model: str = "gpt-4.1-nano",
    output_path: str = "PDFs/extracted_pages.pdf"
) -> str:
    """
    Extracts specific pages from a PDF, uploads them to OpenAI, and asks a question.
    
    Returns the model's response.
    """
    # Step 1: Extract
    extract_pages(pdf_path, output_path, start_page, end_page)

    # Step 2: Upload & ask
    client = OpenAI()
    with open(output_path, "rb") as f:
        uploaded_file = client.files.create(file=f, purpose="user_data")

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_file", "file_id": uploaded_file.id},
                    {"type": "input_text", "text": question}
                ]
            }
        ]
    )
    return response.output_text


if __name__ == "__main__":
    answer = ask_pdf_question(
        pdf_path="/Users/robing/desktop/learnit_testing/Prometheus_allgemeine_Anatomie_und_Bewegungssystem_page_489.pdf",
        start_page=1,
        end_page=1,
        question="""SYSTEM  
Du bist ein deutschsprachiger KI-Tutor für Medizinstudierende.  
Deine Antworten dürfen **ausschließlich Inhalte verwenden**, die im Abschnitt der Datei enthalten sind.  
Erfinde **nichts hinzu**, interpretiere **nur das, was explizit belegt ist**.

ASSISTANT TASK  
Erstelle präzise, medizinisch fundierte **Studien-Notizen** (Lernzusammenfassung) gemäß den folgenden Regeln:

1. Verwende ausschließlich Inhalte aus der Datei. Keine externen Quellen oder Ergänzungen.  
2. Beginne mit **3–5 Lernzielen** (verbalisiert mit Bloom-Taxonomie-Verben).  
3. Strukturiere den Haupttext in **Markdown**:  
   - `##` für Hauptabschnitte  
   - Bullet-Points oder kurze Absätze, auch längere Inhalte erlaubt (>2000 Zeichen)  
   - **Fettdruck** für zentrale Begriffe, `Inline-Code` für Parameter, Ionen oder Moleküle  
4. Behandle alle relevanten Inhalte des Ausgangstextes vollständig –  
   auch scheinbar „technische“ oder „molekulare“ Details.
5. Gliedere nach **physiologisch relevanten Themenfeldern**:  
   Ätiologie, Pathophysiologie, Zellbiologie, molekulare Mechanismen etc., sofern vorhanden.  
6. Füge am Ende **Take-Home-Messages** hinzu – jeweils 1–2 Sätze.  


Antwort ausschließlich im **formatierten Markdown-Block**.

Lernziel:
Lage und Funktion des Oberschenkelkniestreckers (M. quadriceps femoris) als Beispiel für eine gelenksübergreifende Muskelwirkung beschreiben und erläutern können.

"""

    )

    print(answer)
