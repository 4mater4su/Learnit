import tkinter as tk
from tkinter import messagebox
import os
import json
from typing import List
from PyPDF2 import PdfReader

from card_create import (
    ChainedFlashcardGenerator,
    OneShotFlashcardGenerator,
    FlashcardGenerator,
)

# Choose the backend
FLASHCARD_GENERATOR: FlashcardGenerator = ChainedFlashcardGenerator()
# FLASHCARD_GENERATOR: FlashcardGenerator = OneShotFlashcardGenerator()  # switch if desired


class FlashcardManagerFrame(tk.LabelFrame):
    """Flash‑card pipeline that now consumes **all** PDF/TXT files in the goal folder.

    * No path/outdir UI anymore – the goal’s folder is implicit.
    * Generates/overwrites one *flashcards.json* per goal.
    * Keeps dummy methods (`get_selected_files`, `update_pdf_list`, `update_outdir_entry_for_goal`)
      so the rest of the app continues to work unchanged.
    """

    # ──────────────────────────────────────────────────────────────
    # Construction
    # ──────────────────────────────────────────────────────────────
    def __init__(
        self,
        parent,
        get_current_goal,
        get_outdir,
        sanitize_dirname,
        load_flashcard_data,
        open_review_window,
        open_editor_window,
        refresh_all_goal_colors,
        **kwargs,
    ) -> None:
        super().__init__(parent, text="Flashcards generieren", **kwargs)

        # External callbacks / helpers -------------------------------------
        self.get_current_goal = get_current_goal
        self.get_outdir = get_outdir
        self.sanitize_dirname = sanitize_dirname
        self.load_flashcard_data = load_flashcard_data
        self.open_review_window = open_review_window
        self.open_editor_window = open_editor_window
        self.refresh_all_goal_colors = refresh_all_goal_colors

        # ------------------------------------------------------------------
        # UI – just the three action buttons now
        # ------------------------------------------------------------------
        btn_row = tk.Frame(self)
        btn_row.grid(row=0, column=0, pady=10)

        self.gen_btn = tk.Button(
            btn_row, text="Generate Flashcards", command=self.generate_flashcards, state="disabled"
        )
        self.gen_btn.pack(side="left", padx=4)

        self.review_btn = tk.Button(
            btn_row, text="Review Flashcards", command=self.review_current, state="disabled"
        )
        self.review_btn.pack(side="left", padx=4)

        self.edit_btn = tk.Button(
            btn_row, text="Edit Flashcards", command=self.edit_current, state="disabled"
        )
        self.edit_btn.pack(side="left", padx=4)

    # ──────────────────────────────────────────────────────────────
    # Helper utilities
    # ──────────────────────────────────────────────────────────────
    def _goal_dir(self) -> str | None:
        goal = self.get_current_goal()
        if not goal:
            return None
        return os.path.join(self.get_outdir(), self.sanitize_dirname(goal))

    def _collect_source_files(self) -> List[str]:
        """Return absolute paths of all *.pdf / *.txt in goal directory."""
        goal_dir = self._goal_dir()
        if not goal_dir or not os.path.isdir(goal_dir):
            return []
        return [
            os.path.join(goal_dir, f)
            for f in os.listdir(goal_dir)
            if f.lower().endswith((".pdf", ".txt")) and os.path.isfile(os.path.join(goal_dir, f))
        ]

    # ------------------------------------------------------------------
    # Compatibility shims for other frames expecting the old API
    # ------------------------------------------------------------------
    def get_selected_files(self) -> List[str]:
        """Old API: returns all source files now."""
        return self._collect_source_files()

    def update_pdf_list(self):
        """Old checkbox‑refresh routine – no UI left, so nothing to do."""
        pass

    def update_outdir_entry_for_goal(self):
        """Deprecated – kept so callers don’t fail."""
        pass

    def set_action_buttons_state(self, state: str):
        self.gen_btn.config(state=state)
        self.review_btn.config(state=state)
        self.edit_btn.config(state=state)

    # ──────────────────────────────────────────────────────────────
    # Flash‑card generation – unchanged below
    # ──────────────────────────────────────────────────────────────(self, state: str):
        self.gen_btn.config(state=state)
        self.review_btn.config(state=state)
        self.edit_btn.config(state=state)

    # ──────────────────────────────────────────────────────────────
    # Flash‑card generation
    # ──────────────────────────────────────────────────────────────
    def generate_flashcards(self):
        goal = self.get_current_goal()
        if not goal:
            messagebox.showerror("Fehler", "Kein Lernziel ausgewählt.")
            return

        source_files = self._collect_source_files()
        if not source_files:
            messagebox.showerror(
                "Fehler", "Im Zielordner wurden keine PDF- oder TXT-Dateien gefunden."
            )
            return

        goal_dir = self._goal_dir()
        assert goal_dir
        os.makedirs(goal_dir, exist_ok=True)
        out_json = os.path.join(goal_dir, "flashcards.json")

        if os.path.exists(out_json):
            if not messagebox.askyesno(
                "Überschreiben?",
                "Für dieses Lernziel existiert bereits ein flashcards.json.\n"
                "Möchtest du es überschreiben?",
            ):
                return

        all_flashcards, sources, file_paths, errors = [], [], [], []

        for path in source_files:
            filename = os.path.basename(path)
            try:
                if filename.lower().endswith(".pdf"):
                    with open(path, "rb") as fpdf:
                        num_pages = len(PdfReader(fpdf).pages)
                    flashcards = FLASHCARD_GENERATOR.generate_flashcards(
                        pdf_path=path, page_range=(1, num_pages), learning_goal=goal
                    )
                    descriptor = f"PDF {filename} (S1–{num_pages})"
                else:
                    with open(path, "r", encoding="utf-8") as ftxt:
                        text_content = ftxt.read()
                    flashcards = FLASHCARD_GENERATOR.generate_flashcards_from_text(
                        text_content=text_content, learning_goal=goal
                    )
                    descriptor = f"TXT {filename}"

                all_flashcards.extend(flashcards)
                sources.append(descriptor)
                file_paths.append(path)
            except Exception as exc:
                errors.append(f"{filename}: {exc}")

        if all_flashcards:
            with open(out_json, "w", encoding="utf-8") as fjson:
                json.dump(
                    {
                        "learning_goal": goal,
                        "sources": sources,
                        "file_paths": file_paths,
                        "flashcards": [fc.dict() for fc in all_flashcards],
                    },
                    fjson,
                    indent=2,
                    ensure_ascii=False,
                )
            self.review_btn.config(state="normal")
            self.refresh_all_goal_colors()

        if errors:
            messagebox.showerror("Fehler beim Generieren", "\n".join(errors))

    # ──────────────────────────────────────────────────────────────
    # Review / Edit helpers
    # ──────────────────────────────────────────────────────────────
    def _batch_json_path(self, goal: str | None):
        if not goal:
            return None
        goal_dir = self._goal_dir()
        if not goal_dir:
            return None
        p = os.path.join(goal_dir, "flashcards.json")
        return p if os.path.isfile(p) else None

    def review_current(self):
        path = self._batch_json_path(self.get_current_goal())
        if not path:
            messagebox.showerror("Fehler", "Keine Flashcards vorhanden.")
            return
        self.open_review_window(path)

    def edit_current(self):
        path = self._batch_json_path(self.get_current_goal())
        if not path:
            messagebox.showerror("Fehler", "Keine Flashcards vorhanden.")
            return
        self.open_editor_window(path)
        self.refresh_all_goal_colors()
