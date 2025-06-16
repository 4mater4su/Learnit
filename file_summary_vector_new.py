import os
import glob
from openai import OpenAI
from PyPDF2 import PdfReader, PdfWriter

client = OpenAI()

def extract_and_summarize_pages(pdf_path, start_page, end_page, question, model="gpt-4.1-nano", output_dir="pages"):
    reader = PdfReader(pdf_path)
    os.makedirs(output_dir, exist_ok=True)
    summaries = []

    for page_num in range(start_page, end_page + 1):
        print(f"→ Page {page_num}: extracting & summarizing")
        # 1) Extract page PDF
        page_dir = os.path.join(output_dir, str(page_num))
        os.makedirs(page_dir, exist_ok=True)
        p = os.path.join(page_dir, f"page_{page_num}.pdf")
        writer = PdfWriter(); writer.add_page(reader.pages[page_num-1])
        with open(p, "wb") as f: writer.write(f)

        # 2) Upload that page PDF to Files API
        with open(p, "rb") as f:
            file_obj = client.files.create(file=f, purpose="user_data")
        print(f"  • uploaded file_id={file_obj.id}")

        # 3) Ask LLM to summarize
        resp = client.responses.create(
            model=model,
            input=[{
                "role": "user",
                "content": [
                    {"type":"input_file", "file_id":file_obj.id},
                    {"type":"input_text", "text":question}
                ]
            }]
        )
        summary_txt = os.path.join(page_dir, "summary.txt")
        with open(summary_txt, "w", encoding="utf-8") as f:
            f.write(resp.output_text)

        summaries.append((page_num, summary_txt))
        print(f"  • summary written → {summary_txt}")

    return summaries

def build_summary_vector_store(summaries, vs_name="PDF Page Summaries"):
    print("→ Creating vector store for summaries…")
    vs = client.vector_stores.create(name=vs_name)
    print(f"  • vector_store_id={vs.id}")

    for page_num, path in summaries:
        print(f"→ Adding page {page_num} summary to VS")
        # first upload to Files API for vector ingestion
        with open(path, "rb") as f:
            raw = client.files.create(file=f, purpose="user_data")
        # now register that file in the vector store, tagging page number
        job = client.vector_stores.files.create_and_poll(
            vector_store_id=vs.id,
            file_id=raw.id,
            attributes={"page": page_num}
        )
        print(f"  • done (file_id={raw.id}, batch_id={job.id})")

    return vs.id

def query_with_pages(vs_id, query, model="gpt-4o-mini"):
    print(f"→ Searching VS {vs_id} for “{query}”…")
    results = client.vector_stores.search(
        vector_store_id=vs_id,
        query=query
    )

    print("\n--- Results ---")
    for hit in results.data:
        page = hit.attributes.get("page", "<?>")
        # join all text chunks in this hit
        snippet = " ".join(c.text for c in hit.content)
        print(f"[Page {page}] {snippet}\n")

if __name__ == "__main__":
    # 1) extract & summarize pages 1–6
    summaries = extract_and_summarize_pages(
        pdf_path="PDFs/M10_komplett_S1-6.pdf",
        start_page=1,
        end_page=6,
        question="Bitte mit Stichpunkten zusammenfassen"
    )

    # 2) create VS & upload summaries with page attributes
    vs_id = build_summary_vector_store(summaries)

    # 3) query & print page + snippet
    query_with_pages(vs_id, "Schenkelhalsfraktur")
