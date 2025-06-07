#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module: lernziele_gui.py

Ein Tkinter-GUI, das deine Excel-Daten lädt und alle Lernziele
in einer scrollbaren Listbox anzeigt. Wenn du ein Lernziel
anklickst, wird es komplett unten angezeigt – und du kannst
es in die Zwischenablage kopieren oder direkt Flashcards generieren.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox

from excel_parser import load_data
from flashcard_manager import generate_flashcards_from_pdf


class LernzieleViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lernziele Viewer")
        self.geometry("800x700")

        # Top: Datei öffnen
        top_frame = tk.Frame(self, pady=10)
        top_frame.pack(fill="x")
        load_btn = tk.Button(
            top_frame,
            text="Datei öffnen…",
            command=self.choose_and_load_file,
            width=15
        )
        load_btn.pack(side="left", padx=10)

        # Main: Listbox mit Scrollbar
        main_frame = tk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=(0,10))

        v_scroll = tk.Scrollbar(main_frame, orient="vertical")
        v_scroll.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            main_frame,
            selectmode="browse",
            yscrollcommand=v_scroll.set
        )
        self.listbox.pack(fill="both", expand=True)
        v_scroll.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # Detail-Bereich
        details_frame = tk.Frame(self, relief="groove", bd=1, pady=5)
        details_frame.pack(fill="both", padx=10, pady=(0,10))
        tk.Label(details_frame, text="Ausgewähltes Lernziel:").pack(anchor="w")

        self.details_text = tk.Text(
            details_frame,
            height=6,
            wrap="word",
            state="disabled"
        )
        self.details_text.pack(fill="both", expand=True, side="left")
        detail_scroll = tk.Scrollbar(
            details_frame,
            orient="vertical",
            command=self.details_text.yview
        )
        detail_scroll.pack(side="right", fill="y")
        self.details_text.config(yscrollcommand=detail_scroll.set)

        self.copy_btn = tk.Button(
            details_frame,
            text="Kopieren",
            command=self.copy_to_clipboard,
            state="disabled"
        )
        self.copy_btn.pack(pady=5)

        # Flashcard-Generator-Bereich
        fc_frame = tk.Frame(self, relief="ridge", bd=1, pady=5)
        fc_frame.pack(fill="x", padx=10, pady=(0,10))
        tk.Label(fc_frame, text="Flashcards generieren:").grid(row=0, column=0, sticky="w", columnspan=3)

        tk.Label(fc_frame, text="PDF-Datei:").grid(row=1, column=0, sticky="e")
        self.pdf_entry = tk.Entry(fc_frame)
        self.pdf_entry.grid(row=1, column=1, sticky="we", padx=5)
        pdf_btn = tk.Button(
            fc_frame,
            text="Auswählen…",
            command=self.browse_pdf
        )
        pdf_btn.grid(row=1, column=2, padx=5)

        tk.Label(fc_frame, text="Startseite:").grid(row=2, column=0, sticky="e")
        self.start_spin = tk.Spinbox(fc_frame, from_=1, to=9999, width=5)
        self.start_spin.grid(row=2, column=1, sticky="w", padx=5)
        tk.Label(fc_frame, text="Endseite:").grid(row=2, column=2, sticky="e")
        self.end_spin = tk.Spinbox(fc_frame, from_=1, to=9999, width=5)
        self.end_spin.grid(row=2, column=3, sticky="w", padx=5)

        tk.Label(fc_frame, text="Ausgabeverzeichnis:").grid(row=3, column=0, sticky="e")
        self.outdir_entry = tk.Entry(fc_frame)
        self.outdir_entry.insert(0, "flashcards")
        self.outdir_entry.grid(row=3, column=1, sticky="we", padx=5)
        outdir_btn = tk.Button(
            fc_frame,
            text="Verzeichnis…",
            command=self.browse_outdir
        )
        outdir_btn.grid(row=3, column=2, padx=5)

        self.gen_btn = tk.Button(
            fc_frame,
            text="Generate Flashcards",
            command=self.generate_flashcards,
            state="disabled"
        )
        self.gen_btn.grid(row=4, column=0, columnspan=3, pady=10)

        fc_frame.columnconfigure(1, weight=1)

        self.lernziele = []
        self.current_text = ""

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
            preview = txt[:80].rstrip() + ("…" if len(txt)>80 else "")
            self.listbox.insert(tk.END, f"{i}. {preview}")
        self.title(f"Lernziele Viewer — {os.path.basename(path)}")
        # disable fc until selection
        self.details_text.config(state="normal"); self.details_text.delete("1.0","end"); self.details_text.config(state="disabled")
        self.copy_btn.config(state="disabled"); self.gen_btn.config(state="disabled")

    def on_select(self, event):
        sel = self.listbox.curselection()
        if not sel: return
        idx = sel[0]
        text = self.lernziele[idx]
        self.current_text = text
        self.details_text.config(state="normal"); self.details_text.delete("1.0","end"); self.details_text.insert("end", text); self.details_text.config(state="disabled")
        self.copy_btn.config(state="normal"); self.gen_btn.config(state="normal")

    def copy_to_clipboard(self):
        self.clipboard_clear(); self.clipboard_append(self.current_text)
        messagebox.showinfo("Kopiert", "Lernziel in Zwischenablage kopiert.")

    def browse_pdf(self):
        p = filedialog.askopenfilename(
            title="PDF auswählen",
            filetypes=[("PDF Datei", "*.pdf")]
        )
        if p: self.pdf_entry.delete(0, "end"); self.pdf_entry.insert(0, p)

    def browse_outdir(self):
        d = filedialog.askdirectory(
            title="Ausgabeverzeichnis auswählen"
        )
        if d: self.outdir_entry.delete(0, "end"); self.outdir_entry.insert(0, d)

    def generate_flashcards(self):
        pdf = self.pdf_entry.get().strip()
        try:
            start = int(self.start_spin.get())
            end = int(self.end_spin.get())
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
        except Exception as e:
            messagebox.showerror("Fehler beim Generieren", str(e))


if __name__ == "__main__":
    app = LernzieleViewer()
    app.mainloop()
