import tkinter as tk
from tkinter import messagebox, filedialog
import os
import shutil
import sys

class GoalFileManagerFrame(tk.LabelFrame):
    def __init__(self, parent, goal_getter, outdir_getter, sanitize_dirname, refresh_all_goal_colors, **kwargs):
        super().__init__(parent, text="Ausgewähltes Lernziel", **kwargs)
        self.goal_getter = goal_getter            # Function to get current goal text
        self.outdir_getter = outdir_getter        # Function to get output directory
        self.sanitize_dirname = sanitize_dirname  # Function to sanitize goal text

        self.filelist_label = tk.Label(self, text="Dateien im Verzeichnis:", anchor="w")
        self.filelist_label.pack(fill="x", padx=4, pady=(2,0))

        self.filelist_box = tk.Listbox(self, height=4, activestyle='dotbox')
        self.filelist_box.pack(fill="both", expand=False, padx=4, pady=(0,4))
        self.filelist_box.bind('<Double-Button-1>', self.open_selected_file)
        self.filelist_box.bind('<Button-2>', self.show_file_context_menu)

        btn_row = tk.Frame(self)
        btn_row.pack(anchor="center", pady=5)

        self.copy_btn = tk.Button(btn_row, text="Kopieren", command=self.copy_to_clipboard, state="disabled")
        self.copy_btn.pack(side="left", padx=4)

        self.adddoc_btn = tk.Button(btn_row, text="Dokument hinzufügen", command=self.add_document_to_goal, state="disabled")
        self.adddoc_btn.pack(side="left", padx=4)

        self.llm_btn = tk.Button(btn_row, text="LLM-Antwort", command=self.generate_llm_response, state="disabled")
        self.llm_btn.pack(side="left", padx=4)

        self.refresh_all_goal_colors = refresh_all_goal_colors

    
    def generate_llm_response(self):
        """Generate a medical-school-level explanation of the learning goal via the new OpenAI SDK (v1)."""
        goal = self.goal_getter()
        if not goal:
            messagebox.showerror("Fehler", "Kein Lernziel ausgewählt.")
            return

        dirname   = self.sanitize_dirname(goal)
        outdir    = self.outdir_getter()
        targetdir = os.path.join(outdir, dirname)
        os.makedirs(targetdir, exist_ok=True)

        try:
            # --- NEW OpenAI v1 style ---
            from openai import OpenAI
            client = OpenAI()

            prompt = (
                "You are an expert medical educator.\n\n"
                f"Please provide a detailed medical-school-level explanation of the "
                f"following learning goal:\n\n{goal}"
            )

            resp = client.responses.create(
                model="gpt-4o-mini",      # or "gpt-4.1" if that’s your preferred model
                input=prompt
            )
            text = resp.output_text
            # --------------------------------

            # save to TXT
            filename = f"LLM.txt"
            path = os.path.join(targetdir, filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

            self.update_filelist()
            self.refresh_all_goal_colors()
        except Exception as e:
            messagebox.showerror("Fehler", f"LLM-Anfrage fehlgeschlagen:\n{e}")


    # The following methods use goal_getter() and outdir_getter()
    def update_filelist(self):
        goal = self.goal_getter()
        self.filelist_box.delete(0, tk.END)
        if not goal:
            self.filelist_box.insert(tk.END, "(Kein Lernziel ausgewählt)")
            self.copy_btn.config(state="disabled")
            self.adddoc_btn.config(state="disabled")
            self.llm_btn.config(state="disabled")
            return
        
        dirname = self.sanitize_dirname(goal)
        outdir = self.outdir_getter()
        dirpath = os.path.join(outdir, dirname)
        if not os.path.isdir(dirpath):
            self.filelist_box.insert(tk.END, "(Kein Verzeichnis angelegt)")
            # still allow LLM and adddoc to auto-create
            self.copy_btn.config(state="normal")
            self.adddoc_btn.config(state="normal")
            self.llm_btn.config(state="normal")
            return
        
        files = sorted([f for f in os.listdir(dirpath) if os.path.isfile(os.path.join(dirpath, f))])
        if not files:
            self.filelist_box.insert(tk.END, "(Keine Dateien vorhanden)")
        else:
            for f in files:
                self.filelist_box.insert(tk.END, f)
        
        # enable buttons when we have a goal (dir exists or will be auto-created)
        self.copy_btn.config(state="normal")
        self.adddoc_btn.config(state="normal")
        self.llm_btn.config(state="normal")

    def copy_to_clipboard(self):
        goal = self.goal_getter()
        if goal:
            self.clipboard_clear()
            self.clipboard_append(goal)

    # def create_goal_directory(self):
    #     goal = self.goal_getter()
    #     if not goal:
    #         messagebox.showerror("Fehler", "Kein Lernziel ausgewählt.")
    #         return
    #     dirname = self.sanitize_dirname(goal)
    #     outdir = self.outdir_getter()
    #     full_path = os.path.join(outdir, dirname)
    #     try:
    #         os.makedirs(full_path, exist_ok=False)
    #         messagebox.showinfo("Erfolg", f"Verzeichnis erstellt: {full_path}")
    #         self.update_filelist()
    #         self.refresh_all_goal_colors()
    #     except FileExistsError:
    #         messagebox.showwarning("Schon vorhanden", f"Verzeichnis existiert bereits:\n{full_path}")
    #     except Exception as e:
    #         messagebox.showerror("Fehler", f"Verzeichnis konnte nicht erstellt werden:\n{e}")

    def add_document_to_goal(self):
        goal = self.goal_getter()
        if not goal:
            messagebox.showerror("Fehler", "Kein Lernziel ausgewählt.")
            return
        dirname = self.sanitize_dirname(goal)
        outdir = self.outdir_getter()
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
                dest = os.path.join(target_dir, os.path.basename(f))
                shutil.copy2(f, dest)
            except Exception as e:
                errors.append(f"{f}: {e}")
        if not errors:
            self.update_filelist()
            self.refresh_all_goal_colors()
        else:
            messagebox.showerror("Fehler beim Kopieren", "\n".join(errors))

    def open_selected_file(self, event=None):
        sel = self.filelist_box.curselection()
        if not sel:
            return
        filename = self.filelist_box.get(sel[0])
        if filename.startswith('('):
            return
        goal = self.goal_getter()
        dirname = self.sanitize_dirname(goal)
        outdir = self.outdir_getter()
        filepath = os.path.join(outdir, dirname, filename)
        try:
            if sys.platform.startswith('darwin'):
                os.system(f"open '{filepath}'")
            elif sys.platform.startswith('win'):
                os.startfile(filepath)
            else:
                os.system(f"xdg-open '{filepath}'")
        except Exception as e:
            messagebox.showerror("Fehler", f"Datei konnte nicht geöffnet werden:\n{e}")

    def remove_selected_file(self, event=None):
        sel = self.filelist_box.curselection()
        if not sel:
            return
        filename = self.filelist_box.get(sel[0])
        if filename.startswith('('):
            return
        goal = self.goal_getter()
        dirname = self.sanitize_dirname(goal)
        outdir = self.outdir_getter()
        filepath = os.path.join(outdir, dirname, filename)
        answer = messagebox.askyesno("Datei löschen", f"Möchten Sie die Datei wirklich löschen?\n\n{filename}")
        if answer:
            try:
                os.remove(filepath)
                self.update_filelist()
                self.refresh_all_goal_colors()
            except Exception as e:
                messagebox.showerror("Fehler", f"Datei konnte nicht gelöscht werden:\n{e}")

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
