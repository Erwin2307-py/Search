# modules/automated_paper_search.py - FUNKTIONSFÄHIGE PAPER-SUCHE
import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import datetime
import json
import io
import openpyxl
import time
import re
from typing import List, Dict, Any

class PubMedSearchEngine:
    """Echte PubMed-Suche mit esearch + efetch"""
    
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.email = "your_email@example.com"
        self.tool = "StreamlitPaperSearch"
        
    def search_papers(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Führt komplette PubMed-Suche durch"""
        st.info(f"🔍 **Starte PubMed-Suche für:** '{query}'")
        
        # 1. Hole PMIDs
        pmids = self._get_pmids(query, max_results)
        if not pmids:
            st.error(f"❌ Keine Papers für '{query}' gefunden!")
            return []
        
        st.success(f"✅ **{len(pmids)} PMIDs gefunden** für '{query}'")
        
        # 2. Hole Details
        papers = self._fetch_paper_details(pmids)
        st.success(f"🎉 **{len(papers)} vollständige Papers** abgerufen!")
        
        return papers
    
    def _get_pmids(self, query: str, max_results: int) -> List[str]:
        """esearch - hole PMIDs"""
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
            st.write(f"📊 **PubMed meldet:** {count} Papers verfügbar")
            return pmids
        except Exception as e:
            st.error(f"❌ esearch Fehler: {str(e)}")
            return []
    
    def _fetch_paper_details(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """efetch - hole Paper-Details"""
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
            status_text.text("📥 Lade Paper-Details...")
            response = requests.get(fetch_url, params=params, timeout=60)
            response.raise_for_status()
            
            progress_bar.progress(0.5)
            status_text.text("🔧 Parse XML-Daten...")
            
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
                time.sleep(0.1)
            
            progress_bar.empty()
            status_text.empty()
            return papers
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ efetch Fehler: {str(e)}")
            return []
    
    def _parse_article(self, article) -> Dict[str, Any]:
        """Parst einzelnen Artikel"""
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
            
            # Jahr
            year_elem = article.find(".//PubDate/Year")
            if year_elem is None:
                year_elem = article.find(".//PubDate/MedlineDate")
                if year_elem is not None:
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
            
            authors_str = "; ".join(authors[:5])
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
                "Selected": False
            }
            
        except Exception as e:
            st.warning(f"⚠️ Parsing-Fehler: {str(e)}")
            return None

def module_automated_paper_search():
    """Hauptfunktion des Paper-Suche Moduls"""
    st.title("🔍 **FUNKTIONSFÄHIGE PubMed Paper-Suche**")
    st.write("Echte PubMed-Suche mit sofortigen Ergebnissen!")
    
    # Initialize
    search_engine = PubMedSearchEngine()
    
    if "search_results" not in st.session_state:
        st.session_state["search_results"] = {}
    if "selected_papers" not in st.session_state:
        st.session_state["selected_papers"] = []
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Sucheinstellungen")
        max_results = st.number_input("Max. Ergebnisse", min_value=10, max_value=200, value=50)
        
        st.header("📋 Bisherige Suchen")
        if st.session_state["search_results"]:
            for search_term, results in st.session_state["search_results"].items():
                st.write(f"🔍 **{search_term}**: {len(results)} Papers")
        else:
            st.info("Noch keine Suchen")
    
    # HAUPT-SUCHBEREICH
    st.header("🚀 **NEUE SUCHE STARTEN**")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        search_query = st.text_input(
            "**PubMed Suchbegriff:**", 
            placeholder="z.B. 'diabetes genetics', 'BRCA1 mutations', 'COVID-19 treatment'",
            help="Verwenden Sie PubMed-Syntax: AND, OR, [Title], [Author]"
        )
    
    with col2:
        search_button = st.button("🔍 **SUCHEN**", type="primary", use_container_width=True)
    
    # SUCHE DURCHFÜHREN
    if search_button and search_query:
        st.markdown("---")
        st.subheader(f"📊 Suchergebnisse für: '{search_query}'")
        
        with st.spinner("🔍 Durchsuche PubMed-Datenbank..."):
            papers = search_engine.search_papers(search_query, max_results)
            
            if papers:
                # Speichere Ergebnisse
                st.session_state["search_results"][search_query] = papers
                
                # SUCCESS MESSAGE
                st.success(f"🎉 **{len(papers)} Papers gefunden!**")
                st.balloons()
                
                # SOFORTIGE ERGEBNISANZEIGE
                display_search_results(papers, search_query)
            else:
                st.error(f"❌ Keine Papers für '{search_query}' gefunden!")
    
    # FRÜHERE SUCHERGEBNISSE ANZEIGEN
    if st.session_state["search_results"] and not search_button:
        st.markdown("---")
        st.header("📚 Gespeicherte Suchergebnisse")
        
        search_tabs = st.tabs(list(st.session_state["search_results"].keys()))
        
        for idx, (search_term, papers) in enumerate(st.session_state["search_results"].items()):
            with search_tabs[idx]:
                display_search_results(papers, search_term)

def display_search_results(papers: List[Dict[str, Any]], search_term: str):
    """Zeigt Suchergebnisse mit allen Funktionen an"""
    
    # STATISTIKEN
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
    
    # AKTIONSBUTTONS
    col_action1, col_action2, col_action3, col_action4 = st.columns(4)
    
    with col_action1:
        if st.button("✅ **Alle auswählen**", key=f"select_all_{search_term}"):
            for paper in papers:
                paper["Selected"] = True
            st.rerun()
    
    with col_action2:
        if st.button("❌ **Alle abwählen**", key=f"deselect_all_{search_term}"):
            for paper in papers:
                paper["Selected"] = False
            st.rerun()
    
    with col_action3:
        selected_papers = [p for p in papers if p.get("Selected", False)]
        if st.button(f"💾 **{len(selected_papers)} Papers speichern**", key=f"save_{search_term}"):
            if selected_papers:
                save_papers_to_session(selected_papers, search_term)
            else:
                st.warning("⚠️ Keine Papers ausgewählt!")
    
    with col_action4:
        if st.button("📥 **Excel herunterladen**", key=f"excel_{search_term}"):
            create_excel_download(papers, search_term)
    
    # FILTER-OPTIONEN
    st.markdown("---")
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        show_only_selected = st.checkbox("Nur ausgewählte Papers", key=f"filter_selected_{search_term}")
    with col_filter2:
        show_abstracts = st.checkbox("Abstracts anzeigen", value=True, key=f"show_abstracts_{search_term}")
    with col_filter3:
        papers_per_page = st.number_input("Papers pro Seite", min_value=5, max_value=50, value=10, key=f"per_page_{search_term}")
    
    # PAPERS ANZEIGEN
    display_papers = papers
    if show_only_selected:
        display_papers = [p for p in papers if p.get("Selected", False)]
    
    st.subheader(f"📋 Papers ({len(display_papers)} von {len(papers)})")
    
    # PAGINIERUNG
    total_pages = (len(display_papers) - 1) // papers_per_page + 1 if display_papers else 0
    if total_pages > 1:
        page = st.selectbox(f"Seite (1-{total_pages})", range(1, total_pages + 1), key=f"page_{search_term}") - 1
        start_idx = page * papers_per_page
        end_idx = start_idx + papers_per_page
        page_papers = display_papers[start_idx:end_idx]
    else:
        page_papers = display_papers
    
    # PAPERS LISTE
    for idx, paper in enumerate(page_papers):
        paper_idx = display_papers.index(paper) + 1
        
        # PAPER HEADER
        selected_icon = "✅" if paper.get("Selected", False) else "☐"
        header = f"{selected_icon} **{paper_idx}.** {paper.get('Title', 'Unbekannter Titel')[:80]}..."
        
        with st.expander(header):
            col_paper1, col_paper2 = st.columns([3, 1])
            
            with col_paper1:
                # PAPER DETAILS
                st.markdown(f"**📄 Titel:** {paper.get('Title', 'n/a')}")
                st.markdown(f"**👥 Autoren:** {paper.get('Authors', 'n/a')}")
                st.markdown(f"**📚 Journal:** {paper.get('Journal', 'n/a')} ({paper.get('Year', 'n/a')})")
                
                col_ids1, col_ids2 = st.columns(2)
                with col_ids1:
                    st.markdown(f"**🆔 PMID:** {paper.get('PMID', 'n/a')}")
                with col_ids2:
                    st.markdown(f"**🔗 DOI:** {paper.get('DOI', 'n/a')}")
                
                # ABSTRACT
                if show_abstracts and paper.get('Abstract'):
                    st.markdown("**📝 Abstract:**")
                    abstract_text = paper.get('Abstract', 'Kein Abstract verfügbar')
                    if len(abstract_text) > 500:
                        st.text_area("", value=abstract_text, height=150, key=f"abstract_{paper.get('PMID', idx)}", disabled=True)
                    else:
                        st.write(abstract_text)
                
                # LINKS
                if paper.get('URL'):
                    st.markdown(f"🔗 [**PubMed ansehen**]({paper.get('URL')})")
            
            with col_paper2:
                # AUSWAHL
                paper["Selected"] = st.checkbox(
                    "**Auswählen**", 
                    value=paper.get("Selected", False),
                    key=f"select_{paper.get('PMID', idx)}_{search_term}"
                )
                
                # EINZELSPEICHERN
                if st.button("💾 **Speichern**", key=f"save_single_{paper.get('PMID', idx)}_{search_term}"):
                    save_single_paper(paper, search_term)
                
                # BEWERTUNG
                paper["Rating"] = st.select_slider(
                    "Relevanz", 
                    options=[1,2,3,4,5], 
                    value=paper.get("Rating", 3),
                    key=f"rating_{paper.get('PMID', idx)}_{search_term}"
                )

def save_papers_to_session(papers: List[Dict[str, Any]], search_term: str):
    """Speichert Papers in Session State"""
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
    
    st.success(f"✅ **{len(papers)} Papers gespeichert!**")
    
    with st.expander("💾 Gespeicherte Papers anzeigen"):
        for paper in papers:
            st.write(f"• {paper.get('Title', 'Unbekannt')[:60]}... (PMID: {paper.get('PMID', 'n/a')})")

def save_single_paper(paper: Dict[str, Any], search_term: str):
    """Speichert einzelnes Paper"""
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

def create_excel_download(papers: List[Dict[str, Any]], search_term: str):
    """Erstellt Excel-Download"""
    try:
        # Excel Workbook erstellen
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Papers_{search_term.replace(' ', '_')}"
        
        # Headers
        headers = ["PMID", "Titel", "Autoren", "Journal", "Jahr", "DOI", "URL", "Abstract", "Ausgewählt", "Bewertung"]
        ws.append(headers)
        
        # Daten
        for paper in papers:
            row = [
                paper.get("PMID", ""),
                paper.get("Title", ""),
                paper.get("Authors", ""),
                paper.get("Journal", ""),
                paper.get("Year", ""),
                paper.get("DOI", ""),
                paper.get("URL", ""),
                paper.get("Abstract", "")[:1000] + "..." if len(paper.get("Abstract", "")) > 1000 else paper.get("Abstract", ""),
                "Ja" if paper.get("Selected", False) else "Nein",
                paper.get("Rating", 3)
            ]
            ws.append(row)
        
        # Buffer
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        # Download
        st.download_button(
            label="📥 **Excel-Datei herunterladen**",
            data=buffer.getvalue(),
            file_name=f"pubmed_papers_{search_term.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.success("✅ **Excel-Datei erstellt und bereit zum Download!**")
        
    except Exception as e:
        st.error(f"❌ Excel-Fehler: {str(e)}")

def show_saved_papers():
    """Zeigt alle gespeicherten Papers"""
    if "saved_papers" in st.session_state and st.session_state["saved_papers"]:
        st.markdown("---")
        st.header("💾 **Gespeicherte Papers**")
        
        for save_key, save_data in st.session_state["saved_papers"].items():
            with st.expander(f"📁 {save_data['search_term']} - {save_data['count']} Papers ({save_data['saved_at'][:19]})"):
                for paper in save_data['papers']:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"• **{paper.get('Title', 'Unbekannt')}** (PMID: {paper.get('PMID', 'n/a')})")
                    with col2:
                        if st.button("🗑️", key=f"delete_paper_{save_key}_{paper.get('PMID', 'unknown')}"):
                            # Remove this paper
                            save_data['papers'].remove(paper)
                            if not save_data['papers']:
                                del st.session_state["saved_papers"][save_key]
                            st.rerun()
                
                if st.button(f"🗑️ **Alle löschen**", key=f"delete_all_{save_key}"):
                    del st.session_state["saved_papers"][save_key]
                    st.rerun()
