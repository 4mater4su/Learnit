# answer_writer.py
"""
Module: answer_writer.py

Provides functionality to write LLM answers for Lernziele to files.
Each Veranstaltung gets its own text file, named after a sanitized title.
"""
import os
import re

def sanitize_filename(name: str) -> str:
    """Return a safe filename by removing or replacing unsafe characters."""
    # Remove characters other than word chars, spaces, hyphens
    sanitized = re.sub(r"[^\w \-]", "", name)
    # Replace spaces with underscores
    sanitized = sanitized.strip().replace(" ", "_")
    return sanitized

def write_answer(veranstaltung: str, lernziel: str, answer: str, output_dir: str = "answers") -> None:
    """
    Write the answer for a Lernziel to the file corresponding to the Veranstaltung.

    Args:
        veranstaltung: Title of the Veranstaltung (used for file naming).
        lernziel: The learning objective being answered.
        answer: The LLM-generated answer.
        output_dir: Directory where answer files are stored.
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Build safe filename
    filename = sanitize_filename(veranstaltung) + ".txt"
    filepath = os.path.join(output_dir, filename)

    # Check if file already exists to decide whether to write header
    is_new_file = not os.path.exists(filepath)

    with open(filepath, "a", encoding="utf-8") as f:
        if is_new_file:
            # Write header once per Veranstaltung
            f.write(f"Veranstaltung: {veranstaltung}\n")
            f.write("=" * (16 + len(veranstaltung)) + "\n\n")
        # Append this Lernziel and its answer
        f.write("-" * 40 + "\n\n")
        f.write(f"\n\t\tLernziel: {lernziel}\n\n")

        f.write(f"Antwort: {answer}\n\n")
