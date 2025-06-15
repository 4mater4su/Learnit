#!/usr/bin/env python3
"""
fs_setup_and_query.py
---------------------
Create (or reuse) a vector store, upload/attach files, wait until ready,
then ask a question with file_search and show answer + citations.

Requires: openai >= 1.13
"""

import argparse, os, time, sys
from pathlib import Path
from openai import OpenAI

client = OpenAI()
MODEL = "gpt-4o-mini"
POLL_EVERY = 5              # seconds
MAX_RESULTS = 8

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _underlying_file_id(vs_file):
    """
    Return the true file-ID of a VectorStoreFile, no matter the SDK version.
    """
    # 1) oldest SDKs
    if hasattr(vs_file, "file_id"):
        return vs_file.file_id

    # 2) some betas put it directly in .id
    if hasattr(vs_file, "id"):
        return vs_file.id

    # 3) newest SDKs: there is a nested 'file' object
    if getattr(vs_file, "file", None) is not None:
        nested = vs_file.file
        return getattr(nested, "id", None) or nested.get("id")

    # 4) last-resort: look in the raw dict
    dump = vs_file.model_dump() if hasattr(vs_file, "model_dump") else dict(vs_file)
    return (
        dump.get("file_id") or
        dump.get("id") or
        dump.get("file", {}).get("id")
    )

def get_or_create_store(name: str):
    # Look for an existing store with the same name
    stores = client.vector_stores.list().data
    for s in stores:
        if s.name == name:
            print(f"✓ Re-using existing vector store '{name}' ({s.id})")
            return s
    # Otherwise create a new one
    vs = client.vector_stores.create(name=name)
    print(f"✓ Created vector store '{name}' ({vs.id})")
    return vs

def upload_file(path_or_url: str):
    if path_or_url.startswith(("http://", "https://")):
        print(f"  → downloading & uploading {path_or_url}")
        return client.files.create(
            file=(Path(path_or_url).name, path_or_url),
            purpose="assistants"
        )
    else:
        fp = Path(path_or_url).expanduser()
        if not fp.exists():
            raise FileNotFoundError(fp)
        print(f"  → uploading {fp}")
        with fp.open("rb") as f:
            return client.files.create(file=f, purpose="assistants")

def attach_file(vector_store_id: str, file_id: str):
    return client.vector_stores.files.create(
        vector_store_id=vector_store_id,
        file_id=file_id
    )

def wait_until_ready(vector_store_id: str):
    while True:
        lst = client.vector_stores.files.list(vector_store_id=vector_store_id)
        pending = [f for f in lst.data if f.status != "completed"]
        if not pending:
            return
        print(f"  … waiting for {len(pending)} file(s) to finish indexing …")
        time.sleep(POLL_EVERY)

def ask(question: str, vector_store_id: str):
    resp = client.responses.create(
        model=MODEL,
        input=question,
        tools=[{
            "type": "file_search",
            "vector_store_ids": [vector_store_id],
            "max_num_results": MAX_RESULTS,
        }],
        include=["file_search_call.results"],
    )
    msg = next(o for o in resp.output if o.type == "message")
    answer_text = "".join(
        b.text for b in msg.content if b.type == "output_text"
    )
    cites = {a.file_id: a.filename
             for b in msg.content if b.type == "output_text"
             for a in (b.annotations or []) if a.type == "file_citation"}
    search_call = next(o for o in resp.output if o.type == "file_search_call")
    return answer_text, cites, search_call.results or []

# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--name", required=True,
                   help="Vector-store name (will be reused if it exists)")
    p.add_argument("--files", nargs="+", required=True,
                   help="File paths or URLs to add to the store")
    p.add_argument("--question", required=True,
                   help="What you want to ask after setup")
    args = p.parse_args()

    store = get_or_create_store(args.name)

    # 1) upload + attach any new files
    existing_file_ids = {
        _underlying_file_id(f)
        for f in client.vector_stores.files.list(vector_store_id=store.id).data
    }


    for src in args.files:
        file_obj = upload_file(src)
        if file_obj.id not in existing_file_ids:
            attach_file(store.id, file_obj.id)

    # 2) wait for indexing to complete
    wait_until_ready(store.id)

    # 3) ask the question
    answer, citations, results = ask(args.question, store.id)

    # 4) print results
    print("\n── Answer ──")
    print(answer)

    print("\n── Citations ──")
    if citations:
        for fid, fname in citations.items():
            print(f"• {fname}  ({fid})")
    else:
        print("No file citations found.")

    # 4) print results ---------------------------------------------------
        # 4) print results ------------------------------------------------
    print("\n── Matching snippets ──")
    for r in results:
        # Convert to a plain dict once; use it as a universal fallback.
        r_dict = r.model_dump() if hasattr(r, "model_dump") else (
            r if isinstance(r, dict) else {}
        )

        # 1. Pull blocks (chunks/content) safely
        blocks = (
            getattr(r, "chunks", None)            # new SDK
            or getattr(r, "content", None)        # old SDK
            or r_dict.get("chunks")               # fallback
            or r_dict.get("content", [])          # fallback
        )

        # 2. Filename and score
        fname = getattr(r, "filename", None) or r_dict.get("filename", "unknown")
        score = getattr(r, "score", None)    or r_dict.get("score", 0.0)

        print(f"\n↳ {fname}  (score ≈ {score:.3f})")

        # 3. Print text snippets
        for b in blocks:
            b_dict = b if isinstance(b, dict) else (
                b.model_dump() if hasattr(b, "model_dump") else {})
            if b_dict.get("type") == "text":
                snippet = b_dict.get("text", "").replace("\n", " ")
                print("   ", snippet[:200] + ("…" if len(snippet) > 200 else ""))



"""
python3 fs_setup_and_query.py \
    --name "My KB" \
    --files /Users/robing/Desktop/projects/Learnit/PDFs/extracted_pages.pdf \
    --question "M. vastus medialis Ursprung"
"""