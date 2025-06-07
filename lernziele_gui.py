# -*- coding: utf-8 -*-

"""
Module: lernziele_gui.py

Ein Tkinter-GUI, das deine Excel-Daten lädt und alle Lernziele
in einer scrollbaren Listbox anzeigt. Lernziele mit existierenden
Flashcards werden farblich hervorgehoben. Nach Auswahl kannst du
kopieren, Flashcards generieren oder über einen Button reviewen.
"""

import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

from excel_parser import load_data
from flashcard_manager import (
    generate_flashcards_from_pdf,
    load_flashcard_data,
    update_progress
)


class LernzieleViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lernziele Viewer")
        self.geometry("800x800")

        self.default_outdir = "flashcards"
        self.lernziele = []
        self.current_text = ""

        # Oben: Excel laden
        top_frame = tk.Frame(self, pady=10)
        top_frame.pack(fill="x")
        tk.Button(top_frame, text="Excel öffnen…", command=self.choose_and_load_file, width=15).pack(side="left", padx=10)

        # Listbox
        list_frame = tk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0,10))
        v_scroll = tk.Scrollbar(list_frame, orient="vertical")
        v_scroll.pack(side="right", fill="y")
        self.listbox = tk.Listbox(list_frame, selectmode="browse", yscrollcommand=v_scroll.set)
        self.listbox.pack(fill="both", expand=True)
        v_scroll.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # Detail
        details = tk.LabelFrame(self, text="Ausgewähltes Lernziel")
        details.pack(fill="x", padx=10, pady=(0,10))
        self.details_text = tk.Text(details, height=4, wrap="word", state="disabled")
        self.details_text.pack(fill="both", expand=True)
        self.copy_btn = tk.Button(details, text="Kopieren", command=self.copy_to_clipboard, state="disabled")
        self.copy_btn.pack(pady=5)

        # Flashcard Generator
        gen = tk.LabelFrame(self, text="Flashcards generieren")
        gen.pack(fill="x", padx=10, pady=(0,10))
        tk.Label(gen, text="PDF:").grid(row=0,column=0,sticky="e")
        self.pdf_entry = tk.Entry(gen)
        self.pdf_entry.grid(row=0,column=1,sticky="we",padx=5)
        tk.Button(gen,text="…",command=self.browse_pdf).grid(row=0,column=2)
        tk.Label(gen, text="Seiten:").grid(row=1,column=0,sticky="e")
        self.start_spin = tk.Spinbox(gen, from_=1, to=9999, width=5)
        self.start_spin.grid(row=1,column=1,sticky="w")
        self.end_spin = tk.Spinbox(gen, from_=1, to=9999, width=5)
        self.end_spin.grid(row=1,column=2,sticky="w")
        tk.Label(gen, text="Outdir:").grid(row=2,column=0,sticky="e")
        self.outdir_entry = tk.Entry(gen)
        self.outdir_entry.insert(0,self.default_outdir)
        self.outdir_entry.grid(row=2,column=1,sticky="we",padx=5)
        tk.Button(gen,text="…",command=self.browse_outdir).grid(row=2,column=2)
        self.gen_btn = tk.Button(gen, text="Generate Flashcards", command=self.generate_flashcards, state="disabled")
        self.gen_btn.grid(row=3,column=0,columnspan=3,pady=10)
        # Review button in same frame
        self.review_btn = tk.Button(gen, text="Review Flashcards", command=self.review_current, state="disabled")
        self.review_btn.grid(row=4,column=0,columnspan=3,pady=(0,10))
        gen.columnconfigure(1, weight=1)

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
        self.copy_btn.config(state="disabled"); self.gen_btn.config(state="disabled"); self.review_btn.config(state="disabled")
        self.details_text.config(state="normal"); self.details_text.delete("1.0","end"); self.details_text.config(state="disabled")

    def on_select(self,event):
        sel=self.listbox.curselection();
        if not sel: return
        idx=sel[0]; text=self.lernziele[idx]; self.current_text=text
        self.details_text.config(state="normal"); self.details_text.delete("1.0","end"); self.details_text.insert("end",text); self.details_text.config(state="disabled")
        self.copy_btn.config(state="normal"); self.gen_btn.config(state="normal")
        # enable review if exists
        if self.find_json_for_goal(text):
            self.review_btn.config(state="normal")
        else:
            self.review_btn.config(state="disabled")

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

    def browse_pdf(self):
        p=filedialog.askopenfilename(title="PDF auswählen",filetypes=[("PDF","*.pdf")])
        if p: self.pdf_entry.delete(0,'end'); self.pdf_entry.insert(0,p)

    def browse_outdir(self):
        d=filedialog.askdirectory(title="Outdir auswählen")
        if d: self.outdir_entry.delete(0,'end'); self.outdir_entry.insert(0,d)
        # recolor list
        for i,txt in enumerate(self.lernziele):
            color = "#316417" if self.find_json_for_goal(txt) else "white"
            self.listbox.itemconfig(i,bg=color)

    def generate_flashcards(self):
        pdf=self.pdf_entry.get().strip()
        try: start=int(self.start_spin.get()); end=int(self.end_spin.get())
        except: messagebox.showerror("Fehler","Seiten ungültig."); return
        goal=self.current_text.strip(); outdir=self.outdir_entry.get().strip() or self.default_outdir
        os.makedirs(outdir,exist_ok=True)
        fn=goal.replace(' ','_')[:30]+f"_{start}_{end}.json"; path=os.path.join(outdir,fn)
        if os.path.exists(path): messagebox.showerror("Fehler","Batch existiert."); return
        try:
            generate_flashcards_from_pdf(pdf_path=pdf,page_range=(start,end),learning_goal=goal,output_json_path=path)
            messagebox.showinfo("Erfolg","Flashcards gespeichert.")
            idx=self.lernziele.index(goal); self.listbox.itemconfig(idx,bg="#316417")
            self.review_btn.config(state="normal")
        except Exception as e:
            messagebox.showerror("Fehler",str(e))

    def review_current(self):
        path = self.find_json_for_goal(self.current_text)
        if not path:
            messagebox.showerror("Fehler","Keine Flashcards vorhanden.")
            return
        self.start_review(path)

    def start_review(self,json_path):
        data=load_flashcard_data(json_path); self.flashcards=data['flashcards']
        self.session_results=[]; self.review_index=0; self.review_data=data; self.review_stage='question'
        self.rev_win=tk.Toplevel(self); self.rev_win.title('Review'); self.rev_win.geometry('1000x600')
        self.rev_win.bind('<Return>',self.on_action); self.rev_win.bind('<space>',self.on_action)
        self.rev_win.bind('1',lambda e: self.rate_and_next(1)); self.rev_win.bind('2',lambda e: self.rate_and_next(2)); self.rev_win.bind('3',lambda e: self.rate_and_next(3))
        tk.Label(self.rev_win,text='Frage:',font=('Arial',14,'bold')).pack(anchor='w',padx=10,pady=(10,0))
        self.q_label=tk.Label(self.rev_win,text='',wraplength=950,justify='left',font=('Arial',12)); self.q_label.pack(fill='x',padx=10)
        self.a_label=tk.Label(self.rev_win,text='',wraplength=950,justify='left',font=('Arial',12),fg='blue'); self.a_label.pack(fill='x',padx=10,pady=(5,0))
        self.action_btn=tk.Button(self.rev_win,text='Antwort anzeigen',font=('Arial',12),command=self.on_action); self.action_btn.pack(pady=20)
        self.rating_frame=tk.Frame(self.rev_win)
        self.rating_var=tk.IntVar(value=2)
        for val,txt in [(1,'Einfach'),(2,'Mittel'),(3,'Schwer')]: tk.Radiobutton(self.rating_frame,text=txt,variable=self.rating_var,value=val,font=('Arial',12),state='disabled').pack(side='left',padx=20)
        self.show_question()

    def show_question(self):
        card=self.flashcards[self.review_index]
        self.q_label.config(text=card['question']); self.a_label.config(text='')
        self.action_btn.config(text='Antwort anzeigen'); self.review_stage='question'
        self.rating_frame.pack_forget()

    def on_action(self,event=None):
        if self.review_stage=='question':
            card=self.flashcards[self.review_index]; self.a_label.config(text=card['answer'])
            self.rating_frame.pack(pady=10);
            for rb in self.rating_frame.winfo_children(): rb.config(state='normal')
            self.action_btn.config(text='Weiter (1-3 oder Enter)'); self.review_stage='answer'
        else:
            self.rate_and_next(self.rating_var.get())

    def rate_and_next(self,rating):
        card=self.flashcards[self.review_index]
        self.session_results.append({'question':card['question'],'answer':card['answer'],'rating':rating})
        self.review_index+=1
        if self.review_index < len(self.flashcards): self.show_question()
        else:
            key=f"{self.review_data.get('learning_goal','')} (Seiten {self.review_data.get('page_range','')})"
            try: update_progress(key,self.session_results,timestamp=datetime.now().isoformat(timespec='seconds'))
            except: pass
            messagebox.showinfo('Fertig','Review beendet.'); self.rev_win.destroy()

if __name__=='__main__':
    app=LernzieleViewer(); app.mainloop()