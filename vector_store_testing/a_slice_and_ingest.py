# a_slice_and_ingest.py
import os
from PyPDF2 import PdfReader
from vector_store_testing.a_ingest_directory import ingest_directory
from utils.slice_pdf import slice_pdf

def slice_and_mkdir(pdf_path):
    pdf_name = os.path.basename(pdf_path)             # "test.pdf"
    base_name = os.path.splitext(pdf_name)[0]         # "test"

    individual_pdfs_dir = os.path.join("/Users/robing/Desktop/projects/Learnit/PDF_pages", base_name)     # Path to the directory containing 1 page pdfs

    # Ensure output directory exists
    os.makedirs(individual_pdfs_dir, exist_ok=True)

    # Read number of pages
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    # Slice into single-page PDFs
    for i in range(1, total_pages + 1):
        #output_pdf = os.path.join(individual_pdfs_dir, f"page_{i}.pdf")
        output_pdf = os.path.join(individual_pdfs_dir, f"{base_name}_page_{i}.pdf")
        print(f"Slicing page {i}/{total_pages} -> {output_pdf}")
        slice_pdf(pdf_path, output_pdf, i, i)

    return individual_pdfs_dir

if __name__ == "__main__":
    pdf_path = "/Users/robing/Desktop/projects/Learnit/PDFs/M10_komplett.pdf"      # Source PDF
    
    individual_pdfs_dir = slice_and_mkdir(pdf_path)

    vector_store_name = "Experiment_VS"

    # Ingest all pages in the new directory into the vector store
    ingest_directory(individual_pdfs_dir, vector_store_name, ".vector_store_id")