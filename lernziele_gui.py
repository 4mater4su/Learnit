# -*- coding: utf-8 -*-

import os
import tkinter as tk
from tkinter import filedialog, messagebox
import re

from excel_parser import load_data
from flashcard_core import (
    generate_flashcards_from_pdf,
    load_flashcard_data,
    update_progress,
    slice_pdf
)
from flashcard_manager_frame import FlashcardManagerFrame
from goal_file_manager import GoalFileManagerFrame
from pdf_slice_frame import PDFSliceFrame
from flashcard_review_window import FlashcardReviewWindow
from flashcard_editor import FlashcardEditor

def sanitize_dirname(name):
    # Keep letters, numbers, dash/underscore. Replace spaces with underscores.
    sanitized = re.sub(r'[^A-Za-z0-9_\-]', '_', name.replace(' ', '_'))
    return sanitized[:100]

class LernzieleViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lernziele Viewer")
        self.geometry("800x800")
        self.default_outdir = "archive"
        self.current_outdir = self.default_outdir
        self.lernziele = []
        self.current_text = ""
        
        # --- Create scrollable content area ---
        self.scrollable_frame = self._create_scrollable_area()
        
        # --- Top: Excel Loader ---
        self._create_excel_loader(self.scrollable_frame)

        # --- List of Learning Goals ---
        self._create_learning_goal_list(self.scrollable_frame)

        # --- Details text ---
        self.details_text = tk.Text(self.scrollable_frame, height=4, wrap="word", state="disabled")
        self.details_text.pack(fill="x", padx=10, pady=(0, 10))

        # --- Goal File Manager ---
        self.goal_file_manager = GoalFileManagerFrame(
            self.scrollable_frame,
            goal_getter=lambda: self.current_text,
            outdir_getter=lambda: self.current_outdir,
            sanitize_dirname=sanitize_dirname
        )
        self.goal_file_manager.pack(fill="x", padx=10, pady=(0, 10))

        # --- PDF Slice Frame ---
        self.pdf_slice_frame = PDFSliceFrame(
            self.scrollable_frame,
            get_current_goal=lambda: self.current_text,
            get_outdir=lambda: self.current_outdir,
            sanitize_dirname=sanitize_dirname,
            slice_pdf_func=slice_pdf,
            update_callback=lambda: [self.goal_file_manager.update_filelist(), self.flashcard_manager_frame.update_pdf_list()]
        )
        self.pdf_slice_frame.pack(fill="x", padx=10, pady=(0, 10))

        # --- Flashcard Manager Frame ---
        self.flashcard_manager_frame = FlashcardManagerFrame(
            self.scrollable_frame,
            get_current_goal=lambda: self.current_text,
            get_outdir=lambda: self.current_outdir,
            sanitize_dirname=sanitize_dirname,
            generate_flashcards_from_pdf=generate_flashcards_from_pdf,
            load_flashcard_data=load_flashcard_data,
            open_review_window=self.start_review,
            open_editor_window=self.edit_current  # or an editor function
        )
        self.flashcard_manager_frame.pack(fill="x", padx=10, pady=(0, 10))

    def _create_scrollable_area(self):
        # Create a scrollable frame inside a canvas with a vertical scrollbar
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, borderwidth=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollable_frame = tk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        scrollable_frame_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def resize_scrollable_frame(event):
            canvas.itemconfig(scrollable_frame_window, width=event.width)
        canvas.bind("<Configure>", resize_scrollable_frame)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_main_canvas_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_main_canvas_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        return scrollable_frame

    def _create_excel_loader(self, parent):
        top_frame = tk.Frame(parent, pady=10)
        top_frame.pack(fill="x")
        tk.Button(top_frame, text="Excel öffnen…", command=self.choose_and_load_file, width=15).pack(side="left", padx=10)

    def _create_learning_goal_list(self, parent):
        list_frame = tk.Frame(parent)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        v_scroll = tk.Scrollbar(list_frame, orient="vertical")
        v_scroll.pack(side="right", fill="y")
        self.listbox = tk.Listbox(list_frame, selectmode="browse", yscrollcommand=v_scroll.set, height=5)
        self.listbox.pack(fill="x", pady=(0, 10))
        v_scroll.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

    def get_goal_color(self, goal):
        outdir = self.current_outdir
        dirname = sanitize_dirname(goal)
        goal_dir = os.path.join(outdir, dirname)
        json_path = os.path.join(goal_dir, "flashcards.json")
        if os.path.isfile(json_path):
            return "#316417"  # green
        elif os.path.isdir(goal_dir):
            # If directory contains any files (excluding .DS_Store etc.)
            files = [f for f in os.listdir(goal_dir) if os.path.isfile(os.path.join(goal_dir, f)) and not f.startswith('.')]
            if files:
                return "#81720f"  # yellow
        return "#202324"

    def refresh_goal_color(self, goal):
        # Find the index of the goal in self.lernziele
        try:
            idx = self.lernziele.index(goal)
        except ValueError:
            return
        color = self.get_goal_color(goal)
        self.listbox.itemconfig(idx, bg=color)

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
        for i, txt in enumerate(self.lernziele, 1):
            preview = txt[:80].rstrip() + ("…" if len(txt) > 80 else "")
            self.listbox.insert(tk.END, f"{i}. {preview}")
            color = self.get_goal_color(txt)
            self.listbox.itemconfig(i-1, bg=color)

        self.title(f"Lernziele Viewer — {os.path.basename(path)}")

        self.flashcard_manager_frame.set_action_buttons_state("disabled")
        self.pdf_slice_frame.set_slice_button_state("disabled")
        self.goal_file_manager.copy_btn.config(state="disabled")
        self.goal_file_manager.mkdir_btn.config(state="disabled")
        self.goal_file_manager.adddoc_btn.config(state="disabled")

        self.details_text.config(state="normal"); self.details_text.delete("1.0","end"); self.details_text.config(state="disabled")

    def on_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            self.flashcard_manager_frame.set_action_buttons_state("disabled")
            self.pdf_slice_frame.set_slice_button_state("disabled")
            self.goal_file_manager.copy_btn.config(state="disabled")
            self.goal_file_manager.mkdir_btn.config(state="disabled")
            self.goal_file_manager.adddoc_btn.config(state="disabled")
            return
        idx = sel[0]
        text = self.lernziele[idx]
        self.current_text = text

        self.details_text.config(state="normal")
        self.details_text.delete("1.0", "end")
        self.details_text.insert("end", text)
        self.details_text.config(state="disabled")

        self.flashcard_manager_frame.set_action_buttons_state("normal")
        self.pdf_slice_frame.set_slice_button_state("normal")
        self.goal_file_manager.copy_btn.config(state="normal")
        self.goal_file_manager.mkdir_btn.config(state="normal")
        self.goal_file_manager.adddoc_btn.config(state="normal")

        self.goal_file_manager.update_filelist()
        self.flashcard_manager_frame.update_pdf_list()

    def find_json_for_goal(self, goal):
        outdir = lambda: self.current_outdir
        dirname = sanitize_dirname(goal)
        json_path = os.path.join(outdir, dirname, "flashcards.json")
        if os.path.isfile(json_path):
            return json_path
        return None      

    def browse_outdir(self):
        d = filedialog.askdirectory(title="Outdir auswählen")
        if d:
            self.current_outdir = d
            # update any widgets or colors that depend on outdir
            for i, txt in enumerate(self.lernziele):
                color = self.get_goal_color(txt)
                self.listbox.itemconfig(i, bg=color)

    def start_review(self, json_path):
        data = load_flashcard_data(json_path)
        FlashcardReviewWindow(
            master=self,
            data=data,
            update_progress_callback=update_progress
        )

    def edit_current(self, json_path):
        FlashcardEditor(self, json_path)

if __name__=='__main__':
    app=LernzieleViewer(); app.mainloop()
