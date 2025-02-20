import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import re
import openai


class ExtendedTopicsWindow:
    """
    Dieses Fenster enthält die Logik für das 'Erweiterte Themen & Upload'-Feature,
    ausgelagert aus dem Hauptprogramm.
    """
    def __init__(self, parent, openai_api_key):
        """
        :param parent: Referenz auf das Tk-Hauptfenster
        :param openai_api_key: Dein ChatGPT/OpenAI-API-Key (falls du hier Prompting machst)
        """
        self.parent = parent
        self.openai_api_key = openai_api_key

        # OpenAI initialisieren: 
        # Da wir hier selbst direct chat requests machen, setzen wir den Key lokal:
        openai.api_key = self.openai_api_key

        self.window = tk.Toplevel(self.parent)
        self.window.title("Erweiterte Themen & Upload")
        self.window.geometry("800x600")

        # Frame: Themenvorschläge
        frame_topic = tk.LabelFrame(self.window, text="Themenvorschläge", padx=10, pady=10)
        frame_topic.pack(fill=tk.X, padx=10, pady=5)

        label_info = (
            "Gib einen SNP (z.B. rs429358) ODER einen Oberbegriff (z.B. Diabetes) ein,\n"
            "um nach relevanten Single Nucleotide Polymorphisms zu suchen:"
        )
        tk.Label(frame_topic, text=label_info).pack(anchor="w")

        self.snp_entry = tk.Entry(frame_topic, width=30)
        self.snp_entry.pack(anchor="w", padx=5, pady=2)

        btn_suggest = tk.Button(frame_topic, text="Vorschläge generieren", command=self._show_topic_suggestions)
        btn_suggest.pack(anchor="w", padx=5, pady=2)

        self.topic_text = scrolledtext.ScrolledText(frame_topic, height=8, wrap="word")
        self.topic_text.pack(fill=tk.X, padx=5, pady=2)

        # Frame: Alternative SNP Hinweise
        frame_alt = tk.LabelFrame(self.window, text="Alternative SNP Hinweise", padx=10, pady=10)
        frame_alt.pack(fill=tk.X, padx=10, pady=5)

        btn_alt = tk.Button(frame_alt, text="Alternative SNP Hinweise generieren", command=self._show_alternative_hints)
        btn_alt.pack(anchor="w", padx=5, pady=2)

        self.alt_text = scrolledtext.ScrolledText(frame_alt, height=3, wrap="word")
        self.alt_text.pack(fill=tk.X, padx=5, pady=2)

        # Frame: Zusammenfassung
        frame_summary = tk.LabelFrame(self.window, text="Zusammenfassung", padx=10, pady=10)
        frame_summary.pack(fill=tk.X, padx=10, pady=5)
        summary_text = (
            "Ziel: Die wichtigsten Polymorphismen oder Genotypen zu einer Krankheit identifizieren und "
            "mit funktionalen/regulatorischen Effekten verknüpfen, um daraus mögliche Mechanismen und "
            "Interventionen abzuleiten."
        )
        tk.Label(frame_summary, text=summary_text, justify="left").pack(fill=tk.X, padx=5)

        # Frame: Ziele
        frame_goals = tk.LabelFrame(self.window, text="Ziele", padx=10, pady=10)
        frame_goals.pack(fill=tk.X, padx=10, pady=5)
        goals = (
            "• Relevante Polymorphismen auflisten\n"
            "• Verknüpfung SNP -> Genotyp -> Auswirkung\n"
            "• Mechanismen hinter bestimmten SNPs und passenden Umweltfaktoren aufzeigen\n"
            "  (Beispiel: APOE rs429358 -> Zusammenhang mit Alzheimer und Fettstoffwechsel)"
        )
        tk.Label(frame_goals, text=goals, justify="left").pack(fill=tk.X, padx=5)

        # Frame: Upload & Fragen
        frame_upload = tk.LabelFrame(self.window, text="Studien hochladen & Fragen", padx=10, pady=10)
        frame_upload.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        btn_upload = tk.Button(frame_upload, text="Studie hochladen", command=self._upload_study)
        btn_upload.pack(anchor="w", padx=5, pady=2)

        self.upload_label = tk.Label(frame_upload, text="Keine Studie hochgeladen.")
        self.upload_label.pack(anchor="w", padx=5, pady=2)

        tk.Label(frame_upload, text="Stelle deine Frage zur hochgeladenen Studie:").pack(anchor="w", padx=5, pady=2)
        self.question_text = scrolledtext.ScrolledText(frame_upload, height=4, wrap="word")
        self.question_text.pack(fill=tk.X, padx=5, pady=2)

        btn_question = tk.Button(frame_upload, text="Frage senden", command=self._send_question)
        btn_question.pack(anchor="w", padx=5, pady=2)

    # --------------------------------------------------
    # Themenvorschläge
    # --------------------------------------------------
    def _show_topic_suggestions(self):
        snp_id = self.snp_entry.get().strip()
        self.topic_text.delete("1.0", tk.END)

        if not snp_id:
            messagebox.showwarning("Hinweis", "Bitte einen SNP (z.B. rs429358) ODER einen Oberbegriff eingeben.")
            return

        # Prompt aufbauen
        if re.match(r"^rs\d+", snp_id.lower()):
            prompt = (
                f"Bitte liefere mir kurze Forschungsthemen oder Studienideen zu dem SNP {snp_id}. "
                f"Welche möglichen Auswirkungen oder Mechanismen sind bekannt?"
            )
        else:
            prompt = (
                f"Ich habe das Thema '{snp_id}'. Welche Single Nucleotide Polymorphisms (SNPs) "
                f"könnten hierzu relevant sein, und warum?"
            )

        # ChatGPT-Aufruf
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",  # WICHTIG: jetzt GPT-4 statt 3.5
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=512
            )
            answer = response.choices[0].message.content.strip()
            self.topic_text.insert(tk.END, f"*** KI-Vorschläge für '{snp_id}' ***\n\n{answer}\n")
        except Exception as e:
            self.topic_text.insert(tk.END, f"(Fehler bei ChatGPT API: {e})\n")

    # --------------------------------------------------
    # Alternative SNP-Hinweise
    # --------------------------------------------------
    def _show_alternative_hints(self):
        snp_id = self.snp_entry.get().strip()
        self.alt_text.delete("1.0", tk.END)

        if not snp_id:
            messagebox.showwarning("Hinweis", "Bitte erst einen SNP oder Oberbegriff eingeben.")
            return

        alt_prompt = (
            f"Ich habe bereits über '{snp_id}' gesprochen. "
            f"Welche weiteren SNPs oder Genvarianten könnten ebenfalls relevant sein, "
            f"um das Thema zu verstehen oder zu vertiefen?"
        )

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",  # Ebenfalls GPT-4
                messages=[{"role": "user", "content": alt_prompt}],
                temperature=0.7,
                max_tokens=300
            )
            alt_answer = response.choices[0].message.content.strip()
            self.alt_text.insert(tk.END, f"Alternative SNP-Hinweise:\n\n{alt_answer}\n")
        except Exception as e:
            self.alt_text.insert(tk.END, f"(Fehler bei ChatGPT API: {e})\n")

    # --------------------------------------------------
    # Upload Studie
    # --------------------------------------------------
    def _upload_study(self):
        file_path = filedialog.askopenfilename(
            title="Studie hochladen",
            filetypes=[("PDF files", "*.pdf"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.upload_label.config(text=f"Hochgeladen: {os.path.basename(file_path)}")
        else:
            self.upload_label.config(text="Keine Studie hochgeladen.")

    # --------------------------------------------------
    # Frage zur Studie
    # --------------------------------------------------
    def _send_question(self):
        question = self.question_text.get("1.0", tk.END).strip()
        if not question:
            messagebox.showwarning("Hinweis", "Bitte eine Frage eingeben.")
            return
        # Ggf. ChatGPT-Aufruf oder Dummy-Antwort
        messagebox.showinfo("Antwort", f"Frage erhalten: {question}\n\n(Dummy-Antwort: Weitere Analyse erforderlich.)")
        self.question_text.delete("1.0", tk.END)
