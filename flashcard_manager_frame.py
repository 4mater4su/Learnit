import tkinter as tk
from tkinter import messagebox, filedialog
import os
from PyPDF2 import PdfReader

from flashcard_generation import (
    ChainedFlashcardGenerator,
    OneShotFlashcardGenerator,
    FlashcardGenerator
)
# Choose the backend
FLASHCARD_GENERATOR: FlashcardGenerator = ChainedFlashcardGenerator()
# FLASHCARD_GENERATOR: FlashcardGenerator = OneShotFlashcardGenerator()  # switch if desired


class FlashcardManagerFrame(tk.LabelFrame):
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

        # Outdir
        tk.Label(self, text="Outdir:").grid(row=2,column=0,sticky="e")
        tk.Label(self, text="PDF wählen:").grid(row=0, column=0, sticky="e")
        # --- Scrollable checkbox area ---
        self.pdf_checkbox_canvas = tk.Canvas(self, height=120, highlightthickness=0)
        self.pdf_checkbox_scrollbar = tk.Scrollbar(self, orient="vertical", command=self.pdf_checkbox_canvas.yview)
        self.pdf_checkbox_inner_frame = tk.Frame(self.pdf_checkbox_canvas)

        self.pdf_checkbox_inner_frame.bind(
            "<Configure>",
            lambda e: self.pdf_checkbox_canvas.configure(
                scrollregion=self.pdf_checkbox_canvas.bbox("all")
            )
        )

        self.pdf_checkbox_canvas.create_window((0, 0), window=self.pdf_checkbox_inner_frame, anchor="nw")
        self.pdf_checkbox_canvas.configure(yscrollcommand=self.pdf_checkbox_scrollbar.set)
        self.pdf_checkbox_canvas.grid(row=0, column=1, sticky="nsew", padx=5, pady=2)
        self.pdf_checkbox_scrollbar.grid(row=0, column=2, sticky="ns", padx=(0, 2))
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        # --- End scrollable checkbox area ---

        def _on_checkbox_mousewheel(event):
            self.pdf_checkbox_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.pdf_checkbox_canvas.bind("<Enter>", lambda e: self.pdf_checkbox_canvas.bind_all("<MouseWheel>", _on_checkbox_mousewheel))
        self.pdf_checkbox_canvas.bind("<Leave>", lambda e: self.pdf_checkbox_canvas.unbind_all("<MouseWheel>"))

        # Outdir entry
        self.outdir_entry = tk.Entry(self)
        self.outdir_entry.grid(row=2,column=1,sticky="we",padx=5)
        tk.Button(self,text="…",command=self.browse_outdir).grid(row=2,column=2)

        # Action buttons row
        self.gen_btn_row = tk.Frame(self)
        self.gen_btn_row.grid(row=3, column=0, columnspan=3, pady=10)

        self.gen_btn = tk.Button(self.gen_btn_row, text="Generate Flashcards", command=self.generate_flashcards, state="disabled")
        self.gen_btn.pack(side="left", padx=4)
        self.review_btn = tk.Button(self.gen_btn_row, text="Review Flashcards", command=self.review_current, state="disabled")
        self.review_btn.pack(side="left", padx=4)
        self.edit_btn = tk.Button(self.gen_btn_row, text="Edit Flashcards", command=self.edit_current, state="disabled")
        self.edit_btn.pack(side="left", padx=4)

        self.pdf_checkboxes = {}

    def browse_outdir(self):
        d = filedialog.askdirectory(title="Outdir auswählen")
        if d: self.outdir_entry.delete(0,'end'); self.outdir_entry.insert(0,d)

    def update_pdf_list(self):
        # Clear old checkboxes
        for widget in self.pdf_checkbox_inner_frame.winfo_children():
            widget.destroy()
        self.pdf_checkboxes.clear()
        goal = self.get_current_goal()
        if not goal:
            tk.Label(self.pdf_checkbox_inner_frame, text="(Kein Lernziel ausgewählt)").pack(anchor="w")
            return
        dirname = self.sanitize_dirname(goal)
        outdir = self.get_outdir()
        dirpath = os.path.join(outdir, dirname)
        if not os.path.isdir(dirpath):
            tk.Label(self.pdf_checkbox_inner_frame, text="(Kein Verzeichnis angelegt)").pack(anchor="w")
            return
        files = sorted([f for f in os.listdir(dirpath) if f.lower().endswith('.pdf') and os.path.isfile(os.path.join(dirpath, f))])
        if not files:
            tk.Label(self.pdf_checkbox_inner_frame, text="(Keine PDFs gefunden)").pack(anchor="w")
        else:
            for f in files:
                var = tk.BooleanVar()
                chk = tk.Checkbutton(self.pdf_checkbox_inner_frame, text=f, variable=var, anchor="w")
                chk.pack(anchor="w", fill="x")
                self.pdf_checkboxes[f] = var

    def get_outdir_value(self):
        return self.outdir_entry.get().strip()
    
    def update_outdir_entry_for_goal(self):
        """Set the outdir entry to the current goal's folder."""
        outdir = self.get_outdir()
        goal = self.get_current_goal()
        if not goal:
            self.outdir_entry.delete(0, 'end')
            self.outdir_entry.insert(0, outdir)
            return
        dirname = self.sanitize_dirname(goal)
        goal_dir = os.path.join(outdir, dirname)
        self.outdir_entry.delete(0, 'end')
        self.outdir_entry.insert(0, goal_dir)

    def set_action_buttons_state(self, state):
        self.gen_btn.config(state=state)
        self.review_btn.config(state=state)
        self.edit_btn.config(state=state)

    def generate_flashcards(self):
        selected_pdfs = [fname for fname, var in self.pdf_checkboxes.items() if var.get()]
        if not selected_pdfs:
            messagebox.showerror("Fehler", "Bitte wählen Sie mindestens eine PDF-Datei aus.")
            return

        dirname = self.sanitize_dirname(self.get_current_goal())
        outdir = self.get_outdir()
        goal = self.get_current_goal().strip()
        errors = []
        created = []

        for pdf_filename in selected_pdfs:
            pdf_path = os.path.join(outdir, dirname, pdf_filename)
            try:
                with open(pdf_path, "rb") as f:
                    reader = PdfReader(f)
                    num_pages = len(reader.pages)
                page_range = (1, num_pages)

                goal_dir = os.path.join(outdir, dirname)
                os.makedirs(goal_dir, exist_ok=True)
                out_json = os.path.join(goal_dir, "flashcards.json")

                if os.path.exists(out_json):
                    errors.append(f"{pdf_filename}: Batch existiert.")
                    continue

                # ----------- NEW: use pluggable generator backend -----------
                flashcards = FLASHCARD_GENERATOR.generate_flashcards(
                    pdf_path=pdf_path,
                    page_range=page_range,
                    learning_goal=goal
                )
                import json
                with open(out_json, "w", encoding="utf-8") as f:
                    batch = {
                        "learning_goal": goal,
                        "page_range": f"{page_range[0]}-{page_range[1]}",
                        "pdf_path": pdf_path,
                        "flashcards": [fc.dict() for fc in flashcards]
                    }
                    json.dump(batch, f, indent=2, ensure_ascii=False)
                # ----------------------------------------------------------

                created.append(pdf_filename)
            except Exception as e:
                errors.append(f"{pdf_filename}: {e}")

        if created:
            messagebox.showinfo(
                "Erfolg",
                f"Flashcards für {len(created)} PDF(s) erstellt:\n" + "\n".join(created)
            )
            self.review_btn.config(state="normal")
            self.refresh_all_goal_colors()
        if errors:
            messagebox.showerror(
                "Fehler",
                "Bei einigen PDFs gab es Probleme:\n" + "\n".join(errors)
            )

        for var in self.pdf_checkboxes.values():
            var.set(False)

    def find_json_for_goal(self, goal):
        outdir = self.get_outdir()
        dirname = self.sanitize_dirname(goal)
        json_path = os.path.join(outdir, dirname, "flashcards.json")
        if os.path.isfile(json_path):
            return json_path
        return None

    def review_current(self):
        goal = self.get_current_goal()
        path = self.find_json_for_goal(goal)
        if not path:
            messagebox.showerror("Fehler", "Keine Flashcards vorhanden.")
            return
        self.open_review_window(path)

    def edit_current(self):
        goal = self.get_current_goal()
        path = self.find_json_for_goal(goal)
        if not path:
            messagebox.showerror("Fehler", "Keine Flashcards vorhanden.")
            return
        self.open_editor_window(path)
        self.refresh_all_goal_colors()

