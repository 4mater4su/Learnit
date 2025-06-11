import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from typing import List, Dict, Any

# PDF support
from PyPDF2 import PdfReader

try:
    # Re‑use the global OpenAI() instance from flashcard_manager if available
    from flashcard_manager import OpenAI as _FMOpenAI  # type: ignore
    CLIENT = _FMOpenAI()
except Exception:  # pragma: no cover – standalone fallback
    from openai import OpenAI
    CLIENT = OpenAI()  # assumes OPENAI_API_KEY is set in env


class FlashcardEditor(tk.Toplevel):
    """A Tk window that lets the user view, edit and AI‑refine a flashcard batch."""

    def __init__(self, master: tk.Misc | None, json_path: str) -> None:
        super().__init__(master)
        
        # show batch filename and learning goal in the title
        learning_goal = self._load_batch(json_path).get("learning_goal", "")
        self.title(f"Flashcard Editor — {os.path.basename(json_path)}")

        # --- Top bar with goal and delete button ---
        topbar = tk.Frame(self, bg="#181A1B")
        topbar.pack(fill="x", pady=(8,0))

        goal_text = tk.Text(
            topbar,
            height=3,
            wrap="word",
            bg="#181A1B",
            fg="white",
            font=("SF Pro Display", 18, "bold"),
            bd=0,
            highlightthickness=0,
            cursor="xterm",         # show text‐edit cursor
            exportselection=True,    # allow clipboard copy
        )
        goal_text.insert("1.0", f"Lernziel: {learning_goal}")
        goal_text.configure(state="disabled")  # disable editing, still selectable
        goal_text.pack(side="left", fill="x", expand=True, padx=10, pady=(10, 5))

        del_btn = tk.Button(
            topbar,
            text="🗑 Batch löschen",
            bg="#3C2323", fg="white",
            font=("SF Pro Display", 14, "bold"),
            command=self._delete_batch
        )
        del_btn.pack(side="right", padx=10, pady=10)

        self.geometry("1100x700")
        self.configure(bg="#181A1B")
        self.resizable(True, True)

        self.json_path = json_path
        self.batch: Dict[str, Any] = self._load_batch(json_path)
        self.flashcards: List[Dict[str, str]] = self.batch["flashcards"]

        # Track PDF inclusion
        self.pdf_path: str | None = None
        self.include_pdf_var = tk.BooleanVar(value=False)

        # ─────────────────────────── layout ───────────────────────────
        left = tk.Frame(self, bg="#202324", padx=10, pady=10)
        left.pack(side="left", fill="y")

        right = tk.Frame(self, bg="#181A1B", padx=10, pady=10)
        right.pack(side="right", expand=True, fill="both")

        # list of Qs (left pane)
        self.listbox = tk.Listbox(left, width=45, height=30, activestyle="none",
                                  fg="white", bg="#202324", bd=0,
                                  highlightthickness=1, highlightbackground="#444")
        self.listbox.pack(expand=True, fill="both")
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        self._populate_listbox()

        # buttons underneath list
        btn_frame = tk.Frame(left, bg="#202324")
        btn_frame.pack(fill="x", pady=(8, 0))
        tk.Button(btn_frame, text="＋ Neu", width=7, command=self._add_card).pack(side="left", padx=4)
        tk.Button(btn_frame, text="🗑 Löschen", width=9, command=self._delete_card).pack(side="left", padx=4)
        tk.Button(btn_frame, text="🔄 AI‑Überarbeiten", width=16, command=self._ai_refine).pack(side="left", padx=4)
        # PDF selection & checkbox
        tk.Button(btn_frame, text="📄 PDF auswählen", command=self._select_pdf).pack(side="left", padx=4)
        tk.Checkbutton(btn_frame, text="PDF mitsenden", variable=self.include_pdf_var,
                       bg="#202324", fg="white", selectcolor="#2C2F31").pack(side="left", padx=4)

        # editors (right pane)
        q_lbl = tk.Label(right, text="Frage", fg="white", bg="#181A1B")
        q_lbl.pack(anchor="w")
        self.q_text = tk.Text(right, height=4, wrap="word", bg="#2C2F31", fg="white", insertbackground="white")
        self.q_text.pack(fill="x", pady=(0, 8))

        a_lbl = tk.Label(right, text="Antwort", fg="white", bg="#181A1B")
        a_lbl.pack(anchor="w")
        self.a_text = tk.Text(right, height=6, wrap="word", bg="#2C2F31", fg="#7AB8F5", insertbackground="white")
        self.a_text.pack(fill="both", expand=True)

        save_btn = tk.Button(right, text="💾 Speichern", font=("SF Pro Display", 14, "bold"),
                             command=self._save_changes)
        save_btn.pack(pady=10)

        self.selected_index: int | None = None
        if self.flashcards:
            self.listbox.selection_set(0)
            self._load_into_editor(0)

    # ─────────────────────────── helpers ───────────────────────────

    def _load_batch(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "flashcards" not in data or not isinstance(data["flashcards"], list):
            raise ValueError("Ungültige Batchdatei: 'flashcards' fehlt oder ist kein Array")
        return data

    def _populate_listbox(self) -> None:
        self.listbox.delete(0, tk.END)
        for i, card in enumerate(self.flashcards, 1):
            preview = card["question"].strip()[:60].replace("\n", " ")
            self.listbox.insert(tk.END, f"{i:02d}. {preview}")

    def _on_select(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self._load_into_editor(idx)

    def _load_into_editor(self, idx: int) -> None:
        self.selected_index = idx
        card = self.flashcards[idx]
        self.q_text.delete("1.0", "end")
        self.q_text.insert("1.0", card["question"])
        self.a_text.delete("1.0", "end")
        self.a_text.insert("1.0", card["answer"])

    # ─────────────────────────── CRUD ───────────────────────────

    def _add_card(self):
        new_card = {"question": "Neue Frage", "answer": "Neue Antwort"}
        self.flashcards.append(new_card)
        self._populate_listbox()
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(tk.END)
        self._load_into_editor(len(self.flashcards) - 1)

    def _delete_card(self):
        if self.selected_index is None:
            return
        if messagebox.askyesno("Löschen", "Diese Karte wirklich löschen?"):
            del self.flashcards[self.selected_index]
            self._populate_listbox()
            if self.flashcards:
                new_idx = max(0, self.selected_index - 1)
                self.listbox.selection_set(new_idx)
                self._load_into_editor(new_idx)
            else:
                self.selected_index = None
                self.q_text.delete("1.0", "end")
                self.a_text.delete("1.0", "end")

    def _delete_batch(self):
        if messagebox.askyesno("Batch löschen", "Wirklich den gesamten Batch und die zugehörige JSON-Datei löschen? Dieser Vorgang kann nicht rückgängig gemacht werden."):
            try:
                os.remove(self.json_path)
            except Exception as e:
                messagebox.showerror("Fehler", f"JSON-Datei konnte nicht gelöscht werden:\n{e}")
                return
            messagebox.showinfo("Gelöscht", "Batch und JSON-Datei wurden gelöscht.")
            self.destroy()


    def _save_changes(self):
        # write back currently visible edits if any selection
        if self.selected_index is not None:
            self.flashcards[self.selected_index]["question"] = self.q_text.get("1.0", "end").strip()
            self.flashcards[self.selected_index]["answer"] = self.a_text.get("1.0", "end").strip()
        # save file
        self.batch["flashcards"] = self.flashcards
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self.batch, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Gespeichert", "Änderungen gespeichert.")
        self._populate_listbox()

    # ─────────────────────────── PDF chooser & AI refine ───────────────────────────

    def _select_pdf(self):
        path = filedialog.askopenfilename(
            title="PDF auswählen",
            filetypes=[("PDF Dateien", "*.pdf")]
        )
        if path:
            self.pdf_path = path
            messagebox.showinfo("PDF ausgewählt", f"{os.path.basename(path)} wurde geladen.")

    def _ai_refine(self):
        prompt = simpledialog.askstring(
            "AI-Überarbeiten", 
            "Beschreibe, was geändert werden soll.\n(Beispiel: ‚Formuliere die Fragen kürzer‘)"
        )
        if not prompt:
            return

        system_msg = (
            "Du bist ein Tutor, der Lernkarten überarbeitet. "
            "Der Nutzer liefert im JSON-Format eine Liste von Frage-/Antwort-Paaren. "
            "Gib nur JSON zurück, KEINEN FLIESSTEXT. Struktur:\n\n"
            "{\n  \"flashcards\": [\n    {\"question\": \"…\", \"answer\": \"…\"}, …\n  ]\n}"
        )

        # Optionally include PDF text
        pdf_text = ""
        if self.include_pdf_var.get() and self.pdf_path:
            try:
                reader = PdfReader(self.pdf_path)
                pages = []
                for page in reader.pages:
                    text = page.extract_text() or ""
                    pages.append(text)
                pdf_text = "\n\n### PDF-Inhalt:\n" + "\n---\n".join(pages)
            except Exception as e:
                messagebox.showwarning("PDF-Fehler", f"PDF konnte nicht gelesen werden: {e}")

        user_content = prompt
        if pdf_text:
            user_content += pdf_text
        user_content += "\n\n" + json.dumps({"flashcards": self.flashcards}, ensure_ascii=False, indent=2)

        user_msg = {"role": "user", "content": user_content}

        try:
            response = CLIENT.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_msg},
                    user_msg
                ],
                response_format={"type": "json_object"},
            )
            new_data = json.loads(response.choices[0].message.content)
            new_cards = new_data.get("flashcards")
            if not (isinstance(new_cards, list) and new_cards):
                raise ValueError("Antwort enthielt keine gültigen flashcards")
        except Exception as e:
            messagebox.showerror("Fehler", f"AI-Aufruf fehlgeschlagen:\n{e}")
            return

        if messagebox.askyesno("AI-Ergebnis", f"{len(new_cards)} Karten vom Modell erhalten. Änderungen übernehmen?"):
            self.flashcards = new_cards
            self._save_changes()
            messagebox.showinfo("OK", "AI-Änderungen übernommen.")
        else:
            messagebox.showinfo("Abgebrochen", "Änderungen verworfen.")


# ─────────────────────────── helper launcher (for quick module test) ──────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python flashcard_editor.py path/to/batch.json")
        sys.exit(1)
    root = tk.Tk(); root.withdraw()
    FlashcardEditor(root, sys.argv[1])
    root.mainloop()
