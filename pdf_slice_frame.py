import tkinter as tk
from tkinter import filedialog, messagebox
import os

class PDFSliceFrame(tk.LabelFrame):
    def __init__(self, parent, get_current_goal, get_outdir, sanitize_dirname, slice_pdf_func, update_callback, refresh_all_goal_colors, **kwargs):
        super().__init__(parent, text="PDF zuschneiden und speichern", **kwargs)
        self.get_current_goal = get_current_goal
        self.get_outdir = get_outdir
        self.sanitize_dirname = sanitize_dirname
        self.slice_pdf_func = slice_pdf_func
        self.update_callback = update_callback  # To refresh file lists after slicing
        self.refresh_all_goal_colors = refresh_all_goal_colors

        tk.Label(self, text="PDF:").grid(row=0, column=0, sticky="e")
        self.slice_pdf_entry = tk.Entry(self)
        self.slice_pdf_entry.grid(row=0, column=1, sticky="we", padx=5)
        tk.Button(self, text="…", command=self.browse_slice_pdf).grid(row=0, column=2)

        tk.Label(self, text="Seiten:").grid(row=1, column=0, sticky="e")
        self.slice_start_spin = tk.Spinbox(self, from_=1, to=9999, width=5)
        self.slice_start_spin.grid(row=1, column=1, sticky="w")
        self.slice_end_spin = tk.Spinbox(self, from_=1, to=9999, width=5)
        self.slice_end_spin.grid(row=1, column=2, sticky="w")

        self.slice_btn = tk.Button(self, text="PDF ausschneiden & speichern", command=self.slice_and_save_pdf, state="disabled")
        self.slice_btn.grid(row=2, column=0, columnspan=3, pady=8)
        self.columnconfigure(1, weight=1)

    def browse_slice_pdf(self):
        p = filedialog.askopenfilename(title="PDF auswählen", filetypes=[("PDF", "*.pdf")])
        if p:
            self.slice_pdf_entry.delete(0, 'end')
            self.slice_pdf_entry.insert(0, p)

    def slice_and_save_pdf(self):
        goal = self.get_current_goal()
        if not goal:
            messagebox.showerror("Fehler", "Kein Lernziel ausgewählt.")
            return
        in_pdf = self.slice_pdf_entry.get().strip()
        try:
            start = int(self.slice_start_spin.get())
            end = int(self.slice_end_spin.get())
        except:
            messagebox.showerror("Fehler", "Ungültige Seitenzahl.")
            return
        if not os.path.isfile(in_pdf):
            messagebox.showerror("Fehler", "PDF-Datei nicht gefunden.")
            return
        if end < start or start < 1:
            messagebox.showerror("Fehler", "Ungültiger Seitenbereich.")
            return

        dirname = self.sanitize_dirname(goal)
        outdir = self.get_outdir()
        target_dir = os.path.join(outdir, dirname)
        if not os.path.isdir(target_dir):
            messagebox.showerror("Fehler", "Verzeichnis für Lernziel nicht vorhanden. Bitte zuerst anlegen.")
            return
        base = os.path.splitext(os.path.basename(in_pdf))[0]
        out_pdf = os.path.join(target_dir, f"{base}_S{start}-{end}.pdf")
        try:
            self.slice_pdf_func(in_pdf, out_pdf, start, end)
            messagebox.showinfo("Erfolg", f"PDF gespeichert: {out_pdf}")
            if self.update_callback:
                self.update_callback()
            if self.refresh_all_goal_colors:
                self.refresh_all_goal_colors()
        except Exception as e:
            messagebox.showerror("Fehler", f"PDF konnte nicht gespeichert werden:\n{e}")

    def set_slice_button_state(self, state):
        self.slice_btn.config(state=state)
