# file_selection_frame.py
import os
import tkinter as tk

class DirectoryFileSelectionFrame(tk.LabelFrame):
    """
    Zeigt alle Dateien im Ziel­verzeichnis als Checkbox-Liste
    (standardmäßig *.pdf und *.txt).  Ruft man `get_selected_files()`
    auf, bekommt man vollständige Pfade der angehakten Dateien zurück.
    """
    def __init__(self,
                 parent: tk.Misc,
                 dir_getter,
                 filetypes: tuple[str, ...] = ('.pdf', '.txt'),
                 **kwargs):
        super().__init__(parent, text="Dateien auswählen", **kwargs)
        self.dir_getter = dir_getter
        self.filetypes = filetypes
        self.vars: dict[str, tk.BooleanVar] = {}

        # Scrollbare Canvas – optional; bei wenigen Dateien reicht ein Frame
        self.canvas = tk.Canvas(self, height=140, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical",
                                      command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas)
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(
                            scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.refresh()          # initial füllen

    # ------------------------------------------------------------
    def refresh(self) -> None:
        """Liste neu aufbauen (nach Verzeichnis- oder Dateizugriffen)."""
        for w in self.inner.winfo_children():
            w.destroy()
        self.vars.clear()

        directory = self.dir_getter()
        if not directory or not os.path.isdir(directory):
            tk.Label(self.inner, text="(kein Verzeichnis)").pack(anchor="w")
            return

        files = [f for f in sorted(os.listdir(directory))
                 if f.lower().endswith(self.filetypes)]
        if not files:
            tk.Label(self.inner, text="(keine Dateien)").pack(anchor="w")
            return

        for fname in files:
            var = tk.BooleanVar()
            tk.Checkbutton(self.inner, text=fname, variable=var,
                           anchor="w").pack(fill="x", anchor="w")
            self.vars[fname] = var

    # ------------------------------------------------------------
    def get_selected_files(self) -> list[str]:
        """Vollständige Pfade der angehakten Dateien zurückgeben."""
        directory = self.dir_getter()
        return [os.path.join(directory, f)
                for f, v in self.vars.items() if v.get()]
