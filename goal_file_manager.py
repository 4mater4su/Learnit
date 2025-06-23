import tkinter as tk
from tkinter import messagebox, filedialog
import os
import shutil
import sys
from openai import OpenAI

from file_selection_frame import DirectoryFileSelectionFrame

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

        # ⬇︎ NEU: Frame für die Dateiauswahl
        self.file_selector = DirectoryFileSelectionFrame(
            self,
            dir_getter=lambda: os.path.join(
                outdir_getter(),
                sanitize_dirname(goal_getter() or "")),
        )
        self.file_selector.pack(fill="x", padx=4, pady=(4, 6))

        self.llm_btn = tk.Button(btn_row, text="LLM-Antwort", command=self.generate_llm_response, state="disabled")
        self.llm_btn.pack(side="left", padx=4)

        self.refresh_all_goal_colors = refresh_all_goal_colors

    # def generate_llm_response(self):
    #     """Erstellt Studien-Notizen auf Basis der angehakten Dateien."""
    #     goal = self.goal_getter()
    #     if not goal:
    #         messagebox.showerror("Fehler", "Kein Lernziel ausgewählt.")
    #         return

    #     dirname   = self.sanitize_dirname(goal)
    #     outdir    = self.outdir_getter()
    #     targetdir = os.path.join(outdir, dirname)
    #     os.makedirs(targetdir, exist_ok=True)

    #     # ------------------------------------------------------------------ #
    #     # 1) Angekreuzte Dateien einsammeln
    #     # ------------------------------------------------------------------ #
    #     selected_files = self.file_selector.get_selected_files()

    #     retriever_output = ""
    #     for path in selected_files:
    #         try:
    #             with open(path, "r", encoding="utf-8", errors="ignore") as fh:
    #                 retriever_output += (
    #                     f"\n\n### Inhalt von {os.path.basename(path)} ###\n"
    #                     + fh.read()
    #                 )
    #         except Exception as e:
    #             messagebox.showwarning(
    #                 "Dateifehler",
    #                 f"{os.path.basename(path)} konnte nicht gelesen werden:\n{e}",
    #             )

    #     # Wenn keine Datei gewählt wurde, trotzdem ein Platzhalter – sonst Abort
    #     if not retriever_output.strip():
    #         retriever_output = "(kein Text gefunden)"

    #     # ------------------------------------------------------------------ #
    #     # 2) Prompt nach Vorgabe aufbauen
    #     # ------------------------------------------------------------------ #
    #     messages = [
    #         {
    #             "role": "system",
    #             "content": (
    #                 "Du bist ein deutschsprachiger KI-Tutor für Medizinstudierende.\n"
    #                 "Deine Antworten dürfen **ausschließlich Inhalte verwenden**, "
    #                 "die im Abschnitt {retriever_output} enthalten sind.\n"
    #                 "Erfinde **nichts hinzu**, interpretiere **nur das, "
    #                 "was explizit belegt ist**."
    #             ),
    #         },
    #         {
    #             "role": "user",
    #             "content": retriever_output,
    #         },
    #         {
    #             "role": "assistant",
    #             "content": (
    #                 "Erstelle präzise, medizinisch fundierte **Studien-Notizen** "
    #                 "(Lernzusammenfassung) gemäß den folgenden Regeln:\n\n"
    #                 "1. Verwende ausschließlich Inhalte aus {retriever_output}. "
    #                 "Keine externen Quellen oder Ergänzungen.\n"
    #                 "2. Beginne mit **3–5 Lernzielen** "
    #                 "(verbalisiert mit Bloom-Taxonomie-Verben).\n"
    #                 "3. Strukturiere den Haupttext in **Markdown**:\n"
    #                 "   - `##` für Hauptabschnitte\n"
    #                 "   - Bullet-Points oder kurze Absätze, auch längere Inhalte erlaubt (>2000 Zeichen)\n"
    #                 "   - **Fettdruck** für zentrale Begriffe, `Inline-Code` für Parameter, Ionen oder Moleküle\n"
    #                 "4. Behandle alle relevanten Inhalte des Ausgangstextes vollständig – "
    #                 "auch scheinbar „technische“ oder „molekulare“ Details.\n"
    #                 "5. Gliedere nach **physiologisch relevanten Themenfeldern**: "
    #                 "Ätiologie, Pathophysiologie, Zellbiologie, molekulare Mechanismen etc., sofern vorhanden.\n"
    #                 "6. Füge am Ende **Take-Home-Messages** hinzu – jeweils 1–2 Sätze.\n\n"
    #                 "Antwort ausschließlich im **formatierten Markdown-Block**."
    #             ),
    #         },
    #     ]

    #     # ------------------------------------------------------------------ #
    #     # 3) LLM-Aufruf
    #     # ------------------------------------------------------------------ #
    #     try:
    #         client = OpenAI()
    #         response = client.responses.create(
    #             model="gpt-4o-mini",
    #             messages=messages,
    #             temperature=0.4,
    #         )
    #         markdown_notes = response.choices[0].message.content.strip()

    #         # Ergebnis speichern
    #         with open(os.path.join(targetdir, "LLM.md"), "w", encoding="utf-8") as f:
    #             f.write(markdown_notes)

    #         self.update_filelist()
    #         self.refresh_all_goal_colors()
    #     except Exception as e:
    #         messagebox.showerror("Fehler", f"LLM-Anfrage fehlgeschlagen:\n{e}")

    
    def generate_llm_response(self):
        """Erstellt Studien-Notizen, indem alle selektierten Dateien als File-Input an OpenAI gesendet werden."""
        goal = self.goal_getter()
        if not goal:
            messagebox.showerror("Fehler", "Kein Lernziel ausgewählt.")
            return

        # ----------------------------------------------------------- #
        # Pfade vorbereiten
        dirname   = self.sanitize_dirname(goal)
        outdir    = self.outdir_getter()
        targetdir = os.path.join(outdir, dirname)
        os.makedirs(targetdir, exist_ok=True)

        # ----------------------------------------------------------- #
        # Dateien sammeln & hochladen
        selected_files = self.file_selector.get_selected_files()
        if not selected_files:
            messagebox.showwarning("Hinweis", "Keine Datei ausgewählt – es wird nur das Lernziel gesendet.")
        
        client = OpenAI()
        file_blocks = []                          # wird gleich in die 'content'-Liste geschrieben

        for path in selected_files:
            try:
                with open(path, "rb") as fh:
                    uploaded = client.files.create(file=fh, purpose="user_data")
                file_blocks.append({"type": "input_file", "file_id": uploaded.id})
            except Exception as e:
                messagebox.showwarning(
                    "Upload-Fehler",
                    f"{os.path.basename(path)} konnte nicht hochgeladen werden:\n{e}"
                )

        # ----------------------------------------------------------- #
        # Prompt-Text gemäß Vorgabe
        prompt_text = f"""SYSTEM  
    Du bist ein deutschsprachiger KI-Tutor für Medizinstudierende.  
    Deine Antworten dürfen **ausschließlich Inhalte verwenden**, die im Abschnitt der Datei enthalten sind.  
    Erfinde **nichts hinzu**, interpretiere **nur das, was explizit belegt ist**.

    ASSISTANT TASK  
    Erstelle präzise, medizinisch fundierte **Studien-Notizen** (Lernzusammenfassung) gemäß den folgenden Regeln:

    1. Verwende ausschließlich Inhalte aus der Datei. Keine externen Quellen oder Ergänzungen.  
    2. Beginne mit **3–5 Lernzielen** (verbalisiert mit Bloom-Taxonomie-Verben).  
    3. Strukturiere den Haupttext in **Markdown**:  
    - `##` für Hauptabschnitte  
    - Bullet-Points oder kurze Absätze, auch längere Inhalte erlaubt (>2000 Zeichen)  
    - **Fettdruck** für zentrale Begriffe, `Inline-Code` für Parameter, Ionen oder Moleküle  
    4. Behandle alle relevanten Inhalte des Ausgangstextes vollständig –  
    auch scheinbar „technische“ oder „molekulare“ Details.  
    5. Gliedere nach **physiologisch relevanten Themenfeldern**:  
    Ätiologie, Pathophysiologie, Zellbiologie, molekulare Mechanismen etc., sofern vorhanden.  
    6. Füge am Ende **Take-Home-Messages** hinzu – jeweils 1–2 Sätze.  

    Antwort ausschließlich im **formatierten Markdown-Block**.

    Lernziel:
    {goal}
    """

        # ----------------------------------------------------------- #
        # Responses-Endpoint aufrufen  (Datei-Input wird unterstützt)
        try:
            response = client.responses.create(
                model="gpt-4.1",
                input=[
                    {
                        "role": "user",
                        # Kombiniere File-Blöcke + den eigentlichen Prompt-Text
                        "content": file_blocks + [{"type": "input_text", "text": prompt_text}]
                    }
                ]
            )
            markdown_notes = response.output_text.strip()

            # ------------------------------------------------------- #
            # Ergebnis speichern
            out_file = os.path.join(targetdir, "LLM.txt")
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(markdown_notes)

            self.update_filelist()
            self.refresh_all_goal_colors()
            messagebox.showinfo("Fertig", f"Studien-Notizen gespeichert unter:\n{out_file}")

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

        self.file_selector.refresh()   # muss aufgerufen werden, sobald sich das Zielverzeichnis ändert oder neue Dateien hinzukommen.

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
