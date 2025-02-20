import tkinter as tk
from tkinter import messagebox, scrolledtext
import re
import requests
import xml.etree.ElementTree as ET

class AnalysisWindow:
    """
    Dieses Fenster enthält die Logik für das 'Analyse & Bewertung'-Feature,
    ausgelagert aus dem Hauptprogramm.
    """

    def __init__(self, root, selected_data):
        """
        :param root: Das Haupt-Tkinter-Fenster (oder Toplevel).
        :param selected_data: Liste oder Dict mit den ausgewählten Papers (z.B. aus right_tree).
        """
        self.root = root  # Referenz auf das Haupt-Fenster/Eltern-Fenster
        self.selected_data = selected_data  # Struktur mit allen Papers

        self.analysis_data = {}  # Hier speichern wir die Analyse-Informationen zu jedem Paper

        # Hauptfenster aufbauen
        self.analysis_window = tk.Toplevel(self.root)
        self.analysis_window.title("Paper Analyse und Bewertung")
        self.analysis_window.geometry("1200x600")

        # Frames
        left_frame = tk.Frame(self.analysis_window)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        tk.Label(left_frame, text="Ausgewählte Paper").pack()
        self.paper_listbox = tk.Listbox(left_frame, width=40)
        self.paper_listbox.pack(fill=tk.Y, expand=True)

        right_frame = tk.Frame(self.analysis_window)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Zu bearbeitende Felder
        fields = [
            "ClinVar_Info", "Genotypen_Analyse", "Aussage_Genotypen",
            "Publikationsjahr", "Studiengröße", "Ethnische_Gruppe",
            "Zusammenfassung", "Zitierung", "Literaturzitate",
            "Bewertung", "Odds_Ratio", "PubMed_ID", "Link"
        ]
        self.analysis_entries = {}

        for field in fields:
            frame = tk.Frame(right_frame)
            frame.pack(fill=tk.X, pady=2)
            label = tk.Label(frame, text=field + ": ", width=20, anchor="w")
            label.pack(side=tk.LEFT)
            # Mehrzeilige Felder
            if field in ["ClinVar_Info", "Genotypen_Analyse", "Aussage_Genotypen", 
                         "Zusammenfassung", "Zitierung", "Literaturzitate"]:
                text_widget = tk.Text(frame, height=3, wrap="word")
                text_widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self.analysis_entries[field] = text_widget
            else:
                entry = tk.Entry(frame)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self.analysis_entries[field] = entry

        btn_save = tk.Button(right_frame, text="Bewertung speichern", command=self.save_current_analysis)
        btn_save.pack(pady=5)

        btn_overall = tk.Button(right_frame, text="Gesamtanalyse", command=self.show_overall_analysis)
        btn_overall.pack(pady=5)

        btn_relevant = tk.Button(right_frame, text="Relevante Paper anzeigen", command=self.show_relevant_papers)
        btn_relevant.pack(pady=5)

        overall_frame = tk.Frame(self.analysis_window)
        overall_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        tk.Label(overall_frame, text="Gesamtanalyse:").pack(anchor="w")
        self.overall_text = tk.Text(overall_frame, height=4, wrap="word")
        self.overall_text.pack(fill=tk.X, expand=True)

        # Liste befüllen
        for paper_dict in self.selected_data:
            title = paper_dict["Title"]
            self.paper_listbox.insert(tk.END, title)
            self.analysis_data[title] = self.generate_analysis_data(paper_dict)

        # Event-Bind für Auswahl
        self.paper_listbox.bind("<<ListboxSelect>>", self.load_analysis_data)

    def load_analysis_data(self, event):
        selection = self.paper_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        title = self.paper_listbox.get(index)
        data = self.analysis_data.get(title, {})
        for field, widget in self.analysis_entries.items():
            value = data.get(field, "")
            if isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
                widget.insert(tk.END, value)
            else:
                widget.delete(0, tk.END)
                widget.insert(0, value)

    def save_current_analysis(self):
        selection = self.paper_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warnung", "Kein Paper ausgewählt.")
            return
        index = selection[0]
        title = self.paper_listbox.get(index)
        for field, widget in self.analysis_entries.items():
            if isinstance(widget, tk.Text):
                self.analysis_data[title][field] = widget.get("1.0", tk.END).strip()
            else:
                self.analysis_data[title][field] = widget.get().strip()

        messagebox.showinfo("Info", f"Bewertung für '{title}' gespeichert.")

    def show_overall_analysis(self):
        ratings = []
        for title, data in self.analysis_data.items():
            try:
                rating = float(data.get("Bewertung", "0"))
                if rating > 0:
                    ratings.append(rating)
            except ValueError:
                continue

        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            overall_statement = f"Durchschnittliche Bewertung: {avg_rating:.2f}\n"
            if avg_rating >= 4:
                overall_statement += "Die Ergebnisse sind insgesamt signifikant. Die Studie kann weiterverwendet werden."
            elif avg_rating >= 2.5:
                overall_statement += "Die Ergebnisse sind gemischt. Weitere Bewertung ist erforderlich."
            else:
                overall_statement += "Die Ergebnisse sind weniger signifikant. Vorsicht bei der Verwendung der Studie."
        else:
            overall_statement = "Keine Bewertungen vorhanden."

        self.overall_text.delete("1.0", tk.END)
        self.overall_text.insert(tk.END, overall_statement)

    def show_relevant_papers(self):
        # Beispielkriterium: Paper ist "relevant", wenn ClinVar_Info 'pathogenic' enthält
        relevant_titles = []
        for title, data in self.analysis_data.items():
            if "pathogenic" in data.get("ClinVar_Info", "").lower():
                relevant_titles.append(title)

        if not relevant_titles:
            messagebox.showinfo("Relevante Paper", "Keine relevanten Paper basierend auf ClinVar-Informationen gefunden.")
            return

        rel_window = tk.Toplevel(self.analysis_window)
        rel_window.title("Relevante Paper")
        listbox = tk.Listbox(rel_window, width=50)
        listbox.pack(fill=tk.BOTH, expand=True)
        for t in relevant_titles:
            listbox.insert(tk.END, t)

    ##################################################
    # Hilfsfunktionen (falls gewünscht/ausgelagert)
    ##################################################
    def generate_analysis_data(self, result):
        """
        Erzeugt die initialen (Default-)Daten für ein Paper im Analyse-Fenster.
        """
        data = {}
        snp_id = ""
        # Sehr simples Beispiel, um evtl. rsXXXX zu finden
        m = re.search(r'rs\d+', result["Title"].lower())
        if m:
            snp_id = m.group(0)

        # ClinVar-Info
        if snp_id:
            data["ClinVar_Info"] = self.get_clinvar_info(snp_id)
        else:
            data["ClinVar_Info"] = "Keine ClinVar-Informationen"

        data["Genotypen_Analyse"] = "Keine spezifischen Genotyp-Daten vorhanden."
        data["Aussage_Genotypen"] = "Die vorliegenden Genotypen deuten auf eine heterogene Verteilung hin."
        data["Publikationsjahr"] = result["Year"]
        data["Studiengröße"] = "Nicht angegeben"
        data["Ethnische_Gruppe"] = "Nicht angegeben"
        data["Zusammenfassung"] = (
            "Diese Studie untersucht Zusammenhänge zwischen genetischen Faktoren und klinischen Ergebnissen."
        )
        citation_authors = result.get("Authors/Description", "Unbekannte Autoren")
        data["Zitierung"] = f"{citation_authors} ({result['Year']}). {result['Title']}. {result['Journal/Organism']}."
        data["Literaturzitate"] = "Beispielzitat: 'Dies ist ein Beispielzitat aus der Literatur.'"
        data["Bewertung"] = ""
        data["Odds_Ratio"] = "Nicht angegeben"
        data["PubMed_ID"] = result["PMID"]
        data["Link"] = result["URL"]
        return data

    def get_clinvar_info(self, rs_id):
        """
        Beispiel-Funktion, um ClinVar-Daten zu rsXXXX zu holen.
        """
        try:
            params = {"db": "clinvar", "term": f"{rs_id}[variant]", "retmode": "xml"}
            response = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params=params, timeout=10)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            clinvar_id = root.findtext("IdList/Id")
            if not clinvar_id:
                return "Keine ClinVar-Daten gefunden"

            fetch_params = {"db": "clinvar", "id": clinvar_id, "retmode": "xml"}
            fetch_response = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi", params=fetch_params, timeout=10)
            fetch_response.raise_for_status()
            fetch_root = ET.fromstring(fetch_response.content)
            clin_sig = fetch_root.findtext(".//ClinicalSignificance/Description", default="Keine Information")
            return clin_sig
        except Exception as e:
            return f"Fehler: {e}"
