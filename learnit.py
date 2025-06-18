#!/usr/bin/env python3
"""learnit.py – a **library version** (non‑CLI) that unifies PDF slicing, vector‑store ingestion and semantic lookup.

Example
=======
>>> from learnit import LearnIt
>>> li = LearnIt("Experiment_VS")
>>> pages_dir = li.slice_pdf("M10_komplett.pdf")           # 1‑page PDFs under PAGES_ROOT/M10_komplett
>>> li.ingest_directory(pages_dir)                          # upload pages once
>>> li.search_and_copy_page(
...     query="Wie sieht die Diagnostik bei einer Schenkelhalsfraktur aus?",
...     dest_dir="~/Desktop/archive/goal1")                # copy the best hit

Notes
-----
* The class caches the vector‑store ID in `.vector_store_id` so you create the
  store only once.
* `pages_root` defaults to `~/Desktop/projects/Learnit/PDF_pages`. Each call to
  :py:meth:`slice_pdf` creates a **subfolder named after the PDF stem**. The
  improved :py:meth:`search_and_copy_page` now detects that automatically, so
  you no longer need to pass `pages_dir` manually.

Install requirements
--------------------
    pip install openai PyPDF2
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

    #: where the vector‑store ID is persisted (relative to cwd)
    VECTOR_ID_FILE = Path(".vector_store_id")

    def __init__(self, store_name: str, *, pages_root: Path | str | None = None):
        self.client = OpenAI()
        self.store_name = store_name
        self.pages_root = Path(pages_root or (Path.home() / "Desktop/projects/Learnit/PDF_pages"))
        self.pages_root.mkdir(parents=True, exist_ok=True)
        self.vector_store_id = self._get_or_create_store(store_name)
        self._save_vector_id(self.vector_store_id)

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
            out_name = f"{pdf_path.stem}_page_{i}.pdf"
            out_file = out_dir / out_name
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

    def search_and_copy_page(
        self,
        query: str,
        *,
        dest_dir: str | Path,
        pages_dir: str | Path | None = None,
    ) -> Optional[Path]:
        """Run *query* through file‑search, copy first cited PDF into *dest_dir*.

        If *pages_dir* is omitted, the method first looks in ``self.pages_root``
        **and its sub‑directories**. So you can ignore the parameter in the
        common case where you always slice PDFs under the default root.

        Returns the path to the copied file or *None* if nothing was cited.
        """
        store_id = self.vector_store_id
        resp = self.client.responses.create(
            model="gpt-4o-mini",
            input=query,
            tools=[{"type": "file_search", "vector_store_ids": [store_id]}],
        )

        cited = self._extract_citations(resp)
        if not cited:
            return None

        filename, _ = cited[0]
        pages_dir = Path(pages_dir or self.pages_root)

        # ── locate the source file ─────────────────────────────────────────
        src = pages_dir / filename
        if not src.exists():
            matches = list(pages_dir.rglob(filename))
            if matches:
                src = matches[0]
            else:
                raise FileNotFoundError(
                    f"{filename} not found under {pages_dir} (searched recursively)"
                )

        # ── copy to destination ────────────────────────────────────────────
        dest_dir = Path(dest_dir).expanduser()
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filename
        shutil.copy(src, dest)
        return dest

    # ─────────── helpers ────────────

    def _get_or_create_store(self, name: str) -> str:
        stores = self.client.vector_stores.list().data
        store = next((s for s in stores if s.name == name), None)
        if store is None:
            store = self.client.vector_stores.create(name=name)
        return store.id

    @classmethod
    def _save_vector_id(cls, vid: str) -> None:
        cls.VECTOR_ID_FILE.write_text(vid)

    @staticmethod
    def _numeric_sort_key(fname: str) -> int:
        m = re.search(r"(\d+)(?=\.pdf$)", fname, re.IGNORECASE)
        return int(m.group(1)) if m else -1

    # extraction of citations -------------------------------------------------

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
