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

# ✅ CHONKIE INTEGRATION - Neue Imports
try:
    from chonkie import TokenChunker, SemanticChunker, SentenceChunker
    CHONKIE_AVAILABLE = True
    print("✅ Chonkie erfolgreich importiert")
except ImportError:
    CHONKIE_AVAILABLE = False
    print("⚠️ Chonkie nicht verfügbar - installiere mit: pip install chonkie")
    # Fallback-Chunker
    class FallbackChunker:
        def __init__(self, chunk_size=1000, chunk_overlap=100):
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap
        
        def chunk(self, text):
            """Einfacher Fallback-Chunker"""
            words = text.split()
            chunks = []
            for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
                chunk_words = words[i:i + self.chunk_size]
                chunk_text = ' '.join(chunk_words)
                chunks.append(type('Chunk', (), {'text': chunk_text})())
            return chunks
    
    TokenChunker = SentenceChunker = SemanticChunker = FallbackChunker

# ✅ LABEL STUDIO INTEGRATION - Neue Imports
try:
    import label_studio_sdk
    LABELSTUDIO_AVAILABLE = True
    print("✅ Label Studio SDK erfolgreich importiert")
except ImportError:
    LABELSTUDIO_AVAILABLE = False
    print("⚠️ Label Studio SDK nicht verfügbar - installiere mit: pip install label-studio-sdk")

# ✅ EMAIL NOTIFICATIONS - Neue Imports
try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    EMAIL_AVAILABLE = True
    print("✅ E-Mail-Module verfügbar")
except ImportError:
    EMAIL_AVAILABLE = False
    print("⚠️ E-Mail-Module nicht verfügbar")

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
    if os.path.exists("Bild1.jpg"):
        st.image("Bild1.jpg", caption="Willkommen!", use_container_width=False, width=600)

def page_codewords_pubmed():
    st.title("Codewords & PubMed Settings")
    st.write("Module for managing codewords and PubMed search settings.")
    
    # Dummy implementation - would normally import from modules.codewords_pubmed
    st.subheader("Codewords Configuration")
    codewords = st.text_area("Enter codewords (one per line):", height=150)
    
    st.subheader("PubMed Search Settings")
    max_results = st.slider("Maximum results:", 10, 1000, 100)
    date_range = st.selectbox("Date range:", ["Last year", "Last 5 years", "Last 10 years", "All time"])
    
    if st.button("Save Settings"):
        st.success("Settings saved successfully!")

def page_online_api_filter():
    st.title("Online-API_Filter (Combined)")
    st.write("Here, you can combine API selection and filtering in one step.")
    
    # Codewords input
    st.subheader("1. Codewords")
    codewords = st.text_area("Enter your codewords (comma-separated):", 
                           value=st.session_state.get("codewords", ""))
    st.session_state["codewords"] = codewords
    
    # Gene selection
    st.subheader("2. Gene Selection")
    available_genes = ["APOE", "BRCA1", "BRCA2", "TP53", "MTHFR", "ACE", "COMT"]
    selected_genes = st.multiselect("Select genes:", available_genes,
                                  default=st.session_state.get("selected_genes", []))
    st.session_state["selected_genes"] = selected_genes
    
    # API Selection
    st.subheader("3. API Selection")
    api_choices = {
        "PubMed": check_pubmed_connection(),
        "Europe PMC": check_europe_pmc_connection(),
        "CORE": check_core_aggregate_connection(),
        "Semantic Scholar": check_semantic_scholar_connection()
    }
    
    for api_name, is_available in api_choices.items():
        status = "✅ Available" if is_available else "❌ Unavailable"
        st.write(f"**{api_name}**: {status}")
    
    selected_apis = st.multiselect("Select APIs to search:", 
                                 [api for api, available in api_choices.items() if available])
    
    # Search button
    if st.button("Start Search"):
        if not codewords.strip():
            st.warning("Please enter codewords!")
            return
        
        search_query = codewords.strip()
        if selected_genes:
            search_query += " AND (" + " OR ".join(selected_genes) + ")"
        
        st.write(f"**Search Query**: {search_query}")
        
        all_results = []
        
        # Search each selected API
        for api_name in selected_apis:
            st.write(f"Searching {api_name}...")
            
            if api_name == "PubMed":
                results = search_pubmed_simple(search_query)
                for result in results:
                    result["Source"] = "PubMed"
                    # Get abstract
                    pmid = result.get("PMID", "")
                    if pmid and pmid != "n/a":
                        abstract = fetch_pubmed_abstract(pmid)
                        result["Abstract"] = abstract
                    else:
                        result["Abstract"] = ""
                all_results.extend(results)
            
            elif api_name == "Europe PMC":
                results = search_europe_pmc_simple(search_query)
                for result in results:
                    result["Source"] = "Europe PMC"
                    result["Abstract"] = ""  # Would need separate API call
                all_results.extend(results)
            
            elif api_name == "CORE":
                results = search_core_aggregate(search_query)
                for result in results:
                    result["Source"] = "CORE"
                    result["Abstract"] = ""  # Would need separate API call
                all_results.extend(results)
            
            elif api_name == "Semantic Scholar":
                searcher = SemanticScholarSearch()
                searcher.search_semantic_scholar(search_query)
                all_results.extend(searcher.all_results)
        
        # Store results in session state
        st.session_state["search_results"] = all_results
        
        st.write(f"**Found {len(all_results)} results total**")
        
        # Display results in a table
        if all_results:
            df = pd.DataFrame(all_results)
            st.dataframe(df)

# ------------------------------------------------------------------
# ✅ MODUL 1: CHONKIE - Import aus modules
# ------------------------------------------------------------------
try:
    from modules.chonkie_scientific_analysis import module_chonkie_search
    CHONKIE_MODULE_AVAILABLE = True
except ImportError:
    CHONKIE_MODULE_AVAILABLE = False
    def module_chonkie_search():
        st.error("Chonkie-Modul nicht gefunden!")
        st.info("Bitte erstelle die Datei /modules/chonkie_scientific_analysis.py")

# ------------------------------------------------------------------
# ✅ MODUL 2: SCIENTIFIC IMAGES - Import aus modules
# ------------------------------------------------------------------
try:
    from modules.labelstudio_scientific_images import module_scientific_images
    LABELSTUDIO_MODULE_AVAILABLE = True
except ImportError:
    LABELSTUDIO_MODULE_AVAILABLE = False
    def module_scientific_images():
        st.error("Label Studio-Modul nicht gefunden!")
        st.info("Bitte erstelle die Datei /modules/labelstudio_scientific_images.py")

# ------------------------------------------------------------------
# ✅ MODUL 3: EMAIL NOTIFICATIONS - Import aus modules
# ------------------------------------------------------------------
try:
    from modules.email_notifications import module_email_notifications
    EMAIL_MODULE_AVAILABLE = True
except ImportError:
    EMAIL_MODULE_AVAILABLE = False
    def module_email_notifications():
        st.title("📧 E-Mail-Benachrichtigungen für neue Papers")
        
        if not EMAIL_AVAILABLE:
            st.error("E-Mail-Module nicht verfügbar!")
            st.info("Installiere missing dependencies: smtplib ist normalerweise verfügbar")
            return
        
        st.success("✅ E-Mail-Benachrichtigungen verfügbar!")
        
        # Tab-Interface
        tab1, tab2, tab3, tab4 = st.tabs(["⚙️ Setup", "🔍 Suchen", "📧 Senden", "📊 Status"])
        
        with tab1:
            st.header("E-Mail Server Konfiguration")
            
            col1, col2 = st.columns(2)
            with col1:
                smtp_server = st.text_input("SMTP Server:", value="smtp.gmail.com")
                smtp_port = st.number_input("SMTP Port:", value=587, min_value=1, max_value=65535)
            
            with col2:
                sender_email = st.text_input("Absender E-Mail:")
                sender_password = st.text_input("E-Mail Passwort:", type="password")
            
            use_tls = st.checkbox("TLS verwenden", value=True)
            
            if st.button("🔧 E-Mail-Konfiguration speichern"):
                st.session_state["email_config"] = {
                    "smtp_server": smtp_server,
                    "smtp_port": smtp_port,
                    "email": sender_email,
                    "password": sender_password,
                    "use_tls": use_tls
                }
                st.success("✅ E-Mail-Konfiguration gespeichert!")
            
            st.subheader("📋 Such-Alerts konfigurieren")
            
            alert_name = st.text_input("Alert-Name:")
            keywords = st.text_input("Suchbegriffe:")
            recipient_emails = st.text_area("Empfänger E-Mails (eine pro Zeile):")
            
            databases = st.multiselect("Datenbanken:", ["PubMed", "Europe PMC", "Semantic Scholar"])
            frequency = st.selectbox("Häufigkeit:", ["Täglich", "Wöchentlich", "Monatlich"])
            
            if st.button("➕ Alert hinzufügen"):
                if "alerts" not in st.session_state:
                    st.session_state["alerts"] = []
                
                new_alert = {
                    "name": alert_name,
                    "keywords": keywords,
                    "recipients": recipient_emails.split('\n'),
                    "databases": databases,
                    "frequency": frequency,
                    "created": datetime.datetime.now().isoformat(),
                    "active": True
                }
                
                st.session_state["alerts"].append(new_alert)
                st.success(f"✅ Alert '{alert_name}' hinzugefügt!")
        
        with tab2:
            st.header("🔍 Manuelle Suche & Benachrichtigung")
            
            search_keywords = st.text_input("Suchbegriffe für einmalige Suche:")
            search_databases = st.multiselect("Datenbanken:", ["PubMed", "Europe PMC", "Semantic Scholar"], default=["PubMed"])
            days_back = st.slider("Tage zurück:", 1, 30, 7)
            
            if st.button("🔍 Suche starten"):
                if not search_keywords:
                    st.warning("Bitte Suchbegriffe eingeben!")
                    return
                
                all_papers = []
                
                with st.spinner("Suche nach neuen Papers..."):
                    if "PubMed" in search_databases:
                        pubmed_results = search_pubmed_simple(search_keywords)
                        for result in pubmed_results:
                            result["Source"] = "PubMed"
                            if result.get("PMID") != "n/a":
                                result["Abstract"] = fetch_pubmed_abstract(result["PMID"])
                        all_papers.extend(pubmed_results)
                    
                    if "Europe PMC" in search_databases:
                        pmc_results = search_europe_pmc_simple(search_keywords)
                        all_papers.extend(pmc_results)
                    
                    if "Semantic Scholar" in search_databases:
                        scholar_search = SemanticScholarSearch()
                        scholar_search.search_semantic_scholar(search_keywords)
                        all_papers.extend(scholar_search.all_results)
                
                st.session_state["found_papers"] = all_papers
                st.success(f"✅ {len(all_papers)} Papers gefunden!")
                
                # Zeige Ergebnisse
                if all_papers:
                    for i, paper in enumerate(all_papers[:5]):
                        with st.expander(f"Paper {i+1}: {paper.get('Title', 'Unbekannt')}"):
                            st.write(f"**Quelle:** {paper.get('Source', 'N/A')}")
                            st.write(f"**Jahr:** {paper.get('Year', 'N/A')}")
                            st.write(f"**Journal:** {paper.get('Journal', 'N/A')}")
                            if paper.get('Abstract'):
                                st.write(f"**Abstract:** {paper['Abstract'][:300]}...")
        
        with tab3:
            st.header("📧 E-Mail versenden")
            
            if "found_papers" not in st.session_state:
                st.info("Führe erst eine Suche durch!")
                return
            
            if "email_config" not in st.session_state:
                st.warning("Bitte erst E-Mail-Konfiguration speichern!")
                return
            
            papers = st.session_state["found_papers"]
            
            if not papers:
                st.info("Keine Papers zum Versenden gefunden.")
                return
            
            st.write(f"**Gefundene Papers:** {len(papers)}")
            
            recipient_email = st.text_input("Empfänger E-Mail:")
            email_subject = st.text_input("Betreff:", value=f"Neue wissenschaftliche Papers - {len(papers)} gefunden")
            
            include_abstracts = st.checkbox("Abstracts einschließen", value=True)
            max_papers = st.slider("Max. Papers pro E-Mail:", 1, 20, 10)
            
            # E-Mail Vorschau
            st.subheader("📄 E-Mail Vorschau")
            
            email_body = f"""
📚 Neue wissenschaftliche Papers gefunden
{'='*50}

Anzahl gefundener Papers: {len(papers)}
Datum: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

📄 Paper-Details:
{'-'*30}
"""
            
            for i, paper in enumerate(papers[:max_papers], 1):
                email_body += f"""
{i}. {paper.get('Title', 'Unbekannt')}
   📖 Journal: {paper.get('Journal', 'N/A')}
   📅 Jahr: {paper.get('Year', 'N/A')}
   🏷️ Quelle: {paper.get('Source', 'N/A')}
"""
                if include_abstracts and paper.get('Abstract'):
                    abstract = paper['Abstract'][:300] + "..." if len(paper['Abstract']) > 300 else paper['Abstract']
                    email_body += f"   📋 Abstract: {abstract}\n"
                email_body += "\n"
            
            email_body += """
{'='*50}
Diese Benachrichtigung wurde automatisch generiert.

Powered by Streamlit Scientific Paper Notification System
"""
            
            with st.expander("E-Mail Inhalt anzeigen"):
                st.code(email_body)
            
            if st.button("📧 E-Mail senden"):
                config = st.session_state["email_config"]
                
                try:
                    # SMTP-Verbindung
                    server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
                    
                    if config.get('use_tls', True):
                        server.starttls()
                    
                    server.login(config['email'], config['password'])
                    
                    # E-Mail erstellen
                    msg = MIMEMultipart()
                    msg['From'] = config['email']
                    msg['To'] = recipient_email
                    msg['Subject'] = email_subject
                    
                    # Body hinzufügen
                    msg.attach(MIMEText(email_body, 'plain', 'utf-8'))
                    
                    # E-Mail senden
                    text = msg.as_string()
                    server.sendmail(config['email'], [recipient_email], text)
                    server.quit()
                    
                    st.success(f"✅ E-Mail erfolgreich an {recipient_email} gesendet!")
                    
                except Exception as e:
                    st.error(f"❌ E-Mail-Versand fehlgeschlagen: {e}")
        
        with tab4:
            st.header("📊 Alert Status & Verwaltung")
            
            if "alerts" not in st.session_state or not st.session_state["alerts"]:
                st.info("Keine Alerts konfiguriert.")
                return
            
            st.subheader("🔔 Aktive Alerts")
            
            alerts = st.session_state["alerts"]
            
            for i, alert in enumerate(alerts):
                with st.expander(f"Alert: {alert['name']} ({'✅ Aktiv' if alert['active'] else '❌ Inaktiv'})"):
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Keywords:** {alert['keywords']}")
                        st.write(f"**Datenbanken:** {', '.join(alert['databases'])}")
                        st.write(f"**Häufigkeit:** {alert['frequency']}")
                    
                    with col2:
                        st.write(f"**Empfänger:** {len(alert['recipients'])}")
                        st.write(f"**Erstellt:** {alert['created'][:10]}")
                        st.write(f"**Status:** {'Aktiv' if alert['active'] else 'Inaktiv'}")
                    
                    # Alert-Steuerung
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        if st.button(f"▶️ Test", key=f"test_{i}"):
                            st.info(f"Test-Suche für '{alert['name']}' würde hier durchgeführt")
                    
                    with col_b:
                        if alert['active']:
                            if st.button(f"⏸️ Pausieren", key=f"pause_{i}"):
                                st.session_state["alerts"][i]['active'] = False
                                st.rerun()
                        else:
                            if st.button(f"▶️ Aktivieren", key=f"activate_{i}"):
                                st.session_state["alerts"][i]['active'] = True
                                st.rerun()
                    
                    with col_c:
                        if st.button(f"🗑️ Löschen", key=f"delete_{i}"):
                            st.session_state["alerts"].pop(i)
                            st.rerun()
            
            # Zusammenfassung
            st.subheader("📈 Zusammenfassung")
            active_alerts = sum(1 for alert in alerts if alert['active'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Gesamt Alerts", len(alerts))
            with col2:
                st.metric("Aktive Alerts", active_alerts)
            with col3:
                st.metric("Inaktive Alerts", len(alerts) - active_alerts)

# Page functions for existing modules
def page_analyze_paper():
    st.title("Analyze Paper - Integrated")
    st.write("Hier würde die Paper-Analyse-Funktionalität stehen.")
    st.info("Diese Seite ist noch nicht vollständig implementiert.")

def page_genotype_finder():
    st.title("Genotype Frequency Finder")
    st.write("Hier würde der Genotype Frequency Finder stehen.")
    st.info("Diese Seite ist noch nicht vollständig implementiert.")

def page_ai_content_detection():
    st.title("KI-Inhaltserkennung (AI Content Detector)")
    st.write("Hier würde die KI-Inhaltserkennung stehen.")
    st.info("Diese Seite ist noch nicht vollständig implementiert.")

# ------------------------------------------------------------------
# Sidebar Navigation & Chatbot (ERWEITERT mit E-Mail-Button)
# ------------------------------------------------------------------
def sidebar_module_navigation():
    st.sidebar.title("Module Navigation")
    
    # Status-Anzeige für verfügbare Tools
    st.sidebar.subheader("🔧 Tool Status")
    st.sidebar.write(f"🦛 Chonkie: {'✅' if CHONKIE_AVAILABLE else '❌'}")
    st.sidebar.write(f"🏷️ Label Studio: {'✅' if LABELSTUDIO_AVAILABLE else '❌'}")
    st.sidebar.write(f"📧 E-Mail: {'✅' if EMAIL_AVAILABLE else '❌'}")

    pages = {
        "Home": page_home,
        "🦛 Chonkie": module_chonkie_search,
        "🖼️ Abbildungen": module_scientific_images,
        "📧 Benachrichtigungen": module_email_notifications,  # ✅ NEUER BUTTON
        "Online-API_Filter": page_online_api_filter,
        "3) Codewords & PubMed": page_codewords_pubmed,
        "Analyze Paper": page_analyze_paper,
        "Genotype Frequency Finder": page_genotype_finder,
        "AI-Content Detection": page_ai_content_detection
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
        st.subheader("🤖 Chatbot")
        
        # Tool-Status im Chatbot
        if CHONKIE_AVAILABLE:
            st.caption("🦛 Chonkie verfügbar")
        if LABELSTUDIO_AVAILABLE:
            st.caption("🏷️ Label Studio verfügbar")
        if EMAIL_AVAILABLE:
            st.caption("📧 E-Mail verfügbar")
        
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []
        
        user_input = st.text_input("Your question here", key="chatbot_right_input")
        
        if st.button("Send (Chat)", key="chatbot_right_send"):
            if user_input.strip():
                st.session_state["chat_history"].append(("user", user_input))
                bot_answer = answer_chat(user_input)
                st.session_state["chat_history"].append(("bot", bot_answer))
        
        # Chat-Display
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
        
        # Auto-scroll JS
        st.markdown(
            """
            <script>
                function scrollToBottom() {
                    var container = document.getElementById('chat-container');
                    if(container) {
                        container.scrollTop = container.scrollHeight;
                    }
                }
                document.addEventListener('DOMContentLoaded', function() {
                    scrollToBottom();
                });
                const observer = new MutationObserver(function(mutations) {
                    scrollToBottom();
                });
                setTimeout(function() {
                    var container = document.getElementById('chat-container');
                    if(container) {
                        observer.observe(container, { childList: true });
                        scrollToBottom();
                    }
                }, 1000);
            </script>
            """,
            unsafe_allow_html=True
        )

# ------------------------------------------------------------------
# Actually run the Streamlit app
# ------------------------------------------------------------------
if __name__ == '__main__':
    main()
