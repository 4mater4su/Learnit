import os
import io
from openai import OpenAI
from PyPDF2 import PdfReader, PdfWriter

def extract_and_summarize_pages(
    pdf_path: str,
    start_page: int,
    end_page: int,
    question: str,
    model: str = "gpt-4.1-nano",
    output_dir: str = "pages"
) -> None:
    """
    For each page in [start_page, end_page], create a directory,
    save the page as PDF, ask the LLM to summarize, and save summary to a .txt file.
    """
    # Initialize PDF reader and OpenAI client
    reader = PdfReader(pdf_path)
    client = OpenAI()

    # Create base output directory
    os.makedirs(output_dir, exist_ok=True)

    for page_num in range(start_page, end_page + 1):
        # Create directory for this page
        page_dir = os.path.join(output_dir, str(page_num))
        os.makedirs(page_dir, exist_ok=True)

        # Extract single page
        writer = PdfWriter()
        writer.add_page(reader.pages[page_num - 1])  # zero-based index
        page_pdf_path = os.path.join(page_dir, f"page_{page_num}.pdf")
        with open(page_pdf_path, "wb") as f:
            writer.write(f)

        # Upload the page PDF
        with open(page_pdf_path, "rb") as f:
            uploaded = client.files.create(file=f, purpose="user_data")

        # Ask the LLM
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_file", "file_id": uploaded.id},
                        {"type": "input_text", "text": question}
                    ]
                }
            ]
        )

        # Save the summary to a text file
        summary_path = os.path.join(page_dir, "summary.txt")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(response.output_text)


if __name__ == "__main__":
    # Example usage
    pdf_path = "PDFs/M10_komplett_S1-6.pdf"
    start_page = 1
    end_page = 6
    question = "Bitte mit Stichpunkten zusammenfassen"
    extract_and_summarize_pages(pdf_path, start_page, end_page, question)
