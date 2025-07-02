#!/usr/bin/env python3
"""
batch_ingest_archive.py

Walk every sub-directory of ARCHIVE_DIR, look for an LLM.txt, and ingest the
file's contents into your medical KG *iff* that exact file (same SHA-1 hash)
has not been ingested before.

The script maintains processed_llm.json:

    {
      "<abs path to LLM.txt>": "<sha1 hash>",
      ...
    }

Run this script whenever you've created new LLM.txt files; only the new or
modified ones are sent to GPT-parsing and added to the pickle graph.
"""

from pathlib import Path
import hashlib, json, sys
from typing import Dict

from ____medical_kg_lib import ingest_texts   # ← the wrapper we built earlier

# -------------------------------------------------------------------------
# CONFIG — adjust only these two lines if your layout changes
# -------------------------------------------------------------------------
ARCHIVE_DIR      = Path("/Users/robing/Desktop/projects/Learnit/archive")
PROCESSED_RECORD = Path("processed_llm.json")     # record lives next to script
ENCODING         = "utf-8"

# -------------------------------------------------------------------------
def sha1_of_file(path: Path, chunk: int = 65536) -> str:
    h = hashlib.sha1()
    with path.open("rb") as fh:
        while chunk_data := fh.read(chunk):
            h.update(chunk_data)
    return h.hexdigest()

def load_processed() -> Dict[str, str]:
    if PROCESSED_RECORD.exists():
        return json.loads(PROCESSED_RECORD.read_text())
    return {}

def save_processed(mapping: Dict[str, str]) -> None:
    PROCESSED_RECORD.write_text(json.dumps(mapping, indent=2))

# -------------------------------------------------------------------------
def main() -> None:
    if not ARCHIVE_DIR.exists():
        sys.exit(f"Archive dir not found: {ARCHIVE_DIR}")

    processed: dict[str, str] = load_processed()
    newly_processed: dict[str, str] = {}
    total_triples = 0

    # rglob catches *any* depth → adjust (e.g. .iterdir()) if you only want 1-level
    for llm_path in ARCHIVE_DIR.rglob("LLM.txt"):
        real_path = llm_path.resolve()
        file_hash = sha1_of_file(real_path)
        key       = str(real_path)

        if processed.get(key) == file_hash:
            continue                                   # already ingested

        # new or revised summary → ingest
        print(f"📚  Ingesting {llm_path.relative_to(ARCHIVE_DIR)} …")
        text = llm_path.read_text(encoding=ENCODING)
        if not text.strip():
            print("    ⚠️  empty file, skipped.")
            continue

        triples = ingest_texts([text])                 # GPT pipeline + graph
        print(f"    ✓  {triples} facts added.")
        total_triples += triples

        newly_processed[key] = file_hash

    # update record even if nothing new; keeps hashes for mods
    processed.update(newly_processed)
    save_processed(processed)

    print("\n========== SUMMARY ==========")
    print(f"LLM.txt files processed this run : {len(newly_processed)}")
    print(f"Total triples ingested           : {total_triples}")
    print(f"Known LLM.txt files in record    : {len(processed)}")

if __name__ == "__main__":
    main()
