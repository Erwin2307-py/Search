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

# Neu: Excel / openpyxl-Import
import openpyxl

# Neuer Import für die Übersetzung mit google_trans_new
from google_trans_new import google_translator

# ------------------------------------------------------------------
# Umgebungsvariablen laden (für OPENAI_API_KEY, falls vorhanden)
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
# 1) Gemeinsame Funktionen & Klassen
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
# 2) PubMed - Einfacher Check + Search
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
# 3) Europe PMC Check + Search
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
# 4) OpenAlex API
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
# 5) Google Scholar
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
# 6) Semantic Scholar
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
# 8) Weitere Module + Seiten
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
    st.write("Excel Online Search functionality would go here.")

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
# NEUE EMAIL-MODUL SEITE
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
    
    try:
        from modules.email_module import module_email
        module_email()
        st.success("✅ Email-Modul erfolgreich geladen!")
    except ImportError as e:
        st.error(f"❌ Import-Fehler: {str(e)}")
        st.error("Email-Modul konnte nicht importiert werden. Stellen Sie sicher, dass 'modules/email_module.py' existiert.")
        
        # Erstelle ein minimales Email-Modul inline
        st.write("---")
        st.write("**Fallback Email-Interface:**")
        create_fallback_email_interface()
        
    except Exception as e:
        st.error(f"❌ Allgemeiner Fehler beim Laden des Email-Moduls: {str(e)}")
    
    if st.button("Back to Main Menu"):
        st.session_state["current_page"] = "Home"

def create_fallback_email_interface():
    """Erstellt ein einfaches Email-Interface als Fallback"""
    st.subheader("📤 Email senden (Fallback)")
    
    with st.form("fallback_email_form"):
        sender_email = st.text_input("Von (Email)")
        recipient_email = st.text_input("An (Email)")
        subject = st.text_input("Betreff")
        message_body = st.text_area("Nachricht", height=200)
        
        submitted = st.form_submit_button("📤 Email senden (Dummy)")
        
        if submitted:
            if sender_email and recipient_email and subject and message_body:
                st.success("✅ Email würde gesendet werden (Dummy-Modus)")
                st.info(f"Von: {sender_email}\nAn: {recipient_email}\nBetreff: {subject}\n\nNachricht:\n{message_body}")
            else:
                st.error("Bitte füllen Sie alle Felder aus!")

# ------------------------------------------------------------------
# Analyse-Funktionen (verkürzt für Platz)
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

def page_analyze_paper():
    st.title("Analyze Paper - Integrated")
    st.write("Paper-Analyse-Funktionalität würde hier stehen...")
    
    if st.button("Back to Main Menu"):
        st.session_state["current_page"] = "Home"

# ------------------------------------------------------------------
# Sidebar Navigation & Chatbot
# ------------------------------------------------------------------
def sidebar_module_navigation():
    st.sidebar.title("Module Navigation")

    pages = {
        "Home": page_home,
        "Online-API_Filter": page_online_api_filter,
        "3) Codewords & PubMed": page_codewords_pubmed,
        "Analyze Paper": page_analyze_paper,
        "📧 Email Module": page_email_module,  # HIER ist das Email-Modul!
    }

    for label, page in pages.items():
        if st.sidebar.button(label, key=label):
            st.session_state["current_page"] = label
    
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Home"
    return pages.get(st.session_state["current_page"], page_home)

def answer_chat(question: str) -> str:
    """Simple example: uses Paper text (if available) from st.session_state + GPT."""
    api_key = st.session_state.get("api_key", "")
    paper_text = st.session_state.get("paper_text", "")
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

def main():
    # -------- LAYOUT: Left Modules, Right Chatbot --------
    col_left, col_right = st.columns([4, 1])
    
    with col_left:
        # Navigation
        page_fn = sidebar_module_navigation()
        if page_fn is not None:
            page_fn()
    
    with col_right:
        st.subheader("Chatbot")
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []
        user_input = st.text_input("Your question here", key="chatbot_right_input")
        if st.button("Send (Chat)", key="chatbot_right_send"):
            if user_input.strip():
                st.session_state["chat_history"].append(("user", user_input))
                bot_answer = answer_chat(user_input)
                st.session_state["chat_history"].append(("bot", bot_answer))
        
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
# Actually run the Streamlit app
# ------------------------------------------------------------------
if __name__ == '__main__':
    main()
