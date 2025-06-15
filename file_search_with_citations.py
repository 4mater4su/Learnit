"""
filesearch_with_citations.py

Return an answer plus file-level citations and matching snippets
using the OpenAI Responses API and the file_search tool.
"""

import os
from openai import OpenAI

client = OpenAI()

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID", "<vector_store_id>")
MODEL            = "gpt-4o-mini"       # or any model that supports Responses API
MAX_RESULTS      = 8                   # limit search results to save tokens

# ---------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------
def answer_with_citations(query: str, vector_store_id: str = VECTOR_STORE_ID):
    """
    Ask a question against a vector store and print:
      • the assistant’s answer
      • the list of cited files
      • matching snippets (optional but handy for debugging)
    """
    # ---- 1. Create the response with file_search --------------------
    resp = client.responses.create(
        model   = MODEL,
        input   = query,
        tools   = [{
            "type": "file_search",
            "vector_store_ids": [vector_store_id],
            "max_num_results": MAX_RESULTS,
        }],
        include = ["file_search_call.results"],   # <–– request raw results
    )

    # ---- 2. Pull out the assistant message -------------------------
    msg_item = next(
        item for item in resp.output if item.type == "message"
    )
    # messages.content is a list of blocks (text / images / etc.)
    assistant_text = "".join(
        block.text for block in msg_item.content
        if block.type == "output_text"
    )

    # ---- 3. Collect unique file citations --------------------------
    cited = {}
    for block in msg_item.content:
        if block.type != "output_text":
            continue
        for ann in block.annotations or []:
            if ann.type == "file_citation":
                cited[ann.file_id] = ann.filename

    # ---- 4. Fetch the search-call object (has results) -------------
    search_call = next(
        item for item in resp.output if item.type == "file_search_call"
    )
    results = search_call.results or []

    # ---- 5. Print everything cleanly -------------------------------
    print("\n── Answer ──")
    print(assistant_text)

    print("\n── Citations ──")
    if cited:
        for fid, fname in cited.items():
            print(f"• {fname}  ({fid})")
    else:
        print("No file citations found.")

    print("\n── Matching snippets ──")
    for r in results:
        print(f"\n↳ {r.filename}  (score ≈ {r.score:.3f})")
        for part in r.content:
            if part.type == "text":
                print("   ", part.text[:200].replace("\n", " ") + "...")

    return assistant_text, cited, results

# ---------------------------------------------------------------------
# CLI entry-point (run `python filesearch_with_citations.py "your question"`)
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    user_query = " ".join(sys.argv[1:]) or "What is deep research by OpenAI?"
    if VECTOR_STORE_ID.startswith("<"):
        raise ValueError("Please set VECTOR_STORE_ID or replace the placeholder.")
    answer_with_citations(user_query)
