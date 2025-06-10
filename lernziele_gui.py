# -*- coding: utf-8 -*-

from PyPDF2 import PdfReader
import subprocess
import sys
import shutil
import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
import re

from excel_parser import load_data
from flashcard_manager import (
    generate_flashcards_from_pdf,
    load_flashcard_data,
    update_progress,
    slice_pdf
)

def sanitize_dirname(name):
    # Keep letters, numbers, dash/underscore. Replace spaces with underscores.
    sanitized = re.sub(r'[^A-Za-z0-9_\-]', '_', name.replace(' ', '_'))
    return sanitized[:100]

def create_dark_button(parent, text, command, width=400, height=60, font=('SF Pro Display', 20, 'bold'), bg='#232526', fg='white', hover_bg='#34373a', key=None):
    canvas = tk.Canvas(parent, height=height, width=width, bg=bg, highlightthickness=0, bd=0)
    rect = canvas.create_rectangle(0, 0, width, height, fill=bg, outline=bg, width=0)
    label = canvas.create_text(width//2, height//2, text=text, fill=fg, font=font)

    def on_enter(event=None):
        canvas.itemconfig(rect, fill=hover_bg)
    def on_leave(event=None):
        canvas.itemconfig(rect, fill=bg)
    def on_click(event=None):
        command()
    canvas.bind("<Enter>", on_enter)
    canvas.bind("<Leave>", on_leave)
    canvas.bind("<Button-1>", on_click)
    canvas.configure(cursor='hand2')

    # Keyboard support: space/return or optional custom key
    def on_key(event):
        if key:
            # this is a rating button → only react to its specific key ('1','2' or '3')
            if event.char == key:
                command()
        else:
            # this is the action button → only react to Enter/Space
            if event.keysym in ('Return', 'space'):
                command()
    canvas.bind("<Key>", on_key)

    return canvas

class LernzieleViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lernziele Viewer")
        self.geometry("800x800")

        # --- Scrollable main content setup ---
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.container, borderwidth=0)
        self.scrollbar = tk.Scrollbar(self.container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        def _on_main_canvas_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", _on_main_canvas_mousewheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))


        self.default_outdir = "flashcards"
        self.lernziele = []
        self.current_text = ""

        # Oben: Excel laden
        top_frame = tk.Frame(self.scrollable_frame, pady=10)
        top_frame.pack(fill="x")
        tk.Button(top_frame, text="Excel öffnen…", command=self.choose_and_load_file, width=15).pack(side="left", padx=10)

        # Listbox
        list_frame = tk.Frame(self.scrollable_frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0,10))
        v_scroll = tk.Scrollbar(list_frame, orient="vertical")
        v_scroll.pack(side="right", fill="y")
        self.listbox = tk.Listbox(list_frame, selectmode="browse", yscrollcommand=v_scroll.set)
        self.listbox.pack(fill="both", expand=True)
        v_scroll.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # Detail & Make Directory
        details = tk.LabelFrame(self.scrollable_frame, text="Ausgewähltes Lernziel")
        details.pack(fill="x", padx=10, pady=(0,10))
        self.details_text = tk.Text(details, height=4, wrap="word", state="disabled")
        self.details_text.pack(fill="both", expand=True)

        # File list label
        self.filelist_label = tk.Label(details, text="Dateien im Verzeichnis:", anchor="w")
        self.filelist_label.pack(fill="x", padx=4, pady=(2,0))

        # File listbox
        self.filelist_box = tk.Listbox(details, height=4, activestyle='dotbox')
        self.filelist_box.pack(fill="both", expand=False, padx=4, pady=(0,4))
        self.filelist_box.bind('<Double-Button-1>', self.open_selected_file)
        self.filelist_box.bind('<Button-2>', self.show_file_context_menu)  # Right-click on most systems | On Mac, <Button-2> is sometimes used

        self.copy_btn = tk.Button(details, text="Kopieren", command=self.copy_to_clipboard, state="disabled")
        self.copy_btn.pack(pady=5)

        self.mkdir_btn = tk.Button(details, text="Verzeichnis anlegen", command=self.create_goal_directory, state="disabled")
        self.mkdir_btn.pack(pady=5)

        self.adddoc_btn = tk.Button(details, text="Dokument hinzufügen", command=self.add_document_to_goal, state="disabled")
        self.adddoc_btn.pack(pady=5)

        # PDF Slicing and copying to lz directory
        pdfslice = tk.LabelFrame(self.scrollable_frame, text="PDF zuschneiden und speichern")
        pdfslice.pack(fill="x", padx=10, pady=(0,10))

        tk.Label(pdfslice, text="PDF:").grid(row=0, column=0, sticky="e")
        self.slice_pdf_entry = tk.Entry(pdfslice)
        self.slice_pdf_entry.grid(row=0, column=1, sticky="we", padx=5)
        tk.Button(pdfslice, text="…", command=self.browse_slice_pdf).grid(row=0, column=2)

        tk.Label(pdfslice, text="Seiten:").grid(row=1, column=0, sticky="e")
        self.slice_start_spin = tk.Spinbox(pdfslice, from_=1, to=9999, width=5)
        self.slice_start_spin.grid(row=1, column=1, sticky="w")
        self.slice_end_spin = tk.Spinbox(pdfslice, from_=1, to=9999, width=5)
        self.slice_end_spin.grid(row=1, column=2, sticky="w")

        self.slice_btn = tk.Button(pdfslice, text="PDF ausschneiden & speichern", command=self.slice_and_save_pdf, state="disabled")
        self.slice_btn.grid(row=2, column=0, columnspan=3, pady=8)
        pdfslice.columnconfigure(1, weight=1)

        # Checkboxes for selecting the PDFs used for generating flashcards
        self.pdf_checkboxes = {}   # filename → tk.BooleanVar
        self.pdf_checkbox_frame = None  # will be created dynamically

        # Flashcard Generator
        gen = tk.LabelFrame(self.scrollable_frame, text="Flashcards generieren")
        gen.pack(fill="x", padx=10, pady=(0,10))
        tk.Label(gen, text="Outdir:").grid(row=2,column=0,sticky="e")
        tk.Label(gen, text="PDF wählen:").grid(row=0, column=0, sticky="e")
        # --- Begin scrollable checkbox area ---
        self.pdf_checkbox_canvas = tk.Canvas(gen, height=120, highlightthickness=0)
        self.pdf_checkbox_scrollbar = tk.Scrollbar(gen, orient="vertical", command=self.pdf_checkbox_canvas.yview)
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
        gen.grid_rowconfigure(0, weight=1)
        gen.grid_columnconfigure(1, weight=1)
        # --- End scrollable checkbox area ---

        # Mousewheel Support for the Scrollable Checkbox Frame
        def _on_checkbox_mousewheel(event):
            self.pdf_checkbox_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.pdf_checkbox_canvas.bind("<Enter>", lambda e: self.pdf_checkbox_canvas.bind_all("<MouseWheel>", _on_checkbox_mousewheel))
        self.pdf_checkbox_canvas.bind("<Leave>", lambda e: self.pdf_checkbox_canvas.unbind_all("<MouseWheel>"))


        gen.columnconfigure(1, weight=1)

        self.outdir_entry = tk.Entry(gen)
        self.outdir_entry.insert(0,self.default_outdir)
        self.outdir_entry.grid(row=2,column=1,sticky="we",padx=5)
        tk.Button(gen,text="…",command=self.browse_outdir).grid(row=2,column=2)

        self.gen_btn = tk.Button(gen, text="Generate Flashcards", command=self.generate_flashcards, state="disabled")
        self.gen_btn.grid(row=3,column=0,columnspan=3,pady=10)

        self.review_btn = tk.Button(gen, text="Review Flashcards", command=self.review_current, state="disabled")
        self.review_btn.grid(row=4,column=0,columnspan=3,pady=(0,10))
        gen.columnconfigure(1, weight=1)

        self.edit_btn = tk.Button(gen, text="Edit Flashcards",
        command=self.edit_current, state="disabled")
        self.edit_btn.grid(row=5, column=0, columnspan=3, pady=(0,10))

    def choose_and_load_file(self):
        path = filedialog.askopenfilename(title="Bitte Excel-Datei auswählen", filetypes=[("Excel Dateien","*.xlsx *.xls")])
        if not path: return
        try:
            df = load_data(path)
        except Exception as e:
            messagebox.showerror("Fehler", str(e)); return
        if "Lernziel" not in df.columns:
            messagebox.showwarning("Spalte fehlt","Keine Spalte 'Lernziel'."); return
        self.lernziele = df["Lernziel"].astype(str).tolist()
        self.listbox.delete(0,tk.END)
        for i,txt in enumerate(self.lernziele,1):
            preview = txt[:80].rstrip()+("…" if len(txt)>80 else "")
            self.listbox.insert(tk.END,f"{i}. {preview}")
            if self.find_json_for_goal(txt):
                self.listbox.itemconfig(i-1, bg="#316417")
        self.title(f"Lernziele Viewer — {os.path.basename(path)}")

        self.copy_btn.config(state="disabled")
        self.gen_btn.config(state="disabled")
        self.review_btn.config(state="disabled")
        self.mkdir_btn.config(state="disabled")
        self.adddoc_btn.config(state="disabled")
        self.slice_btn.config(state="disabled")

        self.details_text.config(state="normal"); self.details_text.delete("1.0","end"); self.details_text.config(state="disabled")

    def on_select(self,event):
        sel=self.listbox.curselection();
        if not sel: return
        idx=sel[0]; text=self.lernziele[idx]; self.current_text=text
        self.details_text.config(state="normal"); self.details_text.delete("1.0","end"); self.details_text.insert("end",text); self.details_text.config(state="disabled")

        self.copy_btn.config(state="normal")
        self.gen_btn.config(state="normal")
        self.mkdir_btn.config(state="normal")
        self.adddoc_btn.config(state="normal")
        self.slice_btn.config(state="normal")

        if self.find_json_for_goal(text):
            self.review_btn.config(state="normal")
            self.edit_btn.config(state="normal")
        else:
            self.review_btn.config(state="disabled")
            self.edit_btn.config(state="disabled")

        self.update_filelist_for_goal(self.current_text)
        self.update_pdf_list_for_goal(self.current_text)

    def find_json_for_goal(self,goal):
        outdir=self.outdir_entry.get().strip() or self.default_outdir
        if not os.path.isdir(outdir): return None
        for f in os.listdir(outdir):
            if f.endswith('.json'):
                try:
                    d=json.load(open(os.path.join(outdir,f),encoding='utf-8'))
                    if d.get('learning_goal')==goal:
                        return os.path.join(outdir,f)
                except: pass
        return None

    def copy_to_clipboard(self):
        self.clipboard_clear(); self.clipboard_append(self.current_text)
        messagebox.showinfo("Kopiert","Lernziel kopiert.")

    def create_goal_directory(self):
        if not self.current_text:
            messagebox.showerror("Fehler", "Kein Lernziel ausgewählt.")
            return
        dirname = sanitize_dirname(self.current_text)
        outdir = self.outdir_entry.get().strip() or self.default_outdir
        full_path = os.path.join(outdir, dirname)
        try:
            os.makedirs(full_path, exist_ok=False)
            messagebox.showinfo("Erfolg", f"Verzeichnis erstellt: {full_path}")
            self.update_filelist_for_goal(self.current_text)
            self.update_pdf_list_for_goal(self.current_text)
        except FileExistsError:
            messagebox.showwarning("Schon vorhanden", f"Verzeichnis existiert bereits:\n{full_path}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Verzeichnis konnte nicht erstellt werden:\n{e}")
        

    def add_document_to_goal(self):
        if not self.current_text:
            messagebox.showerror("Fehler", "Kein Lernziel ausgewählt.")
            return
        dirname = sanitize_dirname(self.current_text)
        outdir = self.outdir_entry.get().strip() or self.default_outdir
        target_dir = os.path.join(outdir, dirname)
        if not os.path.isdir(target_dir):
            messagebox.showerror("Fehler", "Das Verzeichnis existiert nicht. Bitte zuerst anlegen.")
            return
        files = filedialog.askopenfilenames(title="Dokument(e) auswählen")
        if not files:
            return
        errors = []
        for f in files:
            try:
                # Keep filename only
                dest = os.path.join(target_dir, os.path.basename(f))
                shutil.copy2(f, dest)
            except Exception as e:
                errors.append(f"{f}: {e}")
        if not errors:
            messagebox.showinfo("Erfolg", "Dokument(e) hinzugefügt.")
            self.update_filelist_for_goal(self.current_text)
            self.update_pdf_list_for_goal(self.current_text)
        else:
            messagebox.showerror("Fehler beim Kopieren", "\n".join(errors))
        

    def update_filelist_for_goal(self, goal):
        self.filelist_box.delete(0, tk.END)
        dirname = sanitize_dirname(goal)
        outdir = self.outdir_entry.get().strip() or self.default_outdir
        dirpath = os.path.join(outdir, dirname)
        if not os.path.isdir(dirpath):
            self.filelist_box.insert(tk.END, "(Kein Verzeichnis angelegt)")
            return
        files = sorted([f for f in os.listdir(dirpath) if os.path.isfile(os.path.join(dirpath, f))])
        if not files:
            self.filelist_box.insert(tk.END, "(Keine Dateien vorhanden)")
        else:
            for f in files:
                self.filelist_box.insert(tk.END, f)

    def open_selected_file(self, event=None):
        sel = self.filelist_box.curselection()
        if not sel:
            return
        filename = self.filelist_box.get(sel[0])
        if filename.startswith('('):  # Not a real file
            return
        dirname = sanitize_dirname(self.current_text)
        outdir = self.outdir_entry.get().strip() or self.default_outdir
        filepath = os.path.join(outdir, dirname, filename)
        try:
            if sys.platform.startswith('darwin'):
                subprocess.call(('open', filepath))
            elif sys.platform.startswith('win'):
                os.startfile(filepath)
            else:
                subprocess.call(('xdg-open', filepath))
            self.update_filelist_for_goal(self.current_text)
            self.update_pdf_list_for_goal(self.current_text)
        except Exception as e:
            messagebox.showerror("Fehler", f"Datei konnte nicht geöffnet werden:\n{e}")

    def remove_selected_file(self, event=None):
        sel = self.filelist_box.curselection()
        if not sel:
            return
        filename = self.filelist_box.get(sel[0])
        if filename.startswith('('):  # Not a real file
            return
        dirname = sanitize_dirname(self.current_text)
        outdir = self.outdir_entry.get().strip() or self.default_outdir
        filepath = os.path.join(outdir, dirname, filename)
        answer = messagebox.askyesno("Datei löschen", f"Möchten Sie die Datei wirklich löschen?\n\n{filename}")
        if answer:
            try:
                os.remove(filepath)
                self.update_filelist_for_goal(self.current_text)
                self.update_pdf_list_for_goal(self.current_text)
            except Exception as e:
                messagebox.showerror("Fehler", f"Datei konnte nicht gelöscht werden:\n{e}")

    def browse_slice_pdf(self):
        p = filedialog.askopenfilename(title="PDF auswählen", filetypes=[("PDF", "*.pdf")])
        if p:
            self.slice_pdf_entry.delete(0, 'end')
            self.slice_pdf_entry.insert(0, p)

    def slice_and_save_pdf(self):
        if not self.current_text:
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

        dirname = sanitize_dirname(self.current_text)
        outdir = self.outdir_entry.get().strip() or self.default_outdir
        target_dir = os.path.join(outdir, dirname)
        if not os.path.isdir(target_dir):
            messagebox.showerror("Fehler", "Verzeichnis für Lernziel nicht vorhanden. Bitte zuerst anlegen.")
            return
        # Output filename: original name + range
        base = os.path.splitext(os.path.basename(in_pdf))[0]
        out_pdf = os.path.join(target_dir, f"{base}_S{start}-{end}.pdf")
        try:
            slice_pdf(in_pdf, out_pdf, start, end)  # <---- Corrected call
            messagebox.showinfo("Erfolg", f"PDF gespeichert: {out_pdf}")
            self.update_filelist_for_goal(self.current_text)
            self.update_pdf_list_for_goal(self.current_text)
        except Exception as e:
            messagebox.showerror("Fehler", f"PDF konnte nicht gespeichert werden:\n{e}")

    def show_file_context_menu(self, event):
        sel = self.filelist_box.nearest(event.y)
        if sel < 0:
            return
        self.filelist_box.selection_clear(0, tk.END)
        self.filelist_box.selection_set(sel)
        filename = self.filelist_box.get(sel)
        if filename.startswith('('):
            return
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Datei löschen", command=self.remove_selected_file)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def browse_pdf(self):
        p=filedialog.askopenfilename(title="PDF auswählen",filetypes=[("PDF","*.pdf")])
        if p: self.pdf_entry.delete(0,'end'); self.pdf_entry.insert(0,p)

    def browse_outdir(self):
        d=filedialog.askdirectory(title="Outdir auswählen")
        if d: self.outdir_entry.delete(0,'end'); self.outdir_entry.insert(0,d)
        for i,txt in enumerate(self.lernziele):
            color = "#316417" if self.find_json_for_goal(txt) else "white"
            self.listbox.itemconfig(i,bg=color)

    def update_pdf_list_for_goal(self, goal):
        # Clear old checkboxes
        for widget in self.pdf_checkbox_inner_frame.winfo_children():
            widget.destroy()
        self.pdf_checkboxes.clear()

        dirname = sanitize_dirname(goal)
        outdir = self.outdir_entry.get().strip() or self.default_outdir
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


    def generate_flashcards(self):
        # Collect checked PDFs
        selected_pdfs = [fname for fname, var in self.pdf_checkboxes.items() if var.get()]
        if not selected_pdfs:
            messagebox.showerror("Fehler", "Bitte wählen Sie mindestens eine PDF-Datei aus.")
            return

        dirname = sanitize_dirname(self.current_text)
        outdir = self.outdir_entry.get().strip() or self.default_outdir
        goal = self.current_text.strip()
        errors = []
        created = []

        for pdf_filename in selected_pdfs:
            pdf_path = os.path.join(outdir, dirname, pdf_filename)
            try:
                # Get total number of pages for this PDF
                with open(pdf_path, "rb") as f:
                    reader = PdfReader(f)
                    num_pages = len(reader.pages)
                page_range = (1, num_pages)
                base = os.path.splitext(pdf_filename)[0]
                fn = f"{goal.replace(' ','_')[:30]}_{base}_S{page_range[0]}-{page_range[1]}.json"
                out_json = os.path.join(outdir, fn)
                if os.path.exists(out_json):
                    errors.append(f"{pdf_filename}: Batch existiert.")
                    continue

                # Call your LLM flashcard generator
                generate_flashcards_from_pdf(
                    pdf_path=pdf_path,
                    page_range=page_range,
                    learning_goal=goal,
                    output_json_path=out_json
                )
                created.append(pdf_filename)
            except Exception as e:
                errors.append(f"{pdf_filename}: {e}")

        # Feedback for user
        if created:
            messagebox.showinfo(
                "Erfolg",
                f"Flashcards für {len(created)} PDF(s) erstellt:\n" + "\n".join(created)
            )
            idx = self.lernziele.index(goal)
            self.listbox.itemconfig(idx, bg="#316417")
            self.review_btn.config(state="normal")
        if errors:
            messagebox.showerror(
                "Fehler",
                "Bei einigen PDFs gab es Probleme:\n" + "\n".join(errors)
            )

        # (Optional) Uncheck all after run
        for var in self.pdf_checkboxes.values():
            var.set(False)


    def review_current(self):
        path = self.find_json_for_goal(self.current_text)
        if not path:
            messagebox.showerror("Fehler","Keine Flashcards vorhanden.")
            return
        self.start_review(path)

    def edit_current(self):
        path = self.find_json_for_goal(self.current_text)
        if not path:
            messagebox.showerror("Fehler", "Keine Flashcards vorhanden.")
            return
        # lazy import keeps startup fast
        from flashcard_editor import FlashcardEditor
        FlashcardEditor(self, path)

    def start_review(self, json_path):
        data = load_flashcard_data(json_path)
        self.flashcards = data['flashcards']
        self.session_results = []
        self.review_index = 0
        self.review_data = data
        self.review_stage = 'question'

        self.rev_win = tk.Toplevel(self)
        self.rev_win.title('Flashcard Review')
        self.rev_win.geometry('1000x700')
        self.rev_win.configure(bg='#181A1B')
        self.rev_win.resizable(True, True)
        self.rev_win.focus_set()

        card_frame = tk.Frame(self.rev_win, bg='#232526', highlightbackground='#373B3E', highlightthickness=2)
        card_frame.pack(expand=True, fill='both', padx=40, pady=40)

        self.q_text = tk.Text(
            card_frame,
            height=5,
            font=('SF Pro Display', 26, 'bold'),
            bg='#232526',
            fg='white',
            wrap='word',
            bd=0,
            highlightthickness=0,
            padx=20,
            pady=18
        )
        self.q_text.pack(fill='x', pady=(30, 8))
        self.q_text.configure(state='disabled', cursor='xterm')

        self.a_text = tk.Text(
            card_frame,
            height=6,
            font=('SF Pro Display', 22),
            bg='#232526',
            fg='#7AB8F5',
            wrap='word',
            bd=0,
            highlightthickness=0,
            padx=20,
            pady=12
        )
        self.a_text.pack(fill='x', pady=(8, 20))
        self.a_text.configure(state='disabled', cursor='xterm')

        # --- Custom Action Button (dark, never bright) ---
        self.action_btn = create_dark_button(
            card_frame,
            "Antwort anzeigen",
            self.on_action,
            width=400, height=60,
            font=('SF Pro Display', 20, 'bold'),
            bg="#333637",
            fg='white',
            hover_bg="#42464a"
        )
        self.action_btn.pack(pady=(8, 16))

        # --- Custom Rating Buttons ---
        self.rating_frame = tk.Frame(card_frame, bg='#232526')
        self.rating_buttons = []
        rating_specs = [
            (1, 'Einfach', '#334D37', '1'),
            (2, 'Mittel', '#544c25', '2'),
            (3, 'Schwer', '#4C2326', '3'),
        ]
        for val, txt, color, key in rating_specs:
            btn = create_dark_button(
                self.rating_frame,
                txt,
                lambda v=val: self.rate_and_next(v),
                width=220, height=60,
                font=('SF Pro Display', 18, 'bold'),
                bg=color,
                fg='white',
                hover_bg='#34373a',
                key=key
            )
            btn.pack(side='left', expand=True, padx=24, pady=10)
            self.rating_buttons.append(btn)

        def keypress(event):
            if self.review_stage == 'answer':
                if event.char in '123':
                    self.rate_and_next(int(event.char))
            elif self.review_stage == 'question':
                if event.keysym in ('Return', 'space'):
                    self.on_action()
        self.rev_win.bind('<Key>', keypress)

        self.card_frame = card_frame
        self.show_question()

    def show_question(self):
        card = self.flashcards[self.review_index]
        self.q_text.configure(state='normal')
        self.q_text.delete('1.0', 'end')
        self.q_text.insert('1.0', card['question'])
        self.q_text.configure(state='disabled')

        self.a_text.configure(state='normal')
        self.a_text.delete('1.0', 'end')
        self.a_text.configure(state='disabled')

        self.action_btn.pack(pady=(8, 16))
        self.rating_frame.pack_forget()
        self.review_stage = 'question'
        self.action_btn.focus_set()

    def on_action(self, event=None):
        if self.review_stage == 'question':
            card = self.flashcards[self.review_index]
            self.a_text.configure(state='normal')
            self.a_text.delete('1.0', 'end')
            self.a_text.insert('1.0', card['answer'])
            self.a_text.configure(state='disabled')

            self.action_btn.pack_forget()
            self.rating_frame.pack(side='bottom', fill='x', pady=20)
            self.review_stage = 'answer'
            self.rating_buttons[0].focus_set()

    def rate_and_next(self, rating):
        card = self.flashcards[self.review_index]
        self.session_results.append({
            'question': card['question'],
            'answer': card['answer'],
            'rating': rating
        })
        self.review_index += 1
        if self.review_index < len(self.flashcards):
            self.show_question()
        else:
            key = f"{self.review_data.get('learning_goal','')} (Seiten {self.review_data.get('page_range','')})"
            try:
                update_progress(key, self.session_results, timestamp=datetime.now().isoformat(timespec='seconds'))
            except Exception:
                pass
            messagebox.showinfo('Fertig', 'Review beendet.')
            self.rev_win.destroy()

if __name__=='__main__':
    app=LernzieleViewer(); app.mainloop()
