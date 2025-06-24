"""
gui.py
"""

"""

scale page find

"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox
import re

from utils.excel_parser import load_data
from card_core import (
    load_flashcard_data,
    update_progress,
)
from card_manager_frame import card_manager_frame
from frame_dir_manager import frame_dir_manager

# from frame_pdf_slice import PDFSliceFrame
# from utils.slice_pdf import slice_pdf

from card_review_frame import card_review_frame
from card_editor_frame import card_editor_frame

from learnit import LearnIt

from openai import OpenAI


def sanitize_dirname(name):
    # Keep letters, numbers, dash/underscore. Replace spaces with underscores.
    sanitized = re.sub(r'[^A-Za-z0-9_\-]', '_', name.replace(' ', '_'))
    return sanitized[:100]


class Gui(tk.Tk):
    def __init__(self, learnit: LearnIt):
        super().__init__()
        self.learnit = learnit
        self.learnit_instances = {learnit.store_name: learnit}
        self.title("Lernziele Viewer")
        self.geometry("800x700")
        self.default_outdir = "archive"
        self.current_outdir = self.default_outdir
        self.lernziele = []
        self.current_text = ""

        # --- Create main container (no scrolling) ---
        self.main_frame = tk.Frame(self)
        self.main_frame.pack(fill="both", expand=True)

        # --- Top: Excel Loader & Vector-Store chooser ---
        self._create_excel_loader(self.main_frame)
        self._create_vector_store_selector(self.main_frame)

        # --- List of Learning Goals ---
        self._create_learning_goal_list(self.main_frame)

        # --- Details text ---
        self.details_text = tk.Text(
            self.main_frame, height=4, wrap="word", state="disabled"
        )
        self.details_text.pack(fill="x", padx=10, pady=(0, 10))

        # ——— PageFinder button ———
        self.pagefinder_btn = tk.Button(
            self.main_frame, text="PageFinder", command=self.open_pagefinder, width=15
        )
        self.pagefinder_btn.pack(pady=(0, 10))

        # --- Flashcard Manager Frame ---
        self.flashcard_manager_frame = card_manager_frame(
            self.main_frame,
            get_current_goal=lambda: self.current_text,
            get_outdir=lambda: self.current_outdir,
            sanitize_dirname=sanitize_dirname,
            load_flashcard_data=load_flashcard_data,
            open_review_window=self.start_review,
            open_editor_window=self.edit_current,
            refresh_all_goal_colors=self.refresh_all_goal_colors,
        )
        self.flashcard_manager_frame.pack(fill="x", padx=10, pady=(0, 10))

        # --- Goal File Manager (above Flashcard Manager) ---
        self.goal_file_manager = frame_dir_manager(
            self.main_frame,
            goal_getter=lambda: self.current_text,
            outdir_getter=lambda: self.current_outdir,
            sanitize_dirname=sanitize_dirname,
            refresh_all_goal_colors=self.refresh_all_goal_colors,
            selected_files_getter=lambda: self.flashcard_manager_frame.get_selected_files(),
        )
        self.goal_file_manager.pack(fill="x", padx=10, pady=(0, 10))

        # --- PDF Slice Frame ---
        # self.pdf_slice_frame = PDFSliceFrame(
        #     self.main_frame,
        #     get_current_goal=lambda: self.current_text,
        #     get_outdir=lambda: self.current_outdir,
        #     sanitize_dirname=sanitize_dirname,
        #     update_callback=lambda: [
        #         self.goal_file_manager.update_filelist(),
        #         self.flashcard_manager_frame.update_pdf_list(),
        #     ],
        #     slice_pdf_func=slice_pdf,
        #     refresh_all_goal_colors=self.refresh_all_goal_colors,
        # )
        # self.pdf_slice_frame.pack(fill="x", padx=10, pady=(0, 10))

    def _create_excel_loader(self, parent):
        top_frame = tk.Frame(parent, pady=10)
        top_frame.pack(fill="x")
        tk.Button(
            top_frame, text="Excel öffnen…", command=self.choose_and_load_file, width=15
        ).pack(side="left", padx=10)

    # ────────────────────────────────────────────────────────────────
    # Vector-store selector
    # ────────────────────────────────────────────────────────────────
    def _create_vector_store_selector(self, parent):
        vs_frame = tk.Frame(parent, pady=0)
        vs_frame.pack(fill="x", padx=10, pady=(0, 10))

        tk.Label(vs_frame, text="Vector Store:").pack(side="left")

        self.available_stores = self._discover_vector_stores()
        if not self.available_stores:
            self.available_stores.append(next(iter(self.learnit_instances)))

        self.selected_store = tk.StringVar(value=self.available_stores[0])
        self.vs_menu = tk.OptionMenu(vs_frame, self.selected_store, *self.available_stores)
        self.vs_menu.config(width=25)
        self.vs_menu.pack(side="left", padx=10)

    def _discover_vector_stores(self) -> list[str]:
        """Return every <store>.id file found under .vector_store_ids/."""
        id_dir = LearnIt.VECTOR_ID_DIR
        id_dir.mkdir(exist_ok=True)
        return [p.stem for p in id_dir.glob("*.id")]

    def _create_learning_goal_list(self, parent):
        list_frame = tk.Frame(parent)
        list_frame.pack(fill="both", expand=False, padx=10, pady=(0, 10))

        v_scroll = tk.Scrollbar(list_frame, orient="vertical")
        v_scroll.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            list_frame, selectmode="browse", yscrollcommand=v_scroll.set, height=10
        )
        self.listbox.pack(fill="x")
        v_scroll.config(command=self.listbox.yview)

        self.listbox.bind("<<ListboxSelect>>", self.on_select)

    def open_pagefinder(self):
        query = self.current_text
        store_name = self.selected_store.get().strip()
        if not store_name:
            messagebox.showwarning("PageFinder", "Bitte zuerst einen Vector Store auswählen.")
            return

        li = self.learnit_instances.get(store_name)
        if li is None:
            li = LearnIt(store_name)
            self.learnit_instances[store_name] = li
        dest_dir = os.path.join(self.current_outdir, sanitize_dirname(self.current_text))

        copied = li.search_and_copy_pages(query=query, dest_dir=dest_dir)

        if not copied:
            messagebox.showinfo("PageFinder", "Keine passende Seite im PDF-Archiv gefunden.")
        else:
            messagebox.showinfo(
                "PageFinder",
                f"{len(copied)} Seite(n) nach\n{copied[0].parent}\nkopiert.",
            )

        self.goal_file_manager.update_filelist()
        self.flashcard_manager_frame.update_pdf_list()

    def get_goal_color(self, goal):
        goal_dir = os.path.join(self.current_outdir, sanitize_dirname(goal))
        json_path = os.path.join(goal_dir, "flashcards.json")
        if os.path.isfile(json_path):
            return "#316417"  # green
        elif os.path.isdir(goal_dir):
            files = [
                f
                for f in os.listdir(goal_dir)
                if os.path.isfile(os.path.join(goal_dir, f)) and not f.startswith(".")
            ]
            if files:
                return "#81720f"  # yellow
        return "#202324"

    def refresh_all_goal_colors(self):
        for i, txt in enumerate(self.lernziele):
            color = self.get_goal_color(txt)
            self.listbox.itemconfig(i, bg=color)

    def choose_and_load_file(self):
        # path = filedialog.askopenfilename(title="Bitte Excel-Datei auswählen",
        #                                   filetypes=[("Excel Dateien","*.xlsx *.xls")])
        path = "/Users/robing/Desktop/projects/Learnit/lernziele/M10-LZ.xlsx"
        if not path:
            return
        try:
            df = load_data(path)
        except Exception as e:
            messagebox.showerror("Fehler", str(e))
            return
        if "Lernziel" not in df.columns:
            messagebox.showwarning("Spalte fehlt", "Keine Spalte 'Lernziel'.")
            return
        self.lernziele = df["Lernziel"].astype(str).tolist()
        self.listbox.delete(0, tk.END)
        for i, txt in enumerate(self.lernziele, 1):
            preview = txt[:80].rstrip() + ("…" if len(txt) > 80 else "")
            self.listbox.insert(tk.END, f"{i}. {preview}")
            self.listbox.itemconfig(i - 1, bg=self.get_goal_color(txt))

        self.title(f"Lernziele Viewer — {os.path.basename(path)}")
        self.flashcard_manager_frame.set_action_buttons_state("disabled")
        # self.pdf_slice_frame.set_slice_button_state("disabled")
        self.goal_file_manager.copy_btn.config(state="disabled")
        self.goal_file_manager.adddoc_btn.config(state="disabled")

        self.details_text.config(state="normal")
        self.details_text.delete("1.0", "end")
        self.details_text.config(state="disabled")

    def on_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            self.flashcard_manager_frame.set_action_buttons_state("disabled")
            # self.pdf_slice_frame.set_slice_button_state("disabled")
            self.goal_file_manager.update_filelist()
            return
        idx = sel[0]
        self.current_text = self.lernziele[idx]

        self.details_text.config(state="normal")
        self.details_text.delete("1.0", "end")
        self.details_text.insert("end", self.current_text)
        self.details_text.config(state="disabled")

        self.flashcard_manager_frame.set_action_buttons_state("normal")
        # self.pdf_slice_frame.set_slice_button_state("normal")
        self.goal_file_manager.update_filelist()
        self.flashcard_manager_frame.update_pdf_list()

    def find_json_for_goal(self, goal):
        goal_dir = os.path.join(self.current_outdir, sanitize_dirname(goal))
        p = os.path.join(goal_dir, "flashcards.json")
        return p if os.path.isfile(p) else None

    def browse_outdir(self):
        d = filedialog.askdirectory(title="Outdir auswählen")
        if d:
            self.current_outdir = d
            for i, txt in enumerate(self.lernziele):
                self.listbox.itemconfig(i, bg=self.get_goal_color(txt))

    def start_review(self, json_path):
        data = load_flashcard_data(json_path)
        card_review_frame(
            master=self, data=data, update_progress_callback=update_progress
        )

    def edit_current(self, json_path):
        card_editor_frame(self, json_path, refresh_all_goal_colors=self.refresh_all_goal_colors)


if __name__ == "__main__":
    PDF = "/Users/robing/Desktop/projects/Learnit/PDFs/M10_komplett.pdf"

    li = LearnIt.from_pdf(PDF)  # store “M10_komplett_VS”

    app = Gui(learnit=li)
    app.mainloop()
