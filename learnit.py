#!/usr/bin/env python3
"""learnit.py – library utilities for PDF slicing, vector‑store ingestion and semantic retrieval.

New in this version
-------------------
1. **Vector‑store ID files are now per store** – kept under ``.vector_store_ids/<store>.id`` so you can juggle many stores in one project.
2. **`LearnIt.from_pdf()`** – convenience constructor that derives the vector‑store name from the PDF’s stem (`<stem>_VS`).

Example
=======
```python
from learnit import LearnIt

li = LearnIt.from_pdf("M10_komplett.pdf")          # store named "M10_komplett_VS"
pages_dir = li.slice_pdf("M10_komplett.pdf")        # 1‑page PDFs
li.ingest_directory(pages_dir)                       # upload once
li.search_and_copy_page(
    query="Wie sieht die Diagnostik bei einer Schenkelhalsfraktur aus?",
    dest_dir="~/Desktop/archive/goal1")
```

Install
-------
``pip install openai PyPDF2``
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from openai import OpenAI
from PyPDF2 import PdfReader, PdfWriter

__all__ = ["LearnIt"]


class LearnIt:
    """High‑level helper for slicing PDFs, ingesting them into an OpenAI vector
    store, and performing semantic retrieval.
    """

    #: folder that caches one *file per vector‑store* (created on demand)
    VECTOR_ID_DIR = Path(".vector_store_ids")

    def __init__(
        self,
        store_name: str,
        *,
        pages_root: Path | str | None = None,
        client: Optional[OpenAI] = None,
    ) -> None:
        """Use or create *store_name* and remember its ID under ``.vector_store_ids``.

        ``pages_root`` defaults to ``~/Desktop/projects/Learnit/PDF_pages``.
        """
        self.client = client or OpenAI()
        self.store_name = store_name
        self.pages_root = Path(pages_root or (Path.home() / "Desktop/projects/Learnit/PDF_pages"))
        self.pages_root.mkdir(parents=True, exist_ok=True)

        self.VECTOR_ID_DIR.mkdir(exist_ok=True)
        self.vector_store_id = self._load_or_create_store_id(store_name)

    # ─────────── class helpers ────────────

    @classmethod
    def from_pdf(cls, pdf_path: str | Path, **kwargs):
        """Return *LearnIt* where ``store_name = <pdf_stem>_VS``. Handy when each
        PDF owns its own store.
        """
        pdf_stem = Path(pdf_path).stem
        return cls(f"{pdf_stem}_VS", **kwargs)

    # ─────────── public API ────────────

    # 1) slice PDF ------------------------------------------------------------

    def slice_pdf(self, pdf_path: str | Path, *, out_dir: Path | str | None = None) -> Path:
        """Split *pdf_path* into single‑page PDFs and return the output directory."""
        pdf_path = Path(pdf_path)
        if out_dir is None:
            out_dir = self.pages_root / pdf_path.stem
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        reader = PdfReader(str(pdf_path))
        for i, page in enumerate(reader.pages, start=1):
            out_file = out_dir / f"{pdf_path.stem}_page_{i}.pdf"
            writer = PdfWriter()
            writer.add_page(page)
            with out_file.open("wb") as fh:
                writer.write(fh)
        return out_dir

    # 2) ingest directory -----------------------------------------------------

    def ingest_directory(self, pages_dir: str | Path) -> None:
        """Upload every PDF in *pages_dir* to the vector store."""
        pages_dir = Path(pages_dir)
        pdfs: List[Path] = sorted(
            (p for p in pages_dir.iterdir() if p.suffix.lower() == ".pdf"),
            key=lambda p: self._numeric_sort_key(p.name),
        )
        if not pdfs:
            raise FileNotFoundError(f"No PDFs found in {pages_dir!s}")

        for pdf in pdfs:
            with pdf.open("rb") as fh:
                file_obj = self.client.files.create(file=fh, purpose="user_data")
            page_id = "".join(filter(str.isdigit, pdf.stem)) or pdf.stem
            self.client.vector_stores.files.create(
                vector_store_id=self.vector_store_id,
                file_id=file_obj.id,
                attributes={"page": page_id},
            )

    # 3) semantic search + copy ----------------------------------------------

    def search_and_copy_pages(
        self,
        query: str,
        *,
        dest_dir: str | Path,
        pages_dir: str | Path | None = None,
    ) -> List[Path]:
        """Run *query* through file-search and copy all cited PDFs directly
        into *dest_dir*, ensuring no duplicates. Returns list of newly copied Paths."""
        # 1. Perform semantic file search
        resp = self.client.responses.create(
            model="gpt-4o-mini",
            input=query,
            tools=[{"type": "file_search", "vector_store_ids": [self.vector_store_id]}],
        )
        cited = self._extract_citations(resp)
        if not cited:
            return []

        # 2. Deduplicate citations by filename (preserve order)
        seen_files = set()
        unique_cited = []
        for filename, file_id in cited:
            if filename not in seen_files:
                seen_files.add(filename)
                unique_cited.append((filename, file_id))

        # 3. Ensure destination directory exists
        target = Path(dest_dir).expanduser()
        target.mkdir(parents=True, exist_ok=True)

        # 4. Copy each unique cited file into dest_dir if not already present
        pages_root = Path(pages_dir or self.pages_root)
        copied: List[Path] = []
        for filename, _ in unique_cited:
            dst = target / filename
            if dst.exists():
                # skip duplicates already in dest_dir
                continue
            src = self._locate_file_recursively(pages_root, filename)
            shutil.copy(src, dst)
            copied.append(dst)

        # 5. Print summary to console
        if copied:
            print("Copied pages:", ", ".join(p.name for p in copied))
        else:
            print("No new pages to copy (all were already present).")
        return copied

    # ─────────── internal helpers ────────────

    # vector-store helpers ----------------------------------------------------

    def _load_or_create_store_id(self, name: str) -> str:
        id_file = self.VECTOR_ID_DIR / f"{name}.id"
        if id_file.exists():
            return id_file.read_text().strip()
        # else create store and cache id
        store_id = self._get_or_create_store(name)
        id_file.write_text(store_id)
        return store_id

    def _get_or_create_store(self, name: str) -> str:
        stores = self.client.vector_stores.list().data
        store = next((s for s in stores if s.name == name), None)
        if store is None:
            store = self.client.vector_stores.create(name=name)
        return store.id

    # file‑system helpers -----------------------------------------------------

    @staticmethod
    def _numeric_sort_key(fname: str) -> int:
        m = re.search(r"(\d+)(?=\.pdf$)", fname, re.IGNORECASE)
        return int(m.group(1)) if m else -1

    @staticmethod
    def _extract_citations(resp) -> List[Tuple[str, str]]:
        cited: List[Tuple[str, str]] = []
        for msg in resp.output:
            if getattr(msg, "type", None) == "message":
                for part in msg.content:
                    for ann in getattr(part, "annotations", []):
                        if getattr(ann, "type", "") == "file_citation":
                            cited.append((ann.filename, ann.file_id))
        return cited

    @staticmethod
    def _locate_file_recursively(root: Path, filename: str) -> Path:
        direct = root / filename
        if direct.exists():
            return direct
        matches = list(root.rglob(filename))
        if matches:
            return matches[0]
        raise FileNotFoundError(f"{filename} not found under {root}")
