import os
import glob
from openai import OpenAI
from PyPDF2 import PdfReader, PdfWriter

def extract_and_summarize_pages(
    pdf_path: str,
    start_page: int,
    end_page: int,
    question: str,
    model: str = "gpt-4.1-nano",
    output_dir: str = "pages"
) -> list[str]:
    """
    Extracts pages [start_page…end_page] from pdf_path, saves each as PDF,
    asks the LLM to summarize it, and writes a summary.txt in each page folder.
    Returns a list of all summary.txt paths.
    """
    reader = PdfReader(pdf_path)
    client = OpenAI()
    os.makedirs(output_dir, exist_ok=True)
    summary_paths = []

    print(f"Starting extraction and summarization for pages {start_page}–{end_page} of {pdf_path}")

    for page_num in range(start_page, end_page + 1):
        print(f"\n--- Processing page {page_num} ---")
        page_dir = os.path.join(output_dir, str(page_num))
        os.makedirs(page_dir, exist_ok=True)

        # 1) Extract single page to PDF
        writer = PdfWriter()
        writer.add_page(reader.pages[page_num - 1])
        page_pdf = os.path.join(page_dir, f"page_{page_num}.pdf")
        with open(page_pdf, "wb") as f:
            writer.write(f)
        print(f"Extracted page PDF → {page_pdf}")

        # 2) Upload PDF to OpenAI Files
        with open(page_pdf, "rb") as f:
            uploaded = client.files.create(file=f, purpose="user_data")
        print(f"Uploaded to Files API → file_id={uploaded.id}")

        # 3) Summarize via LLM
        print("Asking LLM to summarize...")
        resp = client.responses.create(
            model=model,
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_file", "file_id": uploaded.id},
                    {"type": "input_text", "text": question}
                ]
            }]
        )
        print("Received summary from LLM.")

        # 4) Write summary.txt
        summary_txt = os.path.join(page_dir, "summary.txt")
        with open(summary_txt, "w", encoding="utf-8") as f:
            f.write(resp.output_text)
        print(f"Wrote summary → {summary_txt}")

        summary_paths.append(summary_txt)

    print(f"\nCompleted summaries for pages {start_page}–{end_page}.")
    return summary_paths

def upload_summaries_to_vector_store(
    summary_paths: list[str],
    vector_store_name: str = "PDF Page Summaries"
) -> str:
    """
    Creates a vector store, uploads each summary.txt into it, and returns its ID.
    """
    client = OpenAI()
    print(f"\nCreating vector store '{vector_store_name}' for summaries...")
    vs = client.vector_stores.create(name=vector_store_name)
    print(f"Created vector store → id={vs.id}")

    for path in summary_paths:
        print(f"Uploading summary file {path}...")
        with open(path, "rb") as f:
            job = client.vector_stores.files.upload_and_poll(
                vector_store_id=vs.id,
                file=f
            )
        print(f"Uploaded → file_id={job.file_id}")

    print("All summaries uploaded.")
    return vs.id

def query_vector_store(
    vector_store_id: str,
    query: str,
    model: str = "gpt-4o-mini"
) -> str:
    """
    Runs a RAG query against vector_store_id and returns the LLM’s answer as text.
    """
    client = OpenAI()
    print(f"\nQuerying vector store {vector_store_id} with '{query}'...")
    rag = client.responses.create(
        model=model,
        input=query,
        tools=[{
            "type": "file_search",
            "vector_store_ids": [vector_store_id]
        }]
    )
    print("Received RAG response.")
    return rag.output_text

if __name__ == "__main__":
    # Parameters
    pdf_path   = "PDFs/M10_komplett_S1-6.pdf"
    start_page = 1
    end_page   = 6
    question   = "Bitte mit Stichpunkten zusammenfassen"
    final_query = "Schenkelhalsfraktur"

    # 1) Extract & summarize
    summaries = extract_and_summarize_pages(
        pdf_path=pdf_path,
        start_page=start_page,
        end_page=end_page,
        question=question
    )

    # 2) Create vector store & upload summaries
    vs_id = upload_summaries_to_vector_store(summaries)

    # 3) Query the summaries store
    answer = query_vector_store(vs_id, final_query)

    print("\n=== RAG Response ===")
    print(answer)
