#!/usr/bin/env python3
"""
Script: generate_answers.py

Loads the Excel data using the excel_parser module, then
for each Lernziel, calls OpenAI to generate a concise answer.
"""
import os
import time
from openai import OpenAI
from excel_parser import load_data

def answer_lernziel(client: OpenAI, lernziel: str) -> str:
    """Call the LLM to produce a concise answer to a Lernziel."""
    prompt = (
        "You are an expert educator. "
        "Please provide a clear, concise answer or explanation for the following learning objective:\n\n"
        f"\"{lernziel}\""
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

    # 2) Initialize OpenAI client
    client = OpenAI(api_key=api_key)

    # 3) Load and group data by Veranstaltung
    file_path = "/Users/robing/Desktop/projects/Learnit/M10-LZ.xlsx"
    vz_dict = load_data(file_path)

    # 4) Iterate through each Veranstaltung and its Lernziele
    for veranst, records in vz_dict.items():
        print(f"### Veranstaltung: {veranst} ###")
        for rec in records:
            lernziel = rec["Lernziel"]
            print(f"- Lernziel: {lernziel}")
            try:
                answer = answer_lernziel(client, lernziel)
                print(f"  Antwort: {answer}\n")
            except Exception as e:
                print(f"  Fehler beim Beantworten: {e}\n")
            # Rate limit pause
            time.sleep(1.0)

if __name__ == "__main__":
    main()
