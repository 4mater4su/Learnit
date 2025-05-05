#!/usr/bin/env python3
"""
run: streamlit run app.py

Streamlit app: Lernziele Dashboard

Shows Lernziele grouped by Veranstaltung in the sidebar, with answered items marked in green.
Selecting a Lernziel displays its answer (if any).
Buttons allow generating the answer for the selected Lernziel or continuing through all unanswered ones.
"""
import os
import time
import pandas as pd
import streamlit as st
from openai import OpenAI

from excel_parser import load_data
from progress_tracker import load_progress, save_progress, is_done, mark_done
from generate_answers import answer_lernziel
from answer_writer import write_answer, sanitize_filename


def get_answer_from_file(veranstaltung: str, lernziel: str, output_dir: str = "answers") -> str:
    """
    Read the stored answer for a given Lernziel from its Veranstaltung file.
    """
    filename = sanitize_filename(veranstaltung) + ".txt"
    filepath = os.path.join(output_dir, filename)
    if not os.path.exists(filepath):
        return ""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if line.strip() == f"Lernziel: {lernziel}":
            for j in range(i+1, len(lines)):
                if lines[j].startswith("Antwort:"):
                    return lines[j].split("Antwort:", 1)[1].strip()
    return ""

# Streamlit configuration
st.set_page_config(page_title="Lernziele Dashboard", layout="wide")

# 1) Load data and state
file_path = "/Users/robing/Desktop/projects/Learnit/M10-LZ.xlsx"
df = load_data(file_path)
progress = load_progress()

# 2) OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("Please set OPENAI_API_KEY in your environment.")
    st.stop()
client = OpenAI(api_key=api_key)

# 3) Sidebar: Veranstaltung & Lernziel selection
st.sidebar.title("Navigation")

# Compute labels for Veranstaltungen, marking those fully answered
unique_veranst = df["Veranstaltung: Titel"].unique()
veranst_labels = {}
for veranst in unique_veranst:
    lz_list = df[df["Veranstaltung: Titel"] == veranst]["Lernziel"].tolist()
    done_all = all(is_done(progress, veranst, lz) for lz in lz_list)
    prefix = "✅ " if done_all else ""
    veranst_labels[veranst] = f"{prefix}{veranst}"

selected_veranst = st.sidebar.selectbox(
    "Veranstaltung",
    options=unique_veranst,
    format_func=lambda v: veranst_labels[v]
)

# Filter rows for the selected Veranstaltung
sub = df[df["Veranstaltung: Titel"] == selected_veranst].reset_index(drop=True)

# Build Lernziel options with checkmarks
options = []
for _, row in sub.iterrows():
    lz = row["Lernziel"]
    done = is_done(progress, selected_veranst, lz)
    prefix = "✅ " if done else ""
    options.append(f"{prefix}{lz}")

selection = st.sidebar.selectbox("Lernziel", options)
sel_idx = options.index(selection)
lernziel = sub.loc[sel_idx, "Lernziel"]

# 4) Main area: display answer
st.header(f"Veranstaltung: {selected_veranst}")
st.subheader(f"Lernziel: {lernziel}")
if is_done(progress, selected_veranst, lernziel):
    answer = get_answer_from_file(selected_veranst, lernziel)
    st.markdown(f"**Antwort:** {answer}")
else:
    st.markdown("*No answer yet.*")

# 5) Buttons
col1, col2 = st.columns(2)

with col1:
    if st.button("Generate answer for selected Lernziel"):
        answer = answer_lernziel(client, lernziel)
        write_answer(selected_veranst, lernziel, answer)
        mark_done(progress, selected_veranst, lernziel)
        save_progress(progress)
        st.success("Answer generated!")
        st.experimental_rerun()

with col2:
    if st.button("Continue answering all"):
        remaining = [
            (row["Veranstaltung: Titel"], row["Lernziel"])  
            for _, row in df.iterrows()  
            if not is_done(progress, row["Veranstaltung: Titel"], row["Lernziel"] )
        ]
        total = len(remaining)
        bar = st.progress(0)
        for i, (vz, lz) in enumerate(remaining, start=1):
            ans = answer_lernziel(client, lz)
            write_answer(vz, lz, ans)
            mark_done(progress, vz, lz)
            save_progress(progress)
            bar.progress(i/total)
            time.sleep(1.0)
        st.success("All Lernziele answered!")
        st.experimental_rerun()


def answer_lernziel(client: OpenAI, lernziel: str) -> str:
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
