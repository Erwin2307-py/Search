# modules/automated_paper_search.py - FUNKTIONSFÄHIGES SYSTEM
import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import datetime
import json
import io
import openpyxl
import time
from typing import List, Dict, Any, Optional

class PubMedSearchEngine:
    """Echte PubMed-Suche mit esearch + efetch"""
    
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.email = "your_email@example.com"  # Erforderlich für NCBI
        self.tool = "StreamlitPaperSearch"
        
    def search_papers(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Führt komplette PubMed-Suche durch: esearch + efetch"""
        st.info(f"🔍 **Starte PubMed-Suche für:** '{query}'")
        
        # Schritt 1: esearch - hole PMIDs
        pmids = self._get_pmids(query, max_results)
        
        if not pmids:
            st.warning(f"❌ Keine Papers für '{query}' gefunden!")
            return []
        
        st.success(f"✅ **{len(pmids)} PMIDs gefunden** für '{query}'")
        
        # Schritt 2: efetch - hole Details
        papers = self._fetch_paper_details(pmids)
        
        st.success(f"🎉 **{len(papers)} vollständige Papers** für '{query}' abgerufen!")
        
        return papers
    
    def _get_pmids(self, query: str, max_results: int) -> List[str]:
        """Schritt 1: esearch - hole PMIDs"""
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
            count = data.get("esearchresult", {}).get("count", "0")
            
            st.write(f"📊 **PubMed meldet:** {count} Papers verfügbar, {len(pmids)} PMIDs abgerufen")
            return pmids
            
        except Exception as e:
            st.error(f"❌ **esearch Fehler:** {str(e)}")
            return []
    
    def _fetch_paper_details(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """Schritt 2: efetch - hole vollständige Paper-Details"""
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
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("📥 Lade Paper-Details von PubMed...")
            response = requests.get(fetch_url, params=params, timeout=60)
            response.raise_for_status()
            
            progress_bar.progress(0.5)
            status_text.text("🔧 Parse XML-Daten...")
            
            # Parse XML
            root = ET.fromstring(response.content)
            papers = []
            
            articles = root.findall(".//PubmedArticle")
            total_articles = len(articles)
            
            for idx, article in enumerate(articles):
                progress_bar.progress(0.5 + (idx + 1) / total_articles * 0.5)
                status_text.text(f"📄 Verarbeite Paper {idx + 1}/{total_articles}")
                
                paper_data = self._parse_article(article)
                if paper_data:
                    papers.append(paper_data)
                
                # Kurze Pause um nicht zu aggressiv zu sein
                time.sleep(0.1)
            
            progress_bar.empty()
            status_text.empty()
            
            return papers
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ **efetch Fehler:** {str(e)}")
            return []
    
    def _parse_article(self, article) -> Optional[Dict[str, Any]]:
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
                    import re
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
                "Search_Date": datetime.datetime.now().isoformat(),
                "Selected": False  # Für Auswahlmöglichkeit
            }
            
        except Exception as e:
            st.warning(f"⚠️ Fehler beim Parsen eines Artikels: {str(e)}")
            return None

def module_automated_paper_search():
    """Hauptfunktion des automatisierten Paper-Suche Moduls"""
    st.title("🔍 Automatisierte PubMed Paper-Suche")
    st.write("Echte PubMed-Suche mit esearch + efetch API")
    
    # Initialisiere PubMed Search Engine
    search_engine = PubMedSearchEngine()
    
    # Initialize Session State
    if "search_results" not in st.session_state:
        st.session_state["search_results"] = {}
    if "selected_papers" not in st.session_state:
        st.session_state["selected_papers"] = []
    
    # Sidebar: Sucheinstellungen
    with st.sidebar:
        st.header("🔧 Sucheinstellungen")
        max_results = st.number_input("Max. Ergebnisse pro Suche", min_value=10, max_value=500, value=50)
        
        # Aktuelle Suchbegriffe anzeigen
        st.header("📋 Bisherige Suchen")
        if st.session_state["search_results"]:
            for search_term, results in st.session_state["search_results"].items():
                st.write(f"🔍 **{search_term}**: {len(results)} Papers")
        else:
            st.info("Noch keine Suchen durchgeführt")
    
    # Hauptbereich: Suche
    st.header("🔍 Neue Suche starten")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_query = st.text_input(
            "PubMed Suchbegriff eingeben", 
            placeholder="z.B. 'diabetes genetics' oder 'BRCA1 mutations'",
            help="Verwenden Sie PubMed-Suchsyntax: AND, OR, [Title], [Author], etc."
        )
    
    with col2:
        search_button = st.button("🚀 **SUCHE STARTEN**", type="primary")
    
    # Suche durchführen
    if search_button and search_query:
        with st.spinner("🔍 Durchsuche PubMed..."):
            papers = search_engine.search_papers(search_query, max_results)
            
            if papers:
                # Speichere Ergebnisse
                st.session_state["search_results"][search_query] = papers
                st.success(f"🎉 **Suche abgeschlossen!** {len(papers)} Papers gefunden für '{search_query}'")
                st.balloons()
            else:
                st.error(f"❌ Keine Papers für '{search_query}' gefunden!")
    
    # Ergebnisse anzeigen
    if st.session_state["search_results"]:
        st.markdown("---")
        st.header("📊 Suchergebnisse")
        
        # Auswahl des Suchbegriffs
        selected_search = st.selectbox(
            "Wählen Sie eine Suche zum Anzeigen:",
            list(st.session_state["search_results"].keys()),
            key="search_selector"
        )
        
        if selected_search:
            papers = st.session_state["search_results"][selected_search]
            
            # Statistiken
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            with col_stat1:
                st.metric("📄 Gesamt Papers", len(papers))
            with col_stat2:
                selected_count = len([p for p in papers if p.get("Selected", False)])
                st.metric("✅ Ausgewählt", selected_count)
            with col_stat3:
                with_abstract = len([p for p in papers if p.get("Abstract", "") != "No abstract available"])
                st.metric("📝 Mit Abstract", with_abstract)
            with col_stat4:
                current_year = datetime.datetime.now().year
                recent = len([p for p in papers if p.get("Year", "0").isdigit() and int(p.get("Year", "0")) >= current_year - 5])
                st.metric("🆕 Letzte 5 Jahre", recent)
            
            # Aktionsbuttons
            col_action1, col_action2, col_action3, col_action4 = st.columns(4)
            
            with col_action1:
                if st.button("✅ **Alle auswählen**"):
                    for paper in papers:
                        paper["Selected"] = True
                    st.rerun()
            
            with col_action2:
                if st.button("❌ **Alle abwählen**"):
                    for paper in papers:
                        paper["Selected"] = False
                    st.rerun()
            
            with col_action3:
                selected_papers = [p for p in papers if p.get("Selected", False)]
                if selected_papers and st.button("💾 **Auswahl speichern**"):
                    save_selected_papers(selected_papers, selected_search)
            
            with col_action4:
                if st.button("📥 **Excel exportieren**"):
                    create_excel_download(papers, selected_search)
            
            # Papers anzeigen
            st.subheader(f"📋 Papers für '{selected_search}' ({len(papers)} Ergebnisse)")
            
            # Filter-Optionen
            col_filter1, col_filter2 = st.columns(2)
            with col_filter1:
                show_only_selected = st.checkbox("Nur ausgewählte Papers anzeigen")
            with col_filter2:
                show_abstracts = st.checkbox("Abstracts anzeigen", value=True)
            
            # Filtere Papers
            display_papers = papers
            if show_only_selected:
                display_papers = [p for p in papers if p.get("Selected", False)]
            
            # Zeige Papers
            for idx, paper in enumerate(display_papers):
                with st.expander(
                    f"{'✅' if paper.get('Selected', False) else '☐'} "
                    f"**{idx + 1}.** {paper.get('Title', 'Unbekannter Titel')[:100]}..."
                ):
                    col_paper1, col_paper2 = st.columns([3, 1])
                    
                    with col_paper1:
                        st.write(f"**📄 Titel:** {paper.get('Title', 'n/a')}")
                        st.write(f"**👥 Autoren:** {paper.get('Authors', 'n/a')}")
                        st.write(f"**📚 Journal:** {paper.get('Journal', 'n/a')} ({paper.get('Year', 'n/a')})")
                        st.write(f"**🆔 PMID:** {paper.get('PMID', 'n/a')}")
                        st.write(f"**🔗 DOI:** {paper.get('DOI', 'n/a')}")
                        
                        if show_abstracts and paper.get('Abstract'):
                            st.write("**📝 Abstract:**")
                            st.write(paper.get('Abstract', 'Kein Abstract verfügbar'))
                        
                        # URL Link
                        if paper.get('URL'):
                            st.markdown(f"🔗 [PubMed Link]({paper.get('URL')})")
                    
                    with col_paper2:
                        # Auswahlcheckbox
                        paper["Selected"] = st.checkbox(
                            "Auswählen", 
                            value=paper.get("Selected", False),
                            key=f"select_{paper.get('PMID', idx)}"
                        )
                        
                        # Einzelspeichern
                        if st.button(f"💾 Speichern", key=f"save_{paper.get('PMID', idx)}"):
                            save_single_paper(paper, selected_search)

def save_selected_papers(papers: List[Dict[str, Any]], search_term: str):
    """Speichert ausgewählte Papers"""
    try:
        if "saved_papers" not in st.session_state:
            st.session_state["saved_papers"] = {}
        
        timestamp = datetime.datetime.now().isoformat()
        save_key = f"{search_term}_{timestamp}"
        
        st.session_state["saved_papers"][save_key] = {
            "search_term": search_term,
            "papers": papers,
            "saved_at": timestamp,
            "count": len(papers)
        }
        
        st.success(f"✅ **{len(papers)} Papers gespeichert** unter '{save_key}'")
        
        # Zeige Speicher-Info
        with st.expander("💾 Gespeicherte Papers anzeigen"):
            for paper in papers:
                st.write(f"• {paper.get('Title', 'Unbekannt')} (PMID: {paper.get('PMID', 'n/a')})")
        
    except Exception as e:
        st.error(f"❌ Fehler beim Speichern: {str(e)}")

def save_single_paper(paper: Dict[str, Any], search_term: str):
    """Speichert einzelnes Paper"""
    try:
        if "saved_papers" not in st.session_state:
            st.session_state["saved_papers"] = {}
        
        timestamp = datetime.datetime.now().isoformat()
        save_key = f"single_{paper.get('PMID', 'unknown')}_{timestamp}"
        
        st.session_state["saved_papers"][save_key] = {
            "search_term": search_term,
            "papers": [paper],
            "saved_at": timestamp,
            "count": 1
        }
        
        st.success(f"✅ **Paper gespeichert:** {paper.get('Title', 'Unbekannt')[:50]}...")
        
    except Exception as e:
        st.error(f"❌ Fehler beim Speichern: {str(e)}")

def create_excel_download(papers: List[Dict[str, Any]], search_term: str):
    """Erstellt Excel-Download"""
    try:
        # Erstelle Excel Workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "PubMed Papers"
        
        # Headers
        headers = ["PMID", "Titel", "Autoren", "Journal", "Jahr", "DOI", "URL", "Abstract", "Ausgewählt"]
        ws.append(headers)
        
        # Daten hinzufügen
        for paper in papers:
            row = [
                paper.get("PMID", ""),
                paper.get("Title", ""),
                paper.get("Authors", ""),
                paper.get("Journal", ""),
                paper.get("Year", ""),
                paper.get("DOI", ""),
                paper.get("URL", ""),
                paper.get("Abstract", "")[:500] + "..." if len(paper.get("Abstract", "")) > 500 else paper.get("Abstract", ""),
                "Ja" if paper.get("Selected", False) else "Nein"
            ]
            ws.append(row)
        
        # Speichern in Buffer
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        # Download-Button
        st.download_button(
            label="📥 **Excel herunterladen**",
            data=buffer.getvalue(),
            file_name=f"pubmed_papers_{search_term.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.success("✅ Excel-Datei erstellt!")
        
    except Exception as e:
        st.error(f"❌ Fehler beim Excel-Export: {str(e)}")

# Zeige gespeicherte Papers
def show_saved_papers():
    """Zeigt gespeicherte Papers an"""
    if "saved_papers" in st.session_state and st.session_state["saved_papers"]:
        st.markdown("---")
        st.header("💾 Gespeicherte Papers")
        
        for save_key, save_data in st.session_state["saved_papers"].items():
            with st.expander(f"📁 {save_data['search_term']} - {save_data['count']} Papers ({save_data['saved_at'][:19]})"):
                for paper in save_data['papers']:
                    st.write(f"• **{paper.get('Title', 'Unbekannt')}** (PMID: {paper.get('PMID', 'n/a')})")
                
                if st.button(f"🗑️ Löschen", key=f"delete_{save_key}"):
                    del st.session_state["saved_papers"][save_key]
                    st.success("Gespeicherte Papers gelöscht!")
                    st.rerun()
