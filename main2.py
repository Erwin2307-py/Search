import os
import sys
import subprocess
import webbrowser
import base64
import time
import datetime
from importlib import metadata  # ab Python 3.8
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import quote_plus
from fpdf import FPDF
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import fitz  # PyMuPDF
import re
import openpyxl
import xml.etree.ElementTree as ET

# Neu: Laden der .env-Variablen
from dotenv import load_dotenv

# Eigene ausgelagerte Module für Analyse & erweiterte Themen
from analysis_and_review import AnalysisWindow
from extended_topics import ExtendedTopicsWindow

# .env-Datei laden (muss im selben Verzeichnis wie main.py liegen)
load_dotenv()

# API-Keys aus den Environment-Variablen lesen
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
CHATGPT_API_KEY = os.environ.get("CHATGPT_API_KEY")

# ChatGPT-Key global setzen
import openai
openai.api_key = CHATGPT_API_KEY


#############################################
# DBSnpAPI-Klasse (NEUE Logik)
#############################################
class DBSnpAPI:
    def __init__(self, email: str, api_key: str):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.params = {
            "db": "snp",
            "retmode": "xml",
            "email": email,
            "api_key": api_key,
            "tool": "DBSnpPythonClient"
        }
        self.namespace = {'ns': 'https://www.ncbi.nlm.nih.gov/SNP/docsum'}

    def get_snp_info(self, rs_id: str):
        try:
            search_params = {"term": f"{rs_id}[RS]", "retmax": "1"}
            search_response = requests.get(
                f"{self.base_url}esearch.fcgi",
                params={**self.params, **search_params},
                timeout=10
            )
            search_response.raise_for_status()
            search_root = ET.fromstring(search_response.content)
            snp_id = search_root.findtext("IdList/Id")
            if not snp_id:
                print("SNP-ID nicht gefunden")
                return None

            fetch_response = requests.get(
                f"{self.base_url}efetch.fcgi",
                params={**self.params, "id": snp_id},
                timeout=10
            )
            fetch_response.raise_for_status()
            return self.parse_xml(fetch_response.content)

        except Exception as e:
            print(f"Fehler: {str(e)}")
            return None

    def parse_xml(self, xml_content):
        root = ET.fromstring(xml_content)
        snp_info = {}
        doc_summary = root.find(".//ns:DocumentSummary", self.namespace)
        if doc_summary is not None:
            snp_info["rs_id"] = f"rs{doc_summary.findtext('ns:SNP_ID', '', self.namespace)}"
            snp_info["chromosome"] = doc_summary.findtext("ns:CHR", "", self.namespace)
            snp_info["position"] = doc_summary.findtext("ns:CHRPOS", "", self.namespace)
            snp_info["alleles"] = doc_summary.findtext("ns:SPDI", "", self.namespace)

            clin_sig = doc_summary.findtext("ns:CLINICAL_SIGNIFICANCE", "", self.namespace)
            snp_info["clinical_significance"] = clin_sig.split(",") if clin_sig else []

            snp_info["gene"] = doc_summary.findtext("ns:GENES/ns:GENE_E/ns:NAME", "", self.namespace)

            mafs = []
            for maf in doc_summary.findall(".//ns:MAF", self.namespace):
                study = maf.findtext("ns:STUDY", "", self.namespace)
                freq = maf.findtext("ns:FREQ", "", self.namespace)
                mafs.append(f"{study}: {freq}")
            snp_info["mafs"] = mafs

        return snp_info


#############################################
# CoreAPI-Klasse für CORE Aggregate
#############################################
class CoreAPI:
    def __init__(self, api_key):
        self.base_url = "https://api.core.ac.uk/v3/"
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def search_publications(self, query, filters=None, sort=None, limit=10):
        endpoint = "search/works"
        params = {"q": query, "limit": limit}
        if filters:
            filter_expressions = []
            for key, value in filters.items():
                filter_expressions.append(f"{key}:{value}")
            params["filter"] = ",".join(filter_expressions)
        if sort:
            params["sort"] = sort
        r = requests.get(
            self.base_url + endpoint,
            headers=self.headers,
            params=params,
            timeout=15
        )
        r.raise_for_status()
        return r.json()


#############################################
# Hilfsfunktion: URL in neuem Chrome-Fenster öffnen
#############################################
def open_in_new_chrome_window(url):
    try:
        subprocess.Popen(["chrome", "--new-window", url])
    except Exception as e:
        messagebox.showerror("Fehler", f"Fehler beim Öffnen in Chrome: {e}")


#############################################
# PubMed-Verbindungsprüfung
#############################################
def check_pubmed_connection(timeout=10):
    test_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {"db": "pubmed", "term": "test", "retmode": "json"}
    try:
        r = requests.get(test_url, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        if "esearchresult" in data:
            return True
        else:
            return False
    except Exception:
        return False


#############################################
# Haupt-App-Klasse
#############################################
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("API-Suche und PDF-Erstellung")
        self.root.geometry("1600x900")

        self.blink_state = True
        self.pubmed_id_search = False

        # Online-Filter
        self.filter_local_var = tk.BooleanVar(value=True)
        self.filter_perplexity_var = tk.BooleanVar(value=False)
        self.filter_deepseek_var = tk.BooleanVar(value=False)
        self.filter_chatgpt_var = tk.BooleanVar(value=False)

        # ChatGPT-spezifisch
        self.chatgpt_genotype_var = tk.BooleanVar(value=True)
        self.chatgpt_phenotype_var = tk.BooleanVar(value=True)
        self.chatgpt_snp_var = tk.BooleanVar(value=True)

        # Extra-Filter
        self.filter_extra_var = tk.BooleanVar(value=False)
        self.extra_filter_string = tk.StringVar(value="")

        # Gene (Excel)
        self.filter_gene_excel_var = tk.BooleanVar(value=False)
        self.gene_excel_selected_sheet = None
        self.gene_excel_genes = []

        self.font_name = "DejaVu"
        self.font_file = "DejaVuSansCondensed.ttf"
        self._ensure_font_available()

        # PubMed-Check
        if check_pubmed_connection():
            self_connection_msg = "[INFO] Verbindung zu PubMed erfolgreich hergestellt."
        else:
            self_connection_msg = "[WARNUNG] Keine Verbindung zu PubMed."

        self.all_results = []
        self.page_size = 50
        self.current_page = 0

        self.available_excels = {
            "Genetik": r"C:\Users\ErwinSchimak\Desktop\Reserach\Journals\Genetik.xlsx",
            "Medizin": r"C:\Users\ErwinSchimak\Desktop\Reserach\Journals\Medizin.xlsx"
        }
        self.current_excel_path = self.available_excels["Genetik"]
        self.journals, self.journal_lookup = self._load_journals_from_excel(self.current_excel_path)

        self.excel_details = []
        self.excel_main = []

        # PubMed session
        self.pubmed_session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.pubmed_session.mount("http://", adapter)
        self.pubmed_session.mount("https://", adapter)

        # ------------- Frame: API Selection -------------
        api_frame = tk.LabelFrame(self.root, text="Wähle APIs aus", padx=10, pady=10)
        api_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.api_vars = {
            "Europe PMC": tk.BooleanVar(value=True),
            "PubMed": tk.BooleanVar(value=False),
            "Ensembl REST": tk.BooleanVar(value=False),
            "UniProt": tk.BooleanVar(value=False),
            "OpenAlex": tk.BooleanVar(value=False),
            "Scopus": tk.BooleanVar(value=False),
            "CORE Aggregate": tk.BooleanVar(value=False),
            "Unpaywall": tk.BooleanVar(value=False),
            "NCBI e": tk.BooleanVar(value=False),
            "PLOS": tk.BooleanVar(value=False),
            "Hathitrust": tk.BooleanVar(value=False),
            "OpenCitations": tk.BooleanVar(value=False),
            "DataCite": tk.BooleanVar(value=False),
            "Google Scholar": tk.BooleanVar(value=False),
            "Semantic Scholar": tk.BooleanVar(value=False)
        }
        for api_name, var in self.api_vars.items():
            cb = tk.Checkbutton(api_frame, text=api_name, variable=var)
            cb.pack(side=tk.LEFT, padx=5)

        # ------------- Frame: Online Filter (erweitert) -------------
        filter_options_frame = tk.LabelFrame(self.root, text="Online-Filter Optionen", padx=10, pady=10)
        filter_options_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        tk.Label(filter_options_frame, text="Wähle, welche Online-Filter angewendet werden sollen:").pack(side=tk.LEFT)
        tk.Checkbutton(filter_options_frame, text="Local (Schlüsselwörter)", variable=self.filter_local_var).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(filter_options_frame, text="Perplexity API", variable=self.filter_perplexity_var).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(filter_options_frame, text="DeepSeek API", variable=self.filter_deepseek_var).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(filter_options_frame, text="ChatGPT API", variable=self.filter_chatgpt_var).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(filter_options_frame, text="Genotype", variable=self.chatgpt_genotype_var).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(filter_options_frame, text="Phenotype", variable=self.chatgpt_phenotype_var).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(filter_options_frame, text="SNP", variable=self.chatgpt_snp_var).pack(side=tk.LEFT, padx=5)

        # Gene (Excel)
        tk.Checkbutton(filter_options_frame, text="Gene (Excel)", variable=self.filter_gene_excel_var, command=self._open_excel_sheet_for_genes).pack(side=tk.LEFT, padx=10)

        # Extra-Filter
        extra_filter_frame = tk.Frame(filter_options_frame)
        extra_filter_frame.pack(side=tk.LEFT, padx=20)
        tk.Checkbutton(extra_filter_frame, text="Extra-Filter aktivieren:", variable=self.filter_extra_var).pack(side=tk.LEFT)
        self.extra_filter_entry = tk.Entry(extra_filter_frame, textvariable=self.extra_filter_string, width=15)
        self.extra_filter_entry.pack(side=tk.LEFT, padx=5)
        btn_set_extra = tk.Button(extra_filter_frame, text="Extra Filterbegriff setzen", command=self._set_extra_filter)
        btn_set_extra.pack(side=tk.LEFT)

        # ------------- Frame: Code Words + Filter -------------
        top_frame = tk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        tk.Label(top_frame, text="Codewörter (OR-Suche):").pack(side=tk.LEFT)
        self.codeword_entry = tk.Entry(top_frame, width=50)
        self.codeword_entry.pack(side=tk.LEFT, padx=5)
        btn_add_code = tk.Button(top_frame, text="+ Codewort", command=self.add_code_word_entry)
        btn_add_code.pack(side=tk.LEFT, padx=5)

        tk.Label(top_frame, text="Genotyp:").pack(side=tk.LEFT, padx=5)
        self.genotype_var = tk.StringVar()
        genotype_options = ["", "A/A", "A/G", "A/T", "C/C", "C/G", "C/T", "G/G", "G/T", "T/T"]
        self.genotype_combo = ttk.Combobox(top_frame, textvariable=self.genotype_var, values=genotype_options, width=6, state="readonly")
        self.genotype_combo.pack(side=tk.LEFT, padx=5)
        self.genotype_combo.set("")

        btn_search = tk.Button(top_frame, text="Suchen", command=self.search_articles)
        btn_search.pack(side=tk.LEFT, padx=5)
        btn_clear = tk.Button(top_frame, text="Suchergebnisse löschen", command=self.clear_search_results)
        btn_clear.pack(side=tk.LEFT, padx=5)
        self.codeword_entry.bind("<Return>", self.search_articles)

        self.words_frame = tk.Frame(self.root)
        self.words_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        self.code_word_entries = []
        self.add_code_word_entry()

        # ------------- PubMed ID Search -------------
        pubmed_id_frame = tk.Frame(self.root)
        pubmed_id_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        tk.Label(pubmed_id_frame, text="PubMed ID(s) (durch Kommas trennen):").pack(side=tk.LEFT)
        self.pubmed_id_entry = tk.Entry(pubmed_id_frame, width=50)
        self.pubmed_id_entry.pack(side=tk.LEFT, padx=5)
        btn_pubmed_id_search = tk.Button(pubmed_id_frame, text="PubMed ID suchen", command=self.search_pubmed_ids)
        btn_pubmed_id_search.pack(side=tk.LEFT, padx=5)

        # ------------- Frame: Search and Filter Criteria -------------
        criteria_frame = tk.Frame(self.root)
        criteria_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        self.apply_search_criteria = tk.BooleanVar(value=False)

        # --- Suchkriterien ---
        such_frame = tk.LabelFrame(criteria_frame, text="Suchkriterien", padx=10, pady=10)
        such_frame.pack(side=tk.LEFT, padx=10, pady=10)
        chk_such = tk.Checkbutton(such_frame, text="Suchkriterien anwenden", variable=self.apply_search_criteria)
        chk_such.grid(row=0, column=0, columnspan=2, sticky="w")

        self.search_populationsgroesse = tk.BooleanVar(value=False)
        tk.Checkbutton(such_frame, text="Populationsgröße (falls vorhanden)", variable=self.search_populationsgroesse).grid(row=1, column=0, sticky="w", padx=5, pady=2)

        tk.Label(such_frame, text="Erscheinungsjahr:").grid(row=2, column=0, sticky="w")
        years_such = list(range(1975, 2026))
        self.search_year_var = tk.StringVar()
        self.search_year_combo = ttk.Combobox(such_frame, textvariable=self.search_year_var, values=years_such, state="readonly")
        self.search_year_combo.grid(row=2, column=1, padx=5, pady=2)
        self.search_year_combo.set("")

        tk.Label(such_frame, text="Journal (aus Excel):").grid(row=3, column=0, sticky="w")
        self.search_journal_var = tk.StringVar()
        self.search_journal_combo = ttk.Combobox(such_frame, textvariable=self.search_journal_var, values=[], state="readonly")
        self.search_journal_combo.grid(row=3, column=1, padx=5, pady=2)
        self.search_journal_combo.set("")

        tk.Label(such_frame, text="Bereich (Excel-Datei):").grid(row=4, column=0, sticky="w")
        self.search_bereich_var = tk.StringVar()
        self.search_bereich_combo = ttk.Combobox(such_frame, textvariable=self.search_bereich_var, values=list(self.available_excels.keys()), state="readonly")
        self.search_bereich_combo.grid(row=4, column=1, padx=5, pady=2)
        self.search_bereich_combo.set("Genetik")
        self.search_bereich_combo.bind("<<ComboboxSelected>>", self._on_search_excel_file_change)

        # --- Filterkriterien ---
        filter_frame = tk.LabelFrame(criteria_frame, text="Filterkriterien", padx=10, pady=10)
        filter_frame.pack(side=tk.LEFT, padx=10, pady=10)

        tk.Label(filter_frame, text="Bereich (Excel-Datei):").grid(row=0, column=0, sticky="w")
        self.bereich_var = tk.StringVar()
        self.bereich_combo = ttk.Combobox(filter_frame, textvariable=self.bereich_var, values=list(self.available_excels.keys()), state="readonly")
        self.bereich_combo.grid(row=0, column=1, padx=5, pady=5)
        self.bereich_combo.set("Genetik")
        self.bereich_combo.bind("<<ComboboxSelected>>", self._on_excel_file_change)

        self.var_populationsgroesse = tk.BooleanVar(value=False)
        tk.Checkbutton(filter_frame, text="Populationsgröße (falls vorhanden)", variable=self.var_populationsgroesse).grid(row=1, column=0, padx=5, pady=5, sticky="w")

        tk.Label(filter_frame, text="Erscheinungsjahr:").grid(row=2, column=0, sticky="w")
        years_filter = list(range(1975, 2026))
        self.year_var = tk.StringVar()
        self.year_combo = ttk.Combobox(filter_frame, textvariable=self.year_var, values=years_filter, state="readonly")
        self.year_combo.grid(row=2, column=1, padx=5, pady=5)
        self.year_combo.set("")

        tk.Label(filter_frame, text="Journal (aus Excel):").grid(row=3, column=0, sticky="w")
        self.journal_var = tk.StringVar()
        self.journal_combo = ttk.Combobox(filter_frame, textvariable=self.journal_var, values=self.journals, state="readonly")
        self.journal_combo.grid(row=3, column=1, padx=5, pady=5)
        self.journal_combo.set("")

        btn_auto_select = tk.Button(filter_frame, text="Auto-Select", command=self.auto_select_papers)
        btn_auto_select.grid(row=4, column=0, columnspan=2, pady=5)

        # --- UniProt ---
        uniprot_frame = tk.LabelFrame(criteria_frame, text="UniProt-Auswahl", padx=10, pady=10)
        uniprot_frame.pack(side=tk.LEFT, padx=10, pady=10)
        tk.Label(uniprot_frame, text="Protein:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.uniprot_protein_var = tk.StringVar()
        protein_list = ["TP53", "MYH7", "EGFR", "ACE2", "GFP", "Hämoglobin", "Myoglobin", "Insulin"]
        self.uniprot_protein_combo = ttk.Combobox(uniprot_frame, textvariable=self.uniprot_protein_var, values=protein_list, state="readonly", width=20)
        self.uniprot_protein_combo.grid(row=0, column=1, padx=5, pady=2)
        self.uniprot_protein_combo.set("")
        btn_uniprot_search = tk.Button(uniprot_frame, text="UniProt suchen", command=self.search_uniprot_direct)
        btn_uniprot_search.grid(row=1, column=0, columnspan=2, pady=5)
        btn_uniprot_manual = tk.Button(uniprot_frame, text="Manuell eingeben", command=self.open_manual_uniprot)
        btn_uniprot_manual.grid(row=2, column=0, columnspan=2, pady=5)

        # --- Ensembl ---
        ensembl_frame = tk.LabelFrame(criteria_frame, text="Ensembl-Auswahl", padx=10, pady=10)
        ensembl_frame.pack(side=tk.LEFT, padx=10, pady=10)
        tk.Label(ensembl_frame, text="Spezies:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.ensembl_species_var = tk.StringVar()
        self.ensembl_species_var.set("homo_sapiens")
        ttk.Entry(ensembl_frame, textvariable=self.ensembl_species_var, width=15).grid(row=0, column=1, padx=5, pady=2)
        tk.Label(ensembl_frame, text="Gen-Symbol:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.ensembl_gene_var = tk.StringVar()
        ttk.Entry(ensembl_frame, textvariable=self.ensembl_gene_var, width=15).grid(row=1, column=1, padx=5, pady=2)
        btn_ensembl_search = tk.Button(ensembl_frame, text="Ensembl suchen", command=self.search_ensembl_direct)
        btn_ensembl_search.grid(row=2, column=0, columnspan=2, pady=5)

        # --- dbSNP ---
        dbsnp_frame = tk.LabelFrame(criteria_frame, text="NCBI dbSNP-Auswahl", padx=10, pady=10)
        dbsnp_frame.pack(side=tk.LEFT, padx=10, pady=10)
        tk.Label(dbsnp_frame, text="RS-ID:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.dbsnp_rs_entry = tk.Entry(dbsnp_frame, width=15)
        self.dbsnp_rs_entry.grid(row=0, column=1, padx=5, pady=2)
        btn_dbsnp_search = tk.Button(dbsnp_frame, text="dbSNP suchen", command=self.search_dbsnp_direct)
        btn_dbsnp_search.grid(row=1, column=0, columnspan=2, pady=5)

        # ------------- Roter Balken mit Log -------------
        self.found_frame = tk.Frame(self.root, bg="red", highlightthickness=2, highlightcolor="red", bd=2, relief="solid")
        self.found_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        self.total_label = tk.Label(self.found_frame, text="Insgesamt 0 Paper gefunden", bg="red", fg="white")
        self.total_label.pack(side=tk.LEFT, padx=10)

        # Blauer Zähler
        self.blue_label = tk.Label(self.found_frame, text="", bg="blue", fg="white", width=40, height=2)
        self.blue_label.pack(side=tk.RIGHT, padx=10)

        page_button_frame = tk.Frame(self.found_frame, bg="red")
        page_button_frame.pack(side=tk.RIGHT)

        self.prev_button = tk.Button(page_button_frame, text="<< Zurück", command=self.prev_page)
        self.prev_button.pack(side=tk.LEFT, padx=5)
        self.next_button = tk.Button(page_button_frame, text="Weiter >>", command=self.next_page)
        self.next_button.pack(side=tk.LEFT, padx=5)

        # ScrolledText für Log
        self.log_text = scrolledtext.ScrolledText(self.found_frame, wrap="word", width=60, height=5, bg="#EEE")
        self.log_text.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(5, 5))

        self.update_log(self_connection_msg)

        # ------------- Verschieben in rechte Treeview -------------
        move_button_frame = tk.Frame(self.root)
        move_button_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        btn_add_selected = tk.Button(move_button_frame, text=">> Auswählen", command=self.add_selected_papers)
        btn_add_selected.pack(side=tk.LEFT, padx=5)
        btn_remove_selected = tk.Button(move_button_frame, text="<< Entfernen", command=self.remove_selected_papers)
        btn_remove_selected.pack(side=tk.LEFT, padx=5)

        # ------------- Trees Frame (Left + Right) -------------
        trees_frame = tk.Frame(self.root)
        trees_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_tree_frame = tk.Frame(trees_frame)
        left_tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        tk.Label(left_tree_frame, text="Gefundene Paper (max. 50 pro Seite)").pack(side=tk.TOP)
        left_cols = ("Source", "Title", "Authors/Description", "Journal/Organism", "Year", "PMID", "DOI", "URL")
        self.left_tree = ttk.Treeview(left_tree_frame, columns=left_cols, show="headings", selectmode="extended")
        for c in left_cols:
            self.left_tree.heading(c, text=c)
            if c == "Title":
                self.left_tree.column(c, width=300)
            elif c == "Authors/Description":
                self.left_tree.column(c, width=250)
            elif c == "Journal/Organism":
                self.left_tree.column(c, width=150)
            elif c == "URL":
                self.left_tree.column(c, width=200)
            else:
                self.left_tree.column(c, width=100)
        self.left_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.left_tree.bind("<Double-1>", self.show_abstract_popup)

        right_tree_frame = tk.Frame(trees_frame)
        right_tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        tk.Label(right_tree_frame, text="Ausgewählte Paper").pack(side=tk.TOP)
        right_cols = ("Source", "Title", "Authors/Description", "Journal/Organism", "Year", "PMID", "DOI", "URL")
        self.right_tree = ttk.Treeview(right_tree_frame, columns=right_cols, show="headings", selectmode="extended")
        for c in right_cols:
            self.right_tree.heading(c, text=c)
            if c == "Title":
                self.right_tree.column(c, width=300)
            elif c == "Authors/Description":
                self.right_tree.column(c, width=250)
            elif c == "Journal/Organism":
                self.right_tree.column(c, width=150)
            elif c == "URL":
                self.right_tree.column(c, width=200)
            else:
                self.right_tree.column(c, width=100)
        self.right_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ------------- Bottom Frame (Buttons) -------------
        bottom_button_frame = tk.Frame(self.root)
        bottom_button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        btn_pdf = tk.Button(bottom_button_frame, text="Abstract herunterladen & Webseite als PDF speichern", command=self.download_papers)
        btn_pdf.pack(side=tk.LEFT, padx=(0, 10))

        btn_open_page = tk.Button(bottom_button_frame, text="Seite öffnen (nur Browser)", command=self.open_article_page)
        btn_open_page.pack(side=tk.LEFT)

        btn_execute_mods = tk.Button(bottom_button_frame, text="Ausgewählte Module ausführen", command=self.execute_selected_modules)
        btn_execute_mods.pack(side=tk.LEFT, padx=10)

        btn_excel_all = tk.Button(bottom_button_frame, text="Komplette Excel-Liste erstellen", command=self.create_complete_excel_list)
        btn_excel_all.pack(side=tk.LEFT, padx=10)

        btn_analysis = tk.Button(bottom_button_frame, text="Analyse & Bewertung", command=self.open_analysis_window, bg="green", fg="white")
        btn_analysis.pack(side=tk.LEFT, padx=10)

        btn_extended = tk.Button(bottom_button_frame, text="Erweiterte Themen & Upload", command=self.open_extended_topic_window, bg="blue", fg="white")
        btn_extended.pack(side=tk.LEFT, padx=10)

        self.blink_label = tk.Label(self.root, text="", width=2, height=1)
        self.blink_label.place(relx=1.0, rely=1.0, x=-50, y=-40, anchor="center")
        self._blink_lamp()

    def open_analysis_window(self):
        selected_papers = []
        for item_id in self.right_tree.get_children():
            vals = self.right_tree.item(item_id, "values")
            paper = {
                "Source": vals[0],
                "Title": vals[1],
                "Authors/Description": vals[2],
                "Journal/Organism": vals[3],
                "Year": vals[4],
                "PMID": vals[5],
                "DOI": vals[6],
                "URL": vals[7],
            }
            selected_papers.append(paper)

        AnalysisWindow(self.root, selected_papers)

    def open_extended_topic_window(self):
        ExtendedTopicsWindow(self.root, openai_api_key=CHATGPT_API_KEY)

    def update_log(self, msg):
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)

    def _open_excel_sheet_for_genes(self):
        if not self.filter_gene_excel_var.get():
            self.gene_excel_genes.clear()
            self.gene_excel_selected_sheet = None
            return
        file_path = filedialog.askopenfilename(title="Excel-Datei für Gene auswählen", filetypes=[("Excel-Dateien", "*.xlsx *.xls")])
        if not file_path:
            self.update_log("Gene (Excel): Keine Datei gewählt.")
            return
        try:
            wb = openpyxl.load_workbook(file_path)
            sheet_names = wb.sheetnames
            sheet_win = tk.Toplevel(self.root)
            sheet_win.title("Sheet auswählen")

            tk.Label(sheet_win, text=f"Bitte wähle ein Sheet aus '{os.path.basename(file_path)}':").pack(padx=10, pady=5)
            sheet_var = tk.StringVar(value=sheet_names[0])
            combo_sheet = ttk.Combobox(sheet_win, textvariable=sheet_var, values=sheet_names, state="readonly")
            combo_sheet.pack(padx=10, pady=5)

            def confirm_sheet():
                self.gene_excel_selected_sheet = combo_sheet.get()
                sheet = wb[self.gene_excel_selected_sheet]
                self.gene_excel_genes.clear()
                row_idx = 3
                col_letter = "C"
                while True:
                    cell_id = f"{col_letter}{row_idx}"
                    val = sheet[cell_id].value
                    if val is None:
                        break
                    gene_str = str(val).strip()
                    if gene_str:
                        self.gene_excel_genes.append(gene_str)
                    row_idx += 1

                self.update_log(f"Gene (Excel): Sheet '{self.gene_excel_selected_sheet}' eingelesen, {len(self.gene_excel_genes)} Einträge.")
                sheet_win.destroy()

            btn_ok = tk.Button(sheet_win, text="OK", command=confirm_sheet)
            btn_ok.pack(padx=10, pady=5)
        except Exception as e:
            self.update_log(f"Fehler beim Öffnen der Excel-Datei: {e}")

    def _set_extra_filter(self):
        term = self.extra_filter_entry.get().strip()
        if term:
            self.extra_filter_string.set(term)
            self.update_log(f"Extra-Filterbegriff gesetzt: '{term}'")
        else:
            self.extra_filter_string.set("")
            self.update_log("Extra-Filterbegriff zurückgesetzt (leer)")

    def _blink_lamp(self):
        any_filter_active = (
            self.filter_local_var.get()
            or self.filter_perplexity_var.get()
            or self.filter_deepseek_var.get()
            or self.filter_chatgpt_var.get()
            or self.filter_extra_var.get()
            or self.filter_gene_excel_var.get()
        )
        color_on = "green" if any_filter_active else "red"
        color_off = "white"

        if self.blink_state:
            self.blink_label.config(bg=color_on)
        else:
            self.blink_label.config(bg=color_off)
        self.blink_state = not self.blink_state
        self.root.after(500, self._blink_lamp)

    def open_manual_uniprot(self):
        top = tk.Toplevel(self.root)
        top.title("Manuelle UniProt-Eingabe")
        tk.Label(top, text="Protein manuell eingeben:").pack(padx=10, pady=5)
        manual_entry = tk.Entry(top, width=30)
        manual_entry.pack(padx=10, pady=5)

        def set_value():
            value = manual_entry.get().strip()
            if value:
                self.uniprot_protein_var.set(value)
                self.uniprot_protein_combo.set(value)
            top.destroy()

        btn_ok = tk.Button(top, text="OK", command=set_value)
        btn_ok.pack(padx=10, pady=5)

    def add_code_word_entry(self):
        entry = tk.Entry(self.words_frame, width=30)
        entry.pack(side=tk.LEFT, padx=2, pady=2)
        self.code_word_entries.append(entry)

    def clear_search_results(self):
        self.all_results.clear()
        self.current_page = 0
        self.excel_details.clear()
        self.excel_main.clear()
        for ch in self.left_tree.get_children():
            self.left_tree.delete(ch)
        for ch in self.right_tree.get_children():
            self.right_tree.delete(ch)

        self.found_frame.config(bg="red")
        self.total_label.config(text="Insgesamt 0 Paper gefunden", bg="red", fg="white")
        self.log_text.delete("1.0", tk.END)

    def clear_codewords(self):
        self.codeword_entry.delete(0, tk.END)
        for entry in self.code_word_entries:
            entry.delete(0, tk.END)

    def _on_excel_file_change(self, event):
        chosen_key = self.bereich_var.get()
        if chosen_key in self.available_excels:
            self.current_excel_path = self.available_excels[chosen_key]
            self.journals, self.journal_lookup = self._load_journals_from_excel(self.current_excel_path)
            self.journal_combo["values"] = self.journals
            self.journal_combo.set("")

    def _on_search_excel_file_change(self, event):
        chosen_key = self.search_bereich_var.get()
        if chosen_key in self.available_excels:
            new_xlsx = self.available_excels[chosen_key]
            jlist, jlookup = self._load_journals_from_excel(new_xlsx)
            self.search_journal_combo["values"] = jlist
            self.search_journal_combo.set("")

    def _ensure_font_available(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ttf_path = os.path.join(script_dir, self.font_file)
        if not os.path.exists(ttf_path):
            url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSansCondensed.ttf"
            try:
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
                with open(ttf_path, "wb") as f:
                    f.write(resp.content)
            except Exception as e:
                raise RuntimeError(f"Fehler beim Laden {self.font_file}: {e}")

    def _load_journals_from_excel(self, excel_path):
        jlist = []
        jlookup = {}
        if not os.path.exists(excel_path):
            return jlist, jlookup
        try:
            wb = openpyxl.load_workbook(excel_path)
            ws = wb.active
            data_temp = []
            for row in ws.iter_rows(min_row=2, min_col=1, max_col=2, values_only=True):
                if row and row[0] and row[1]:
                    data_temp.append((row[0], row[1]))
            data_temp.sort(key=lambda x: x[0])
            for (r, t) in data_temp:
                combined = f"{r}) {t}"
                jlist.append(combined)
                jlookup[combined] = t
        except Exception:
            pass
        return jlist, jlookup

    def get_query_string(self):
        code_words = []
        for entry in self.code_word_entries:
            w = entry.get().strip()
            if w:
                code_words.append(w)
        main_word = self.codeword_entry.get().strip()
        if main_word:
            code_words.append(main_word)
        selected_geno = self.genotype_var.get().strip()
        if selected_geno:
            code_words.append(selected_geno)
        if not code_words:
            return ""
        return " OR ".join(code_words)

    def search_articles(self, event=None):
        self.pubmed_id_search = False
        query = self.get_query_string()
        if not query:
            messagebox.showwarning("Hinweis", "Bitte mindestens ein Suchwort oder Genotyp eingeben!")
            return

        selected_apis = [api for api, var in self.api_vars.items() if var.get()]
        if not selected_apis:
            messagebox.showwarning("Hinweis", "Mindestens eine API auswählen!")
            return

        self.all_results.clear()
        self.current_page = 0
        self.excel_details.clear()
        self.excel_main.clear()
        for ch in self.left_tree.get_children():
            self.left_tree.delete(ch)
        for ch in self.right_tree.get_children():
            self.right_tree.delete(ch)

        if self.apply_search_criteria.get():
            self.search_pop = bool(self.search_populationsgroesse.get())
            y = self.search_year_var.get().strip()
            if y:
                self.search_year = f"{y}:{y}[dp]"
            else:
                self.search_year = ""
            self.search_journal = self.search_journal_var.get().strip()
        else:
            self.search_pop = False
            self.search_year = ""
            self.search_journal = ""

        self.update_log(f"Starte Suche für: {query}")

        for api in selected_apis:
            self.update_log(f"Rufe API '{api}' auf ...")
            if api == "Europe PMC":
                self.search_europe_pmc(query)
            elif api == "PubMed":
                self.search_pubmed(query)
            elif api == "OpenAlex":
                self.search_openalex(query)
            elif api == "Google Scholar":
                self.search_google_scholar(query)
            elif api == "Semantic Scholar":
                self.search_semantic_scholar(query)
            elif api == "CORE Aggregate":
                self.search_core_aggregate(query)

        use_filter = (
            self.filter_local_var.get()
            or self.filter_perplexity_var.get()
            or self.filter_deepseek_var.get()
            or self.filter_chatgpt_var.get()
            or self.filter_extra_var.get()
            or self.filter_gene_excel_var.get()
        )
        if use_filter:
            messagebox.showinfo(
                "Filter",
                "Die Online-Filterung wird durchgeführt. Dies kann einige Zeit dauern.\n"
                "Bitte auf 'OK' klicken, um fortzufahren..."
            )
            original_count = len(self.all_results)
            filtered_results = []

            for i, paper in enumerate(self.all_results, start=1):
                self.blue_label.config(text=f"({i}/{original_count}) -> {paper.get('Title','')[:30]}")
                self.root.update()

                info_line = f"Online-Filter: Prüfe Paper {i}/{original_count} -> '{paper.get('Title','')}'"
                self.update_log(info_line)

                keep_it = self.online_filter_paper(paper)
                if keep_it:
                    filtered_results.append(paper)
                else:
                    self.update_log(f"Ergebnis Filter für '{paper.get('Title','')}' -> False")

            self.blue_label.config(text="Filter abgeschlossen")

            if not filtered_results:
                messagebox.showinfo("Online Filter", "Keine Ergebnisse nach Online-Filterung gefunden. Es werden alle Paper angezeigt.")
            else:
                self.all_results = filtered_results

            if messagebox.askyesno("Codewörter löschen?", "Möchten Sie die eingegebenen Codewörter für die nächste Suche entfernen?"):
                self.clear_codewords()

            messagebox.showinfo("Neue Suche möglich", "Die Filterung ist abgeschlossen. Du kannst jetzt erneut auf 'Suchen' klicken oder die Codewörter anpassen.")

        self.update_log("Suche abgeschlossen.")
        self._display_page()

    def online_filter_paper(self, paper):
        url = paper.get("URL", "")
        if not url or url == "n/a":
            self.update_log(f"[Filter] Keine gültige URL -> PAPER gefiltert")
            return False

        combined_text = paper.get("Abstract", "").lower()
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            combined_text += " " + r.text.lower()
        except Exception as e:
            self.update_log(f"Local Filter: Fehler beim Abruf URL {url}: {e}")

        self.update_log(f"[Filter] Prüfe Paper: {paper.get('Title','(kein Titel)')} mit URL: {url}")

        result_local = False
        result_perplexity = False
        result_deepseek = False
        result_chatgpt = False
        result_extra = False
        result_gene_excel = False

        if self.filter_local_var.get():
            keywords = ["genotype", "phenotype", "snp", "genotyp", "phänotyp", "gene"]
            for kw in keywords:
                if kw in combined_text:
                    self.update_log(f"  -> Lokaler Filter: Schlüsselwort '{kw}' in (Abstract/Seite) gefunden -> PAPER OK")
                    result_local = True
                    break

        if self.filter_perplexity_var.get():
            result_perplexity = self.filter_with_perplexity(url, paper.get("Abstract", ""))
            self.update_log(f"  Perplexity Filter: {result_perplexity}")

        if self.filter_deepseek_var.get():
            result_deepseek = self.filter_with_deepseek(url, paper.get("Abstract", ""))
            self.update_log(f"  DeepSeek Filter: {result_deepseek}")

        if self.filter_chatgpt_var.get():
            criteria = []
            if self.chatgpt_genotype_var.get():
                criteria.append("genotype")
            if self.chatgpt_phenotype_var.get():
                criteria.append("phenotype")
            if self.chatgpt_snp_var.get():
                criteria.append("SNP")
            result_chatgpt = self.filter_with_chatgpt(url, criteria, paper.get("Abstract", ""))
            self.update_log(f"  ChatGPT Filter: {result_chatgpt}")

        if self.filter_extra_var.get():
            term = self.extra_filter_string.get().lower().strip()
            if term:
                if term in combined_text:
                    self.update_log(f"  -> Extra Filterbegriff '{term}' im kombinierten Text gefunden -> PAPER OK")
                    result_extra = True

        if self.filter_gene_excel_var.get() and self.gene_excel_genes:
            found_match = False
            title_lower = paper.get("Title", "").lower()
            for gene_candidate in self.gene_excel_genes:
                g_lower = gene_candidate.lower()
                if g_lower in title_lower or g_lower in combined_text:
                    found_match = True
                    break

            if found_match:
                self.update_log(f"  -> Gene-Excel-Filter: '{gene_candidate}' in Titel/Abstract/Seite gefunden -> PAPER OK")
                result_gene_excel = True
            else:
                self.update_log(f"  Gene-Excel-Filter: Keine Übereinstimmung")

        keep_paper = (result_local or result_perplexity or result_deepseek or result_chatgpt or result_extra or result_gene_excel)
        self.update_log(f"Ergebnis Filter für '{paper.get('Title','')}' -> {keep_paper}")
        return keep_paper

    def filter_with_perplexity(self, url, abstract_text):
        api_url = "https://api.perplexity.ai/chat/completions"
        context_snippet = abstract_text[:500]
        payload = {
            "model": "sonar",
            "frequency_penalty": 0.1,
            "max_tokens": 1000,
            "return_images": True,
            "return_related_questions": True,
            "search_recency_filter": "hour",
            "stream": False,
            "temperature": 0,
            "top_k": 0,
            "top_p": 1,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Bitte prüfe anhand des folgenden Abstract-Ausschnitts "
                        f"und ggf. der Seite {url} (wenn frei zugänglich), "
                        f"ob Informationen zu Genotype, Phenotype oder SNP enthalten sind. "
                        f"Abstract-Auszug:\n{context_snippet}\n\n"
                        f"Antworte mit JA oder NEIN."
                    )
                }
            ]
        }
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                answer = data.get("choices", [{}])[0].get("message", {}).get("content", "").lower()
                return "ja" in answer
            else:
                self.update_log(f"Perplexity API Fehler: {response.status_code} - {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            self.update_log(f"Perplexity API Fehler: {e}")
            return False

    def filter_with_deepseek(self, url, abstract_text):
        api_url = "https://api.deepseek.ai/chat/completions"
        context_snippet = abstract_text[:500]
        payload = {
            "model": "deep-model-v1",
            "max_tokens": 1000,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Überprüfe diese Infos (Abstract-Ausschnitt + Seite {url}) "
                        f"auf Genotype, Phenotype oder SNP:\n"
                        f"{context_snippet}\n\n"
                        f"Antworte mit JA oder NEIN."
                    )
                }
            ]
        }
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                answer = data.get("choices", [{}])[0].get("message", {}).get("content", "").lower()
                return "ja" in answer
            else:
                self.update_log(f"DeepSeek API Fehler: {response.status_code} - {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            self.update_log(f"DeepSeek API Fehler: {e}")
            return False

    def filter_with_chatgpt(self, url, criteria_list, abstract_text):
        try:
            snippet = abstract_text[:1000]
            criteria_str = ", ".join(criteria_list)
            prompt = (
                f"Analysiere diesen Textauszug (Abstract) und ggf. die Seite {url}, "
                f"um festzustellen, ob es Informationen über {criteria_str} gibt. "
                f"Antworte mit 'Yes' oder 'No'.\n\nText: {snippet}"
            )
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            answer = response.choices[0].message.content.strip().lower()
            return "yes" in answer
        except Exception as e:
            self.update_log(f"ChatGPT API Fehler: {e}")
            return False

    def search_europe_pmc(self, base_query):
        q = base_query
        if self.search_pop:
            q += " OR popul"
        if self.search_year:
            raw_year = self.search_year.split(':')[0]
            q += f" AND PUB_YEAR:{raw_year}"
        if self.search_journal:
            q += f' AND JOURNAL:"{self.search_journal}"'
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        params = {"query": q, "format": "json", "pageSize": 1000, "resultType": "core"}
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if "resultList" not in data or "result" not in data["resultList"]:
                return
            for item in data["resultList"]["result"]:
                title = item.get("title", "n/a")
                authors = item.get("authorString", "n/a")
                journ = item.get("journalTitle", "n/a")
                year = item.get("pubYear", "n/a")
                pmid = item.get("pmid", "n/a")
                pmcid = item.get("pmcid", "")
                doi = item.get("doi", "")
                abstract_text = item.get("abstractText", "")
                if pmcid:
                    if not pmcid.startswith("PMC"):
                        pmcid = "PMC" + pmcid
                    url_article = f"https://europepmc.org/articles/{pmcid}"
                elif pmid:
                    url_article = f"https://europepmc.org/article/MED/{pmid}"
                elif doi:
                    url_article = f"https://doi.org/{doi}"
                else:
                    url_article = f"https://europepmc.org/search?query={title}"
                self.all_results.append({
                    "Source": "Europe PMC",
                    "Title": title,
                    "Authors/Description": authors,
                    "Journal/Organism": journ,
                    "Year": year,
                    "PMID": pmid,
                    "DOI": doi,
                    "URL": url_article,
                    "Abstract": abstract_text
                })
        except Exception as e:
            messagebox.showerror("Fehler", f"Europe PMC: {e}")
            self.update_log(f"Europe PMC Error: {e}")

    def search_pubmed(self, base_query):
        q = f"({base_query})"
        if self.search_pop:
            q += " OR population"
        if self.search_year:
            q += f" AND {self.search_year}"
        if self.search_journal:
            q += f' AND "{self.search_journal}"[journal]'
        esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {"db": "pubmed", "term": q, "retmode": "json", "retmax": 0}
        try:
            r = self.pubmed_session.get(esearch_url, params=params, timeout=10)
            r.raise_for_status()
            js = r.json()
            total_str = js.get("esearchresult", {}).get("count", "0")
            total = int(total_str)
            if total == 0:
                return
            max_to_fetch = min(total, 1000)
            step = 100
            fetched = 0
            all_ids = []
            while fetched < max_to_fetch:
                retmax = step
                retstart = fetched
                if (fetched + step) > max_to_fetch:
                    retmax = max_to_fetch - fetched
                block_params = {
                    "db": "pubmed",
                    "term": q,
                    "retmode": "json",
                    "retmax": retmax,
                    "retstart": retstart
                }
                block_resp = self.pubmed_session.get(esearch_url, params=block_params, timeout=10)
                block_resp.raise_for_status()
                block_data = block_resp.json()
                block_ids = block_data.get("esearchresult", {}).get("idlist", [])
                if not block_ids:
                    break
                all_ids.extend(block_ids)
                fetched += len(block_ids)
                if len(block_ids) < retmax:
                    break
            if not all_ids:
                return
            esummary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            step_sum = 100
            idx = 0
            while idx < len(all_ids):
                subset = all_ids[idx:idx + step_sum]
                idx += step_sum
                id_str = ",".join(subset)
                sum_params = {"db": "pubmed", "id": id_str, "retmode": "json"}
                sum_resp = self.pubmed_session.get(esummary_url, params=sum_params, timeout=10)
                sum_resp.raise_for_status()
                sum_data = sum_resp.json()
                for uid in subset:
                    summ = sum_data.get("result", {}).get(uid, {})
                    if not summ:
                        continue
                    title = summ.get("title", "n/a")
                    authors_list = summ.get("authors", [])
                    authors = ", ".join(a.get("name", "") for a in authors_list)
                    journ = summ.get("fulljournalname", "n/a")
                    pub_date = summ.get("pubdate", "n/a")[:4]
                    pmid = summ.get("uid", "n/a")
                    doi = summ.get("elocationid", "n/a")
                    url_article = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    abstract_text = self._fetch_pubmed_abstract(pmid)
                    self.all_results.append({
                        "Source": "PubMed",
                        "Title": title,
                        "Authors/Description": authors,
                        "Journal/Organism": journ,
                        "Year": pub_date,
                        "PMID": pmid,
                        "DOI": doi,
                        "URL": url_article,
                        "Abstract": abstract_text
                    })
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Fehler", f"PubMed-Verbindungsfehler:\n{e}")
            self.update_log(f"PubMed Error: {e}")

    def search_pubmed_ids(self):
        self.pubmed_id_search = True
        ids_input = self.pubmed_id_entry.get().strip()
        if not ids_input:
            messagebox.showwarning("Hinweis", "Bitte mindestens eine PubMed-ID eingeben!")
            return
        pubmed_ids = [pmid.strip() for pmid in ids_input.split(',')]
        self.all_results.clear()
        for ch in self.left_tree.get_children():
            self.left_tree.delete(ch)
        for pmid in pubmed_ids:
            self.search_pubmed_id(pmid)
        self._display_page()

    def search_pubmed_id(self, pmid):
        esummary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        params = {"db": "pubmed", "id": pmid, "retmode": "json"}
        try:
            response = self.pubmed_session.get(esummary_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if "result" in data and pmid in data["result"]:
                summ = data["result"][pmid]
                title = summ.get("title", "n/a")
                authors_list = summ.get("authors", [])
                authors = ", ".join([a.get("name", "") for a in authors_list])
                journal = summ.get("fulljournalname", "n/a")
                pubdate = summ.get("pubdate", "n/a")
                year = pubdate[:4] if pubdate != "n/a" else "n/a"
                doi = summ.get("elocationid", "n/a")
                url_article = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                abstract_text = self._fetch_pubmed_abstract(pmid)
                self.all_results.append({
                    "Source": "PubMed (ID-Suche)",
                    "Title": title,
                    "Authors/Description": authors,
                    "Journal/Organism": journal,
                    "Year": year,
                    "PMID": pmid,
                    "DOI": doi,
                    "URL": url_article,
                    "Abstract": abstract_text
                })
            else:
                messagebox.showwarning("Warnung", f"Keine Daten für PubMed ID {pmid} gefunden.")
                self.update_log(f"PubMed ID {pmid}: keine Daten gefunden.")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Fehler", f"Fehler beim Abrufen der PubMed ID {pmid}:\n{e}")
            self.update_log(f"PubMed ID Error: {e}")

    def search_openalex(self, base_query):
        url = f"https://api.openalex.org/works?filter=title.search:{base_query}&sort=cited_by_count:desc&per-page=25"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            results = data.get("results", [])
            for work in results:
                title = work.get("title", "n/a")
                auths = work.get("authorships", [])
                authors = ", ".join(a["author"]["display_name"] for a in auths[:3])
                if len(auths) > 3:
                    authors += " et al."
                year = work.get("publication_year", "n/a")
                doi = work.get("doi", "n/a")
                url_article = "n/a"
                if doi != "n/a":
                    url_article = "https://doi.org/" + doi.replace("https://doi.org/", "")
                host_venue = work.get("host_venue", {})
                journ = host_venue.get("display_name", "n/a") if host_venue else "n/a"
                abstract_text = work.get("abstract", "")
                self.all_results.append({
                    "Source": "OpenAlex",
                    "Title": title,
                    "Authors/Description": authors,
                    "Journal/Organism": journ,
                    "Year": str(year),
                    "PMID": "n/a",
                    "DOI": doi,
                    "URL": url_article,
                    "Abstract": abstract_text
                })
        except Exception as e:
            messagebox.showerror("Fehler", f"OpenAlex: {e}")
            self.update_log(f"OpenAlex Error: {e}")

    def search_google_scholar(self, base_query):
        try:
            from scholarly import scholarly
            search_results = scholarly.search_pubs(base_query)
            for _ in range(5):
                result = next(search_results)
                title = result['bib'].get('title', "n/a")
                authors = result['bib'].get('author', "n/a")
                year = result['bib'].get('pub_year', "n/a")
                url_article = result.get('url_scholarbib', "n/a")
                abstract_text = result['bib'].get('abstract', "")
                self.all_results.append({
                    "Source": "Google Scholar",
                    "Title": title,
                    "Authors/Description": authors,
                    "Journal/Organism": "n/a",
                    "Year": year,
                    "PMID": "n/a",
                    "DOI": "n/a",
                    "URL": url_article,
                    "Abstract": abstract_text
                })
        except Exception as e:
            messagebox.showerror("Fehler", f"Google Scholar: {e}")
            self.update_log(f"Google Scholar Error: {e}")

    def search_semantic_scholar(self, base_query):
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
            params = {"query": base_query, "limit": 5, "fields": "title,authors,year,abstract,doi,paperId"}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            for paper in data.get("data", []):
                title = paper.get("title", "n/a")
                authors = ", ".join([author.get("name", "") for author in paper.get("authors", [])])
                year = paper.get("year", "n/a")
                doi = paper.get("doi", "n/a")
                paper_id = paper.get("paperId", "")
                abstract_text = paper.get("abstract", "")
                url_article = f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else "n/a"
                self.all_results.append({
                    "Source": "Semantic Scholar",
                    "Title": title,
                    "Authors/Description": authors,
                    "Journal/Organism": "n/a",
                    "Year": year,
                    "PMID": "n/a",
                    "DOI": doi,
                    "URL": url_article,
                    "Abstract": abstract_text
                })
        except Exception as e:
            messagebox.showerror("Fehler", f"Semantic Scholar: {e}")
            self.update_log(f"Semantic Scholar Error: {e}")

    def search_core_aggregate(self, base_query):
        API_KEY = "LmAMxdYnK6SDJsPRQCpGgwN7f5yTUBHF"
        core = CoreAPI(API_KEY)
        filters = {"yearPublished": ">=2020,<=2024", "language.name": "English"}
        sort = "citationCount:desc"
        limit = 5
        try:
            result = core.search_publications(query=base_query, filters=filters, sort=sort, limit=limit)
            if result and "results" in result:
                for pub in result["results"]:
                    title = pub.get("title", "n/a")
                    doi = pub.get("doi", "n/a")
                    year = pub.get("yearPublished", "n/a")
                    authors = ", ".join(pub.get("authors", []))
                    downloadUrl = pub.get("downloadUrl", "n/a")
                    abstract = pub.get("abstract", "")
                    publisher = pub.get("publisher", "n/a")
                    self.all_results.append({
                        "Source": "CORE Aggregate",
                        "Title": title,
                        "Authors/Description": authors,
                        "Journal/Organism": publisher,
                        "Year": year,
                        "PMID": "n/a",
                        "DOI": doi,
                        "URL": downloadUrl,
                        "Abstract": abstract
                    })
        except Exception as e:
            messagebox.showerror("Fehler", f"CORE Aggregate: {e}")
            self.update_log(f"CORE Aggregate Error: {e}")

    def search_ensembl_direct(self):
        species_val = self.ensembl_species_var.get().strip()
        gene_val = self.ensembl_gene_var.get().strip()
        if not species_val or not gene_val:
            messagebox.showwarning("Fehler", "Bitte Species und Gene eingeben!")
            return
        self.all_results.clear()
        self.current_page = 0
        for ch in self.left_tree.get_children():
            self.left_tree.delete(ch)
        self._search_ensembl_api(species_val, gene_val)
        self._display_page()

    def _search_ensembl_api(self, species, gene):
        base_url = "https://rest.ensembl.org"
        endpoint = f"/lookup/symbol/{species}/{gene}"
        headers = {"Content-Type": "application/json"}
        try:
            resp = requests.get(base_url + endpoint, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            desc_str = f"chr: {data.get('seq_region_name', 'n/a')}, strand: {data.get('strand', 'n/a')}"
            ensembl_url = f"https://www.ensembl.org/{species}/Gene/Summary?g={data.get('id','')}"
            self.all_results.append({
                "Source": "Ensembl REST",
                "Title": data.get("display_name", gene),
                "Authors/Description": desc_str,
                "Journal/Organism": data.get("species", "n/a"),
                "Year": "n/a",
                "PMID": "n/a",
                "DOI": "n/a",
                "URL": ensembl_url,
                "Abstract": ""
            })
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Fehler", f"Ensembl REST: {e}")
            self.update_log(f"Ensembl Error: {e}")

    def search_uniprot_direct(self):
        protein_name = self.uniprot_protein_var.get().strip()
        if not protein_name:
            messagebox.showwarning("Hinweis", "Bitte Protein auswählen oder manuell eingeben!")
            return
        self.all_results.clear()
        self.current_page = 0
        for ch in self.left_tree.get_children():
            self.left_tree.delete(ch)
        self._search_uniprot(protein_name)
        self._display_page()

    def _search_uniprot(self, protein):
        try:
            url_search = f"https://rest.uniprot.org/uniprotkb/search?query={protein}&format=json&size=1"
            resp1 = requests.get(url_search, timeout=10)
            resp1.raise_for_status()
            data_search = resp1.json()
            results = data_search.get("results", [])
            if not results:
                return
            accession = results[0].get("primaryAccession", "")
            if not accession:
                return
            url_detail = f"https://rest.uniprot.org/uniprotkb/{accession}.json"
            resp2 = requests.get(url_detail, timeout=10)
            resp2.raise_for_status()
            data_detail = resp2.json()
            protein_name = data_detail.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", "n/a")
            organism = data_detail.get("organism", {}).get("scientificName", "n/a")
            seq_len = data_detail.get("sequence", {}).get("length", "n/a")
            url_article = f"https://www.uniprot.org/uniprotkb/{accession}"
            authors_description = f"Organismus: {organism}; Länge: {seq_len}"
            self.all_results.append({
                "Source": "UniProt",
                "Title": protein_name,
                "Authors/Description": authors_description,
                "Journal/Organism": organism,
                "Year": "n/a",
                "PMID": "n/a",
                "DOI": "n/a",
                "URL": url_article,
                "Abstract": ""
            })
        except Exception as e:
            messagebox.showerror("Fehler", f"UniProt: {e}")
            self.update_log(f"UniProt Error: {e}")

    def search_dbsnp_direct(self):
        rs_id = self.dbsnp_rs_entry.get().strip()
        if not rs_id:
            messagebox.showwarning("Fehler", "Bitte eine RS-ID eingeben!")
            return
        YOUR_EMAIL = "erwin.schimak@novogenia.com"
        API_KEY = "7c60b310bfd435eed965f2b203f4a1900208"
        dbsnp = DBSnpAPI(email=YOUR_EMAIL, api_key=API_KEY)
        result = dbsnp.get_snp_info(rs_id)
        if result:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, "Detaillierte SNP-Informationen", ln=True, align="C")
            pdf.ln(10)
            for key, value in result.items():
                if isinstance(value, list):
                    value_str = ", ".join(value)
                else:
                    value_str = str(value)
                pdf.cell(0, 10, f"{key}: {value_str}", ln=True)
            pdf_filename = f"dbSNP_{rs_id}.pdf"
            pdf.output(pdf_filename)
            self.update_log(f"dbSNP PDF erstellt: {pdf_filename}")
            try:
                webbrowser.open(pdf_filename)
            except Exception as e:
                self.update_log(f"Öffnen PDF Fehler: {e}")
        else:
            messagebox.showinfo("Ergebnis", "Keine Informationen gefunden.")
            self.update_log("dbSNP: Keine Informationen gefunden.")

    def show_abstract_popup(self, event):
        sel = self.left_tree.selection()
        if not sel:
            return
        item_id = self.left_tree.item(sel[0], "values")
        source, title, authors, _, _, pmid, _, _ = item_id
        paper = None
        for p in self.all_results:
            if p["Title"] == title and p.get("PMID", None) == pmid:
                paper = p
                break
        if paper is None:
            abstract_text = "(Kein Abstract verfügbar)"
        else:
            abstract_text = paper.get("Abstract", "(Kein Abstract verfügbar)")
        popup = tk.Toplevel(self.root)
        popup.title("Paper-Details")
        tk.Label(popup, text=f"Titel: {title}", font=("Arial", 11, "bold")).pack(anchor="w", padx=10, pady=5)
        tk.Label(popup, text=f"Autoren: {authors}", font=("Arial", 10)).pack(anchor="w", padx=10, pady=5)
        st = scrolledtext.ScrolledText(popup, wrap="word", width=80, height=15)
        st.pack(fill="both", expand=True, padx=10, pady=5)
        st.insert("1.0", abstract_text)
        st.config(state="disabled")

    def _fetch_pubmed_abstract(self, pmid):
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params = {"db": "pubmed", "id": pmid, "retmode": "xml"}
        try:
            r = self.pubmed_session.get(url, params=params, timeout=10)
            r.raise_for_status()
            root = ET.fromstring(r.content)
            abs_text = ""
            for elem in root.findall(".//AbstractText"):
                if elem.text:
                    abs_text += (elem.text + "\n")
            if not abs_text.strip():
                abs_text = "(Kein Abstract via eFetch)"
            return abs_text.strip()
        except Exception as e:
            return f"(Fehler eFetch: {e})"

    def _get_esummary_data(self, pmid):
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        params = {"db": "pubmed", "id": pmid, "retmode": "json"}
        out = {}
        try:
            r = self.pubmed_session.get(url, params=params, timeout=10)
            r.raise_for_status()
            js = r.json()
            results = js.get("result", {})
            if pmid in results:
                summ = results[pmid]
                out["Title"] = summ.get("title", "n/a")
                out["FullJournalName"] = summ.get("fulljournalname", "n/a")
                out["PubDate"] = summ.get("pubdate", "n/a")
                auth_list = summ.get("authors", [])
                auth_str = ", ".join(a.get("name", "") for a in auth_list)
                out["Authors"] = auth_str
                out["DOI"] = summ.get("elocationid", "n/a")
            else:
                out["Error"] = "Keine eSummary Daten"
        except Exception as e:
            out["Error"] = f"Fehler eSummary: {e}"
        return out

    def auto_select_papers(self):
        pop_checked = self.var_populationsgroesse.get()
        chosen_year = self.year_var.get()
        chosen_journal_label = self.journal_var.get()
        chosen_journal_title = ""
        if chosen_journal_label and chosen_journal_label in self.journal_lookup:
            chosen_journal_title = self.journal_lookup[chosen_journal_label]
        for item_id in self.left_tree.get_children():
            vals = self.left_tree.item(item_id, "values")
            if self._is_item_in_tree(self.right_tree, vals):
                continue
            if pop_checked:
                text_concat = (vals[1] + " " + vals[2]).lower()
                if "popul" not in text_concat:
                    continue
            if chosen_year:
                if vals[4] != chosen_year:
                    continue
            if chosen_journal_title:
                if vals[3].lower() != chosen_journal_title.lower():
                    continue
            self.right_tree.insert("", tk.END, values=vals)

    def add_selected_papers(self):
        sel = self.left_tree.selection()
        for s in sel:
            vals = self.left_tree.item(s, "values")
            if not self._is_item_in_tree(self.right_tree, vals):
                self.right_tree.insert("", tk.END, values=vals)

    def remove_selected_papers(self):
        sel = self.right_tree.selection()
        for s in sel:
            self.right_tree.delete(s)

    def _is_item_in_tree(self, tree, values):
        for child in tree.get_children():
            if tree.item(child, "values") == values:
                return True
        return False

    def next_page(self):
        max_page = (len(self.all_results) - 1) // self.page_size
        if self.current_page < max_page:
            self.current_page += 1
            self._display_page()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._display_page()

    def _display_page(self):
        for row_id in self.left_tree.get_children():
            self.left_tree.delete(row_id)
        start_idx = self.current_page * self.page_size
        end_idx = start_idx + self.page_size
        page_items = self.all_results[start_idx:end_idx]
        for res in page_items:
            vals = (
                res.get("Source", ""),
                res.get("Title", ""),
                res.get("Authors/Description", ""),
                res.get("Journal/Organism", ""),
                res.get("Year", ""),
                res.get("PMID", ""),
                res.get("DOI", ""),
                res.get("URL", "")
            )
            self.left_tree.insert("", tk.END, values=vals)
        total_count = len(self.all_results)
        if total_count > 0:
            self.found_frame.config(bg="green")
            self.total_label.config(text=f"Insgesamt {total_count} Paper gefunden (Seite {self.current_page+1})", bg="green", fg="white")
        else:
            self.found_frame.config(bg="red")
            self.total_label.config(text="Insgesamt 0 Paper gefunden", bg="red", fg="white")

    def download_papers(self):
        selected_items = self.right_tree.get_children()
        if not selected_items:
            messagebox.showwarning("Hinweis", "Bitte mindestens ein Paper auswählen.")
            return
        storage_dir = filedialog.askdirectory(title="Speicherort für PDFs und Excel-Dateien")
        if not storage_dir:
            messagebox.showwarning("Hinweis", "Kein Speicherort ausgewählt.")
            return
        curr = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if self.pubmed_id_search:
            folder_name = f"PubMedID_Search_{curr}"
        else:
            query = self.get_query_string()
            folder_name = f"{query}_{curr}" if query else f"Ergebnisse_{curr}"
        output_dir = os.path.join(storage_dir, folder_name)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            self.update_log(f"Ordner erstellt: {output_dir}")
        else:
            self.update_log(f"Ordner existiert bereits: {output_dir}")
        for sel in selected_items:
            vals = self.right_tree.item(sel, "values")
            result = {
                "Source": vals[0],
                "Title": vals[1],
                "Authors/Description": vals[2],
                "Journal/Organism": vals[3],
                "Year": vals[4],
                "PMID": vals[5],
                "DOI": vals[6],
                "URL": vals[7]
            }
            title = result.get("Title", "article")
            sanitized_title = self._sanitize_filename(title)
            abstract_pdf_filename = f"{sanitized_title}_abstract.pdf"
            webpage_pdf_filename = f"{sanitized_title}_webpage_chrome.pdf"
            abstract_pdf_path = os.path.join(output_dir, abstract_pdf_filename)
            webpage_pdf_path = os.path.join(output_dir, webpage_pdf_filename)
            article_url = result.get("URL", "")
            pmid = result.get("PMID", "n/a")
            doi = result.get("DOI", "n/a")
            self._create_abstract_pdf(result, article_url, abstract_pdf_path)
            self.update_log(f"PDF erstellt: {abstract_pdf_path}")
            if article_url and article_url != "n/a":
                try:
                    time.sleep(5)
                    self._save_page_via_headless_chrome(article_url, webpage_pdf_path)
                    self.update_log(f"Webseite als PDF gespeichert: {webpage_pdf_path}")
                except Exception as e:
                    self.update_log(f"Fehler Chrome Headless: {e}")
                    messagebox.showerror("Fehler", f"Fehler beim Drucken der Webseite via Chrome Headless:\n{e}")
                    continue
            else:
                self.update_log("Keine gültige URL -> skip.")
                continue
            doi_links = self._extract_doi_links_from_pdf(webpage_pdf_path)
            if not doi_links and doi and doi != "n/a":
                doi_link = doi if doi.startswith("http") else f"https://doi.org/{doi}"
                if doi_link.startswith("https://doi.org/doi:"):
                    doi_link = doi_link.replace("https://doi.org/doi:", "https://doi.org/")
                doi_links.append(doi_link)
            if doi_links:
                for dl in doi_links:
                    sanitized_doi_filename = self._sanitize_filename(dl) + ".pdf"
                    doi_pdf_path = os.path.join(output_dir, sanitized_doi_filename)
                    try:
                        self._save_page_via_headless_chrome(dl, doi_pdf_path)
                        self.update_log(f"DOI-Link als PDF gespeichert: {doi_pdf_path}")
                        pdf_download_link = self._find_pdf_download_link(dl)
                        if pdf_download_link:
                            downloaded_pdf_filename = f"{sanitized_doi_filename[:-4]}_downloaded.pdf"
                            downloaded_pdf_path = os.path.join(output_dir, downloaded_pdf_filename)
                            self._download_pdf(pdf_download_link, downloaded_pdf_path)
                            self.update_log(f"Download PDF: {downloaded_pdf_path}")
                        else:
                            self.update_log(f"Kein direkter PDF-Download-Link: {dl}")
                    except Exception as e:
                        self.update_log(f"Fehler Druck DOI-Link: {e}")
                        messagebox.showerror("Fehler", f"Fehler beim Drucken des DOI-Links:\n{e}")
            else:
                self.update_log("Keine DOI-Links gefunden.")
            try:
                webbrowser.open(article_url)
            except Exception as e:
                self.update_log(f"Fehler Browser öffnen URL: {e}")
            if doi_links:
                for dl in doi_links:
                    try:
                        webbrowser.open(dl)
                    except Exception as e:
                        self.update_log(f"Fehler Browser öffnen DOI: {e}")
            details_entry = {
                "Download Name": abstract_pdf_filename,
                "Abstract": result.get("Authors/Description", ""),
                "PMID": pmid,
                "DOI": doi,
                "eSummary": "n/a"
            }
            self.excel_details.append(details_entry)
            main_entry = {
                "Title": title,
                "PMID": pmid,
                "DOI": doi
            }
            self.excel_main.append(main_entry)
            time.sleep(2)
        self._create_excel_files(output_dir)
        messagebox.showinfo("Fertig", "Alle ausgewählten Paper wurden verarbeitet.")
        self.update_log("Download + PDF-Erstellung beendet.")

    def _create_excel_files(self, output_dir):
        details_path = os.path.join(output_dir, "details.xlsx")
        wb_details = openpyxl.Workbook()
        ws_details = wb_details.active
        ws_details.title = "Details"
        headers_details = ["Download Name", "Abstract", "PMID", "DOI", "eSummary"]
        ws_details.append(headers_details)
        for entry in self.excel_details:
            row = [
                entry.get("Download Name", "n/a"),
                entry.get("Abstract", "n/a"),
                entry.get("PMID", "n/a"),
                entry.get("DOI", "n/a"),
                entry.get("eSummary", "n/a")
            ]
            ws_details.append(row)
        try:
            wb_details.save(details_path)
            self.update_log(f"Excel details.xlsx erstellt: {details_path}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern details.xlsx: {e}")
            self.update_log(f"Fehler details.xlsx: {e}")
        main_path = os.path.join(output_dir, "AllPapers.xlsx")
        wb = openpyxl.Workbook()
        ws_main = wb.active
        ws_main.title = "Main"
        headers_main = ["Title", "Year", "PMID", "DOI", "Abstract", "Link", "Populationsgröße?", "Journal"]
        ws_main.append(headers_main)
        selected_items = self.right_tree.get_children()
        for sel in selected_items:
            vals = self.right_tree.item(sel, "values")
            title = vals[1]
            year = vals[4]
            pmid = vals[5]
            doi = vals[6]
            abstract = vals[2]
            link = vals[7]
            pop_found = "Ja" if ("popul" in (vals[1] + " " + vals[2]).lower()) else "Nein"
            journal = vals[3]
            ws_main.append([title, year, pmid, doi, abstract, link, pop_found, journal])
            sheet_name = self._sanitize_filename(title)[:31]
            if sheet_name in wb.sheetnames:
                idx = 2
                orig = sheet_name
                while sheet_name in wb.sheetnames:
                    sheet_name = f"{orig}_{idx}"
                    idx += 1
            ws_detail = wb.create_sheet(title=sheet_name)
            ws_detail.append(["Titel", title])
            ws_detail.append(["Year", year])
            ws_detail.append(["PMID", pmid])
            ws_detail.append(["DOI", doi])
            ws_detail.append(["Journal", journal])
            ws_detail.append(["Populationsgröße?", pop_found])
            if pmid and pmid != "n/a":
                e_sum = self._get_esummary_data(pmid)
                e_abs = self._fetch_pubmed_abstract(pmid)
                ws_detail.append([])
                ws_detail.append(["** eSummary **", ""])
                for k, v in e_sum.items():
                    ws_detail.append([k, v])
                ws_detail.append([])
                ws_detail.append(["** eFetch Abstract **", e_abs])
            else:
                ws_detail.append([])
                ws_detail.append(["(Keine PMID, daher keine eSummary/eFetch-Daten verfügbar)"])
        try:
            wb.save(main_path)
            self.update_log(f"Excel AllPapers.xlsx erstellt: {main_path}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern AllPapers.xlsx: {e}")
            self.update_log(f"Fehler AllPapers.xlsx: {e}")

    def open_article_page(self):
        sel = self.right_tree.get_children()
        if not sel:
            messagebox.showwarning("Hinweis", "Bitte mindestens eine Zeile auswählen.")
            return
        for s in sel:
            vals = self.right_tree.item(s, "values")
            url = vals[7]
            if "search?query=" in url:
                messagebox.showinfo("Info", "Keine pmcid/pmid/doi -> Europe PMC-Suche.")
            elif url == "n/a" or not url:
                messagebox.showinfo("Info", "Keine URL.")
                continue
            try:
                webbrowser.open(url)
            except Exception as e:
                self.update_log(f"Fehler open URL: {e}")

    def execute_selected_modules(self):
        messagebox.showinfo("Info", "Ausgewählte Module ausgeführt.")
        self.update_log("Module ausgeführt.")

    def _save_page_via_headless_chrome(self, url, output_pdf):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
        prefs = {
            "download.default_directory": os.path.dirname(output_pdf),
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        with webdriver.Chrome(options=chrome_options) as driver:
            driver.get(url)
            try:
                WebDriverWait(driver, 20).until(lambda d: d.execute_script("return document.readyState") == "complete")
            except TimeoutException:
                self.update_log(f"Timeout Laden: {url}")
            time.sleep(5)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            try:
                pdf_data = driver.execute_cdp_cmd("Page.printToPDF", {"printBackground": True, "paperWidth": 8.27, "paperHeight": 11.69})
                pdf_bytes = base64.b64decode(pdf_data["data"])
                with open(output_pdf, "wb") as f:
                    f.write(pdf_bytes)
            except Exception as e:
                self.update_log(f"Chrome printToPDF Fehler: {e}")

    def _create_abstract_pdf(self, result, article_url, output_file):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        try:
            pdf.add_font(self.font_name, "", self.font_file, uni=True)
            pdf.set_font(self.font_name, "", 12)
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler Schriftart: {e}")
            return
        page_width = pdf.w - pdf.l_margin - pdf.r_margin
        title_txt = f"** Titel **\n{result.get('Title', 'Keine Angabe')}"
        pdf.multi_cell(page_width, 10, self._wrap_long_words(title_txt))
        pdf.ln(5)
        desc = result.get("Authors/Description", "") or "Keine Beschreibung verfügbar."
        desc_txt = f"** Abstract/Description **\n{desc}"
        pdf.multi_cell(page_width, 10, self._wrap_long_words(desc_txt))
        pdf.ln(5)
        url_txt = "** URL **\n" + article_url
        pdf.multi_cell(page_width, 8, self._wrap_long_words(url_txt))
        pdf.ln(5)
        pdf.cell(0, 10, "** Metadaten **", ln=1)
        for key, val in result.items():
            if key in ["Source", "Title", "Authors/Description", "Journal/Organism", "Year", "URL"]:
                continue
            line = f"{key}: {str(val)}"
            pdf.multi_cell(page_width, 6, self._wrap_long_words(line))
        try:
            pdf.output(output_file)
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern PDF: {e}")

    def _wrap_long_words(self, text, max_len=80):
        words = text.split()
        result = []
        while words:
            w = words.pop(0)
            while len(w) > max_len:
                result.append(w[:max_len])
                w = w[max_len:]
            result.append(w)
        return " ".join(result)

    def _sanitize_filename(self, filename):
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for c in invalid_chars:
            filename = filename.replace(c, '_')
        return filename

    def _extract_doi_links_from_pdf(self, pdf_path):
        doi_links = []
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                text = page.get_text()
                matches = re.findall(r'(https?://(?:dx\.)?doi\.org/\S+)', text)
                for m in matches:
                    if m not in doi_links:
                        doi_links.append(m.strip())
            doc.close()
        except Exception as e:
            self.update_log(f"Fehler PyMuPDF: {e}")
        return doi_links

    def _find_pdf_download_link(self, url):
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            match = re.search(r'href=["\']([^"\']+\.pdf)["\']', r.text, re.IGNORECASE)
            if match:
                link = match.group(1)
                if link.startswith("/"):
                    from urllib.parse import urljoin
                    link = urljoin(url, link)
                return link
            return None
        except Exception as e:
            self.update_log(f"Fehler PDF-Link: {e}")
            return None

    def _download_pdf(self, pdf_url, output_path):
        try:
            r = requests.get(pdf_url, timeout=10)
            r.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(r.content)
        except Exception as e:
            self.update_log(f"Fehler PDF-Download: {e}")

    def create_complete_excel_list(self):
        selected_items = self.right_tree.get_children()
        if not selected_items:
            messagebox.showwarning("Hinweis", "Bitte mindestens ein Paper auswählen.")
            return
        storage_dir = filedialog.askdirectory(title="Speicherort für Excel-Dateien")
        if not storage_dir:
            messagebox.showwarning("Hinweis", "Kein Speicherort gewählt.")
            return
        curr = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if self.pubmed_id_search:
            folder_name = f"PubMedID_Search_{curr}"
        else:
            query = self.get_query_string()
            folder_name = f"{query}_{curr}" if query else f"Ergebnisse_{curr}"
        output_dir = os.path.join(storage_dir, folder_name)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            self.update_log(f"Ordner erstellt: {output_dir}")
        else:
            self.update_log(f"Ordner existiert bereits: {output_dir}")
        self._create_excel_files(output_dir)
        messagebox.showinfo("Fertig", "Die komplette Excel-Liste wurde erstellt.")
        self.update_log("Komplette Excel-Liste erstellt.")


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
