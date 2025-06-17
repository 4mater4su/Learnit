# slice_and_ingest.py
import os
from PyPDF2 import PdfReader, PdfWriter
from a_ingest_directory import ingest_directory
from slice_pdf import slice_pdf

# Configuration variables (update these values as needed)
INPUT_PDF = "/Users/robing/Desktop/projects/Learnit/PDFs/M10_komplett_S1-6.pdf"      # Path to the source PDF
OUTPUT_BASE_DIR = os.path.splitext(os.path.basename(INPUT_PDF))[0]
vector_store_name = "Experiment_VS"

def slice_and_mkdir():
    # Ensure output directory exists
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)

    # Read number of pages
    reader = PdfReader(INPUT_PDF)
    total_pages = len(reader.pages)

    # Slice into single-page PDFs
    for i in range(1, total_pages + 1):
        output_pdf = os.path.join(OUTPUT_BASE_DIR, f"{OUTPUT_BASE_DIR}_page_{i}.pdf")
        print(f"Slicing page {i}/{total_pages} -> {output_pdf}")
        slice_pdf(INPUT_PDF, output_pdf, i, i)

    

if __name__ == "__main__":
    
    slice_and_mkdir()

    # Ingest all pages in the new directory into the vector store
    ingest_directory(OUTPUT_BASE_DIR, vector_store_name, ".vector_store_id")