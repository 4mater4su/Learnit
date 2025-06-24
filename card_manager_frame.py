import tkinter as tk
from tkinter import messagebox, filedialog
import os
from PyPDF2 import PdfReader

from card_create import (
    ChainedFlashcardGenerator,
    OneShotFlashcardGenerator,
    FlashcardGenerator
)
# Choose the backend
FLASHCARD_GENERATOR: FlashcardGenerator = ChainedFlashcardGenerator()
# FLASHCARD_GENERATOR: FlashcardGenerator = OneShotFlashcardGenerator()  # switch if desired


class FlashcardManagerFrame(tk.LabelFrame):
    """
    Shows the list of *.pdf AND *.txt files that live in the current goal’s folder,
    lets the user tick any combination, and then generates/reviews/edits a
    flash-card batch (flashcards.json) for that learning goal.

    TXT support: requires the generator to expose
        generate_flashcards_from_text(text_content, learning_goal)
    which should return a list[Flashcard].
    """
    def __init__(self, parent,
                 get_current_goal, get_outdir, sanitize_dirname,
                 load_flashcard_data,
                 open_review_window,
                 open_editor_window,
                 refresh_all_goal_colors,
                 **kwargs):
        super().__init__(parent, text="Flashcards generieren", **kwargs)
        self.get_current_goal = get_current_goal
        self.get_outdir = get_outdir
        self.sanitize_dirname = sanitize_dirname
        self.load_flashcard_data = load_flashcard_data
        self.open_review_window = open_review_window
        self.open_editor_window = open_editor_window
        self.refresh_all_goal_colors = refresh_all_goal_colors

        # --- UI ----------------------------------------------------------------
        tk.Label(self, text="Outdir:").grid(row=2, column=0, sticky="e")
        tk.Label(self, text="Dateien wählen:").grid(row=0, column=0, sticky="e")

        # Scrollable checkbox canvas
        self.pdf_checkbox_canvas = tk.Canvas(self, height=120, highlightthickness=0)
        self.pdf_checkbox_scrollbar = tk.Scrollbar(
            self, orient="vertical",
            command=self.pdf_checkbox_canvas.yview
        )
        self.pdf_checkbox_inner_frame = tk.Frame(self.pdf_checkbox_canvas)

        self.pdf_checkbox_inner_frame.bind(
            "<Configure>",
            lambda e: self.pdf_checkbox_canvas.configure(
                scrollregion=self.pdf_checkbox_canvas.bbox("all"))
        )
        self.pdf_checkbox_canvas.create_window(
            (0, 0), window=self.pdf_checkbox_inner_frame, anchor="nw")
        self.pdf_checkbox_canvas.configure(yscrollcommand=self.pdf_checkbox_scrollbar.set)
        self.pdf_checkbox_canvas.grid(row=0, column=1, sticky="nsew", padx=5, pady=2)
        self.pdf_checkbox_scrollbar.grid(row=0, column=2, sticky="ns", padx=(0, 2))
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # scroll with wheel
        def _on_mousewheel(event):
            self.pdf_checkbox_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.pdf_checkbox_canvas.bind("<Enter>",
                                      lambda e: self.pdf_checkbox_canvas.bind_all(
                                          "<MouseWheel>", _on_mousewheel))
        self.pdf_checkbox_canvas.bind("<Leave>",
                                      lambda e: self.pdf_checkbox_canvas.unbind_all(
                                          "<MouseWheel>"))

        # Outdir entry
        self.outdir_entry = tk.Entry(self)
        self.outdir_entry.grid(row=2, column=1, sticky="we", padx=5)
        tk.Button(self, text="…", command=self.browse_outdir).grid(row=2, column=2)

        # Action buttons
        self.gen_btn_row = tk.Frame(self)
        self.gen_btn_row.grid(row=3, column=0, columnspan=3, pady=10)

        self.gen_btn = tk.Button(
            self.gen_btn_row, text="Generate Flashcards",
            command=self.generate_flashcards, state="disabled")
        self.gen_btn.pack(side="left", padx=4)

        self.review_btn = tk.Button(
            self.gen_btn_row, text="Review Flashcards",
            command=self.review_current, state="disabled")
        self.review_btn.pack(side="left", padx=4)

        self.edit_btn = tk.Button(
            self.gen_btn_row, text="Edit Flashcards",
            command=self.edit_current, state="disabled")
        self.edit_btn.pack(side="left", padx=4)

        self.pdf_checkboxes: dict[str, tk.BooleanVar] = {}

    # -------------------------------------------------------------------------#
    # Helper UI utilities
    # -------------------------------------------------------------------------#
    def browse_outdir(self):
        d = filedialog.askdirectory(title="Outdir auswählen")
        if d:
            self.outdir_entry.delete(0, 'end')
            self.outdir_entry.insert(0, d)

    def update_pdf_list(self):
        """Refresh list of *.pdf and *.txt files for the current goal dir."""
        # clear old
        for widget in self.pdf_checkbox_inner_frame.winfo_children():
            widget.destroy()
        self.pdf_checkboxes.clear()

        goal = self.get_current_goal()
        if not goal:
            tk.Label(self.pdf_checkbox_inner_frame,
                     text="(Kein Lernziel ausgewählt)").pack(anchor="w")
            return

        dirname = self.sanitize_dirname(goal)
        outdir = self.get_outdir()
        dirpath = os.path.join(outdir, dirname)
        if not os.path.isdir(dirpath):
            tk.Label(self.pdf_checkbox_inner_frame,
                     text="(Kein Verzeichnis angelegt)").pack(anchor="w")
            return

        files = sorted(
            f for f in os.listdir(dirpath)
            if f.lower().endswith(('.pdf', '.txt'))
            and os.path.isfile(os.path.join(dirpath, f))
        )
        if not files:
            tk.Label(self.pdf_checkbox_inner_frame,
                     text="(Keine passenden Dateien gefunden)").pack(anchor="w")
            return

        for f in files:
            var = tk.BooleanVar()
            chk = tk.Checkbutton(self.pdf_checkbox_inner_frame,
                                 text=f, variable=var, anchor="w")
            chk.pack(anchor="w", fill="x")
            self.pdf_checkboxes[f] = var

    def update_outdir_entry_for_goal(self):
        """Adjust outdir entry so user sees full path of current goal folder."""
        outdir = self.get_outdir()
        goal = self.get_current_goal()
        if not goal:
            self.outdir_entry.delete(0, 'end')
            self.outdir_entry.insert(0, outdir)
            return
        goal_dir = os.path.join(outdir, self.sanitize_dirname(goal))
        self.outdir_entry.delete(0, 'end')
        self.outdir_entry.insert(0, goal_dir)

    def set_action_buttons_state(self, state: str):
        """Enable/disable main buttons together."""
        self.gen_btn.config(state=state)
        self.review_btn.config(state=state)
        self.edit_btn.config(state=state)

    # -------------------------------------------------------------------------#
    # Flash-card generation
    # -------------------------------------------------------------------------#
    def generate_flashcards(self):
        selected_files = [fn for fn, v in self.pdf_checkboxes.items() if v.get()]
        if not selected_files:
            messagebox.showerror("Fehler",
                                 "Bitte wählen Sie mindestens eine Datei aus (.pdf oder .txt).")
            return

        goal = self.get_current_goal().strip()
        dirname = self.sanitize_dirname(goal)
        outdir = self.get_outdir()

        errors, created = [], []

        for filename in selected_files:
            path = os.path.join(outdir, dirname, filename)
            goal_dir = os.path.join(outdir, dirname)
            os.makedirs(goal_dir, exist_ok=True)
            out_json = os.path.join(goal_dir, "flashcards.json")

            # keep one batch file per goal; if it exists, abort this file
            if os.path.exists(out_json):
                errors.append(f"{filename}: Batch existiert.")
                continue

            try:
                # determine file type
                if filename.lower().endswith(".pdf"):
                    # convert *all* pages
                    with open(path, "rb") as fpdf:
                        num_pages = len(PdfReader(fpdf).pages)
                    page_range = (1, num_pages)
                    flashcards = FLASHCARD_GENERATOR.generate_flashcards(
                        pdf_path=path,
                        page_range=page_range,
                        learning_goal=goal,
                    )
                    source_descriptor = f"PDF {filename} (S{page_range[0]}-{page_range[1]})"

                else:  # .txt
                    with open(path, "r", encoding="utf-8") as ftxt:
                        text_content = ftxt.read()
                    # Requires new helper on the generator backend:
                    flashcards = FLASHCARD_GENERATOR.generate_flashcards_from_text(
                        text_content=text_content,
                        learning_goal=goal,
                    )
                    source_descriptor = f"TXT {filename}"

                # write batch JSON
                import json
                with open(out_json, "w", encoding="utf-8") as fjson:
                    json.dump(
                        {
                            "learning_goal": goal,
                            "source": source_descriptor,
                            "file_path": path,
                            "flashcards": [fc.dict() for fc in flashcards],
                        },
                        fjson,
                        indent=2,
                        ensure_ascii=False,
                    )
                created.append(filename)

            except Exception as e:
                errors.append(f"{filename}: {e}")

        # Report results
        if created:
            self.review_btn.config(state="normal")
            self.refresh_all_goal_colors()

        if errors:
            messagebox.showerror(
                "Fehler",
                "Bei folgenden Dateien gab es Probleme:\n" + "\n".join(errors),
            )

        # reset checkboxes
        for var in self.pdf_checkboxes.values():
            var.set(False)

    # -------------------------------------------------------------------------#
    # Review / edit
    # -------------------------------------------------------------------------#
    def _batch_json_path(self, goal: str | None):
        if not goal:
            return None
        dir_ = os.path.join(self.get_outdir(), self.sanitize_dirname(goal))
        p = os.path.join(dir_, "flashcards.json")
        return p if os.path.isfile(p) else None

    def review_current(self):
        path = self._batch_json_path(self.get_current_goal())
        if not path:
            messagebox.showerror("Fehler", "Keine Flashcards vorhanden.")
            return
        data = self.load_flashcard_data(path)
        self.open_review_window(path)

    def edit_current(self):
        path = self._batch_json_path(self.get_current_goal())
        if not path:
            messagebox.showerror("Fehler", "Keine Flashcards vorhanden.")
            return
        self.open_editor_window(path)
        self.refresh_all_goal_colors()
