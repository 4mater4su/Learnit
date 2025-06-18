# search_and_copy_page.py

import os
import platform
import shutil
import subprocess
from openai import OpenAI

client = OpenAI()

def search_and_copy_page(query: str, individual_pdfs_dir: str, learning_goal_dir: str, vector_store_id: str = None):
    """
    Search a vector store for a query, download the first cited PDF into the specified directory,
    and open it with the system's default PDF viewer.

    Args:
        query: The search query string.
        individual_pdfs_dir: Path to the directory where cited PDFs should be saved.
        vector_store_id: Optional preloaded vector store ID. If None, reads from ".vector_store_id".
    """
    # Load vector store ID if not provided
    if vector_store_id is None:
        try:
            with open(".vector_store_id", "r") as f:
                vector_store_id = f.read().strip()
        except FileNotFoundError:
            raise RuntimeError("Missing .vector_store_id — run ingest_pages.py first!")

    # Run the semantic file search
    response = client.responses.create(
        model="gpt-4o-mini",
        input=query,
        tools=[{
            "type": "file_search",
            "vector_store_ids": [vector_store_id]
        }]
    )

    # Extract file citations from the response
    cited = []
    for msg in response.output:
        if getattr(msg, "type", None) == "message":
            for part in msg.content:
                for ann in getattr(part, "annotations", []):
                    if getattr(ann, "type", "") == "file_citation":
                        cited.append((ann.filename, ann.file_id))

    if not cited:
        print("⚠ No files were cited in the response.")
        return

    # Report all cited files
    print("🔖 Cited files:")
    for filename, file_id in cited:
        print(f"- {filename}: {file_id}")

    # Take the first cited file
    first_filename, first_file_id = cited[0]

    print()
    print(first_filename)
    print(first_file_id)

    # ———————— Build paths and copy the PDF ————————

    # 1. Source path under individual_pdfs_dir
    source_path = os.path.join(individual_pdfs_dir, first_filename)

    # 2. Ensure the learning-goal directory exists
    os.makedirs(learning_goal_dir, exist_ok=True)

    # 3. Destination path: same filename in learning_goal_dir
    dest_path = os.path.join(learning_goal_dir, first_filename)

    # 4. Copy the file
    shutil.copy(source_path, dest_path)
    print(f"📁 Copied from {source_path} to {dest_path}")



if __name__ == "__main__":

    query = "Wie sieht die Diagnostik bei einer Schenkelhalsfraktur aus?"
    individual_pdfs_dir = "/Users/robing/Desktop/projects/Learnit/PDF_pages"
    learning_goal_dir = "/Users/robing/Desktop/projects/Learnit/archive/die_Begriffe__Adaptation__und__Plastizit_t__im_Hinblick_auf_das_Fasertypenmuster_und_-gr__e_eines_ak"
    
    
    # 1️⃣ Load the existing vector store ID
    try:
        with open(".vector_store_id") as f:
            vs_id = f.read().strip()
    except FileNotFoundError:
        raise RuntimeError("Could not find .vector_store_id—run ingest_pages.py first!")
    vector_store_id = vs_id


    search_and_copy_page(query, individual_pdfs_dir, learning_goal_dir, vector_store_id)