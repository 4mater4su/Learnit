# a_ingest_pages.py
import os
from openai import OpenAI


def ingest_directory(pages_dir: str, vector_store_name: str, vector_store_id_file: str):
    """
    Create (or reuse) the vector store and ingest all PDF files in the given directory.

    Args:
        pages_dir: Directory containing PDF files to ingest.
        vector_store_name: Name of the vector store to create or reuse.
        vector_store_id_file: Path to file where vector store ID is persisted.
    """
    client = OpenAI()

    # Try to find an existing store with that name
    stores = client.vector_stores.list().data
    vs = next((s for s in stores if s.name == vector_store_name), None)

    if vs is None:
        print(f"❓ No existing vector store named '{vector_store_name}', creating new one…")
        vs = client.vector_stores.create(name=vector_store_name)
    else:
        print(f"✔ Reusing existing vector store '{vector_store_name}': {vs.id}")

    print("Vector store ID:", vs.id, "\n")

    # Persist the VS ID for later
    with open(vector_store_id_file, "w") as f:
        f.write(vs.id)

    # Upload & attach each PDF in the directory
    for fname in sorted(os.listdir(pages_dir)):
        if not fname.lower().endswith('.pdf'):
            continue
        path = os.path.join(pages_dir, fname)
        print(f"Uploading {path!r}…")
        with open(path, "rb") as f_pdf:
            file_obj = client.files.create(
                file=f_pdf,
                purpose="user_data"
            )
        print(" → File ID:", file_obj.id)

        # Extract page identifier from filename
        page_id = ''.join(filter(str.isdigit, os.path.splitext(fname)[0])) or fname
        print(" Attaching to vector store…")
        vsf = client.vector_stores.files.create(
            vector_store_id=vs.id,
            file_id=file_obj.id,
            attributes={"page": page_id}
        )
        print(" → Attached as:", vsf.id, "\n")

    print("✅ Ingestion complete. You can now query this store anytime.")