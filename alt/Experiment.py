import os
from PyPDF2 import PdfReader, PdfWriter

def split_pdf_pages(pdf_path, start_page=1, end_page=3, output_dir="pages"):
    """
    Splits the given PDF into individual pages within the specified range.

    Args:
        pdf_path (str): Path to the source PDF file.
        start_page (int): First page number to extract (1-based).
        end_page (int): Last page number to extract (1-based).
        output_dir (str): Directory where split pages will be saved.
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    # Validate page range
    if start_page < 1 or end_page > total_pages or start_page > end_page:
        raise ValueError(f"Page range must be between 1 and {total_pages}, and start_page <= end_page.")

    # Extract pages
    for page_num in range(start_page, end_page + 1):
        writer = PdfWriter()
        writer.add_page(reader.pages[page_num - 1])

        output_path = os.path.join(output_dir, f"page_{page_num}.pdf")
        with open(output_path, "wb") as output_file:
            writer.write(output_file)

        print(f"Saved page {page_num} to {output_path}")


if __name__ == "__main__":
    # Example usage: split pages 1 to 3
    #split_pdf_pages("/Users/robing/Desktop/projects/Learnit/PDFs/M10_komplett_S1-6.pdf", start_page=1, end_page=3, output_dir="output_pages")

    from openai import OpenAI
    client = OpenAI()

    # Create vector store
    print("Creating vector store\n")
    vector_store = client.vector_stores.create(
        name="Experiment_VS"
    )
    print(vector_store)
    
    # Upload file
    file_obj =client.files.create(
        file=open("pages/page_1.pdf", "rb"),
        purpose="user_data"
    )

    print("File object ID\n")
    print(file_obj.id)

    # Create vector store file
    vector_store_file = client.vector_stores.files.create(
        vector_store_id = vector_store.id,
        file_id = file_obj.id,
        attributes = {
            "page": "1"
        }
    )
    print("Vector store file\n")
    print(vector_store_file)
    print("\n")
    
    # Retrieve vector store file
    vector_store_file = client.vector_stores.files.retrieve(
        vector_store_id=vector_store.id,
        file_id=vector_store_file.id
    )
    print(vector_store_file)

    # Search vector store
    user_query = "Funktionen der Skelettmuskelatur"

    response = client.responses.create(
        model="gpt-4o-mini",
        input="Funktionen der Skelettmuskelatur",
        tools=[{
            "type": "file_search",
            "vector_store_ids": [vector_store.id]
        }]
    )
    print("Response\n")
    print(response)

    # Delete vector store
    deleted_vector_store = client.vector_stores.delete(
        vector_store_id=vector_store.id
    )
    print(deleted_vector_store)