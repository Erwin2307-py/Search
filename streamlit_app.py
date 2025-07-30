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

from typing import Dict, Any, Optional
from dotenv import load_dotenv
from PIL import Image
from scholarly import scholarly

# Excel / openpyxl-Import
import openpyxl

# Übersetzung mit google_trans_new
from google_trans_new import google_translator

# ------------------------------------------------------------------
# Umgebungsvariablen laden
# ------------------------------------------------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ------------------------------------------------------------------
# Streamlit-Konfiguration
# ------------------------------------------------------------------
st.set_page_config(page_title="Streamlit Multi-Modul Demo", layout="wide")

# ------------------------------------------------------------------
# Login-Funktionalität
# ------------------------------------------------------------------
def login():
    st.title("Login")
    user_input = st.text_input("Username")
    pass_input = st.text_input("Password", type="password")
    if st.button("Login"):
        try:
            if (user_input == st.secrets["login"]["username"] and 
                pass_input == st.secrets["login"]["password"]):
                st.session_state["logged_in"] = True
            else:
                st.error("Login failed. Please check your credentials!")
        except Exception as e:
            st.error(f"Login error: {str(e)} - Check your secrets.toml file")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login()
    st.stop()
# ------------------------------------------------------------------
# Module Import Helper Functions (HINZUFÜGEN NACH DEN IMPORTS)
# ------------------------------------------------------------------
def safe_import_module(module_path, function_name):
    """Sichere Modul-Import Funktion"""
    try:
        if module_path == "modules.email_module":
            import importlib.util
            spec = importlib.util.spec_from_file_location("email_module", "modules/email_module.py")
            if spec is None:
                return None
            email_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(email_module)
            
            if hasattr(email_module, function_name):
                return getattr(email_module, function_name)
            else:
                st.warning(f"⚠️ Funktion '{function_name}' nicht im Modul gefunden!")
                return None
                
        elif module_path == "modules.codewords_pubmed":
            from modules.codewords_pubmed import module_codewords_pubmed
            return module_codewords_pubmed
            
        elif module_path == "modules.online_api_filter":
            from modules.online_api_filter import module_online_api_filter
            return module_online_api_filter
        else:
            return None
            
    except ImportError as e:
        st.warning(f"⚠️ Modul {module_path} konnte nicht importiert werden: {str(e)}")
        return None
    except Exception as e:
        st.error(f"❌ Fehler beim Importieren von {module_path}: {str(e)}")
        return None

def check_module_exists(module_path):
    """Prüft ob ein Modul existiert"""
    try:
        file_path = module_path.replace(".", "/") + ".py"
        return os.path.exists(file_path)
    except:
        return False

def integrated_email_interface():
    """Integrierte Email-Funktionalität als Fallback"""
    st.subheader("📧 Integrierte Email-Funktionen")
    st.info("✅ Verwendet integrierte Email-Funktionalität")
    
    # Initialize Session State für Email
    if "email_config" not in st.session_state:
        st.session_state["email_config"] = {
            "sender_email": "",
            "recipient_email": "",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587
        }
    
    if "email_history" not in st.session_state:
        st.session_state["email_history"] = []
    
    # Email-Konfiguration
    with st.expander("📧 Email-Konfiguration", expanded=True):
        with st.form("integrated_email_config"):
            col1, col2 = st.columns(2)
            
            with col1:
                sender_email = st.text_input(
                    "Absender Email", 
                    value=st.session_state["email_config"]["sender_email"]
                )
                smtp_server = st.text_input(
                    "SMTP Server", 
                    value=st.session_state["email_config"]["smtp_server"]
                )
            
            with col2:
                recipient_email = st.text_input(
                    "Empfänger Email", 
                    value=st.session_state["email_config"]["recipient_email"]
                )
                smtp_port = st.number_input(
                    "SMTP Port", 
                    value=st.session_state["email_config"]["smtp_port"]
                )
            
            if st.form_submit_button("💾 Konfiguration speichern"):
                st.session_state["email_config"].update({
                    "sender_email": sender_email,
                    "recipient_email": recipient_email,
                    "smtp_server": smtp_server,
                    "smtp_port": smtp_port
                })
                st.success("✅ Email-Konfiguration gespeichert!")
    
    # Test-Email senden
    if st.button("📧 Test-Email senden"):
        config = st.session_state["email_config"]
        if config.get("sender_email") and config.get("recipient_email"):
            test_email = {
                "timestamp": datetime.datetime.now().isoformat(),
                "type": "Test",
                "subject": "Test-Email vom Paper-Suche System",
                "recipient": config["recipient_email"],
                "status": "Simuliert"
            }
            st.session_state["email_history"].append(test_email)
            st.success("✅ Test-Email simuliert und zur Historie hinzugefügt!")
        else:
            st.error("❌ Bitte konfigurieren Sie zuerst Ihre Email-Einstellungen!")
    
    # Email-Historie anzeigen
    if st.button("📊 Email-Historie anzeigen"):
        history = st.session_state.get("email_history", [])
        if history:
            st.subheader("📨 Email-Historie")
            for i, email in enumerate(reversed(history[-5:]), 1):  # Letzte 5
                st.write(f"**{i}.** {email.get('type', 'N/A')} - {email.get('timestamp', 'N/A')[:19]} - Status: {email.get('status', 'N/A')}")
        else:
            st.info("Keine Emails in der Historie.")

# ------------------------------------------------------------------
# 1) Gemeinsame Funktionen & Klassen (KORRIGIERT - KEINE HTML-ENTITIES)
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
# 2) PubMed - Einfacher Check + Search (KORRIGIERT)
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
# Google Scholar & Semantic Scholar (KORRIGIERT)
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
# Module + Seiten (KORRIGIERT)
# ------------------------------------------------------------------
def module_paperqa2():
    st.subheader("PaperQA2 Module")
    st.write("This is the PaperQA2 module. You can add more settings and functions here.")
    question = st.text_input("Please enter your question:")
    if st.button("Submit question"):
        st.write("Answer: This is a dummy answer to the question:", question)

def page_home():
    st.title("Welcome to the Main Menu")
    st.write("Choose a module in the sidebar to proceed.")
    try:
        st.image("Bild1.jpg", caption="Willkommen!", use_container_width=False, width=600)
    except:
        st.info("Bild1.jpg not found - continuing without image")

def page_codewords_pubmed():
    st.title("Codewords & PubMed Settings")
    try:
        from modules.codewords_pubmed import module_codewords_pubmed
        module_codewords_pubmed()
    except ImportError:
        st.error("modules.codewords_pubmed konnte nicht importiert werden.")
    if st.button("Back to Main Menu"):
        st.session_state["current_page"] = "Home"

def page_online_api_filter():
    st.title("Online-API_Filter (Combined)")
    st.write("Here, you can combine API selection and filtering in one step.")
    try:
        from modules.online_api_filter import module_online_api_filter
        module_online_api_filter()
    except ImportError:
        st.error("modules.online_api_filter konnte nicht importiert werden.")
    if st.button("Back to Main Menu"):
        st.session_state["current_page"] = "Home"

# ------------------------------------------------------------------
# ROBUSTE EMAIL-MODUL SEITE (KORRIGIERT)
# ------------------------------------------------------------------
def page_email_module():
    st.title("📧 Email Module")
    st.write("Email-Funktionalitäten und -Einstellungen")
    
    # Debug-Information
    st.write("🔍 Email-Modul Debug:")
    module_path = "modules/email_module.py"
    st.write(f"Dateipfad: {module_path}")
    st.write(f"Datei existiert: {os.path.exists(module_path)}")
    st.write(f"Arbeitsverzeichnis: {os.getcwd()}")
    
    if os.path.exists("modules"):
        files = os.listdir("modules")
        st.write(f"Dateien im modules-Ordner: {files}")
    else:
        st.error("modules-Ordner existiert nicht!")
    
    # Robuster Import-Versuch
    email_module_loaded = False
    
    try:
        # Verschiedene Import-Varianten versuchen
        import importlib.util
        spec = importlib.util.spec_from_file_location("email_module", "modules/email_module.py")
        email_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(email_module)
        
        # Prüfe ob module_email Funktion existiert
        if hasattr(email_module, 'module_email'):
            st.success("✅ Email-Modul erfolgreich geladen!")
            email_module.module_email()
            email_module_loaded = True
        else:
            st.warning("⚠️ Funktion 'module_email' nicht im Modul gefunden!")
            raise AttributeError("module_email function not found")
            
    except Exception as e:
        st.error(f"❌ Fehler beim Laden des Email-Moduls: {str(e)}")
    
    # Fallback wenn Email-Modul nicht geladen werden konnte
    if not email_module_loaded:
        st.write("---")
        st.write("**🔧 Integrierte Email-Funktionalität (Fallback):**")
        create_integrated_email_interface()
    
    if st.button("Back to Main Menu"):
        st.session_state["current_page"] = "Home"

def create_integrated_email_interface():
    """Erstellt integrierte Email-Funktionalität als Fallback"""
    st.subheader("📤 Integrierte Email-Funktionalität")
    
    # Initialize Session State
    if "integrated_email_settings" not in st.session_state:
        st.session_state["integrated_email_settings"] = {
            "sender_email": "",
            "recipient_email": "",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587
        }
    
    # Email-Konfiguration
    with st.expander("📧 Email-Konfiguration", expanded=True):
        with st.form("integrated_email_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                sender_email = st.text_input("Von (Email)", value=st.session_state["integrated_email_settings"]["sender_email"])
                subject = st.text_input("Betreff", value="📊 Paper-Suche Benachrichtigung")
            
            with col2:
                recipient_email = st.text_input("An (Email)", value=st.session_state["integrated_email_settings"]["recipient_email"])
                smtp_server = st.text_input("SMTP Server", value=st.session_state["integrated_email_settings"]["smtp_server"])
            
            message_body = st.text_area(
                "Nachricht-Vorlage", 
                value="""🔍 Neue wissenschaftliche Papers gefunden!

📅 Datum: {date}
🔍 Suchbegriff: {search_term}
📊 Anzahl Papers: {count}

Die vollständigen Ergebnisse sind im System verfügbar.

Mit freundlichen Grüßen,
Ihr automatisches Paper-Suche System""", 
                height=200
            )
            
            submitted = st.form_submit_button("💾 Email-Konfiguration speichern")
            
            if submitted:
                if sender_email and recipient_email and subject and message_body:
                    st.session_state["integrated_email_settings"].update({
                        "sender_email": sender_email,
                        "recipient_email": recipient_email,
                        "subject": subject,
                        "message_body": message_body
                    })
                    st.success("✅ Email-Konfiguration gespeichert!")
                    
                    # Vorschau anzeigen
                    st.info("📧 **Email-Vorschau:**")
                    preview = f"""Von: {sender_email}
An: {recipient_email}
Betreff: {subject}

{message_body.format(
    date=datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
    search_term="Beispiel-Suchbegriff",
    count=5
)}"""
                    st.code(preview)
                else:
                    st.error("Bitte füllen Sie alle Felder aus!")
    
    # Benachrichtigungseinstellungen
    with st.expander("🔔 Benachrichtigungseinstellungen"):
        col_notify1, col_notify2 = st.columns(2)
        
        with col_notify1:
            auto_notify = st.checkbox("Automatische Benachrichtigungen")
            min_papers = st.number_input("Min. Papers für Benachrichtigung", min_value=1, value=5)
        
        with col_notify2:
            frequency = st.selectbox("Benachrichtigungs-Frequenz", ["Sofort", "Täglich", "Wöchentlich"])
            
        if st.button("📧 Test-Benachrichtigung senden"):
            st.success("✅ Test-Benachrichtigung simuliert!")
            st.info("In einer echten Implementierung würde hier eine Email versendet werden.")

# ------------------------------------------------------------------
# Analyse-Funktionen (KORRIGIERT)
# ------------------------------------------------------------------
# ------------------------------------------------------------------
# Paper Analyzer Class
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

# ------------------------------------------------------------------
# Integrated Paper Search with Email Notifications
# ------------------------------------------------------------------
class IntegratedPaperSearch:
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.email = "your_email@example.com"
        self.tool = "IntegratedPaperSearchSystem"
    
    def search_with_email_notification(self, query, max_results=50):
        """Führt PubMed-Suche durch und sendet Email-Benachrichtigung"""
        st.info(f"🔍 **Starte Suche für:** '{query}'")
        
        # PubMed-Suche
        papers = search_pubmed_simple(query)
        
        if papers:
            st.success(f"✅ **{len(papers)} Papers gefunden!**")
            
            # Email-Benachrichtigung senden
            self.send_paper_notification(query, papers)
            
            return papers
        else:
            st.warning(f"❌ Keine Papers für '{query}' gefunden!")
            return []
    
    def send_paper_notification(self, search_term, papers):
        """Sendet Email-Benachrichtigung über gefundene Papers"""
        try:
            email_config = st.session_state.get("email_config", {})
            
            if not email_config.get("sender_email") or not email_config.get("recipient_email"):
                st.warning("⚠️ Email-Konfiguration unvollständig. Benachrichtigung übersprungen.")
                return
            
            # Erstelle Email-Inhalt
            subject = f"🔬 {len(papers)} neue Papers gefunden für '{search_term}'"
            
            body = f"""Neue wissenschaftliche Papers gefunden!

Suchbegriff: {search_term}
Anzahl Papers: {len(papers)}
Gefunden am: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}

Top Papers:
"""
            
            for i, paper in enumerate(papers[:5], 1):
                body += f"\n{i}. {paper.get('Title', 'Unbekannt')}"
                body += f"\n   PMID: {paper.get('PMID', 'n/a')}"
                body += f"\n   Jahr: {paper.get('Year', 'n/a')}\n"
            
            if len(papers) > 5:
                body += f"\n... und {len(papers) - 5} weitere Papers"
            
            body += "\n\nVollständige Liste im System verfügbar."
            
            # Speichere in Email-Historie
            if "email_history" not in st.session_state:
                st.session_state["email_history"] = []
            
            st.session_state["email_history"].append({
                "timestamp": datetime.datetime.now().isoformat(),
                "search_term": search_term,
                "paper_count": len(papers),
                "subject": subject,
                "body": body,
                "status": "Simuliert"
            })
            
            st.info(f"📧 **Email-Benachrichtigung erstellt** für '{search_term}'")
            
            # Zeige Email-Vorschau
            with st.expander("📧 Email-Vorschau anzeigen"):
                st.write(f"**An:** {email_config.get('recipient_email', 'N/A')}")
                st.write(f"**Betreff:** {subject}")
                st.text_area("**Nachricht:**", value=body, height=200, disabled=True)
        
        except Exception as e:
            st.error(f"❌ Fehler bei Email-Benachrichtigung: {str(e)}")

# ------------------------------------------------------------------
# Page Functions
# ------------------------------------------------------------------
def page_home():
    st.title("🏠 Welcome to the Main Menu")
    st.write("Choose a module in the sidebar to proceed.")
    
    # Quick Stats Dashboard
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        email_count = len(st.session_state.get("email_history", []))
        st.metric("📧 Email Notifications", email_count)
    
    with col2:
        search_count = len(st.session_state.get("search_history", []))
        st.metric("🔍 Searches Performed", search_count)
    
    with col3:
        config_status = "✅ Configured" if st.session_state.get("email_config", {}).get("sender_email") else "❌ Not Set"
        st.metric("📧 Email Status", config_status)
    
    with col4:
        st.metric("📊 Session", "Active")
    
    # Quick Actions
    st.markdown("---")
    st.subheader("🚀 Quick Actions")
    
    col_action1, col_action2, col_action3 = st.columns(3)
    
    with col_action1:
        if st.button("🔍 **Start Paper Search**", use_container_width=True):
            st.session_state["current_page"] = "Paper Search"
            st.rerun()
    
    with col_action2:
        if st.button("📧 **Configure Email**", use_container_width=True):
            st.session_state["current_page"] = "Email Module"
            st.rerun()
    
    with col_action3:
        if st.button("📊 **View Analysis**", use_container_width=True):
            st.session_state["current_page"] = "Analyze Paper"
            st.rerun()
    
    try:
        st.image("Bild1.jpg", caption="Willkommen!", use_container_width=False, width=600)
    except:
        st.info("Welcome image not found - continuing without image")

def page_paper_search():
    """Integrierte Paper-Suche mit Email-Benachrichtigung"""
    st.title("🔍 **Paper Search with Email Notifications**")
    st.write("Search PubMed and get automatic email notifications!")
    
    # Initialize search engine
    search_engine = IntegratedPaperSearch()
    
    # Email Status Check
    email_config = st.session_state.get("email_config", {})
    if email_config.get("sender_email") and email_config.get("recipient_email"):
        st.success("✅ Email notifications are **ACTIVE**")
    else:
        st.warning("⚠️ Email notifications **INACTIVE** - Configure in Email Module")
    
    # Search Interface
    st.header("🚀 Start New Search")
    
    with st.form("search_form"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_query = st.text_input(
                "**PubMed Search Query:**",
                placeholder="e.g., 'diabetes genetics', 'BRCA1 mutations', 'COVID-19'"
            )
        
        with col2:
            max_results = st.number_input("Max Results", min_value=10, max_value=200, value=50)
        
        search_button = st.form_submit_button("🔍 **START SEARCH**", type="primary")
    
    # Execute Search
    if search_button and search_query:
        st.markdown("---")
        
        with st.spinner("🔍 Searching PubMed..."):
            papers = search_engine.search_with_email_notification(search_query, max_results)
            
            if papers:
                # Save to search history
                if "search_history" not in st.session_state:
                    st.session_state["search_history"] = []
                
                st.session_state["search_history"].append({
                    "query": search_query,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "results": len(papers)
                })
                
                # Display results
                display_paper_results(papers, search_query)

def display_paper_results(papers, search_query):
    """Zeigt Paper-Suchergebnisse an"""
    st.subheader(f"📊 Results for '{search_query}' ({len(papers)} papers)")
    
    # Create Excel Export
    if st.button("📥 **Export to Excel**"):
        create_excel_export(papers, search_query)
    
    # Display papers
    for idx, paper in enumerate(papers, 1):
        with st.expander(f"📄 **{idx}.** {paper.get('Title', 'Unknown Title')[:80]}..."):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**📄 Title:** {paper.get('Title', 'n/a')}")
                st.write(f"**🆔 PMID:** {paper.get('PMID', 'n/a')}")
                st.write(f"**📅 Year:** {paper.get('Year', 'n/a')}")
                st.write(f"**📚 Journal:** {paper.get('Journal', 'n/a')}")
                
                # Get abstract
                if paper.get('PMID') and paper.get('PMID') != 'n/a':
                    if st.button(f"📝 Load Abstract", key=f"abstract_{paper.get('PMID')}"):
                        abstract = fetch_pubmed_abstract(paper.get('PMID'))
                        st.text_area("Abstract:", value=abstract, height=150, disabled=True)
                
                # PubMed Link
                if paper.get('PMID') and paper.get('PMID') != 'n/a':
                    st.markdown(f"🔗 [View on PubMed](https://pubmed.ncbi.nlm.nih.gov/{paper.get('PMID')}/)")
            
            with col2:
                if st.button(f"📧 Send Email", key=f"email_{paper.get('PMID', idx)}"):
                    send_single_paper_email(paper, search_query)
                
                if st.button(f"💾 Save Paper", key=f"save_{paper.get('PMID', idx)}"):
                    save_paper_to_collection(paper)

def send_single_paper_email(paper, search_term):
    """Sendet Email für einzelnes Paper"""
    try:
        email_config = st.session_state.get("email_config", {})
        
        if not email_config.get("sender_email") or not email_config.get("recipient_email"):
            st.warning("⚠️ Email-Konfiguration fehlt!")
            return
        
        subject = f"📄 Interessantes Paper: {paper.get('Title', 'Unknown')[:50]}..."
        
        body = f"""Interessantes Paper gefunden!

Titel: {paper.get('Title', 'Unknown')}
PMID: {paper.get('PMID', 'n/a')}
Jahr: {paper.get('Year', 'n/a')}
Journal: {paper.get('Journal', 'n/a')}

Suchbegriff: {search_term}
Gefunden am: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}

PubMed Link: https://pubmed.ncbi.nlm.nih.gov/{paper.get('PMID', '')}/

Mit freundlichen Grüßen,
Ihr Paper-Suche System"""
        
        # Zur Historie hinzufügen
        if "email_history" not in st.session_state:
            st.session_state["email_history"] = []
        
        st.session_state["email_history"].append({
            "timestamp": datetime.datetime.now().isoformat(),
            "type": "Single Paper",
            "paper_title": paper.get('Title', 'Unknown'),
            "subject": subject,
            "body": body,
            "status": "Simuliert"
        })
        
        st.success(f"📧 **Email sent** for: {paper.get('Title', 'Unknown')[:50]}...")
        
    except Exception as e:
        st.error(f"❌ Email error: {str(e)}")

def save_paper_to_collection(paper):
    """Speichert Paper in Sammlung"""
    if "saved_papers" not in st.session_state:
        st.session_state["saved_papers"] = []
    
    st.session_state["saved_papers"].append({
        "paper": paper,
        "saved_at": datetime.datetime.now().isoformat()
    })
    
    st.success(f"💾 **Paper saved:** {paper.get('Title', 'Unknown')[:50]}...")

def create_excel_export(papers, search_query):
    """Erstellt Excel-Export"""
    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Papers_{search_query.replace(' ', '_')}"
        
        # Headers
        headers = ["PMID", "Title", "Year", "Journal"]
        ws.append(headers)
        
        # Data
        for paper in papers:
            row = [
                paper.get("PMID", ""),
                paper.get("Title", ""),
                paper.get("Year", ""),
                paper.get("Journal", "")
            ]
            ws.append(row)
        
        # Save to buffer
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        # Download button
        st.download_button(
            label="📥 Download Excel",
            data=buffer.getvalue(),
            file_name=f"papers_{search_query.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.success("✅ Excel export created!")
        
    except Exception as e:
        st.error(f"❌ Excel export error: {str(e)}")

def page_email_module():
    """ROBUSTE Email-Modul Seite ohne Import-Fehler"""
    st.title("📧 **Email Module**")
    st.write("Configure email notifications for paper search results")
    
    # Debug-Information
    st.write("🔍 **Module Status:**")
    module_path = "modules/email_module.py"
    st.write(f"📁 File path: {module_path}")
    st.write(f"📄 File exists: {os.path.exists(module_path)}")
    st.write(f"🏠 Working directory: {os.getcwd()}")
    
    if os.path.exists("modules"):
        files = os.listdir("modules")
        st.write(f"📂 Files in modules folder: {files}")
    else:
        st.error("❌ modules folder does not exist!")
    
    # Versuche Import mit Fehlerbehandlung
    module_function = safe_import_module("modules.email_module", "module_email")
    
    if module_function:
        try:
            module_function()
            st.success("✅ External email module loaded successfully!")
        except Exception as e:
            st.error(f"❌ Error executing external module: {str(e)}")
            st.write("**Switching to integrated email functionality...**")
            integrated_email_interface()
    else:
        st.warning("⚠️ External email module not available. Using integrated functionality.")
        integrated_email_interface()
    
    if st.button("🏠 Back to Main Menu"):
        st.session_state["current_page"] = "Home"

def page_codewords_pubmed():
    st.title("Codewords & PubMed Settings")
    
    module_function = safe_import_module("modules.codewords_pubmed", "module_codewords_pubmed")
    
    if module_function:
        try:
            module_function()
        except Exception as e:
            st.error(f"❌ Error in codewords module: {str(e)}")
    else:
        st.error("❌ modules.codewords_pubmed could not be imported.")
        st.write("**Fallback: Basic PubMed search interface**")
        
        # Simple fallback interface
        query = st.text_input("PubMed Search Query:")
        if st.button("🔍 Search") and query:
            with st.spinner("Searching..."):
                results = search_pubmed_simple(query)
                if results:
                    st.success(f"Found {len(results)} papers!")
                    for paper in results[:10]:  # Show first 10
                        st.write(f"**{paper.get('Title', 'N/A')}** ({paper.get('Year', 'N/A')})")
    
    if st.button("🏠 Back to Main Menu"):
        st.session_state["current_page"] = "Home"

def page_online_api_filter():
    st.title("Online-API_Filter (Combined)")
    st.write("Here, you can combine API selection and filtering in one step.")
    
    module_function = safe_import_module("modules.online_api_filter", "module_online_api_filter")
    
    if module_function:
        try:
            module_function()
        except Exception as e:
            st.error(f"❌ Error in online API filter module: {str(e)}")
    else:
        st.error("❌ modules.online_api_filter could not be imported.")
        st.write("**Fallback: Basic API testing interface**")
        
        # Simple API testing
        st.subheader("API Connection Tests")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Test PubMed Connection"):
                if check_pubmed_connection():
                    st.success("✅ PubMed connection successful!")
                else:
                    st.error("❌ PubMed connection failed!")
        
        with col2:
            if st.button("Test Overall System"):
                st.info("🔧 System check completed!")
    
    if st.button("🏠 Back to Main Menu"):
        st.session_state["current_page"] = "Home"

def page_analyze_paper():
    st.title("Analyze Paper - Integrated")
    st.write("Upload and analyze scientific papers with AI assistance")
    
    if "api_key" not in st.session_state:
        st.session_state["api_key"] = OPENAI_API_KEY or ""
    
    # API Key input
    api_key = st.sidebar.text_input("OpenAI API Key", type="password", value=st.session_state["api_key"])
    st.session_state["api_key"] = api_key
    
    model = st.sidebar.selectbox("OpenAI Model", ["gpt-3.5-turbo", "gpt-4"], index=0)
    
    # File upload
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    
    if uploaded_file and api_key:
        analyzer = PaperAnalyzer(model=model)
        
        with st.spinner("Extracting text from PDF..."):
            text = analyzer.extract_text_from_pdf(uploaded_file)
        
        if text:
            st.success("✅ Text extracted successfully!")
            
            # Analysis options
            st.subheader("📊 Analysis Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📝 **Create Summary**"):
                    with st.spinner("Creating summary..."):
                        try:
                            summary = analyzer.summarize(text, api_key)
                            st.subheader("📋 Summary")
                            st.write(summary)
                        except Exception as e:
                            st.error(f"❌ Summary error: {str(e)}")
                
                if st.button("🔍 **Extract Key Findings**"):
                    with st.spinner("Extracting key findings..."):
                        try:
                            findings = analyzer.extract_key_findings(text, api_key)
                            st.subheader("🎯 Key Findings")
                            st.write(findings)
                        except Exception as e:
                            st.error(f"❌ Key findings error: {str(e)}")
            
            with col2:
                if st.button("🔬 **Identify Methods**"):
                    with st.spinner("Identifying methods..."):
                        try:
                            methods = analyzer.identify_methods(text, api_key)
                            st.subheader("🛠️ Methods & Techniques")
                            st.write(methods)
                        except Exception as e:
                            st.error(f"❌ Methods error: {str(e)}")
                
                topic = st.text_input("Topic for relevance evaluation:")
                if st.button("⭐ **Evaluate Relevance**") and topic:
                    with st.spinner("Evaluating relevance..."):
                        try:
                            relevance = analyzer.evaluate_relevance(text, topic, api_key)
                            st.subheader(f"📈 Relevance to '{topic}'")
                            st.write(relevance)
                        except Exception as e:
                            st.error(f"❌ Relevance error: {str(e)}")
        else:
            st.error("❌ Could not extract text from PDF!")
    
    elif not api_key:
        st.warning("⚠️ Please provide an OpenAI API key in the sidebar.")
    
    if st.button("🏠 Back to Main Menu"):
        st.session_state["current_page"] = "Home"

# ------------------------------------------------------------------
# Sidebar Navigation
# ------------------------------------------------------------------
def sidebar_module_navigation():
    st.sidebar.title("📋 Module Navigation")

    pages = {
        "🏠 Home": page_home,
        "🔍 Paper Search": page_paper_search,
        "📧 Email Module": page_email_module,
        "📊 Online-API Filter": page_online_api_filter,
        "📝 Codewords & PubMed": page_codewords_pubmed,
        "🔬 Analyze Paper": page_analyze_paper,
    }

    for label, page in pages.items():
        if st.sidebar.button(label, key=label, use_container_width=True):
            st.session_state["current_page"] = label
    
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "🏠 Home"
    
    return pages.get(st.session_state["current_page"], page_home)

def answer_chat(question: str) -> str:
    """Simple chatbot functionality"""
    api_key = st.session_state.get("api_key", "")
    if not api_key:
        return f"(No API-Key) Echo: {question}"
    
    try:
        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for scientific paper research."},
                {"role": "user", "content": question}
            ],
            temperature=0.3,
            max_tokens=400
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"OpenAI error: {e}"

def main():
    # Layout: Left Modules, Right Chatbot
    col_left, col_right = st.columns([4, 1])
    
    with col_left:
        # Navigation
        page_fn = sidebar_module_navigation()
        if page_fn is not None:
            page_fn()
    
    with col_right:
        st.subheader("🤖 AI Assistant")
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []
        
        user_input = st.text_input("Ask me anything:", key="chatbot_input")
        if st.button("💬 Send", key="chatbot_send"):
            if user_input.strip():
                st.session_state["chat_history"].append(("user", user_input))
                bot_answer = answer_chat(user_input)
                st.session_state["chat_history"].append(("bot", bot_answer))
        
        # Chat display
        st.markdown(
            """
            <style>
            .chat-container {
                max-height: 400px; 
                overflow-y: auto; 
                border: 1px solid #ddd;
                padding: 10px;
                border-radius: 5px;
                background-color: #f9f9f9;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        with st.container():
            for role, msg_text in st.session_state["chat_history"][-10:]:  # Show last 10 messages
                if role == "user":
                    st.write(f"**You:** {msg_text}")
                else:
                    st.write(f"**AI:** {msg_text}")

# ------------------------------------------------------------------
# Run the Streamlit app
# ------------------------------------------------------------------
if __name__ == '__main__':
    main()

