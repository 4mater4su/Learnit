import tkinter as tk
from tkinter import messagebox
from datetime import datetime

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

    def on_key(event):
        if key:
            if event.char == key:
                command()
        else:
            if event.keysym in ('Return', 'space'):
                command()
    canvas.bind("<Key>", on_key)
    return canvas

class FlashcardReviewWindow(tk.Toplevel):
    def __init__(self, master, data, update_progress_callback):
        super().__init__(master)
        self.title('Flashcard Review')
        self.geometry('1000x700')
        self.configure(bg='#181A1B')
        self.resizable(True, True)
        self.focus_set()

        self.flashcards = data['flashcards']
        self.review_data = data
        self.update_progress_callback = update_progress_callback
        self.session_results = []
        self.review_index = 0
        self.review_stage = 'question'

        card_frame = tk.Frame(self, bg='#232526', highlightbackground='#373B3E', highlightthickness=2)
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
        self.bind('<Key>', keypress)

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
                self.update_progress_callback(key, self.session_results, timestamp=datetime.now().isoformat(timespec='seconds'))
            except Exception:
                pass
            messagebox.showinfo('Fertig', 'Review beendet.')
            self.destroy()
