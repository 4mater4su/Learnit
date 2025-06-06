#!/usr/bin/env python3
"""
Script: generate_answers.py

Loads the Excel rows (in sheet order) using excel_parser.load_data,
then for each Lernziel, calls OpenAI, writes the answer to file,
and tracks progress so it only does each Lernziel once.
"""
import os
import time
from openai import OpenAI
import pandas as pd

from excel_parser import load_data
from old.answer_writer import write_answer
from old.progress_tracker import load_progress, save_progress, is_done, mark_done


def answer_lernziel(client: OpenAI, lernziel: str) -> str:
    """Call the LLM to produce a concise answer to a Lernziel."""
    prompt = (
        "You are an expert educator. "
        "Please provide a clear, concise answer or explanation for the following learning objective:\n\n"
        f"\"{lernziel}\"\n\n"
        "Only return the answer."
    )
    resp = client.responses.create(
        model="gpt-4.1",
        input=prompt
    )
    return resp.output_text.strip()


def main():
    # 1) Ensure API key is set
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: Please set OPENAI_API_KEY in your environment.")
        return

    # 2) Init OpenAI
    client = OpenAI(api_key=api_key)

    # 3) Load the raw DataFrame (in Excel row order)
    file_path = "/Users/robing/Desktop/projects/Learnit/M10-LZ.xlsx"
    df = load_data(file_path)  # now returns a pandas.DataFrame

    # 4) Load persistent progress state
    progress = load_progress()

    # 5) Iterate every row, in sheet order
    for idx, row in df.iterrows():
        veranst = row["Veranstaltung: Titel"]
        lernziel = row["Lernziel"]

        # 5a) Skip if already done
        if is_done(progress, veranst, lernziel):
            print(f"✔️ Skipping already processed Lernziel: {lernziel}")
            continue

        # 5b) Print context
        print(f"\n### Veranstaltung: {veranst} ###")
        print(f"- Lernziel: {lernziel}")

        try:
            # 6) Ask the LLM
            answer = answer_lernziel(client, lernziel)
            print(f"  Antwort: {answer}")

            # 7) Write to its Veranstaltung file
            write_answer(veranst, lernziel, answer)

            # 8) Mark done & save progress
            mark_done(progress, veranst, lernziel)
            save_progress(progress)

        except Exception as e:
            print(f"⚠️ Fehler beim Beantworten: {e}")

        # 9) Rate‐limit pause
        time.sleep(1.0)


if __name__ == "__main__":
    main()
