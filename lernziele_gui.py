# -*- coding: utf-8 -*-

"""
Module: lernziele_gui.py

Ein Tkinter-GUI, das deine Excel-Daten lädt und alle Lernziele
in einer scrollbaren Listbox anzeigt. Nach Auswahl eines Lernziels
kannst du es in die Zwischenablage kopieren, Flashcards generieren
oder direkt eine Review-Session starten, falls Flashcards bereits existieren.
"""

import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

from excel_parser import load_data
from flashcard_manager import (
    generate_flashcards_from_pdf,
    load_flashcard_data,
    update_progress
)


class LernzieleViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lernziele Viewer")
        self.geometry("800x800")

        # Top: Datei öffnen
        top_frame = tk.Frame(self, pady=10)
        top_frame.pack(fill="x")
        load_btn = tk.Button(
            top_frame,
            text="Excel öffnen…",
            command=self.choose_and_load_file,
            width=15
        )
        load_btn.pack(side="left", padx=10)

        # Listbox Bereich
        list_frame = tk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0,10))
        v_scroll = tk.Scrollbar(list_frame, orient="vertical")
        v_scroll.pack(side="right", fill="y")
        self.listbox = tk.Listbox(
            list_frame,
            selectmode="browse",
            yscrollcommand=v_scroll.set
        )
        self.listbox.pack(fill="both", expand=True)
        v_scroll.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # Detail Bereich
        details_frame = tk.LabelFrame(self, text="Ausgewähltes Lernziel")
        details_frame.pack(fill="x", padx=10, pady=(0,10))
        self.details_text = tk.Text(
            details_frame,
            height=4,
            wrap="word",
            state="disabled"
        )
        self.details_text.pack(fill="both", expand=True)
        self.copy_btn = tk.Button(
            details_frame,
            text="Kopieren",
            command=self.copy_to_clipboard,
            state="disabled"
        )
        self.copy_btn.pack(pady=5)

        # Flashcard Generator Bereich
        fc_frame = tk.LabelFrame(self, text="Flashcards generieren")
        fc_frame.pack(fill="x", padx=10, pady=(0,10))
        tk.Label(fc_frame, text="PDF-Datei:").grid(row=0, column=0, sticky="e")
        self.pdf_entry = tk.Entry(fc_frame)
        self.pdf_entry.grid(row=0, column=1, sticky="we", padx=5)
        tk.Button(fc_frame, text="…", command=self.browse_pdf).grid(row=0, column=2)

        tk.Label(fc_frame, text="Seiten (Start End):").grid(row=1, column=0, sticky="e")
        self.start_spin = tk.Spinbox(fc_frame, from_=1, to=9999, width=5)
        self.start_spin.grid(row=1, column=1, sticky="w")
        self.end_spin = tk.Spinbox(fc_frame, from_=1, to=9999, width=5)
        self.end_spin.grid(row=1, column=2, sticky="w")

        tk.Label(fc_frame, text="Ausgabeverz.:").grid(row=2, column=0, sticky="e")
        self.outdir_entry = tk.Entry(fc_frame)
        self.outdir_entry.insert(0, "flashcards")
        self.outdir_entry.grid(row=2, column=1, sticky="we", padx=5)
        tk.Button(fc_frame, text="…", command=self.browse_outdir).grid(row=2, column=2)

        self.gen_btn = tk.Button(
            fc_frame,
            text="Generate Flashcards",
            command=self.generate_flashcards,
            state="disabled"
        )
        self.gen_btn.grid(row=3, column=0, columnspan=3, pady=10)
        fc_frame.columnconfigure(1, weight=1)

        # Review Bereich
        rev_frame = tk.LabelFrame(self, text="Flashcards reviewen")
        rev_frame.pack(fill="x", padx=10, pady=(0,10))
        tk.Label(rev_frame, text="Batch-JSON:").grid(row=0, column=0, sticky="e")
        self.json_entry = tk.Entry(rev_frame)
        self.json_entry.grid(row=0, column=1, sticky="we", padx=5)
        self.rev_btn = tk.Button(
            rev_frame,
            text="Start Review",
            command=self.start_review,
            state="disabled"
        )
        self.rev_btn.grid(row=1, column=0, columnspan=3, pady=10)
        rev_frame.columnconfigure(1, weight=1)

        # Review Session State
        self.lernziele = []
        self.current_text = ""
        self.flashcards = []
        self.review_index = 0
        self.session_results = []
        self.current_json_path = None

    def choose_and_load_file(self):
        path = filedialog.askopenfilename(
            title="Bitte Excel-Datei auswählen",
            filetypes=[("Excel Dateien", "*.xlsx *.xls")]
        )
        if not path:
            return
        try:
            df = load_data(path)
        except Exception as e:
            messagebox.showerror("Fehler beim Laden", str(e))
            return
        if "Lernziel" not in df.columns:
            messagebox.showwarning("Spalte fehlt", "Keine Spalte 'Lernziel'.")
            return
        self.lernziele = df["Lernziel"].astype(str).tolist()
        self.listbox.delete(0, tk.END)
        for i, txt in enumerate(self.lernziele, 1):
            preview = txt[:80].rstrip() + ("…" if len(txt) > 80 else "")
            self.listbox.insert(tk.END, f"{i}. {preview}")
        self.title(f"Lernziele Viewer — {os.path.basename(path)}")
        # Reset controls
        self.details_text.config(state="normal"); self.details_text.delete("1.0","end"); self.details_text.config(state="disabled")
        self.copy_btn.config(state="disabled"); self.gen_btn.config(state="disabled")
        self.json_entry.delete(0, "end"); self.rev_btn.config(state="disabled")

    def on_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        text = self.lernziele[idx]
        self.current_text = text
        # show detail
        self.details_text.config(state="normal"); self.details_text.delete("1.0","end"); self.details_text.insert("end", text); self.details_text.config(state="disabled")
        self.copy_btn.config(state="normal"); self.gen_btn.config(state="normal")
        # auto-find existing JSON batch
        self.auto_find_json()

    def auto_find_json(self):
        outdir = self.outdir_entry.get().strip() or "flashcards"
        if not os.path.isdir(outdir):
            return
        matches = []
        for fname in os.listdir(outdir):
            if fname.endswith('.json'):
                try:
                    data = json.load(open(os.path.join(outdir, fname), 'r', encoding='utf-8'))
                    if data.get('learning_goal') == self.current_text:
                        matches.append(os.path.join(outdir, fname))
                except Exception:
                    continue
        if matches:
            # take first match
            self.current_json_path = matches[0]
            self.json_entry.delete(0, 'end')
            self.json_entry.insert(0, self.current_json_path)
            self.rev_btn.config(state='normal')
        else:
            self.current_json_path = None
            self.json_entry.delete(0, 'end')
            self.rev_btn.config(state='disabled')

    def copy_to_clipboard(self):
        self.clipboard_clear(); self.clipboard_append(self.current_text)
        messagebox.showinfo("Kopiert", "Lernziel in Zwischenablage kopiert.")

    def browse_pdf(self):
        p = filedialog.askopenfilename(title="PDF auswählen", filetypes=[("PDF Datei", "*.pdf")])
        if p:
            self.pdf_entry.delete(0, "end"); self.pdf_entry.insert(0, p)

    def browse_outdir(self):
        d = filedialog.askdirectory(title="Ausgabeverzeichnis auswählen")
        if d:
            self.outdir_entry.delete(0, "end"); self.outdir_entry.insert(0, d)
        # after changing outdir, try auto-find again if a goal is selected
        if self.current_text:
            self.auto_find_json()

    def generate_flashcards(self):
        pdf = self.pdf_entry.get().strip()
        try:
            start = int(self.start_spin.get()); end = int(self.end_spin.get())
        except ValueError:
            messagebox.showerror("Ungültige Seitenzahl", "Bitte gültige Zahlen eingeben.")
            return
        goal = self.current_text.strip()
        outdir = self.outdir_entry.get().strip() or "flashcards"
        os.makedirs(outdir, exist_ok=True)
        fname = goal.replace(" ", "_")[:30] + f"_{start}_{end}.json"
        outpath = os.path.join(outdir, fname)
        if os.path.exists(outpath):
            messagebox.showerror("Datei existiert", f"{outpath} existiert bereits.")
            return
        try:
            generate_flashcards_from_pdf(
                pdf_path=pdf,
                page_range=(start, end),
                learning_goal=goal,
                output_json_path=outpath
            )
            messagebox.showinfo("Erfolg", f"Flashcards gespeichert:\n{outpath}")
            # after generation, auto-find and enable review
            self.auto_find_json()
        except Exception as e:
            messagebox.showerror("Fehler beim Generieren", str(e))

    def start_review(self):
        json_path = self.json_entry.get().strip()
        if not json_path or not os.path.exists(json_path):
            messagebox.showerror("Fehler", "Bitte gültige JSON-Datei auswählen.")
            return
        data = load_flashcard_data(json_path)
        self.flashcards = data["flashcards"]
        self.review_index = 0
        self.session_results = []
        self.review_data = data
        # build and show review window
        self.review_window = tk.Toplevel(self)
        self.review_window.title("Flashcard Review")
        self._build_review_ui()
        self._show_current_card()

    def _build_review_ui(self):
        f = self.review_window
        tk.Label(f, text="Frage:").pack(anchor="w", padx=10, pady=(10,0))
        self.q_label = tk.Label(f, text="", wraplength=600, justify="left")
        self.q_label.pack(fill="x", padx=10)
        tk.Button(f, text="Antwort anzeigen", command=self._show_answer).pack(pady=5)
        tk.Label(f, text="Antwort:").pack(anchor="w", padx=10)
        self.a_label = tk.Label(f, text="", wraplength=600, justify="left", fg="blue")
        self.a_label.pack(fill="x", padx=10)
        rating_frame = tk.Frame(f)
        rating_frame.pack(pady=10)
        tk.Label(rating_frame, text="Bewertung:").pack(side="left")
        self.rating_var = tk.IntVar(value=2)
        for val, txt in [(1,"Einfach"),(2,"Mittel"),(3,"Schwer")]:
            tk.Radiobutton(rating_frame, text=txt, variable=self.rating_var, value=val).pack(side="left", padx=5)
        tk.Button(f, text="Weiter", command=self._next_card).pack(pady=(0,10))

    def _show_current_card(self):
        card = self.flashcards[self.review_index]
        self.q_label.config(text=card["question"])
        self.a_label.config(text="")
        self.rating_var.set(2)

    def _show_answer(self):
        card = self.flashcards[self.review_index]
        self.a_label.config(text=card["answer"])

    def _next_card(self):
        rating = self.rating_var.get()
        card = self.flashcards[self.review_index]
        self.session_results.append({
            "question": card["question"],
            "answer": card["answer"],
            "rating": rating
        })
        self.review_index += 1
        if self.review_index < len(self.flashcards):
            self._show_current_card()
        else:
            # Ende der Session: speichern & schließen
            key = f"{self.review_data.get('learning_goal','')} (Seiten {self.review_data.get('page_range','')})"
            try:
                update_progress(key, self.session_results, timestamp=datetime.now().isoformat(timespec="seconds"))
            except Exception:
                pass
            messagebox.showinfo("Fertig", "Review beendet.")
            self.review_window.destroy()


if __name__ == __name__ == "__main__":
    app = LernzieleViewer()
    app.mainloop()
