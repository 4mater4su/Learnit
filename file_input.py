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

    # with open(output_path, "wb") as out_f:
    #     writer.write(out_f)

def ask_pdf_question(
    pdf_path: str,
    start_page: int,
    end_page: int,
    question: str,
    model: str = "gpt-4.1",
    output_path: str = "past_papers/fragen.pdf"
) -> str:
    """
    Extracts specific pages from a PDF, uploads them to OpenAI, and asks a question.
    
    Returns the model's response.
    """
    # Step 1: Extract
    #extract_pages(pdf_path, output_path, start_page, end_page)

    # Step 2: Upload & ask
    client = OpenAI()
    with open(pdf_path, "rb") as f:
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
        pdf_path="/Users/robing/Desktop/projects/Learnit/past_papers/fragen.pdf",
        start_page=1,
        end_page=23,
        question="""SYSTEM  
Du bist ein ausgezeichneter Medizinprofessor. Du schreibst die nächsten Prüfungsfragen. Generiere 5 ähnliche fragen basierend auf dem input. 
"""

    )

    print(answer)
