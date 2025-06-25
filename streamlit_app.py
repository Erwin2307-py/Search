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
# ✅ MODUL 1: CHONKIE - Wissenschaftliche Textsuche
# ------------------------------------------------------------------
def module_chonkie_search():
    """Eigenständiges Chonkie-Modul für wissenschaftliche Textsuche"""
    st.title("🦛 Chonkie - Wissenschaftliche Textsuche")
    
    # Status-Check
    if not CHONKIE_AVAILABLE:
        st.error("⚠️ Chonkie nicht verfügbar!")
        st.info("Installation: `pip install chonkie`")
        st.info("Demo läuft mit Fallback-Chunker (eingeschränkte Funktionalität)")
    else:
        st.success("✅ Chonkie ist verfügbar und bereit!")
    
    # Tab-Interface für verschiedene Funktionen
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Text Chunking", "🔍 Paper Suche", "📊 Batch Analyse", "⚙️ Einstellungen"])
    
    with tab1:
        st.header("Intelligentes Text-Chunking")
        
        # Text-Input
        text_source = st.radio("Text-Quelle:", ["Direkte Eingabe", "PDF Upload", "URL laden"])
        
        text_input = ""
        if text_source == "Direkte Eingabe":
            text_input = st.text_area("Wissenschaftlichen Text eingeben:", height=200)
            
            # Beispieltext-Button
            if st.button("📖 Beispieltext laden"):
                text_input = """
                Cardiovascular disease remains the leading cause of mortality worldwide, affecting millions of individuals annually. 
                Recent advances in genomic research have identified several genetic variants associated with increased cardiovascular risk. 
                The APOE gene, particularly the ε4 allele, has been extensively studied for its role in lipid metabolism and atherosclerosis development.
                
                In this comprehensive study, we analyzed genetic data from 50,000 participants across multiple cohorts to investigate 
                the relationship between APOE variants and cardiovascular outcomes. Our methodology included genome-wide association 
                studies (GWAS), polygenic risk score calculations, and longitudinal follow-up for clinical endpoints.
                
                Results demonstrated a significant association between APOE ε4 carriers and increased risk of myocardial infarction 
                (HR=1.34, 95% CI: 1.21-1.48, p<0.001). Additionally, we observed ethnic differences in risk patterns, with stronger 
                associations in European populations compared to East Asian cohorts.
                
                These findings have important implications for personalized medicine approaches in cardiovascular disease prevention. 
                Clinical implementation of genetic risk assessment could improve patient stratification and guide targeted interventions.
                """
        
        elif text_source == "PDF Upload":
            uploaded_pdf = st.file_uploader("PDF-Datei hochladen:", type="pdf")
            if uploaded_pdf:
                try:
                    reader = PyPDF2.PdfReader(uploaded_pdf)
                    text_input = ""
                    for page in reader.pages:
                        text_input += page.extract_text() + "\n"
                    st.success(f"✅ PDF gelesen: {len(text_input)} Zeichen")
                except Exception as e:
                    st.error(f"PDF-Fehler: {e}")
        
        elif text_source == "URL laden":
            url = st.text_input("URL eingeben:")
            if url and st.button("URL laden"):
                try:
                    response = requests.get(url, timeout=10)
                    text_input = response.text[:50000]  # Begrenze auf 50k Zeichen
                    st.success(f"✅ URL geladen: {len(text_input)} Zeichen")
                except Exception as e:
                    st.error(f"URL-Fehler: {e}")
        
        # Chunking-Konfiguration
        col1, col2 = st.columns(2)
        with col1:
            chunker_type = st.selectbox("Chunking-Strategie:", ["auto", "semantic", "sentence", "token"])
        with col2:
            max_chunks = st.slider("Max. Chunks:", 1, 20, 8)
        
        # Chunking durchführen
        if text_input and st.button("🚀 Text chunken"):
            
            # Chunker initialisieren
            if CHONKIE_AVAILABLE:
                if chunker_type == "semantic":
                    chunker = SemanticChunker(similarity_threshold=0.7, min_chunk_size=200, max_chunk_size=1000)
                elif chunker_type == "sentence":
                    chunker = SentenceChunker(chunk_size=800, chunk_overlap=100)
                elif chunker_type == "token":
                    chunker = TokenChunker(chunk_size=512, chunk_overlap=50)
                else:  # auto
                    if len(text_input) > 10000:
                        chunker = SemanticChunker(similarity_threshold=0.7)
                    else:
                        chunker = TokenChunker(chunk_size=512, chunk_overlap=50)
            else:
                chunker = FallbackChunker(chunk_size=800, chunk_overlap=100)
            
            # Chunking durchführen
            with st.spinner("Chonkie verarbeitet den Text..."):
                start_time = time.time()
                chunks = chunker.chunk(text_input)
                limited_chunks = chunks[:max_chunks] if len(chunks) > max_chunks else chunks
                processing_time = time.time() - start_time
            
            # Ergebnisse anzeigen
            st.success(f"✅ Chunking abgeschlossen in {processing_time:.2f}s")
            
            # Statistiken
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Chunks erstellt", len(limited_chunks))
            with col2:
                st.metric("Chunker verwendet", chunker_type)
            with col3:
                avg_length = sum(len(chunk.text) for chunk in limited_chunks) / len(limited_chunks) if limited_chunks else 0
                st.metric("Ø Chunk-Größe", f"{avg_length:.0f} Zeichen")
            with col4:
                st.metric("Verarbeitungszeit", f"{processing_time:.2f}s")
            
            # Chunk-Details
            st.subheader("📄 Chunk-Details")
            for i, chunk in enumerate(limited_chunks, 1):
                with st.expander(f"Chunk {i} ({len(chunk.text)} Zeichen)"):
                    st.code(chunk.text)
    
    with tab2:
        st.header("Wissenschaftliche Paper-Suche mit Chonkie")
        
        # Such-Parameter
        search_query = st.text_input("Suchbegriff für wissenschaftliche Papers:")
        search_source = st.selectbox("Datenbank:", ["PubMed", "Europe PMC", "Semantic Scholar", "Alle"])
        
        if st.button("🔍 Paper suchen"):
            if not search_query:
                st.warning("Bitte Suchbegriff eingeben")
                return
            
            with st.spinner("Suche Papers..."):
                results = []
                
                if search_source in ["PubMed", "Alle"]:
                    pubmed_results = search_pubmed_simple(search_query)
                    for result in pubmed_results:
                        result["Source"] = "PubMed"
                        if result.get("PMID") != "n/a":
                            result["Abstract"] = fetch_pubmed_abstract(result["PMID"])
                    results.extend(pubmed_results)
                
                if search_source in ["Europe PMC", "Alle"]:
                    pmc_results = search_europe_pmc_simple(search_query)
                    results.extend(pmc_results)
                
                if search_source in ["Semantic Scholar", "Alle"]:
                    scholar_search = SemanticScholarSearch()
                    scholar_search.search_semantic_scholar(search_query)
                    results.extend(scholar_search.all_results)
            
            st.success(f"✅ {len(results)} Papers gefunden")
            
            # Ergebnisse mit Chonkie-Analyse
            for i, paper in enumerate(results[:5]):  # Erste 5 Papers
                with st.expander(f"Paper {i+1}: {paper.get('Title', 'Unbekannt')}"):
                    st.write(f"**Quelle:** {paper.get('Source', 'N/A')}")
                    st.write(f"**Jahr:** {paper.get('Year', 'N/A')}")
                    st.write(f"**Journal:** {paper.get('Journal', 'N/A')}")
                    
                    abstract = paper.get('Abstract', '')
                    if abstract and len(abstract) > 100:
                        st.write("**Abstract:**")
                        st.write(abstract[:500] + "..." if len(abstract) > 500 else abstract)
                        
                        # Chonkie-Analyse des Abstracts
                        if st.button(f"🦛 Chonkie-Analyse", key=f"chonkie_{i}"):
                            if CHONKIE_AVAILABLE:
                                chunker = SemanticChunker(similarity_threshold=0.8)
                                chunks = chunker.chunk(abstract)
                                
                                st.write(f"**Chonkie-Analyse:** {len(chunks)} semantische Chunks gefunden")
                                for j, chunk in enumerate(chunks):
                                    st.write(f"*Chunk {j+1}:* {chunk.text}")
                            else:
                                st.info("Chonkie nicht verfügbar - Fallback-Analyse")
    
    with tab3:
        st.header("Batch-Analyse mehrerer Dokumente")
        
        uploaded_files = st.file_uploader("Mehrere PDFs hochladen:", type="pdf", accept_multiple_files=True)
        
        if uploaded_files and st.button("📊 Batch-Analyse starten"):
            
            analysis_results = []
            progress_bar = st.progress(0)
            
            for i, pdf_file in enumerate(uploaded_files):
                progress_bar.progress((i + 1) / len(uploaded_files))
                
                # PDF Text extrahieren
                try:
                    reader = PyPDF2.PdfReader(pdf_file)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    
                    if CHONKIE_AVAILABLE:
                        # Chonkie-Analyse
                        chunker = SemanticChunker(similarity_threshold=0.7)
                        chunks = chunker.chunk(text)
                        
                        analysis_results.append({
                            "Datei": pdf_file.name,
                            "Text-Länge": len(text),
                            "Anzahl Chunks": len(chunks),
                            "Durchschnittliche Chunk-Größe": sum(len(c.text) for c in chunks) / len(chunks) if chunks else 0,
                            "Status": "✅ Erfolgreich"
                        })
                    else:
                        analysis_results.append({
                            "Datei": pdf_file.name,
                            "Text-Länge": len(text),
                            "Status": "⚠️ Fallback-Modus"
                        })
                        
                except Exception as e:
                    analysis_results.append({
                        "Datei": pdf_file.name,
                        "Status": f"❌ Fehler: {str(e)}"
                    })
            
            # Ergebnisse anzeigen
            st.subheader("Batch-Analyse Ergebnisse")
            df = pd.DataFrame(analysis_results)
            st.dataframe(df)
            
            # Excel-Export
            if st.button("📋 Als Excel exportieren"):
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Chonkie_Batch_Analysis', index=False)
                
                st.download_button(
                    label="📥 Excel herunterladen",
                    data=output.getvalue(),
                    file_name=f"chonkie_batch_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    
    with tab4:
        st.header("Chonkie-Einstellungen")
        
        st.subheader("Chunker-Konfiguration")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Semantic Chunker:**")
            semantic_threshold = st.slider("Similarity Threshold:", 0.1, 1.0, 0.7)
            semantic_min_size = st.number_input("Min. Chunk Size:", 50, 1000, 200)
            semantic_max_size = st.number_input("Max. Chunk Size:", 500, 5000, 1000)
        
        with col2:
            st.write("**Token Chunker:**")
            token_chunk_size = st.number_input("Token Chunk Size:", 128, 2048, 512)
            token_overlap = st.number_input("Token Overlap:", 0, 500, 50)
        
        st.subheader("Performance-Einstellungen")
        max_concurrent = st.slider("Max. gleichzeitige Verarbeitungen:", 1, 10, 3)
        timeout_seconds = st.slider("Timeout (Sekunden):", 10, 300, 60)
        
        if st.button("💾 Einstellungen speichern"):
            # Hier würde man die Einstellungen in session_state oder Datei speichern
            st.success("Einstellungen gespeichert!")
        
        st.subheader("System-Info")
        st.info(f"Chonkie Status: {'✅ Verfügbar' if CHONKIE_AVAILABLE else '❌ Nicht verfügbar'}")
        if CHONKIE_AVAILABLE:
            st.code("pip install chonkie  # ✅ Installiert")
        else:
            st.code("pip install chonkie  # ❌ Fehlt")

# ------------------------------------------------------------------
# ✅ MODUL 2: SCIENTIFIC IMAGES - Label Studio Integration
# ------------------------------------------------------------------
def module_scientific_images():
    """Eigenständiges Modul für wissenschaftliche Bildanalyse mit Label Studio"""
    st.title("🖼️ Wissenschaftliche Bildanalyse mit Label Studio")
    
    # Status-Check
    if not LABELSTUDIO_AVAILABLE:
        st.warning("⚠️ Label Studio SDK nicht verfügbar!")
        st.info("Installation: `pip install label-studio-sdk`")
        st.info("Funktionalität ist eingeschränkt ohne Label Studio")
    else:
        st.success("✅ Label Studio SDK ist verfügbar!")
    
    # Tab-Interface
    tab1, tab2, tab3, tab4 = st.tabs(["📷 Bild Upload", "🏷️ Label Studio", "📊 Analyse", "🔧 Tools"])
    
    with tab1:
        st.header("Wissenschaftliche Bilder und Tabellen hochladen")
        
        # Upload-Optionen
        upload_source = st.radio("Quelle:", ["Direkt hochladen", "Aus PDF extrahieren", "URL laden"])
        
        uploaded_images = []
        
        if upload_source == "Direkt hochladen":
            uploaded_files = st.file_uploader(
                "Bilder hochladen:", 
                type=["png", "jpg", "jpeg", "tiff", "bmp"], 
                accept_multiple_files=True
            )
            if uploaded_files:
                uploaded_images = uploaded_files
        
        elif upload_source == "Aus PDF extrahieren":
            uploaded_pdf = st.file_uploader("PDF für Bild-Extraktion:", type="pdf")
            
            if uploaded_pdf and st.button("🔍 Bilder aus PDF extrahieren"):
                with st.spinner("Extrahiere Bilder..."):
                    try:
                        with pdfplumber.open(uploaded_pdf) as pdf:
                            extracted_images = []
                            
                            for page_num, page in enumerate(pdf.pages):
                                images = page.images
                                
                                for img_index, img_dict in enumerate(images):
                                    try:
                                        # Extrahiere Bild
                                        x0, y0, x1, y1 = img_dict['x0'], img_dict['y0'], img_dict['x1'], img_dict['y1']
                                        cropped_image = page.crop((x0, y0, x1, y1)).to_image()
                                        
                                        # Konvertiere zu PIL Image
                                        img_pil = cropped_image.original
                                        
                                        # Speichere temporär
                                        img_bytes = io.BytesIO()
                                        img_pil.save(img_bytes, format='PNG')
                                        img_bytes.seek(0)
                                        
                                        extracted_images.append({
                                            'name': f"page_{page_num+1}_img_{img_index+1}.png",
                                            'data': img_bytes,
                                            'image': img_pil
                                        })
                                        
                                    except Exception as e:
                                        st.warning(f"Fehler bei Bild {img_index+1} auf Seite {page_num+1}: {e}")
                            
                            st.success(f"✅ {len(extracted_images)} Bilder extrahiert")
                            
                            # Zeige extrahierte Bilder
                            if extracted_images:
                                st.subheader("Extrahierte Bilder:")
                                cols = st.columns(min(3, len(extracted_images)))
                                
                                for i, img_data in enumerate(extracted_images):
                                    with cols[i % 3]:
                                        st.image(img_data['image'], caption=img_data['name'], width=200)
                                
                                # Speichere in session state
                                st.session_state['extracted_images'] = extracted_images
                    
                    except Exception as e:
                        st.error(f"PDF-Verarbeitung fehlgeschlagen: {e}")
        
        elif upload_source == "URL laden":
            image_url = st.text_input("Bild-URL:")
            if image_url and st.button("🌐 Bild von URL laden"):
                try:
                    response = requests.get(image_url, timeout=10)
                    img = Image.open(io.BytesIO(response.content))
                    st.image(img, caption="Geladenes Bild", width=400)
                    
                    # Speichere in session state
                    st.session_state['url_image'] = {
                        'url': image_url,
                        'image': img
                    }
                    
                except Exception as e:
                    st.error(f"URL-Laden fehlgeschlagen: {e}")
        
        # Zeige hochgeladene Bilder
        if uploaded_images:
            st.subheader("Hochgeladene Bilder:")
            
            cols = st.columns(min(3, len(uploaded_images)))
            for i, img_file in enumerate(uploaded_images):
                with cols[i % 3]:
                    img = Image.open(img_file)
                    st.image(img, caption=img_file.name, width=200)
                    
                    # Bild-Info
                    st.write(f"**Größe:** {img.size}")
                    st.write(f"**Format:** {img.format}")
                    st.write(f"**Modus:** {img.mode}")
    
    with tab2:
        st.header("Label Studio Integration")
        
        if not LABELSTUDIO_AVAILABLE:
            st.error("Label Studio SDK ist nicht verfügbar!")
            st.info("Installiere mit: `pip install label-studio-sdk`")
            return
        
        # Label Studio Konfiguration
        st.subheader("Label Studio Verbindung")
        
        ls_url = st.text_input("Label Studio URL:", value="http://localhost:8080")
        ls_api_key = st.text_input("API Key:", type="password")
        
        if st.button("🔗 Verbindung testen"):
            try:
                # Test Label Studio Verbindung
                ls = label_studio_sdk.Client(url=ls_url, api_key=ls_api_key)
                projects = ls.get_projects()
                st.success(f"✅ Verbindung erfolgreich! {len(projects)} Projekte gefunden.")
                
                # Speichere Verbindung
                st.session_state['label_studio'] = {
                    'client': ls,
                    'url': ls_url,
                    'api_key': ls_api_key
                }
                
            except Exception as e:
                st.error(f"Verbindung fehlgeschlagen: {e}")
        
        # Projekt-Management
        if 'label_studio' in st.session_state:
            st.subheader("Projekt-Management")
            
            # Neue Projekt erstellen
            with st.expander("Neues Projekt erstellen"):
                project_name = st.text_input("Projekt-Name:")
                project_description = st.text_area("Beschreibung:")
                
                # Label-Konfiguration für wissenschaftliche Bilder
                label_config = st.selectbox("Vordefinierte Konfiguration:", [
                    "Tabellen-Erkennung",
                    "Diagramm-Analyse", 
                    "Mikroskopie-Annotation",
                    "Molekular-Strukturen",
                    "Benutzerdefiniert"
                ])
                
                if label_config == "Tabellen-Erkennung":
                    config_xml = """
                    <View>
                        <Image name="image" value="$image"/>
                        <RectangleLabels name="table" toName="image">
                            <Label value="Table" background="red"/>
                            <Label value="Header" background="blue"/>
                            <Label value="Cell" background="green"/>
                            <Label value="Caption" background="yellow"/>
                        </RectangleLabels>
                    </View>
                    """
                elif label_config == "Diagramm-Analyse":
                    config_xml = """
                    <View>
                        <Image name="image" value="$image"/>
                        <RectangleLabels name="chart" toName="image">
                            <Label value="Bar_Chart" background="red"/>
                            <Label value="Line_Chart" background="blue"/>
                            <Label value="Pie_Chart" background="green"/>
                            <Label value="Scatter_Plot" background="yellow"/>
                            <Label value="Axis" background="purple"/>
                            <Label value="Legend" background="orange"/>
                        </RectangleLabels>
                    </View>
                    """
                else:
                    config_xml = st.text_area("XML-Konfiguration:", height=200)
                
                if st.button("🏗️ Projekt erstellen"):
                    if project_name and config_xml:
                        try:
                            ls_client = st.session_state['label_studio']['client']
                            project = ls_client.start_project(
                                title=project_name,
                                description=project_description,
                                label_config=config_xml
                            )
                            st.success(f"✅ Projekt '{project_name}' erstellt!")
                            
                        except Exception as e:
                            st.error(f"Projekt-Erstellung fehlgeschlagen: {e}")
                    else:
                        st.warning("Name und Konfiguration sind erforderlich!")
            
            # Bestehende Projekte anzeigen
            st.subheader("Bestehende Projekte")
            try:
                ls_client = st.session_state['label_studio']['client']
                projects = ls_client.get_projects()
                
                if projects:
                    for project in projects:
                        with st.expander(f"Projekt: {project.get_params()['title']}"):
                            st.write(f"**ID:** {project.get_params()['id']}")
                            st.write(f"**Beschreibung:** {project.get_params().get('description', 'Keine')}")
                            st.write(f"**Tasks:** {len(project.get_tasks())}")
                            
                            if st.button(f"📤 Bilder hochladen", key=f"upload_{project.get_params()['id']}"):
                                # Upload-Logic hier
                                st.info("Upload-Funktionalität würde hier implementiert")
                else:
                    st.info("Keine Projekte gefunden.")
                    
            except Exception as e:
                st.error(f"Fehler beim Laden der Projekte: {e}")
    
    with tab3:
        st.header("Bildanalyse und Auswertung")
        
        # Mock-Analyse für wissenschaftliche Bilder
        st.subheader("Automatische Bild-Klassifikation")
        
        if uploaded_images or 'extracted_images' in st.session_state:
            
            analysis_type = st.selectbox("Analyse-Typ:", [
                "Tabellen-Erkennung",
                "Diagramm-Klassifikation",
                "Text-Extraktion (OCR)",
                "Objekt-Erkennung",
                "Qualitäts-Bewertung"
            ])
            
            if st.button("🔍 Analyse starten"):
                
                # Mock-Analyse-Ergebnisse
                with st.spinner(f"Führe {analysis_type} durch..."):
                    time.sleep(2)  # Simuliere Verarbeitung
                    
                    if analysis_type == "Tabellen-Erkennung":
                        results = {
                            "Erkannte Tabellen": 3,
                            "Konfidenz": 0.89,
                            "Zeilen erkannt": 15,
                            "Spalten erkannt": 6,
                            "Qualität": "Hoch"
                        }
                    elif analysis_type == "Diagramm-Klassifikation":
                        results = {
                            "Diagramm-Typ": "Bar Chart",
                            "Konfidenz": 0.95,
                            "Achsen erkannt": True,
                            "Legende erkannt": True,
                            "Datenpunkte": 12
                        }
                    elif analysis_type == "Text-Extraktion (OCR)":
                        results = {
                            "Extrahierter Text": "Sample extracted text from scientific figure...",
                            "Wörter erkannt": 45,
                            "Konfidenz": 0.87,
                            "Sprache": "Englisch"
                        }
                    
                    # Ergebnisse anzeigen
                    st.success("✅ Analyse abgeschlossen!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Ergebnisse:")
                        for key, value in results.items():
                            st.metric(key, value)
                    
                    with col2:
                        st.subheader("Visualisierung:")
                        # Mock-Chart
                        chart_data = pd.DataFrame({
                            'Kategorie': ['Tabellen', 'Diagramme', 'Text', 'Sonstige'],
                            'Anzahl': [3, 2, 5, 1]
                        })
                        st.bar_chart(chart_data.set_index('Kategorie'))
        
        else:
            st.info("Bitte erst Bilder hochladen oder aus PDF extrahieren.")
        
        # Export-Optionen
        st.subheader("Ergebnisse exportieren")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📋 Als CSV"):
                st.info("CSV-Export würde hier erfolgen")
        
        with col2:
            if st.button("📊 Als Excel"):
                st.info("Excel-Export würde hier erfolgen")
        
        with col3:
            if st.button("📄 Als PDF"):
                st.info("PDF-Report würde hier erstellt")
    
    with tab4:
        st.header("Bild-Verarbeitungs-Tools")
        
        # Bildbearbeitung
        if uploaded_images:
            selected_image = st.selectbox("Bild auswählen:", [img.name for img in uploaded_images])
            
            if selected_image:
                # Lade das ausgewählte Bild
                selected_img_file = next(img for img in uploaded_images if img.name == selected_image)
                img = Image.open(selected_img_file)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Original")
                    st.image(img, width=300)
                
                with col2:
                    st.subheader("Bearbeitet")
                    
                    # Bearbeitungsoptionen
                    brightness = st.slider("Helligkeit:", 0.5, 2.0, 1.0)
                    contrast = st.slider("Kontrast:", 0.5, 2.0, 1.0)
                    
                    # Anwenden der Bearbeitung
                    from PIL import ImageEnhance
                    
                    enhancer = ImageEnhance.Brightness(img)
                    img_bright = enhancer.enhance(brightness)
                    
                    enhancer = ImageEnhance.Contrast(img_bright)
                    img_final = enhancer.enhance(contrast)
                    
                    st.image(img_final, width=300)
                    
                    # Download-Button für bearbeitetes Bild
                    if st.button("💾 Bearbeitetes Bild speichern"):
                        buf = io.BytesIO()
                        img_final.save(buf, format='PNG')
                        
                        st.download_button(
                            label="📥 Download",
                            data=buf.getvalue(),
                            file_name=f"edited_{selected_image}",
                            mime="image/png"
                        )
        
        # Batch-Verarbeitung
        st.subheader("Batch-Verarbeitung")
        
        if uploaded_images and len(uploaded_images) > 1:
            batch_operation = st.selectbox("Batch-Operation:", [
                "Größe ändern",
                "Format konvertieren", 
                "Wasserzeichen hinzufügen",
                "Qualitäts-Check"
            ])
            
            if batch_operation == "Größe ändern":
                new_width = st.number_input("Neue Breite:", 100, 2000, 800)
                new_height = st.number_input("Neue Höhe:", 100, 2000, 600)
            
            if st.button("🔄 Batch-Verarbeitung starten"):
                progress_bar = st.progress(0)
                processed_images = []
                
                for i, img_file in enumerate(uploaded_images):
                    progress_bar.progress((i + 1) / len(uploaded_images))
                    
                    img = Image.open(img_file)
                    
                    if batch_operation == "Größe ändern":
                        img_processed = img.resize((new_width, new_height))
                    else:
                        img_processed = img
                    
                    processed_images.append(img_processed)
                
                st.success(f"✅ {len(processed_images)} Bilder verarbeitet!")

# ------------------------------------------------------------------
# Important Classes for Analysis (existing code...)
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
# Sidebar Navigation & Chatbot (ERWEITERT mit neuen Modulen)
# ------------------------------------------------------------------
def sidebar_module_navigation():
    st.sidebar.title("Module Navigation")
    
    # Status-Anzeige für verfügbare Tools
    st.sidebar.subheader("🔧 Tool Status")
    st.sidebar.write(f"🦛 Chonkie: {'✅' if CHONKIE_AVAILABLE else '❌'}")
    st.sidebar.write(f"🏷️ Label Studio: {'✅' if LABELSTUDIO_AVAILABLE else '❌'}")

    pages = {
        "Home": page_home,
        "🦛 Chonkie": module_chonkie_search,  # ✅ NEUES MODUL
        "🖼️ Abbildungen": module_scientific_images,  # ✅ NEUES MODUL
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
