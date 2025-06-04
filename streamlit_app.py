import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import re
import datetime
import sys
import concurrent.futures
import os
import PyPDF2
import openai
import time
import json
import pdfplumber
import io
import subprocess
import threading

from typing import Dict, Any, Optional
from dotenv import load_dotenv
from PIL import Image
from scholarly import scholarly

# Neu: Excel / openpyxl-Import
import openpyxl

# Neuer Import für die Übersetzung mit google_trans_new
from google_trans_new import google_translator

# NEU: Imports für lokale API
import httpx

# ------------------------------------------------------------------
# Umgebungsvariablen laden (für OPENAI_API_KEY, falls vorhanden)
# ------------------------------------------------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ------------------------------------------------------------------
# Streamlit-Konfiguration
# ------------------------------------------------------------------
st.set_page_config(page_title="Streamlit Multi-Modul Demo mit lokaler API", layout="wide")

# ------------------------------------------------------------------
# NEU: Lokale API-Konfiguration
# ------------------------------------------------------------------
LOCAL_API_URL = "http://localhost:8000"

# ------------------------------------------------------------------
# NEU: Lokale API Funktionen
# ------------------------------------------------------------------
def check_local_api_status():
    """Überprüft Status der lokalen API"""
    try:
        response = requests.get(f"{LOCAL_API_URL}/health", timeout=2)
        if response.status_code == 200:
            return True, response.json()
        return False, None
    except:
        return False, None

def start_local_api():
    """Startet die lokale API im Hintergrund"""
    try:
        # Startet local_api.py als subprocess
        subprocess.Popen([sys.executable, "local_api.py"], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        time.sleep(3)  # Wartezeit für API-Start
        return True
    except Exception as e:
        st.error(f"Fehler beim Starten der lokalen API: {e}")
        return False

def upload_paper_to_api(file_content, filename):
    """Lädt Paper zur lokalen API hoch"""
    try:
        files = {"file": (filename, file_content, "application/pdf")}
        response = requests.post(f"{LOCAL_API_URL}/upload_paper", files=files, timeout=30)
        if response.status_code == 200:
            return True, response.json()
        return False, response.text
    except Exception as e:
        return False, str(e)

def ask_api_question(question, top_k=3):
    """Stellt Frage an die lokale API"""
    try:
        data = {"question": question, "top_k": top_k}
        response = requests.post(f"{LOCAL_API_URL}/ask_question", json=data, timeout=15)
        if response.status_code == 200:
            return True, response.json()
        return False, response.text
    except Exception as e:
        return False, str(e)

# ------------------------------------------------------------------
# Login-Funktionalität (unverändert)
# ------------------------------------------------------------------
def login():
    st.title("Login")
    user_input = st.text_input("Username")
    pass_input = st.text_input("Password", type="password")
    if st.button("Login"):
        if (
            user_input == st.secrets["login"]["username"]
            and pass_input == st.secrets["login"]["password"]
        ):
            st.session_state["logged_in"] = True
        else:
            st.error("Login failed. Please check your credentials!")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login()
    st.stop()

# ------------------------------------------------------------------
# NEU: Seite für Lokale API Paper QA
# ------------------------------------------------------------------
def page_local_api_paper_qa():
    """Neue Seite für lokale API Paper QA"""
    st.title("🤖 Lokale API Paper QA System")
    
    # API-Status überprüfen
    api_online, api_status = check_local_api_status()
    
    # Status-Anzeige
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if api_online:
            st.success("🟢 Lokale API ist online und bereit")
            if api_status:
                st.info(f"Modell geladen: {'✅' if api_status.get('model_loaded') else '❌'}")
                st.info(f"Dokumente geladen: {'✅' if api_status.get('documents_loaded') else '❌'}")
        else:
            st.error("🔴 Lokale API ist offline")
            if st.button("🚀 Lokale API starten"):
                with st.spinner("Starte lokale API..."):
                    if start_local_api():
                        st.success("API wird gestartet... Bitte warten Sie einen Moment und laden Sie die Seite neu.")
                    else:
                        st.error("Fehler beim Starten der API")
    
    if not api_online:
        st.warning("⚠️ Die lokale API muss gestartet werden, um diese Funktion zu nutzen.")
        return
    
    # Paper Upload Bereich
    st.header("📄 Paper Upload")
    
    uploaded_file = st.file_uploader(
        "PDF-Paper hochladen",
        type=['pdf'],
        help="Laden Sie ein wissenschaftliches Paper im PDF-Format hoch"
    )
    
    if uploaded_file is not None:
        st.info(f"📁 Datei: {uploaded_file.name} ({uploaded_file.size} Bytes)")
        
        if st.button("🔄 Paper verarbeiten"):
            with st.spinner("Verarbeite Paper mit lokaler API..."):
                file_content = uploaded_file.read()
                success, result = upload_paper_to_api(file_content, uploaded_file.name)
                
                if success:
                    st.success("✅ Paper erfolgreich hochgeladen und verarbeitet!")
                    st.json(result)
                    st.session_state["paper_loaded_api"] = True
                    st.session_state["current_paper_name"] = uploaded_file.name
                else:
                    st.error(f"❌ Fehler beim Hochladen: {result}")
    
    # Fragen-Bereich
    if st.session_state.get("paper_loaded_api", False):
        st.header("❓ Fragen zum Paper")
        
        current_paper = st.session_state.get("current_paper_name", "Unbekannt")
        st.info(f"📖 Aktuelles Paper: {current_paper}")
        
        question = st.text_area(
            "Ihre Frage:",
            placeholder="Z.B.: Was sind die Hauptergebnisse dieser Studie?",
            height=100
        )
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button("🎯 Frage stellen", disabled=not question.strip()):
                with st.spinner("Verarbeite Frage..."):
                    success, result = ask_api_question(question.strip())
                    
                    if success:
                        st.subheader("🤖 Antwort:")
                        st.write(result["answer"])
                        
                        if result.get("sources"):
                            st.subheader("📚 Quellen:")
                            for source in result["sources"]:
                                st.write(f"• {source}")
                        
                        # Speichere Antwort für Excel-Export
                        if "api_qa_results" not in st.session_state:
                            st.session_state["api_qa_results"] = []
                        
                        st.session_state["api_qa_results"].append({
                            "paper": current_paper,
                            "question": question,
                            "answer": result["answer"],
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                    else:
                        st.error(f"❌ Fehler bei der Fragestellung: {result}")
        
        with col2:
            top_k = st.selectbox("Top K Ergebnisse:", [1, 3, 5], index=1)
    
    # Excel Export
    if st.session_state.get("api_qa_results"):
        st.header("📊 Excel Export")
        
        if st.button("📥 Ergebnisse nach Excel exportieren"):
            try:
                # Erstelle Excel-Datei
                df = pd.DataFrame(st.session_state["api_qa_results"])
                
                # Excel-Buffer
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='API_QA_Results', index=False)
                
                excel_buffer.seek(0)
                
                # Download-Button
                st.download_button(
                    label="📁 Excel-Datei herunterladen",
                    data=excel_buffer.getvalue(),
                    file_name=f"local_api_qa_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                st.success("✅ Excel-Datei erstellt!")
                
            except Exception as e:
                st.error(f"❌ Fehler beim Excel-Export: {e}")
        
        # Aktuelle Ergebnisse anzeigen
        st.subheader("📋 Aktuelle QA-Ergebnisse:")
        st.dataframe(pd.DataFrame(st.session_state["api_qa_results"]))
        
        if st.button("🗑️ Ergebnisse löschen"):
            st.session_state["api_qa_results"] = []
            st.rerun()

# ------------------------------------------------------------------
# 1) Gemeinsame Funktionen & Klassen (UNVERÄNDERT)
# ------------------------------------------------------------------
def clean_html_except_br(text):
    """Removes all HTML tags except <br>."""
    cleaned_text = re.sub(r'</?(?!br\b)[^>]*>', '', text)
    return cleaned_text

def translate_text_openai(text, source_language, target_language, api_key):
    """Übersetzt Text über OpenAI-ChatCompletion."""
    import openai
    openai.api_key = api_key
    prompt_system = (
        f"You are a translation engine from {source_language} to {target_language} for a biotech company called Novogenia "
        f"that focuses on lifestyle and health genetics and health analyses. The outputs you provide will be used directly as "
        f"the translated text blocks. Please translate as accurately as possible in the context of health and lifestyle reporting. "
        f"If there is no appropriate translation, the output should be 'TBD'. Keep the TAGS and do not add additional punctuation."
    )
    prompt_user = f"Translate the following text from {source_language} to {target_language}:\n'{text}'"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt_system},
                {"role": "user", "content": prompt_user}
            ],
            temperature=0
        )
        translation = response.choices[0].message.content.strip()
        # Removes leading/trailing quotes
        if translation and translation[0] in ["'", '"', "'", "„"]:
            translation = translation[1:]
            if translation and translation[-1] in ["'", '"']:
                translation = translation[:-1]
        translation = clean_html_except_br(translation)
        return translation
    except Exception as e:
        st.warning("Translation error: " + str(e))
        return text

class CoreAPI:
    def __init__(self, api_key):
        self.base_url = "https://api.core.ac.uk/v3/"
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def search_publications(self, query, filters=None, sort=None, limit=100):
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

def check_core_aggregate_connection(api_key="LmAMxdYnK6SDJsPRQCpGgwN7f5yTUBHF", timeout=15):
    """Check if CORE aggregator is reachable."""
    try:
        core = CoreAPI(api_key)
        result = core.search_publications("test", limit=1)
        return "results" in result
    except Exception:
        return False

def search_core_aggregate(query, api_key="LmAMxdYnK6SDJsPRQCpGgwN7f5yTUBHF"):
    """Simple search in CORE aggregator."""
    if not api_key:
        return []
    try:
        core = CoreAPI(api_key)
        raw = core.search_publications(query, limit=100)
        out = []
        results = raw.get("results", [])
        for item in results:
            title = item.get("title", "n/a")
            year = str(item.get("yearPublished", "n/a"))
            journal = item.get("publisher", "n/a")
            out.append({
                "PMID": "n/a",
                "Title": title,
                "Year": year,
                "Journal": journal
            })
        return out
    except Exception as e:
        st.error(f"CORE search error: {e}")
        return []

# ------------------------------------------------------------------
# 2) PubMed - Einfacher Check + Search (UNVERÄNDERT)
# ------------------------------------------------------------------
def check_pubmed_connection(timeout=10):
    """Quick connection test to PubMed."""
    test_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {"db": "pubmed", "term": "test", "retmode": "json"}
    try:
        r = requests.get(test_url, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return "esearchresult" in data
    except Exception:
        return False

def search_pubmed_simple(query):
    """Short search (title/journal/year) in PubMed."""
    esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {"db": "pubmed", "term": query, "retmode": "json", "retmax": 100}
    out = []
    try:
        r = requests.get(esearch_url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        idlist = data.get("esearchresult", {}).get("idlist", [])
        if not idlist:
            return out
        esummary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        sum_params = {"db": "pubmed", "id": ",".join(idlist), "retmode": "json"}
        r2 = requests.get(esummary_url, params=sum_params, timeout=10)
        r2.raise_for_status()
        summary_data = r2.json().get("result", {})
        for pmid in idlist:
            info = summary_data.get(pmid, {})
            title = info.get("title", "n/a")
            pubdate = info.get("pubdate", "")
            year = pubdate[:4] if pubdate else "n/a"
            journal = info.get("fulljournalname", "n/a")
            out.append({
                "PMID": pmid,
                "Title": title,
                "Year": year,
                "Journal": journal
            })
        return out
    except Exception as e:
        st.error(f"Error searching PubMed: {e}")
        return []

def fetch_pubmed_abstract(pmid):
    """Fetches abstract via efetch for a given PubMed ID."""
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {"db": "pubmed", "id": pmid, "retmode": "xml"}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        abs_text = []
        for elem in root.findall(".//AbstractText"):
            if elem.text:
                abs_text.append(elem.text.strip())
        if abs_text:
            return "\n".join(abs_text)
        else:
            return "(No abstract available)"
    except Exception as e:
        return f"(Error: {e})"

def fetch_pubmed_doi_and_link(pmid: str) -> (str, str):
    """
    Attempts to retrieve the DOI and PubMed link for a given PMID via E-Summary/E-Fetch.
    Returns (doi, pubmed_link). If no DOI is found, returns ("n/a", link).
    """
    if not pmid or pmid == "n/a":
        return ("n/a", "")
    
    # PubMed link
    link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    
    # 1) esummary
    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    params_sum = {"db": "pubmed", "id": pmid, "retmode": "json"}
    try:
        rs = requests.get(summary_url, params=params_sum, timeout=8)
        rs.raise_for_status()
        data = rs.json()
        result_obj = data.get("result", {}).get(pmid, {})
        eloc = result_obj.get("elocationid", "")
        if eloc and eloc.startswith("doi:"):
            doi_ = eloc.split("doi:", 1)[1].strip()
            if doi_:
                return (doi_, link)
    except Exception:
        pass
    
    # 2) efetch
    efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params_efetch = {"db": "pubmed", "id": pmid, "retmode": "xml"}
    try:
        r_ef = requests.get(efetch_url, params=params_efetch, timeout=8)
        r_ef.raise_for_status()
        root = ET.fromstring(r_ef.content)
        doi_found = "n/a"
        for aid in root.findall(".//ArticleId"):
            id_type = aid.attrib.get("IdType", "")
            if id_type.lower() == "doi":
                doi_found = aid.text.strip() if aid.text else "n/a"
                break
        return (doi_found, link)
    except Exception:
        return ("n/a", link)

# ------------------------------------------------------------------
# 3) Europe PMC Check + Search (UNVERÄNDERT)
# ------------------------------------------------------------------
def check_europe_pmc_connection(timeout=10):
    """Check if Europe PMC is reachable."""
    test_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {"query": "test", "format": "json", "pageSize": 100}
    try:
        r = requests.get(test_url, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return "resultList" in data and "result" in data["resultList"]
    except Exception:
        return False

def search_europe_pmc_simple(query):
    """Simple search in Europe PMC."""
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {
        "query": query,
        "format": "json",
        "pageSize": 100,
        "resultType": "core"
    }
    out = []
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if "resultList" not in data or "result" not in data["resultList"]:
            return out
        results = data["resultList"]["result"]
        for item in results:
            pmid = item.get("pmid", "n/a")
            title = item.get("title", "n/a")
            year = str(item.get("pubYear", "n/a"))
            journal = item.get("journalTitle", "n/a")
            out.append({
                "PMID": pmid if pmid else "n/a",
                "Title": title,
                "Year": year,
                "Journal": journal
            })
        return out
    except Exception as e:
        st.error(f"Europe PMC search error: {e}")
        return []

# ------------------------------------------------------------------
# 4) OpenAlex API (UNVERÄNDERT)
# ------------------------------------------------------------------
BASE_URL = "https://api.openalex.org"

def fetch_openalex_data(entity_type, entity_id=None, params=None):
    url = f"{BASE_URL}/{entity_type}"
    if entity_id:
        url += f"/{entity_id}"
    if params is None:
        params = {}
    params["mailto"] = "your_email@example.com"
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Fehler: {response.status_code} - {response.text}")
        return None

def search_openalex_simple(query):
    """Short version: fetches raw data, checks if anything is returned."""
    search_params = {"search": query}
    return fetch_openalex_data("works", params=search_params)

# ------------------------------------------------------------------
# 5) Google Scholar (UNVERÄNDERT)
# ------------------------------------------------------------------
class GoogleScholarSearch:
    def __init__(self):
        self.all_results = []
    def search_google_scholar(self, base_query):
        try:
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
            st.error(f"Fehler bei der Google Scholar-Suche: {e}")

# ------------------------------------------------------------------
# 6) Semantic Scholar (UNVERÄNDERT)
# ------------------------------------------------------------------
def check_semantic_scholar_connection(timeout=10):
    """Connection test to Semantic Scholar."""
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {"query": "test", "limit": 1, "fields": "title"}
        headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, params=params, timeout=timeout)
        response.raise_for_status()
        return response.status_code == 200
    except Exception:
        return False

class SemanticScholarSearch:
    def __init__(self):
        self.all_results = []
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
                    "DOI": "n/a",
                    "URL": url_article,
                    "Abstract": abstract_text
                })
        except Exception as e:
            st.error(f"Semantic Scholar: {e}")

# ------------------------------------------------------------------
# 8) Weitere Module + Seiten (UNVERÄNDERT)
# ------------------------------------------------------------------
def module_paperqa2():
    st.subheader("PaperQA2 Module")
    st.write("This is the PaperQA2 module. You can add more settings and functions here.")
    question = st.text_input("Please enter your question:")
    if st.button("Submit question"):
        st.write("Answer: This is a dummy answer to the question:", question)

def page_home():
    st.title("🎉 Welcome to the Enhanced Main Menu")
    st.write("Choose a module in the sidebar to proceed.")
    
    # NEU: API-Status auf Hauptseite
    st.subheader("🤖 Lokale API Status")
    api_online, api_status = check_local_api_status()
    
    if api_online:
        st.success("✅ Lokale Paper QA API ist verfügbar")
        if api_status:
            st.info(f"Modell geladen: {'✅' if api_status.get('model_loaded') else '❌'}")
    else:
        st.warning("⚠️ Lokale Paper QA API ist offline")
        st.info("💡 Nutzen Sie den 'Lokale API Paper QA' Bereich zum Starten")
    
    try:
        st.image("Bild1.jpg", caption="Willkommen!", use_container_width=False, width=600)
    except:
        st.info("Willkommensbild nicht gefunden - weiter ohne Bild")

def page_codewords_pubmed():
    st.title("Codewords & PubMed Settings")
    from modules.codewords_pubmed import module_codewords_pubmed
    module_codewords_pubmed()
    if st.button("Back to Main Menu"):
        st.session_state["current_page"] = "Home"

def page_paper_selection():
    st.title("Paper Selection Settings")
    st.write("Define how you want to pick or exclude certain papers. (Dummy placeholder...)")
    if st.button("Back to Main Menu"):
        st.session_state["current_page"] = "Home"

def page_analysis():
    st.title("Analysis & Evaluation Settings")
    st.write("Set up your analysis parameters, thresholds, etc. (Dummy placeholder...)")
    if st.button("Back to Main Menu"):
        st.session_state["current_page"] = "Home"

def page_extended_topics():
    st.title("Extended Topics")
    st.write("Access advanced or extended topics for further research. (Dummy placeholder...)")
    if st.button("Back to Main Menu"):
        st.session_state["current_page"] = "Home"

def page_paperqa2():
    st.title("PaperQA2")
    module_paperqa2()
    if st.button("Back to Main Menu"):
        st.session_state["current_page"] = "Home"

def page_excel_online_search():
    st.title("Excel Online Search")
    # Placeholder, or import existing code if needed

def page_online_api_filter():
    st.title("Online-API_Filter (Combined)")
    st.write("Here, you can combine API selection and filtering in one step.")
    from modules.online_api_filter import module_online_api_filter
    module_online_api_filter()
    if st.button("Back to Main Menu"):
        st.session_state["current_page"] = "Home"

# ------------------------------------------------------------------
# Important Classes for Analysis (UNVERÄNDERT)
# ------------------------------------------------------------------
class PaperAnalyzer:
    def __init__(self, model="gpt-3.5-turbo"):
        self.model = model
    
    def extract_text_from_pdf(self, pdf_file):
        """Extracts raw text via PyPDF2."""
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    
    def analyze_with_openai(self, text, prompt_template, api_key):
        """Helper function to call OpenAI via ChatCompletion."""
        import openai
        openai.api_key = api_key
        if len(text) > 15000:
            text = text[:15000] + "..."
        prompt = prompt_template.format(text=text)
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert in scientific paper analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        return response.choices[0].message.content
    
    def summarize(self, text, api_key):
        """Creates a summary in German."""
        prompt = (
            "Erstelle eine strukturierte Zusammenfassung des folgenden wissenschaftlichen Papers. "
            "Gliedere sie in mindestens vier klar getrennte Abschnitte (z.B. 1. Hintergrund, 2. Methodik, 3. Ergebnisse, 4. Schlussfolgerungen). "
            "Verwende maximal 500 Wörter:\n\n{text}"
        )
        return self.analyze_with_openai(text, prompt, api_key)
    
    def extract_key_findings(self, text, api_key):
        """Extract the 5 most important findings."""
        prompt = (
            "Extrahiere die 5 wichtigsten Erkenntnisse aus diesem wissenschaftlichen Paper. "
            "Liste sie mit Bulletpoints auf:\n\n{text}"
        )
        return self.analyze_with_openai(text, prompt, api_key)
    
    def identify_methods(self, text, api_key):
        """Identify methods and techniques used in the paper."""
        prompt = (
            "Identifiziere und beschreibe die im Paper verwendeten Methoden und Techniken. "
            "Gib zu jeder Methode eine kurze Erklärung:\n\n{text}"
        )
        return self.analyze_with_openai(text, prompt, api_key)
    
    def evaluate_relevance(self, text, topic, api_key):
        """Rates relevance to the topic on a scale of 1-10."""
        prompt = (
            f"Bewerte die Relevanz dieses Papers für das Thema '{topic}' auf einer Skala von 1-10. "
            f"Begründe deine Bewertung:\n\n{{text}}"
        )
        return self.analyze_with_openai(text, prompt, api_key)

class AlleleFrequencyFinder:
    """Class for retrieving and displaying allele frequencies from various sources (Ensembl primarily)."""
    def __init__(self):
        self.ensembl_server = "https://rest.ensembl.org"
        self.max_retries = 3
        self.retry_delay = 2  # seconds between retries

    def get_allele_frequencies(self, rs_id: str, retry_count: int = 0) -> Optional[Dict[str, Any]]:
        """Fetches allele frequencies from Ensembl."""
        if not rs_id.startswith("rs"):
            rs_id = f"rs{rs_id}"
        endpoint = f"/variation/human/{rs_id}?pops=1"
        url = f"{self.ensembl_server}{endpoint}"
        try:
            response = requests.get(url, headers={"Content-Type": "application/json"}, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError:
            if response.status_code == 500 and retry_count < self.max_retries:
                time.sleep(self.retry_delay)
                return self.get_allele_frequencies(rs_id, retry_count + 1)
            elif response.status_code == 404:
                return None
            else:
                return None
        except requests.exceptions.RequestException:
            if retry_count < self.max_retries:
                time.sleep(self.retry_delay)
                return self.get_allele_frequencies(rs_id, retry_count + 1)
            return None
    
    def try_alternative_source(self, rs_id: str) -> Optional[Dict[str, Any]]:
        return None
    
    def build_freq_info_text(self, data: Dict[str, Any]) -> str:
        """Generates a short text about allele frequencies in ENGLISH for the Excel."""
        if not data:
            return "No data from Ensembl"
        maf = data.get("MAF", None)
        pops = data.get("populations", [])
        out = []
        out.append(f"MAF={maf}" if maf else "MAF=n/a")
        if pops:
            max_pop = 2
            for i, pop in enumerate(pops):
                if i >= max_pop:
                    break
                pop_name = pop.get('population', 'N/A')
                allele = pop.get('allele', 'N/A')
                freq = pop.get('frequency', 'N/A')
                out.append(f"{pop_name}:{allele}={freq}")
        else:
            out.append("No population data found.")
        return " | ".join(out)

def split_summary(summary_text):
    """Attempts to split 'Ergebnisse' and 'Schlussfolgerungen' from a German summary."""
    pattern = re.compile(
        r'(Ergebnisse(?:\:|\s*\n)|Resultate(?:\:|\s*\n))(?P<results>.*?)(Schlussfolgerungen(?:\:|\s*\n)|Fazit(?:\:|\s*\n))(?P<conclusion>.*)',
        re.IGNORECASE | re.DOTALL
    )
    match = pattern.search(summary_text)
    if match:
        ergebnisse = match.group('results').strip()
        schlussfolgerungen = match.group('conclusion').strip()
        return ergebnisse, schlussfolgerungen
    else:
        return summary_text, ""

def parse_cohort_info(summary_text: str) -> dict:
    """Parses rough info about the cohort (number of patients, origin, etc.) from a German summary."""
    info = {"study_size": "", "origin": ""}
    pattern_both = re.compile(
        r"(\d+)\s*Patient(?:en)?(?:[^\d]+)(\d+)\s*gesunde\s*Kontroll(?:personen)?",
        re.IGNORECASE
    )
    m_both = pattern_both.search(summary_text)
    if m_both:
        p_count = m_both.group(1)
        c_count = m_both.group(2)
        info["study_size"] = f"{p_count} Patienten / {c_count} Kontrollpersonen"
    else:
        pattern_single_p = re.compile(r"(\d+)\s*Patient(?:en)?", re.IGNORECASE)
        m_single_p = pattern_single_p.search(summary_text)
        if m_single_p:
            info["study_size"] = f"{m_single_p.group(1)} Patienten"
    pattern_origin = re.compile(r"in\s*der\s+(\S+)\s+Bevölkerung", re.IGNORECASE)
    m_orig = pattern_origin.search(summary_text)
    if m_orig:
        info["origin"] = m_orig.group(1).strip()
    return info

# [Weitere Funktionen und Klassen bleiben unverändert...]

# ------------------------------------------------------------------
# KI-Inhaltserkennung (UNVERÄNDERT)
# ------------------------------------------------------------------
class AIContentDetector:
    def __init__(self, api_key=None, api_provider=None):
        self.api_key = api_key
        self.api_provider = api_provider
        self.detection_methods = {
            "pattern_analysis": self.analyze_patterns,
            "consistency_check": self.check_consistency,
            "citation_verification": self.verify_citations,
            "api_detection": self.detect_with_api
        }
    
    def analyze_patterns(self, text):
        """Untersucht typische KI-Schreibmuster"""
        patterns = {
            "wiederholende_phrasen": r'(\b\w+\s+\w+\b)(?=.*\1)',  
            "gleichmäßiger_ton": r'(jedoch|allerdings|dennoch|daher|folglich|somit)',  
            "generische_übergänge": r'\b(zunächst|anschließend|abschließend|zusammenfassend)\b'
        }
        
        scores = {}
        for name, pattern in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            density = len(matches) / (len(text.split()) / 100 + 1e-8)
            scores[name] = min(100, density * 5)
        
        return sum(scores.values()) / len(scores) if scores else 0
    
    def check_consistency(self, text):
        """Prüft auf konsistente Schreibweise und Ton"""
        paragraphs = text.split('\n\n')
        if len(paragraphs) < 3:
            return 50
        
        sentences = re.split(r'[.!?]+', text)
        lengths = [len(s.split()) for s in sentences if s.strip()]
        if not lengths:
            return 50
        
        avg_length = sum(lengths) / len(lengths)
        variation = sum(abs(l - avg_length) for l in lengths) / len(lengths)
        
        consistency_score = 100 - min(100, variation * 10)
        return consistency_score
    
    def verify_citations(self, text):
        """Überprüft Zitate auf Plausibilität"""
        citation_pattern = r'\(([^)]+\d{4}[^)]*)\)'
        citations = re.findall(citation_pattern, text)
        
        if not citations:
            return 60
        
        formats = {}
        for citation in citations:
            format_key = re.sub(r'[A-Za-z\s]', 'X', citation)
            format_key = re.sub(r'\d', '9', format_key)
            formats[format_key] = formats.get(format_key, 0) + 1
        
        uniformity = max(formats.values()) / len(citations) * 100
        return uniformity
    
    def detect_with_api(self, text):
        """Verwendet externe APIs"""
        if not self.api_key:
            return 50
        
        if self.api_provider == "originality":
            try:
                response = requests.post(
                    "https://api.originality.ai/api/v1/scan/ai",
                    headers={"X-OAI-API-KEY": self.api_key},
                    json={"content": text}
                )
                if response.status_code == 200:
                    result = response.json()
                    return result.get("score", {}).get("ai", 0.5) * 100
            except Exception as e:
                print(f"Originality.ai API-Fehler: {e}")
        
        return 50
    
    def analyze_text(self, text):
        """Führt eine komplette Analyse durch."""
        scores = {}
        for method_name, method_func in self.detection_methods.items():
            scores[method_name] = method_func(text)
        
        weights = {
            "pattern_analysis": 0.20,
            "consistency_check": 0.20,
            "citation_verification": 0.10,
            "api_detection": 0.50
        }
        
        weighted_score = sum(scores[m] * weights[m] for m in scores)
        return {
            "gesamtbewertung": round(weighted_score, 2),
            "einzelbewertungen": {m: round(scores[m], 2) for m in scores},
            "interpretation": self.interpret_score(weighted_score)
        }
    
    def interpret_score(self, score):
        """Interpretation der KI-Wahrscheinlichkeit"""
        if score < 30:
            return "Wahrscheinlich von Menschen geschrieben"
        elif score < 60:
            return "Unklare Herkunft, könnte teilweise KI-unterstützt sein"
        elif score < 85:
            return "Wahrscheinlich KI-unterstützt oder überarbeitet"
        else:
            return "Sehr wahrscheinlich vollständig KI-generiert"

def page_ai_content_detection():
    """Seite zur Erkennung von KI-Textinhalten"""
    st.title("🔬 KI-Inhaltserkennung (AI Content Detector)")
    
    st.info("Hier kannst du Text eingeben oder eine Datei hochladen, um eine KI-Analyse durchzuführen.")
    
    api_key_input = st.text_input("API Key (optional)", value="", type="password")
    provider_option = st.selectbox("API-Anbieter", ["Kein API-Einsatz", "originality", "scribbr"], index=0)
    
    input_mode = st.radio("Eingabemethode für den Text:", ["Direkte Eingabe", "Textdatei hochladen"])
    
    text_data = ""
    if input_mode == "Direkte Eingabe":
        text_data = st.text_area("Gib hier deinen Text ein:", height=200)
    else:
        uploaded_text_file = st.file_uploader("Text-Datei wählen (.txt, .md, etc.)", type=["txt","md","csv","json"])
        if uploaded_text_file is not None:
            try:
                text_data = uploaded_text_file.read().decode("utf-8", errors="ignore")
            except Exception as e:
                st.error(f"Fehler beim Lesen der Datei: {e}")
                return
    
    if st.button("KI-Analyse starten"):
        if not text_data.strip():
            st.warning("Bitte Text eingeben oder Datei hochladen.")
            return
        
        if provider_option == "Kein API-Einsatz":
            detector = AIContentDetector(api_key=None, api_provider=None)
        else:
            detector = AIContentDetector(api_key=api_key_input, api_provider=provider_option.lower())
        
        with st.spinner("Analyse läuft..."):
            result = detector.analyze_text(text_data)
        
        st.subheader("Ergebnis der KI-Analyse")
        gesamtbewertung = result["gesamtbewertung"]
        interpretation = result["interpretation"]
        einzelbewertungen = result["einzelbewertungen"]
        
        st.metric("KI-Wahrscheinlichkeit (gesamt)", f"{gesamtbewertung} %", help=interpretation)
        st.write("**Interpretation:** ", interpretation)
        
        st.write("### Einzelbewertungen")
        for method, score in einzelbewertungen.items():
            st.write(f"- **{method}**: {score} %")
        
        if provider_option != "Kein API-Einsatz":
            st.write(f"Verwendeter API-Dienst: **{provider_option}**")
        else:
            st.write("**Hinweis:** Keine externe API genutzt, nur lokale Heuristiken.")

def page_genotype_finder():
    """Seite für Genotyp-Frequenz-Suche"""
    st.title("🧬 Genotype Frequency Finder")

    class GenotypeFinder:
        def __init__(self):
            self.ensembl_server = "https://rest.ensembl.org"
        
        def get_variant_info(self, rs_id):
            if not rs_id.startswith("rs"):
                rs_id = f"rs{rs_id}"
            ext = f"/variation/human/{rs_id}?pops=1"
            url = f"{self.ensembl_server}{ext}"
            try:
                r = requests.get(url, headers={"Content-Type": "application/json"}, timeout=10)
                r.raise_for_status()
                return r.json()
            except:
                return None
        
        def calculate_genotype_frequency(self, data, genotype):
            if not data or 'populations' not in data:
                return {}
            if len(genotype) < 2:
                return {}
            allele1, allele2 = genotype[0], genotype[1]
            results = {}
            for pop in data['populations']:
                pop_name = pop.get('population', '')
                if '1000GENOMES' not in pop_name:
                    continue
                allele_freq_map = {}
                for pop2 in data['populations']:
                    if pop2.get('population') == pop_name:
                        a_ = pop2.get('allele')
                        f_ = pop2.get('frequency')
                        allele_freq_map[a_] = f_
                if allele1 in allele_freq_map and allele2 in allele_freq_map:
                    if allele1 == allele2:
                        freq_g = allele_freq_map[allele1] ** 2
                    else:
                        freq_g = 2 * allele_freq_map[allele1] * allele_freq_map[allele2]
                    results[pop_name] = freq_g
            return results
    
    def build_genotype_freq_text(freq_dict: Dict[str, float]) -> str:
        if not freq_dict:
            return "No genotype frequency data found."
        lines = []
        if "1000GENOMES:phase_3:ALL" in freq_dict:
            lines.append(f"Global population (ALL): {freq_dict['1000GENOMES:phase_3:ALL']:.4f}")
            lines.append("---")
        for pop, val in sorted(freq_dict.items()):
            if pop == "1000GENOMES:phase_3:ALL":
                continue
            lines.append(f"{pop}: {val:.4f}")
        return "\n".join(lines)

    st.write("Look up genotype frequencies for a given rsID (from Ensembl).")
    rs_input = st.text_input("Enter an rsID (e.g., 'rs1234'):", "")
    genotype_input = st.text_input("Enter a genotype (e.g., 'AA','AC','CC','AG', etc.):", "")

    if st.button("Check Frequencies"):
        if not rs_input.strip():
            st.warning("Please enter an rsID.")
            return
        gf = GenotypeFinder()
        data = gf.get_variant_info(rs_input.strip())
        if not data:
            st.error(f"No data found for {rs_input.strip()}. Are you sure it's correct?")
            return
        freq_dict = gf.calculate_genotype_frequency(data, genotype_input.strip().upper())
        freq_text = build_genotype_freq_text(freq_dict)
        st.subheader("Result:")
        st.write(freq_text)

# [Weitere unveränderte Funktionen und Klassen...]

# ------------------------------------------------------------------
# ERWEITERTE Sidebar Navigation (NEU: Lokale API Button hinzugefügt)
# ------------------------------------------------------------------
def sidebar_module_navigation():
    st.sidebar.title("🚀 Module Navigation")
    
    # NEU: API-Status in Sidebar
    api_online, _ = check_local_api_status()
    api_indicator = "🟢" if api_online else "🔴"
    st.sidebar.markdown(f"**Lokale API:** {api_indicator}")

    pages = {
        "🏠 Home": page_home,
        "🤖 Lokale API Paper QA": page_local_api_paper_qa,  # NEU HINZUGEFÜGT
        "🔍 Online-API_Filter": page_online_api_filter,
        "📚 3) Codewords & PubMed": page_codewords_pubmed,
        "📄 Analyze Paper": page_analyze_paper,
        "🧬 Genotype Frequency Finder": page_genotype_finder,
        "🔬 AI-Content Detection": page_ai_content_detection
    }

    for label, page in pages.items():
        if st.sidebar.button(label, key=label):
            st.session_state["current_page"] = label
    
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "🏠 Home"
    
    return pages.get(st.session_state["current_page"], page_home)

# ------------------------------------------------------------------
# ERWEITERTE Chatbot Funktionalität (NEU: lokale API Integration)
# ------------------------------------------------------------------
def answer_chat(question: str) -> str:
    """Enhanced chatbot mit lokaler API Integration"""
    api_key = st.session_state.get("api_key", "")
    paper_text = st.session_state.get("paper_text", "")
    
    # NEU: Prüfe ob lokale API verfügbar und Paper geladen
    api_online, _ = check_local_api_status()
    if api_online and st.session_state.get("paper_loaded_api", False):
        # Nutze lokale API für Antworten
        success, result = ask_api_question(question, top_k=2)
        if success:
            return f"🤖 Lokale API: {result['answer']}"
        else:
            return f"🤖 Lokale API Fehler: {result}"
    
    # Fallback auf ursprüngliche OpenAI-Implementierung
    if not api_key:
        return f"(No API-Key) Echo: {question}"
    
    if not paper_text.strip():
        sys_msg = "You are a helpful assistant for general questions."
    else:
        sys_msg = (
            "You are a helpful assistant, and here is a paper as context:\n\n"
            + paper_text[:12000] + "\n\n"
            "Please use it to answer questions as expertly as possible."
        )
    
    openai.api_key = api_key
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": question}
            ],
            temperature=0.3,
            max_tokens=400
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"OpenAI error: {e}"

# ------------------------------------------------------------------
# Haupt-App Layout (ERWEITERT mit lokaler API-Integration)
# ------------------------------------------------------------------
def main():
    # -------- LAYOUT: Left Modules, Right Chatbot --------
    col_left, col_right = st.columns([4, 1])
    
    with col_left:
        # Navigation
        page_fn = sidebar_module_navigation()
        if page_fn is not None:
            page_fn()
    
    with col_right:
        st.subheader("🤖 Enhanced Chatbot")
        
        # NEU: API-Status im Chatbot
        api_online, _ = check_local_api_status()
        if api_online:
            st.success("🟢 Lokale API verfügbar")
        else:
            st.warning("🔴 Lokale API offline")
        
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []
        
        user_input = st.text_input("Your question here", key="chatbot_right_input")
        if st.button("Send (Chat)", key="chatbot_right_send"):
            if user_input.strip():
                st.session_state["chat_history"].append(("user", user_input))
                bot_answer = answer_chat(user_input)
                st.session_state["chat_history"].append(("bot", bot_answer))
        
        # Chat-History Anzeige (unverändert)
        st.markdown(
            """
            <style>
            .scrollable-chat {
                max-height: 400px; 
                overflow-y: auto; 
                border: 1px solid #CCC;
                padding: 8px;
                margin-top: 10px;
                border-radius: 4px;
                background-color: #f9f9f9;
            }
            .message {
                padding: 0.5rem 1rem;
                border-radius: 15px;
                margin-bottom: 0.5rem;
                max-width: 80%;
                word-wrap: break-word;
            }
            .user-message {
                background-color: #e3f2fd;
                margin-left: auto;
                border-bottom-right-radius: 0;
            }
            .assistant-message {
                background-color: #f0f0f0;
                margin-right: auto;
                border-bottom-left-radius: 0;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown('<div class="scrollable-chat" id="chat-container">', unsafe_allow_html=True)
        for role, msg_text in st.session_state["chat_history"]:
            if role == "user":
                st.markdown(
                    f'<div class="message user-message"><strong>You:</strong> {msg_text}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="message assistant-message"><strong>Bot:</strong> {msg_text}</div>',
                    unsafe_allow_html=True
                )
        st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------
# App starten
# ------------------------------------------------------------------
if __name__ == '__main__':
    main()
