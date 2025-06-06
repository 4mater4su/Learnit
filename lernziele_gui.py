#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module: lernziele_gui.py

Ein Tkinter-GUI, das deine Excel-Daten lädt und alle Lernziele
in einer scrollbaren Listbox anzeigt. Wenn du ein Lernziel
anklickst, wird es komplett unten angezeigt – und per Button
kannst du es in die Zwischenablage kopieren.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from excel_parser import load_data


class LernzieleViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lernziele Viewer")
        self.geometry("800x600")

        # ─── Obere Leiste mit „Datei öffnen…“-Button ───────────────────────────────
        top_frame = tk.Frame(self, pady=10)
        top_frame.pack(fill="x")
        load_btn = tk.Button(
            top_frame,
            text="Datei öffnen…",
            command=self.choose_and_load_file,
            width=15
        )
        load_btn.pack(side="left", padx=10)

        # ─── Hauptbereich mit Listbox + Scrollbar ─────────────────────────────────
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

        # ─── Detail-Bereich ───────────────────────────────────────────────────────
        details_frame = tk.Frame(self, relief="groove", bd=1, pady=5)
        details_frame.pack(fill="both", padx=10, pady=(0,10))

        tk.Label(details_frame, text="Ausgewähltes Lernziel:").pack(anchor="w")

        # Text-Widget für das komplette Lernziel
        self.details_text = tk.Text(
            details_frame,
            height=8,
            wrap="word",
            state="disabled"
        )
        self.details_text.pack(fill="both", expand=True, side="left")

        # Scrollbar fürs Detail-Textfeld
        detail_scroll = tk.Scrollbar(details_frame, orient="vertical", command=self.details_text.yview)
        detail_scroll.pack(side="right", fill="y")
        self.details_text.config(yscrollcommand=detail_scroll.set)

        # Copy-Button
        self.copy_btn = tk.Button(
            details_frame,
            text="In Zwischenablage kopieren",
            command=self.copy_to_clipboard,
            state="disabled"
        )
        self.copy_btn.pack(pady=5)

        # intern: Liste kompletter Lernziele und aktuell ausgewählter Text
        self.lernziele = []
        self.current_text = ""

    def choose_and_load_file(self):
        pfad = filedialog.askopenfilename(
            title="Bitte wähle eine Excel-Datei mit Lernzielen aus",
            filetypes=[("Excel Dateien", "*.xlsx *.xls")]
        )
        if not pfad:
            return

        try:
            df = load_data(pfad)
        except Exception as e:
            messagebox.showerror(
                "Fehler beim Laden",
                f"Die Datei konnte nicht gelesen werden:\n{e}"
            )
            return

        if "Lernziel" not in df.columns:
            messagebox.showwarning(
                "Spalte fehlt",
                "In der geladenen Tabelle wurde keine Spalte 'Lernziel' gefunden."
            )
            return

        self.lernziele = df["Lernziel"].astype(str).tolist()
        self.listbox.delete(0, tk.END)
        for idx, text in enumerate(self.lernziele, start=1):
            preview = text.strip()
            if len(preview) > 80:
                preview = preview[:80].rstrip() + "…"
            self.listbox.insert(tk.END, f"{idx}. {preview}")

        import os
        self.title(f"Lernziele Viewer — {os.path.basename(pfad)}")

        # Reset Detail-Bereich
        self.details_text.config(state="normal")
        self.details_text.delete("1.0", "end")
        self.details_text.config(state="disabled")
        self.copy_btn.config(state="disabled")
        self.current_text = ""

    def on_select(self, event):
        sel = event.widget.curselection()
        if not sel:
            return

        idx = sel[0]
        self.current_text = self.lernziele[idx]

        # Detail-Text anzeigen
        self.details_text.config(state="normal")
        self.details_text.delete("1.0", "end")
        self.details_text.insert("end", self.current_text)
        self.details_text.config(state="disabled")

        # Copy-Button aktivieren
        self.copy_btn.config(state="normal")

    def copy_to_clipboard(self):
        if not self.current_text:
            return
        # In die Zwischenablage kopieren
        self.clipboard_clear()
        self.clipboard_append(self.current_text)
        #messagebox.showinfo("Kopiert", "Lernziel wurde in die Zwischenablage kopiert.")


if __name__ == "__main__":
    app = LernzieleViewer()
    app.mainloop()
