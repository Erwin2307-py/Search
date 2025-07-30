# modules/paper_search_module.py - FUNKTIONSFÄHIGE PAPER-SUCHE
import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import datetime
import time
import re
import io
import openpyxl
from typing import List, Dict, Any

class PubMedSearchEngine:
    """Echte PubMed-Suche mit esearch + efetch"""
    
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.email = "your_email@example.com"
        self.tool = "PaperSearchSystem"
    
    def search_papers_complete(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Führt KOMPLETTE PubMed-Suche durch mit Anzeige der Anzahl"""
        st.info(f"🔍 **Starte PubMed-Suche für:** '{query}'")
        
        # 1. Schritt: esearch - hole PMIDs
        pmids, total_available = self._get_pmids_with_count(query, max_results)
        
        if not pmids:
            st.error(f"❌ **Keine Papers für '{query}' gefunden!**")
            st.metric("📄 Gefundene Papers", 0)
            return []
        
        # Anzeige der Anzahl
        st.success(f"✅ **{len(pmids)} Papers abgerufen von {total_available} verfügbaren**")
        st.metric("📊 PubMed Treffer", f"{total_available}")
        st.metric("📥 Abgerufen", f"{len(pmids)}")
        
        # 2. Schritt: efetch - hole vollständige Details
        papers = self._fetch_complete_paper_details(pmids)
        
        if papers:
            st.success(f"🎉 **{len(papers)} vollständige Papers erfolgreich abgerufen!**")
            
            # Email-Benachrichtigung triggern
            self._trigger_email_notification(query, len(papers), papers)
            
            return papers
        else:
            st.warning("❌ Keine Paper-Details konnten abgerufen werden!")
            return []
    
    def _get_pmids_with_count(self, query: str, max_results: int) -> tuple:
        """esearch mit Anzahl-Anzeige"""
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
            total_count = int(data.get("esearchresult", {}).get("count", 0))
            
            st.write(f"📊 **PubMed Datenbank:** {total_count:,} Papers verfügbar für '{query}'")
            st.write(f"📥 **Abruf:** {len(pmids)} Papers werden heruntergeladen")
            
            return pmids, total_count
            
        except Exception as e:
            st.error(f"❌ **PubMed esearch Fehler:** {str(e)}")
            return [], 0
    
    def _fetch_complete_paper_details(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """Holt vollständige Paper-Details mit Progress"""
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
        
        # Progress-Anzeige
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("📥 Lade Paper-Details von PubMed...")
            response = requests.get(fetch_url, params=params, timeout=60)
            response.raise_for_status()
            
            progress_bar.progress(0.3)
            status_text.text("🔧 Parse XML-Daten...")
            
            root = ET.fromstring(response.content)
            papers = []
            
            articles = root.findall(".//PubmedArticle")
            total_articles = len(articles)
            
            status_text.text(f"📄 Verarbeite {total_articles} Papers...")
            
            for idx, article in enumerate(articles):
                progress = 0.3 + (idx + 1) / total_articles * 0.7
                progress_bar.progress(progress)
                
                paper_data = self._parse_single_article(article)
                if paper_data:
                    papers.append(paper_data)
                
                # Kurze Pause für API-Freundlichkeit
                if idx % 10 == 0:
                    time.sleep(0.1)
            
            progress_bar.empty()
            status_text.empty()
            
            return papers
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ **PubMed efetch Fehler:** {str(e)}")
            return []
    
    def _parse_single_article(self, article) -> Dict[str, Any]:
        """Parst einzelnen Artikel aus XML"""
        try:
            # PMID
            pmid_elem = article.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else "n/a"
            
            # Title
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
            
            # Year
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
            
            # Authors
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
                "Selected": False,
                "Relevance_Score": 0
            }
            
        except Exception as e:
            return None
    
    def _trigger_email_notification(self, search_term: str, paper_count: int, papers: List[Dict]):
        """Triggert Email-Benachrichtigung"""
        try:
            from modules.email_module import trigger_email_notification
            success = trigger_email_notification(search_term, paper_count)
            if success:
                st.info(f"📧 **Email-Benachrichtigung** für '{search_term}' versendet!")
        except ImportError:
            pass  # Email-Modul optional

def module_paper_search():
    """Haupt-Paper-Suche Modul"""
    st.title("🔍 **Paper-Suche mit Anzahl-Anzeige**")
    st.write("Durchsuchen Sie PubMed und sehen Sie genau, wie viele Papers gefunden wurden!")
    
    # Initialize Search Engine
    search_engine = PubMedSearchEngine()
    
    # Initialize Session State
    if "paper_search_results" not in st.session_state:
        st.session_state["paper_search_results"] = {}
    if "paper_search_history" not in st.session_state:
        st.session_state["paper_search_history"] = []
    
    # Sidebar: Search Settings
    with st.sidebar:
        st.header("🔧 Sucheinstellungen")
        
        max_results = st.number_input(
            "Max. Ergebnisse pro Suche", 
            min_value=10, 
            max_value=500, 
            value=50,
            help="Anzahl der Papers, die heruntergeladen werden"
        )
        
        st.header("📊 Such-Statistiken")
        
        if st.session_state["paper_search_history"]:
            total_searches = len(st.session_state["paper_search_history"])
            total_papers = sum(search["results_count"] for search in st.session_state["paper_search_history"])
            
            st.metric("🔍 Gesamt Suchen", total_searches)
            st.metric("📄 Gesamt Papers", total_papers)
            
            # Letzte Suchen
            st.write("**🕒 Letzte Suchen:**")
            for search in st.session_state["paper_search_history"][-5:]:
                st.write(f"• {search['query']}: {search['results_count']} Papers")
        else:
            st.info("Noch keine Suchen durchgeführt")
    
    # Main Search Interface
    st.header("🚀 **Neue Suche starten**")
    
    with st.form("paper_search_form"):
        col1, col2 = st.columns([4, 1])
        
        with col1:
            search_query = st.text_input(
                "**PubMed Suchbegriff:**",
                placeholder="z.B. 'diabetes genetics', 'BRCA1 mutations', 'COVID-19 treatment'",
                help="Verwenden Sie PubMed-Syntax: AND, OR, [Title], [Author], etc."
            )
        
        with col2:
            search_button = st.form_submit_button("🔍 **SUCHEN**", type="primary", use_container_width=True)
    
    # Advanced Search Options
    with st.expander("🔧 Erweiterte Suchoptionen"):
        col_adv1, col_adv2, col_adv3 = st.columns(3)
        
        with col_adv1:
            date_filter = st.selectbox(
                "Zeitraum:",
                ["Alle", "Letztes Jahr", "Letzte 5 Jahre", "Letzte 10 Jahre"],
                index=0
            )
        
        with col_adv2:
            article_type = st.selectbox(
                "Artikel-Typ:",
                ["Alle", "Review", "Clinical Trial", "Meta-Analysis"],
                index=0
            )
        
        with col_adv3:
            language_filter = st.selectbox(
                "Sprache:",
                ["Alle", "English", "German"],
                index=0
            )
    
    # Execute Search
    if search_button and search_query:
        # Build advanced query
        advanced_query = build_advanced_query(search_query, date_filter, article_type, language_filter)
        
        st.markdown("---")
        st.subheader(f"📊 **Suchergebnisse für:** '{search_query}'")
        
        with st.spinner("🔍 Durchsuche PubMed-Datenbank..."):
            papers = search_engine.search_papers_complete(advanced_query, max_results)
            
            if papers:
                # Save to search results and history
                timestamp = datetime.datetime.now().isoformat()
                
                st.session_state["paper_search_results"][search_query] = {
                    "papers": papers,
                    "timestamp": timestamp,
                    "query": advanced_query,
                    "results_count": len(papers)
                }
                
                st.session_state["paper_search_history"].append({
                    "query": search_query,
                    "timestamp": timestamp,
                    "results_count": len(papers)
                })
                
                # Success message with balloons
                st.success(f"🎉 **Suche erfolgreich abgeschlossen!**")
                st.balloons()
                
                # Display Results
                display_search_results(papers, search_query, max_results)
            
            else:
                st.error(f"❌ **Keine Papers für '{search_query}' gefunden!**")
                
                # Suggestions for better search
                st.write("💡 **Verbesserungsvorschläge:**")
                st.write("• Verwenden Sie weniger spezifische Begriffe")
                st.write("• Prüfen Sie die Rechtschreibung")
                st.write("• Verwenden Sie Synonyme oder verwandte Begriffe")
                st.write("• Nutzen Sie PubMed-Syntax: AND, OR")
    
    # Display Previous Results
    if st.session_state["paper_search_results"] and not search_button:
        st.markdown("---")
        st.header("📚 **Gespeicherte Suchergebnisse**")
        
        search_tabs = st.tabs(list(st.session_state["paper_search_results"].keys()))
        
        for idx, (search_term, data) in enumerate(st.session_state["paper_search_results"].items()):
            with search_tabs[idx]:
                papers = data["papers"]
                timestamp = data["timestamp"]
                
                st.info(f"📅 Suche vom: {timestamp[:19]} | 📄 Papers: {len(papers)}")
                display_search_results(papers, search_term, max_results, show_new_search_controls=False)

def build_advanced_query(base_query: str, date_filter: str, article_type: str, language_filter: str) -> str:
    """Baut erweiterte PubMed-Suche auf"""
    query_parts = [base_query]
    
    # Date filter
    if date_filter != "Alle":
        current_year = datetime.datetime.now().year
        if date_filter == "Letztes Jahr":
            query_parts.append(f"AND {current_year-1}:{current_year}[dp]")
        elif date_filter == "Letzte 5 Jahre":
            query_parts.append(f"AND {current_year-5}:{current_year}[dp]")
        elif date_filter == "Letzte 10 Jahre":
            query_parts.append(f"AND {current_year-10}:{current_year}[dp]")
    
    # Article type filter
    if article_type != "Alle":
        if article_type == "Review":
            query_parts.append("AND Review[ptyp]")
        elif article_type == "Clinical Trial":
            query_parts.append("AND Clinical Trial[ptyp]")
        elif article_type == "Meta-Analysis":
            query_parts.append("AND Meta-Analysis[ptyp]")
    
    # Language filter
    if language_filter != "Alle":
        if language_filter == "English":
            query_parts.append("AND English[lang]")
        elif language_filter == "German":
            query_parts.append("AND German[lang]")
    
    return " ".join(query_parts)

def display_search_results(papers: List[Dict], search_query: str, max_results: int, show_new_search_controls: bool = True):
    """Zeigt Suchergebnisse mit Anzahl-Informationen an"""
    
    # Statistics Dashboard
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    with col_stat1:
        st.metric("📄 **Gefundene Papers**", len(papers))
    
    with col_stat2:
        selected_count = len([p for p in papers if p.get("Selected", False)])
        st.metric("✅ **Ausgewählt**", selected_count)
    
    with col_stat3:
        with_abstract = len([p for p in papers if p.get("Abstract", "") != "No abstract available"])
        st.metric("📝 **Mit Abstract**", with_abstract)
    
    with col_stat4:
        current_year = datetime.datetime.now().year
        recent_papers = len([p for p in papers if p.get("Year", "0").isdigit() and int(p.get("Year", "0")) >= current_year - 5])
        st.metric("🆕 **Letzte 5 Jahre**", recent_papers)
    
    # Action Buttons
    if show_new_search_controls:
        col_action1, col_action2, col_action3, col_action4 = st.columns(4)
        
        with col_action1:
            if st.button("✅ **Alle auswählen**", key=f"select_all_{search_query}"):
                for paper in papers:
                    paper["Selected"] = True
                st.rerun()
        
        with col_action2:
            if st.button("❌ **Alle abwählen**", key=f"deselect_all_{search_query}"):
                for paper in papers:
                    paper["Selected"] = False
                st.rerun()
        
        with col_action3:
            selected_papers = [p for p in papers if p.get("Selected", False)]
            if st.button(f"💾 **{len(selected_papers)} Papers speichern**", key=f"save_selected_{search_query}"):
                if selected_papers:
                    save_selected_papers(selected_papers, search_query)
                else:
                    st.warning("⚠️ Keine Papers ausgewählt!")
        
        with col_action4:
            if st.button("📥 **Excel exportieren**", key=f"export_{search_query}"):
                create_excel_export(papers, search_query)
    
    # Paper Display Options
    st.write("**🔍 Anzeige-Optionen:**")
    col_display1, col_display2, col_display3 = st.columns(3)
    
    with col_display1:
        show_abstracts = st.checkbox("Abstracts anzeigen", value=True, key=f"show_abs_{search_query}")
    
    with col_display2:
        papers_per_page = st.number_input(
            "Papers pro Seite", 
            min_value=5, 
            max_value=50, 
            value=10, 
            key=f"per_page_{search_query}"
        )
    
    with col_display3:
        sort_option = st.selectbox(
            "Sortieren nach:",
            ["Relevanz", "Jahr (neu-alt)", "Jahr (alt-neu)", "Titel"],
            key=f"sort_{search_query}"
        )
    
    # Sort papers
    sorted_papers = sort_papers(papers, sort_option)
    
    # Pagination
    total_pages = (len(sorted_papers) - 1) // papers_per_page + 1 if sorted_papers else 0
    
    if total_pages > 1:
        page = st.selectbox(
            f"Seite (1-{total_pages})", 
            range(1, total_pages + 1), 
            key=f"page_{search_query}"
        ) - 1
        
        start_idx = page * papers_per_page
        end_idx = start_idx + papers_per_page
        display_papers = sorted_papers[start_idx:end_idx]
        
        st.write(f"📄 **Zeige Papers {start_idx + 1}-{min(end_idx, len(sorted_papers))} von {len(sorted_papers)}**")
    else:
        display_papers = sorted_papers
    
    # Display Papers
    st.subheader(f"📋 **Papers für '{search_query}'**")
    
    for idx, paper in enumerate(display_papers):
        paper_idx = sorted_papers.index(paper) + 1
        selected_icon = "✅" if paper.get("Selected", False) else "☐"
        
        # Paper Header
        header = f"{selected_icon} **{paper_idx}.** {paper.get('Title', 'Unbekannter Titel')[:80]}..."
        
        with st.expander(header):
            col_paper1, col_paper2 = st.columns([3, 1])
            
            with col_paper1:
                # Paper Details
                st.markdown(f"**📄 Titel:** {paper.get('Title', 'n/a')}")
                st.markdown(f"**👥 Autoren:** {paper.get('Authors', 'n/a')}")
                st.markdown(f"**📚 Journal:** {paper.get('Journal', 'n/a')} ({paper.get('Year', 'n/a')})")
                
                col_ids1, col_ids2 = st.columns(2)
                with col_ids1:
                    st.markdown(f"**🆔 PMID:** {paper.get('PMID', 'n/a')}")
                with col_ids2:
                    st.markdown(f"**🔗 DOI:** {paper.get('DOI', 'n/a')}")
                
                # Abstract
                if show_abstracts and paper.get('Abstract'):
                    st.markdown("**📝 Abstract:**")
                    abstract_text = paper.get('Abstract', 'Kein Abstract verfügbar')
                    if len(abstract_text) > 500:
                        st.text_area("", value=abstract_text, height=150, disabled=True, key=f"abs_{paper.get('PMID', idx)}")
                    else:
                        st.write(abstract_text)
                
                # Links
                if paper.get('URL'):
                    st.markdown(f"🔗 [**PubMed ansehen**]({paper.get('URL')})")
            
            with col_paper2:
                # Selection checkbox
                paper["Selected"] = st.checkbox(
                    "**Auswählen**",
                    value=paper.get("Selected", False),
                    key=f"select_{paper.get('PMID', idx)}_{search_query}"
                )
                
                # Individual actions
                if st.button("💾 **Speichern**", key=f"save_{paper.get('PMID', idx)}_{search_query}"):
                    save_single_paper(paper, search_query)
                
                # Rating
                paper["Relevance_Score"] = st.select_slider(
                    "Relevanz",
                    options=[1, 2, 3, 4, 5],
                    value=paper.get("Relevance_Score", 3),
                    key=f"rating_{paper.get('PMID', idx)}_{search_query}"
                )
                
                # Quick actions
                if st.button("📧 **Email**", key=f"email_{paper.get('PMID', idx)}_{search_query}"):
                    send_paper_email(paper, search_query)

def sort_papers(papers: List[Dict], sort_option: str) -> List[Dict]:
    """Sortiert Papers nach gewählter Option"""
    try:
        if sort_option == "Jahr (neu-alt)":
            return sorted(papers, key=lambda x: int(x.get("Year", "0")) if x.get("Year", "0").isdigit() else 0, reverse=True)
        elif sort_option == "Jahr (alt-neu)":
            return sorted(papers, key=lambda x: int(x.get("Year", "0")) if x.get("Year", "0").isdigit() else 0)
        elif sort_option == "Titel":
            return sorted(papers, key=lambda x: x.get("Title", "").lower())
        else:  # Relevanz (Standard)
            return papers
    except:
        return papers

def save_selected_papers(papers: List[Dict], search_query: str):
    """Speichert ausgewählte Papers"""
    if "saved_paper_collections" not in st.session_state:
        st.session_state["saved_paper_collections"] = {}
    
    timestamp = datetime.datetime.now().isoformat()
    collection_name = f"{search_query}_{timestamp}"
    
    st.session_state["saved_paper_collections"][collection_name] = {
        "papers": papers,
        "search_query": search_query,
        "saved_at": timestamp,
        "count": len(papers)
    }
    
    st.success(f"✅ **{len(papers)} Papers gespeichert** als '{collection_name}'")
    
    # Show saved papers preview
    with st.expander("💾 Gespeicherte Papers anzeigen"):
        for i, paper in enumerate(papers, 1):
            st.write(f"**{i}.** {paper.get('Title', 'Unbekannt')[:60]}... (PMID: {paper.get('PMID', 'n/a')})")

def save_single_paper(paper: Dict, search_query: str):
    """Speichert einzelnes Paper"""
    if "saved_individual_papers" not in st.session_state:
        st.session_state["saved_individual_papers"] = []
    
    paper_entry = {
        **paper,
        "search_query": search_query,
        "saved_at": datetime.datetime.now().isoformat()
    }
    
    st.session_state["saved_individual_papers"].append(paper_entry)
    st.success(f"💾 **Paper gespeichert:** {paper.get('Title', 'Unbekannt')[:50]}...")

def send_paper_email(paper: Dict, search_query: str):
    """Sendet Email für einzelnes Paper"""
    try:
        from modules.email_module import trigger_email_notification
        success = trigger_email_notification(f"Einzelpaper: {paper.get('Title', 'Unknown')[:30]}...", 1)
        if success:
            st.success(f"📧 **Email gesendet** für Paper: {paper.get('Title', 'Unknown')[:40]}...")
        else:
            st.info("📧 Email-Benachrichtigung erstellt (simuliert)")
    except:
        st.info("📧 Email-Funktionalität nicht verfügbar")

def create_excel_export(papers: List[Dict], search_query: str):
    """Erstellt Excel-Export mit vollständigen Informationen"""
    try:
        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Papers_{search_query.replace(' ', '_')}"
        
        # Headers
        headers = [
            "PMID", "Titel", "Autoren", "Journal", "Jahr", "DOI", "URL", 
            "Abstract", "Ausgewählt", "Relevanz-Score", "Suche", "Export-Datum"
        ]
        ws.append(headers)
        
        # Data
        export_date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        
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
                paper.get("Relevance_Score", 3),
                search_query,
                export_date
            ]
            ws.append(row)
        
        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Save to buffer
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        # Download button
        filename = f"papers_{search_query.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        st.download_button(
            label="📥 **Excel-Datei herunterladen**",
            data=buffer.getvalue(),
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.success(f"✅ **Excel-Export erstellt!** Dateiname: {filename}")
        st.info(f"📊 **Exportiert:** {len(papers)} Papers mit vollständigen Details")
        
    except Exception as e:
        st.error(f"❌ **Excel-Export Fehler:** {str(e)}")
