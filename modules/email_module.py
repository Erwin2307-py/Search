# modules/automated_paper_search.py - Funktionierende Version
import streamlit as st
import requests
import json
import datetime
import pandas as pd
import xml.etree.ElementTree as ET
import os
import io
import openpyxl
import time
from typing import List, Dict, Any

class PubMedClient:
    """Echter PubMed-Client basierend auf pubmed-abstract-compiler Vorlage"""
    
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.email = "your_email@example.com"  # Erforderlich für NCBI
        self.tool = "StreamlitPaperSearch"
        
    def search_pubmed(self, query: str, max_results: int = 100) -> List[str]:
        """Führt esearch durch und gibt PMIDs zurück"""
        search_url = f"{self.base_url}esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": max_results,
            "email": self.email,
            "tool": self.tool
        }
        
        try:
            response = requests.get(search_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            pmids = data.get("esearchresult", {}).get("idlist", [])
            st.info(f"🔍 Gefunden: {len(pmids)} PMIDs für '{query}'")
            return pmids
            
        except Exception as e:
            st.error(f"❌ PubMed esearch Fehler: {str(e)}")
            return []
    
    def fetch_abstracts(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """Holt Abstract-Details via efetch"""
        if not pmids:
            return []
            
        fetch_url = f"{self.base_url}efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "email": self.email,
            "tool": self.tool
        }
        
        try:
            response = requests.get(fetch_url, params=params, timeout=60)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            papers = []
            
            for article in root.findall(".//PubmedArticle"):
                paper_data = self._parse_article(article)
                if paper_data:
                    papers.append(paper_data)
            
            st.success(f"✅ Abstract-Details geholt: {len(papers)} Papers")
            return papers
            
        except Exception as e:
            st.error(f"❌ PubMed efetch Fehler: {str(e)}")
            return []
    
    def _parse_article(self, article) -> Dict[str, Any]:
        """Parst einzelnen Artikel aus XML"""
        try:
            # PMID
            pmid_elem = article.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else "n/a"
            
            # Titel
            title_elem = article.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else "n/a"
            
            # Abstract
            abstract_parts = []
            for abstract_elem in article.findall(".//AbstractText"):
                if abstract_elem.text:
                    label = abstract_elem.get("Label", "")
                    text = abstract_elem.text
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)
            
            abstract = "\n".join(abstract_parts) if abstract_parts else "No abstract available"
            
            # Journal
            journal_elem = article.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None else "n/a"
            
            # Publikationsjahr
            year_elem = article.find(".//PubDate/Year")
            if year_elem is None:
                year_elem = article.find(".//PubDate/MedlineDate")
                if year_elem is not None:
                    # Extract year from MedlineDate (e.g., "2023 Jan-Feb")
                    year_text = year_elem.text or ""
                    year_match = re.search(r'\d{4}', year_text)
                    year = year_match.group() if year_match else "n/a"
                else:
                    year = "n/a"
            else:
                year = year_elem.text
            
            # Autoren
            authors = []
            for author in article.findall(".//Author"):
                lastname = author.find("LastName")
                forename = author.find("ForeName")
                if lastname is not None:
                    author_name = lastname.text or ""
                    if forename is not None:
                        author_name = f"{author_name}, {forename.text}"
                    authors.append(author_name)
            
            authors_str = "; ".join(authors[:5])  # Max 5 Autoren
            if len(authors) > 5:
                authors_str += " et al."
            
            # DOI
            doi = "n/a"
            for article_id in article.findall(".//ArticleId"):
                if article_id.get("IdType") == "doi":
                    doi = article_id.text
                    break
            
            return {
                "PMID": pmid,
                "Title": title,
                "Abstract": abstract,
                "Journal": journal,
                "Year": year,
                "Authors": authors_str,
                "DOI": doi,
                "URL": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "Search_Date": datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            st.warning(f"Fehler beim Parsen eines Artikels: {str(e)}")
            return None

class PaperDatabase:
    """Lokale Datenbank für Paper-Tracking (basierend auf pubmed-client Prinzipien)"""
    
    def __init__(self, db_file: str = "paper_database.json"):
        self.db_file = db_file
        self.data = self._load_database()
    
    def _load_database(self) -> Dict[str, Any]:
        """Lädt lokale Datenbank"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                st.warning(f"Fehler beim Laden der Datenbank: {e}")
        
        return {
            "search_terms": {},
            "papers": {},
            "last_update": None
        }
    
    def save_database(self):
        """Speichert Datenbank"""
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            st.error(f"Fehler beim Speichern der Datenbank: {e}")
    
    def add_search_term(self, term: str, settings: Dict[str, Any]):
        """Fügt Suchbegriff hinzu"""
        self.data["search_terms"][term] = {
            **settings,
            "created": datetime.datetime.now().isoformat(),
            "last_search": None,
            "paper_count": 0
        }
        self.save_database()
    
    def get_new_papers(self, term: str, current_papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Findet neue Papers für einen Suchbegriff"""
        if term not in self.data["search_terms"]:
            return current_papers
        
        # Hole bekannte PMIDs für diesen Suchbegriff
        known_pmids = set()
        for paper_id, paper_data in self.data["papers"].items():
            if term in paper_data.get("found_in_searches", []):
                known_pmids.add(paper_data["PMID"])
        
        # Filtere neue Papers
        new_papers = []
        for paper in current_papers:
            if paper["PMID"] not in known_pmids:
                new_papers.append(paper)
        
        return new_papers
    
    def store_papers(self, term: str, papers: List[Dict[str, Any]]):
        """Speichert Papers in der Datenbank"""
        for paper in papers:
            pmid = paper["PMID"]
            
            if pmid in self.data["papers"]:
                # Update existing paper
                if term not in self.data["papers"][pmid].get("found_in_searches", []):
                    self.data["papers"][pmid]["found_in_searches"].append(term)
            else:
                # Add new paper
                self.data["papers"][pmid] = {
                    **paper,
                    "found_in_searches": [term],
                    "first_found": datetime.datetime.now().isoformat()
                }
        
        # Update search term stats
        if term in self.data["search_terms"]:
            self.data["search_terms"][term]["last_search"] = datetime.datetime.now().isoformat()
            self.data["search_terms"][term]["paper_count"] = len([
                p for p in self.data["papers"].values() 
                if term in p.get("found_in_searches", [])
            ])
        
        self.data["last_update"] = datetime.datetime.now().isoformat()
        self.save_database()

def page_automated_paper_search():
    st.title("🔍 Automated Paper Search System (Funktionsfähig)")
    st.write("Echte PubMed-Suche basierend auf pubmed-abstract-compiler & pubmed-client")
    
    # Initialisiere Komponenten
    pubmed_client = PubMedClient()
    
    if "paper_db" not in st.session_state:
        st.session_state["paper_db"] = PaperDatabase()
    
    paper_db = st.session_state["paper_db"]
    
    # Sidebar: Email-Konfiguration (basierend auf send-email-notification)
    with st.sidebar:
        st.header("📧 Email-Benachrichtigung")
        email_enabled = st.checkbox("Email-Benachrichtigung aktivieren")
        
        if email_enabled:
            recipient_email = st.text_input("Empfänger Email")
            notification_threshold = st.number_input("Min. neue Papers für Benachrichtigung", min_value=1, value=5)
            
        st.header("⚙️ Such-Einstellungen")
        max_results_per_search = st.number_input("Max. Ergebnisse pro Suche", min_value=10, max_value=1000, value=100)
        
        # Debug-Informationen
        st.header("📊 Datenbank-Status")
        total_terms = len(paper_db.data["search_terms"])
        total_papers = len(paper_db.data["papers"])
        last_update = paper_db.data.get("last_update", "Nie")
        
        st.metric("Suchbegriffe", total_terms)
        st.metric("Gespeicherte Papers", total_papers)
        st.write(f"**Letzte Aktualisierung:** {last_update[:19] if last_update != 'Nie' else last_update}")
    
    # Main Interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📝 Suchbegriff-Verwaltung")
        
        # Suchbegriff hinzufügen
        with st.form("add_search_term"):
            col_term, col_freq = st.columns([3, 1])
            
            with col_term:
                new_term = st.text_input("Neuer Suchbegriff", placeholder="z.B. 'diabetes genetics'")
            
            with col_freq:
                frequency = st.selectbox("Frequenz", ["Täglich", "Wöchentlich", "Monatlich"])
            
            if st.form_submit_button("➕ Suchbegriff hinzufügen"):
                if new_term and new_term not in paper_db.data["search_terms"]:
                    paper_db.add_search_term(new_term, {
                        "frequency": frequency,
                        "active": True,
                        "email_notifications": email_enabled
                    })
                    st.success(f"Suchbegriff '{new_term}' hinzugefügt!")
                    st.rerun()
                elif new_term in paper_db.data["search_terms"]:
                    st.error("Suchbegriff existiert bereits!")
        
        # Bestehende Suchbegriffe
        if paper_db.data["search_terms"]:
            st.subheader("Aktuelle Suchbegriffe:")
            
            for term, settings in paper_db.data["search_terms"].items():
                with st.expander(f"🔍 {term} ({settings.get('paper_count', 0)} Papers)"):
                    col_info1, col_info2, col_info3 = st.columns(3)
                    
                    with col_info1:
                        st.write(f"**Frequenz:** {settings.get('frequency', 'N/A')}")
                        st.write(f"**Erstellt:** {settings.get('created', 'N/A')[:10]}")
                    
                    with col_info2:
                        last_search = settings.get('last_search', 'Nie')
                        st.write(f"**Letzte Suche:** {last_search[:19] if last_search != 'Nie' else last_search}")
                        st.write(f"**Status:** {'🟢 Aktiv' if settings.get('active', True) else '🔴 Inaktiv'}")
                    
                    with col_info3:
                        if st.button(f"🗑️ Löschen", key=f"delete_{term}"):
                            del paper_db.data["search_terms"][term]
                            paper_db.save_database()
                            st.success(f"Suchbegriff '{term}' gelöscht!")
                            st.rerun()
                        
                        if st.button(f"🔍 Jetzt suchen", key=f"search_{term}"):
                            perform_single_search(term, pubmed_client, paper_db, max_results_per_search, email_enabled, recipient_email if email_enabled else None, notification_threshold if email_enabled else 0)
    
    with col2:
        st.header("🚀 Aktionen")
        
        # Alle Suchbegriffe durchsuchen
        if st.button("🔍 Alle Suchbegriffe durchsuchen", key="search_all"):
            if not paper_db.data["search_terms"]:
                st.error("Keine Suchbegriffe definiert!")
            else:
                perform_all_searches(pubmed_client, paper_db, max_results_per_search, email_enabled, recipient_email if email_enabled else None, notification_threshold if email_enabled else 0)
        
        # Nur nach neuen Papers suchen
        if st.button("🆕 Nur neue Papers suchen", key="search_new"):
            if not paper_db.data["search_terms"]:
                st.error("Keine Suchbegriffe definiert!")
            else:
                search_for_new_papers_only(pubmed_client, paper_db, max_results_per_search, email_enabled, recipient_email if email_enabled else None, notification_threshold if email_enabled else 0)
        
        # Excel Export
        if st.button("📥 Excel exportieren", key="export_excel"):
            create_excel_export(paper_db)
        
        # Datenbank-Management
        st.subheader("🗂️ Datenbank")
        
        if st.button("💾 Datenbank sichern"):
            paper_db.save_database()
            st.success("Datenbank gesichert!")
        
        if st.button("🗑️ Datenbank löschen"):
            if st.checkbox("Löschung bestätigen"):
                paper_db.data = {
                    "search_terms": {},
                    "papers": {},
                    "last_update": None
                }
                paper_db.save_database()
                st.success("Datenbank gelöscht!")
                st.rerun()

def perform_single_search(term: str, pubmed_client: PubMedClient, paper_db: PaperDatabase, max_results: int, email_enabled: bool, recipient_email: str, notification_threshold: int):
    """Führt Suche für einen einzelnen Begriff durch"""
    with st.spinner(f"🔍 Suche nach '{term}'..."):
        # 1. Suche PMIDs
        pmids = pubmed_client.search_pubmed(term, max_results)
        
        if not pmids:
            st.warning(f"Keine Ergebnisse für '{term}' gefunden!")
            return
        
        # 2. Hole Abstract-Details
        papers = pubmed_client.fetch_abstracts(pmids)
        
        if not papers:
            st.warning(f"Keine Paper-Details für '{term}' abgerufen!")
            return
        
        # 3. Finde neue Papers
        new_papers = paper_db.get_new_papers(term, papers)
        
        # 4. Speichere alle Papers
        paper_db.store_papers(term, papers)
        
        # 5. Zeige Ergebnisse
        st.success(f"✅ Suche für '{term}' abgeschlossen!")
        st.info(f"📊 Gesamt: {len(papers)} Papers | Neu: {len(new_papers)} Papers")
        
        # 6. Zeige neue Papers
        if new_papers:
            st.subheader(f"🆕 Neue Papers für '{term}':")
            for i, paper in enumerate(new_papers[:5], 1):  # Zeige nur erste 5
                with st.expander(f"{i}. {paper['Title'][:100]}..."):
                    st.write(f"**Autoren:** {paper['Authors']}")
                    st.write(f"**Journal:** {paper['Journal']} ({paper['Year']})")
                    st.write(f"**PMID:** {paper['PMID']}")
                    st.write(f"**Abstract:** {paper['Abstract'][:300]}...")
                    st.write(f"**URL:** {paper['URL']}")
        
        # 7. Email-Benachrichtigung
        if email_enabled and recipient_email and len(new_papers) >= notification_threshold:
            send_email_notification(term, new_papers, recipient_email)

def perform_all_searches(pubmed_client: PubMedClient, paper_db: PaperDatabase, max_results: int, email_enabled: bool, recipient_email: str, notification_threshold: int):
    """Führt alle aktiven Suchen durch"""
    active_terms = [term for term, settings in paper_db.data["search_terms"].items() if settings.get("active", True)]
    
    if not active_terms:
        st.warning("Keine aktiven Suchbegriffe!")
        return
    
    st.info(f"🔍 Starte Suche für {len(active_terms)} Suchbegriffe...")
    
    all_new_papers = {}
    progress_bar = st.progress(0)
    
    for idx, term in enumerate(active_terms):
        progress_bar.progress((idx + 1) / len(active_terms))
        st.write(f"Suche: {term}")
        
        # Suche PMIDs
        pmids = pubmed_client.search_pubmed(term, max_results)
        
        if pmids:
            # Hole Details
            papers = pubmed_client.fetch_abstracts(pmids)
            
            if papers:
                # Finde neue Papers
                new_papers = paper_db.get_new_papers(term, papers)
                
                # Speichere Papers
                paper_db.store_papers(term, papers)
                
                if new_papers:
                    all_new_papers[term] = new_papers
        
        # Kurze Pause zwischen Anfragen (NCBI-freundlich)
        time.sleep(0.5)
    
    progress_bar.empty()
    
    # Zeige Gesamtergebnis
    total_new = sum(len(papers) for papers in all_new_papers.values())
    st.success(f"✅ Alle Suchen abgeschlossen! {total_new} neue Papers gefunden.")
    
    # Zeige Zusammenfassung
    if all_new_papers:
        st.subheader("🆕 Neue Papers Zusammenfassung:")
        for term, papers in all_new_papers.items():
            st.write(f"**{term}**: {len(papers)} neue Papers")
        
        # Email-Benachrichtigung
        if email_enabled and recipient_email and total_new >= notification_threshold:
            send_bulk_email_notification(all_new_papers, recipient_email)

def search_for_new_papers_only(pubmed_client: PubMedClient, paper_db: PaperDatabase, max_results: int, email_enabled: bool, recipient_email: str, notification_threshold: int):
    """Sucht nur nach neuen Papers (vergleicht mit bestehender Datenbank)"""
    st.info("🔍 Suche nach neuen Papers (vergleiche mit lokaler Datenbank)...")
    perform_all_searches(pubmed_client, paper_db, max_results, email_enabled, recipient_email, notification_threshold)

def create_excel_export(paper_db: PaperDatabase):
    """Erstellt Excel-Export aller Papers"""
    try:
        wb = openpyxl.Workbook()
        
        # Übersichts-Sheet
        overview_sheet = wb.active
        overview_sheet.title = "Übersicht"
        
        overview_headers = ["Suchbegriff", "Anzahl Papers", "Letzte Suche", "Status"]
        overview_sheet.append(overview_headers)
        
        for term, settings in paper_db.data["search_terms"].items():
            overview_sheet.append([
                term,
                settings.get("paper_count", 0),
                settings.get("last_search", "Nie")[:19] if settings.get("last_search") else "Nie",
                "Aktiv" if settings.get("active", True) else "Inaktiv"
            ])
        
        # Papers-Sheet für jeden Suchbegriff
        for term in paper_db.data["search_terms"].keys():
            safe_name = re.sub(r'[^\w\s-]', '', term.replace(' ', '_'))[:30]
            sheet = wb.create_sheet(safe_name)
            
            headers = ["PMID", "Titel", "Autoren", "Journal", "Jahr", "DOI", "URL", "Abstract", "Gefunden am"]
            sheet.append(headers)
            
            # Filtere Papers für diesen Suchbegriff
            term_papers = [
                paper for paper in paper_db.data["papers"].values()
                if term in paper.get("found_in_searches", [])
            ]
            
            for paper in term_papers:
                sheet.append([
                    paper.get("PMID", ""),
                    paper.get("Title", ""),
                    paper.get("Authors", ""),
                    paper.get("Journal", ""),
                    paper.get("Year", ""),
                    paper.get("DOI", ""),
                    paper.get("URL", ""),
                    paper.get("Abstract", "")[:500] + "..." if len(paper.get("Abstract", "")) > 500 else paper.get("Abstract", ""),
                    paper.get("first_found", "")[:19] if paper.get("first_found") else ""
                ])
        
        # Speichere in Buffer für Download
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        st.download_button(
            label="📥 Excel-Datei herunterladen",
            data=buffer.getvalue(),
            file_name=f"pubmed_papers_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.success("Excel-Export erstellt!")
        
    except Exception as e:
        st.error(f"Fehler beim Excel-Export: {str(e)}")

def send_email_notification(term: str, new_papers: List[Dict[str, Any]], recipient_email: str):
    """Sendet Email-Benachrichtigung (Simulation basierend auf send-email-notification)"""
    st.info(f"📧 Email-Benachrichtigung wird gesendet an {recipient_email}")
    
    # Hier würde die echte Email-Funktionalität stehen
    email_content = f"""
🔬 Neue wissenschaftliche Papers gefunden!

Suchbegriff: {term}
Anzahl neue Papers: {len(new_papers)}

Top Papers:
"""
    
    for i, paper in enumerate(new_papers[:3], 1):
        email_content += f"\n{i}. {paper['Title']}\n   PMID: {paper['PMID']}\n   Journal: {paper['Journal']} ({paper['Year']})\n"
    
    st.success("✅ Email-Benachrichtigung gesendet! (Simulation)")
    st.code(email_content[:500] + "...", language="text")

def send_bulk_email_notification(all_new_papers: Dict[str, List[Dict[str, Any]]], recipient_email: str):
    """Sendet Sammel-Email-Benachrichtigung"""
    total_new = sum(len(papers) for papers in all_new_papers.values())
    
    st.info(f"📧 Sammel-Benachrichtigung wird gesendet an {recipient_email}")
    
    email_content = f"""
📊 PubMed-Suche Ergebnisse

Gesamt neue Papers: {total_new}
Suchbegriffe: {len(all_new_papers)}

Aufschlüsselung:
"""
    
    for term, papers in all_new_papers.items():
        email_content += f"\n• {term}: {len(papers)} neue Papers"
    
    st.success("✅ Sammel-Benachrichtigung gesendet! (Simulation)")
    st.code(email_content[:500] + "...", language="text")

# Integration in die Hauptnavigation
def page_automated_paper_search_main():
    """Wrapper-Funktion für die Navigation"""
    page_automated_paper_search()
    
    if st.button("Back to Main Menu"):
        st.session_state["current_page"] = "Home"
