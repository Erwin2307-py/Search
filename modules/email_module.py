# modules/paper_search_module.py - ERWEITERTE VERSION MIT NEU-PAPER-ERKENNUNG
import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import datetime
import time
import re
import io
import openpyxl
import os
import json
from typing import List, Dict, Any

class PubMedSearchEngineAdvanced:
    """Erweiterte PubMed-Suche mit Neu-Paper-Erkennung"""
    
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.email = "your_email@example.com"
        self.tool = "PaperSearchSystemAdvanced"
        self.excel_storage_path = "saved_searches"
        
        # Stelle sicher, dass der Speicher-Ordner existiert
        if not os.path.exists(self.excel_storage_path):
            os.makedirs(self.excel_storage_path)
    
    def search_papers_with_comparison(self, query: str, max_results: int = 50) -> Dict[str, Any]:
        """Führt Suche durch und vergleicht mit vorherigen Ergebnissen"""
        st.info(f"🔍 **Starte intelligente PubMed-Suche für:** '{query}'")
        
        # 1. Aktuelle Suche durchführen
        current_papers = self._perform_current_search(query, max_results)
        
        if not current_papers:
            st.error(f"❌ **Keine Papers für '{query}' gefunden!**")
            return {"current": [], "new": [], "total_found": 0, "is_repeat_search": False}
        
        # 2. Prüfe ob dies eine wiederholte Suche ist
        previous_papers = self._load_previous_search_results(query)
        
        if previous_papers:
            # Wiederholte Suche - finde neue Papers
            st.info(f"🔄 **Wiederholte Suche erkannt!** Vergleiche mit vorherigen Ergebnissen...")
            
            new_papers = self._find_new_papers(current_papers, previous_papers)
            
            if new_papers:
                st.success(f"🆕 **{len(new_papers)} NEUE Papers gefunden** (von {len(current_papers)} gesamt)")
                
                # Aktualisiere Excel-Datei mit neuen Papers
                self._update_excel_with_new_papers(query, current_papers, new_papers)
                
                # Sende Email mit nur neuen Papers
                self._send_new_papers_email(query, new_papers, len(current_papers))
                
                return {
                    "current": current_papers,
                    "new": new_papers,
                    "total_found": len(current_papers),
                    "is_repeat_search": True,
                    "new_count": len(new_papers)
                }
            else:
                st.info(f"ℹ️ **Keine neuen Papers gefunden** - Alle {len(current_papers)} Papers waren bereits bekannt")
                return {
                    "current": current_papers,
                    "new": [],
                    "total_found": len(current_papers),
                    "is_repeat_search": True,
                    "new_count": 0
                }
        else:
            # Erste Suche - alle Papers sind neu
            st.success(f"🎉 **Erste Suche:** {len(current_papers)} Papers gefunden!")
            
            # Erstelle neue Excel-Datei
            self._create_initial_excel_file(query, current_papers)
            
            # Sende Email mit allen Papers
            self._send_initial_papers_email(query, current_papers)
            
            return {
                "current": current_papers,
                "new": current_papers,
                "total_found": len(current_papers),
                "is_repeat_search": False,
                "new_count": len(current_papers)
            }
    
    def _perform_current_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Führt aktuelle PubMed-Suche durch"""
        # 1. esearch - hole PMIDs
        pmids, total_available = self._get_pmids_with_count(query, max_results)
        
        if not pmids:
            return []
        
        st.success(f"✅ **{len(pmids)} Papers abgerufen von {total_available:,} verfügbaren**")
        
        # 2. efetch - hole Details
        papers = self._fetch_complete_paper_details(pmids)
        
        return papers
    
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
            
            return pmids, total_count
            
        except Exception as e:
            st.error(f"❌ **PubMed esearch Fehler:** {str(e)}")
            return [], 0
    
    def _fetch_complete_paper_details(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """Holt vollständige Paper-Details"""
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
            
            progress_bar.progress(0.3)
            status_text.text("🔧 Parse XML-Daten...")
            
            root = ET.fromstring(response.content)
            papers = []
            
            articles = root.findall(".//PubmedArticle")
            total_articles = len(articles)
            
            for idx, article in enumerate(articles):
                progress = 0.3 + (idx + 1) / total_articles * 0.7
                progress_bar.progress(progress)
                
                paper_data = self._parse_single_article(article)
                if paper_data:
                    papers.append(paper_data)
                
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
                "Relevance_Score": 0,
                "Is_New": True  # Markierung für neue Papers
            }
            
        except Exception as e:
            return None
    
    def _load_previous_search_results(self, query: str) -> List[Dict[str, Any]]:
        """Lädt vorherige Suchergebnisse aus Excel-Datei"""
        excel_filename = self._get_excel_filename(query)
        excel_path = os.path.join(self.excel_storage_path, excel_filename)
        
        if not os.path.exists(excel_path):
            return []
        
        try:
            df = pd.read_excel(excel_path)
            
            # Konvertiere DataFrame zurück zu Dictionary-Liste
            previous_papers = []
            for _, row in df.iterrows():
                paper = {
                    "PMID": str(row.get("PMID", "")),
                    "Title": str(row.get("Titel", "")),
                    "Abstract": str(row.get("Abstract", "")),
                    "Journal": str(row.get("Journal", "")),
                    "Year": str(row.get("Jahr", "")),
                    "Authors": str(row.get("Autoren", "")),
                    "DOI": str(row.get("DOI", "")),
                    "URL": str(row.get("URL", ""))
                }
                previous_papers.append(paper)
            
            st.info(f"📂 **{len(previous_papers)} vorherige Papers** aus Excel-Datei geladen")
            return previous_papers
            
        except Exception as e:
            st.warning(f"⚠️ Fehler beim Laden der Excel-Datei: {str(e)}")
            return []
    
    def _find_new_papers(self, current_papers: List[Dict], previous_papers: List[Dict]) -> List[Dict]:
        """Findet neue Papers durch Vergleich der PMIDs"""
        previous_pmids = set(paper.get("PMID", "") for paper in previous_papers if paper.get("PMID"))
        
        new_papers = []
        for paper in current_papers:
            current_pmid = paper.get("PMID", "")
            if current_pmid and current_pmid not in previous_pmids:
                paper["Is_New"] = True
                new_papers.append(paper)
            else:
                paper["Is_New"] = False
        
        return new_papers
    
    def _get_excel_filename(self, query: str) -> str:
        """Generiert konsistenten Excel-Dateinamen"""
        # Bereinige Query für Dateinamen
        clean_query = re.sub(r'[^\w\s-]', '', query).strip()
        clean_query = re.sub(r'[-\s]+', '_', clean_query)
        return f"papers_{clean_query}.xlsx"
    
    def _create_initial_excel_file(self, query: str, papers: List[Dict]):
        """Erstellt initiale Excel-Datei für erste Suche"""
        excel_filename = self._get_excel_filename(query)
        excel_path = os.path.join(self.excel_storage_path, excel_filename)
        
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Papers"
            
            # Headers
            headers = [
                "PMID", "Titel", "Autoren", "Journal", "Jahr", "DOI", "URL", 
                "Abstract", "Erstmals_gefunden", "Letzte_Aktualisierung"
            ]
            ws.append(headers)
            
            # Data
            current_time = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            
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
                    current_time,
                    current_time
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
            
            wb.save(excel_path)
            
            st.success(f"✅ **Excel-Datei erstellt:** {excel_filename}")
            st.info(f"📁 **Gespeichert unter:** {excel_path}")
            
            # Download-Button für initiale Datei
            with open(excel_path, 'rb') as f:
                st.download_button(
                    label="📥 **Excel-Datei herunterladen**",
                    data=f.read(),
                    file_name=excel_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
        except Exception as e:
            st.error(f"❌ **Fehler beim Erstellen der Excel-Datei:** {str(e)}")
    
    def _update_excel_with_new_papers(self, query: str, all_papers: List[Dict], new_papers: List[Dict]):
        """Aktualisiert Excel-Datei mit neuen Papers"""
        excel_filename = self._get_excel_filename(query)
        excel_path = os.path.join(self.excel_storage_path, excel_filename)
        
        try:
            # Lade existierende Datei
            wb = openpyxl.load_workbook(excel_path)
            ws = wb.active
            
            # Füge neue Papers hinzu
            current_time = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            
            for paper in new_papers:
                row = [
                    paper.get("PMID", ""),
                    paper.get("Title", ""),
                    paper.get("Authors", ""),
                    paper.get("Journal", ""),
                    paper.get("Year", ""),
                    paper.get("DOI", ""),
                    paper.get("URL", ""),
                    paper.get("Abstract", "")[:1000] + "..." if len(paper.get("Abstract", "")) > 1000 else paper.get("Abstract", ""),
                    current_time,  # Erstmals_gefunden
                    current_time   # Letzte_Aktualisierung
                ]
                ws.append(row)
            
            wb.save(excel_path)
            
            st.success(f"✅ **Excel-Datei aktualisiert:** {len(new_papers)} neue Papers hinzugefügt")
            
            # Download-Button für aktualisierte Datei
            with open(excel_path, 'rb') as f:
                st.download_button(
                    label="📥 **Aktualisierte Excel-Datei herunterladen**",
                    data=f.read(),
                    file_name=f"updated_{excel_filename}",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="updated_excel_download"
                )
            
        except Exception as e:
            st.error(f"❌ **Fehler beim Aktualisieren der Excel-Datei:** {str(e)}")
    
    def _send_initial_papers_email(self, query: str, papers: List[Dict]):
        """Sendet Email für erste Suche"""
        try:
            from modules.email_module import trigger_email_notification
            success = trigger_email_notification(f"Erste Suche: {query}", len(papers))
            if success:
                st.info(f"📧 **Email gesendet:** Erste Suche für '{query}' mit {len(papers)} Papers")
                
                # Zusätzliche Email-Details
                self._create_detailed_email_notification(query, papers, is_initial=True)
        except ImportError:
            st.warning("📧 Email-Modul nicht verfügbar")
    
    def _send_new_papers_email(self, query: str, new_papers: List[Dict], total_papers: int):
        """Sendet Email nur mit neuen Papers"""
        try:
            from modules.email_module import trigger_email_notification
            success = trigger_email_notification(f"Neue Papers: {query}", len(new_papers))
            if success:
                st.info(f"📧 **Email gesendet:** {len(new_papers)} neue Papers für '{query}'")
                
                # Zusätzliche Email-Details für neue Papers
                self._create_detailed_email_notification(query, new_papers, is_initial=False, total_papers=total_papers)
        except ImportError:
            st.warning("📧 Email-Modul nicht verfügbar")
    
    def _create_detailed_email_notification(self, query: str, papers: List[Dict], is_initial: bool = True, total_papers: int = None):
        """Erstellt detaillierte Email-Benachrichtigung"""
        if "email_history" not in st.session_state:
            st.session_state["email_history"] = []
        
        email_type = "Erste Suche" if is_initial else "Neue Papers"
        subject = f"🔬 {email_type}: {len(papers)} Papers für '{query}'"
        
        if is_initial:
            message = f"""🔍 Erste Paper-Suche durchgeführt!

📅 Datum: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}
🔍 Suchbegriff: '{query}'
📊 Papers gefunden: {len(papers)}

📋 Top 5 Papers:"""
        else:
            message = f"""🆕 Neue Papers gefunden!

📅 Datum: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}
🔍 Suchbegriff: '{query}'
📊 Neue Papers: {len(papers)}
📊 Gesamt Papers: {total_papers}

📋 Neue Papers:"""
        
        # Top 5 Papers zur Email hinzufügen
        for i, paper in enumerate(papers[:5], 1):
            message += f"""

{i}. {paper.get('Title', 'Unbekannt')[:80]}...
   Autoren: {paper.get('Authors', 'n/a')[:60]}...
   Journal: {paper.get('Journal', 'n/a')} ({paper.get('Year', 'n/a')})
   PMID: {paper.get('PMID', 'n/a')}"""
        
        if len(papers) > 5:
            message += f"\n\n... und {len(papers) - 5} weitere Papers"
        
        message += f"""\n\n🔗 Vollständige Ergebnisse und Excel-Datei im System verfügbar.
📁 Excel-Datei: papers_{re.sub(r'[^\w\s-]', '', query).strip().replace(' ', '_')}.xlsx

Mit freundlichen Grüßen,
Ihr intelligentes Paper-Suche System"""
        
        # Zur Email-Historie hinzufügen
        email_notification = {
            "timestamp": datetime.datetime.now().isoformat(),
            "recipient": "user@example.com",
            "subject": subject,
            "message": message,
            "search_term": query,
            "paper_count": len(papers),
            "email_type": email_type,
            "status": "Gesendet (simuliert)"
        }
        
        st.session_state["email_history"].append(email_notification)
        
        # Email-Vorschau anzeigen
        with st.expander(f"📧 {email_type} Email-Vorschau anzeigen"):
            st.write(f"**Betreff:** {subject}")
            st.text_area("**Nachricht:**", value=message, height=300, disabled=True)

def module_paper_search():
    """Haupt-Paper-Suche Modul mit intelligenter Neu-Paper-Erkennung"""
    st.title("🔍 **Intelligente Paper-Suche mit Neu-Paper-Erkennung**")
    st.write("Sucht Papers, erstellt Excel-Dateien und sendet Emails mit nur **neuen** Papers!")
    
    # Initialize Advanced Search Engine
    search_engine = PubMedSearchEngineAdvanced()
    
    # Initialize Session State
    if "paper_search_results_advanced" not in st.session_state:
        st.session_state["paper_search_results_advanced"] = {}
    if "paper_search_history_advanced" not in st.session_state:
        st.session_state["paper_search_history_advanced"] = []
    
    # Informations-Box
    with st.expander("ℹ️ **Wie funktioniert die intelligente Suche?**", expanded=False):
        st.write("""
**🎯 Funktionen:**
• **Erste Suche:** Alle Papers werden als Excel gespeichert + Email versendet
• **Wiederholte Suche:** Vergleich mit Excel-Datei → nur NEUE Papers per Email
• **Automatische Excel-Updates:** Neue Papers werden zur bestehenden Datei hinzugefügt
• **Intelligente Erkennung:** Basiert auf PMID-Vergleich

**📁 Excel-Dateien werden gespeichert unter:** `saved_searches/papers_[suchbegriff].xlsx`
        """)
    
    # Sidebar: Search Settings & Statistics
    with st.sidebar:
        st.header("🔧 Intelligente Sucheinstellungen")
        
        max_results = st.number_input(
            "Max. Ergebnisse pro Suche", 
            min_value=10, 
            max_value=500, 
            value=50
        )
        
        st.header("📊 Such-Statistiken")
        
        if st.session_state["paper_search_history_advanced"]:
            total_searches = len(st.session_state["paper_search_history_advanced"])
            total_new_papers = sum(search.get("new_papers_count", 0) for search in st.session_state["paper_search_history_advanced"])
            
            st.metric("🔍 Gesamt Suchen", total_searches)
            st.metric("🆕 Neue Papers", total_new_papers)
            
            # Letzte Suchen mit Neu-Paper-Info
            st.write("**🕒 Letzte Suchen:**")
            for search in st.session_state["paper_search_history_advanced"][-5:]:
                repeat_icon = "🔄" if search.get("is_repeat") else "🆕"
                st.write(f"{repeat_icon} {search['query']}: +{search.get('new_papers_count', 0)} neue")
        else:
            st.info("Noch keine Suchen durchgeführt")
        
        # Excel-Dateien anzeigen
        st.header("📁 Gespeicherte Excel-Dateien")
        excel_files = []
        if os.path.exists("saved_searches"):
            excel_files = [f for f in os.listdir("saved_searches") if f.endswith('.xlsx')]
        
        if excel_files:
            st.write(f"**{len(excel_files)} Excel-Dateien:**")
            for file in excel_files[:5]:
                st.write(f"📄 {file}")
        else:
            st.info("Keine Excel-Dateien gespeichert")
    
    # Main Search Interface
    st.header("🚀 **Intelligente Suche starten**")
    
    with st.form("advanced_paper_search_form"):
        col1, col2 = st.columns([4, 1])
        
        with col1:
            search_query = st.text_input(
                "**PubMed Suchbegriff:**",
                placeholder="z.B. 'diabetes genetics', 'BRCA1 mutations'",
                help="Bei wiederholter Suche werden nur NEUE Papers per Email gesendet!"
            )
        
        with col2:
            search_button = st.form_submit_button(
                "🔍 **INTELLIGENTE SUCHE**", 
                type="primary", 
                use_container_width=True
            )
    
    # Execute Advanced Search
    if search_button and search_query:
        st.markdown("---")
        st.subheader(f"🧠 **Intelligente Suche für:** '{search_query}'")
        
        with st.spinner("🔍 Führe intelligente PubMed-Suche durch..."):
            search_result = search_engine.search_papers_with_comparison(search_query, max_results)
            
            if search_result["total_found"] > 0:
                # Save to search history
                timestamp = datetime.datetime.now().isoformat()
                
                history_entry = {
                    "query": search_query,
                    "timestamp": timestamp,
                    "total_papers": search_result["total_found"],
                    "new_papers_count": search_result["new_count"],
                    "is_repeat": search_result["is_repeat_search"]
                }
                
                st.session_state["paper_search_history_advanced"].append(history_entry)
                
                # Save to results
                st.session_state["paper_search_results_advanced"][search_query] = {
                    "papers": search_result["current"],
                    "new_papers": search_result["new"],
                    "timestamp": timestamp,
                    "is_repeat_search": search_result["is_repeat_search"]
                }
                
                # Success message with different icons
                if search_result["is_repeat_search"]:
                    if search_result["new_count"] > 0:
                        st.success(f"🆕 **{search_result['new_count']} NEUE Papers gefunden!** (von {search_result['total_found']} gesamt)")
                        st.balloons()
                    else:
                        st.info(f"ℹ️ **Keine neuen Papers** - Alle {search_result['total_found']} Papers bereits bekannt")
                else:
                    st.success(f"🎉 **Erste Suche erfolgreich:** {search_result['total_found']} Papers gefunden!")
                    st.balloons()
                
                # Display Results
                display_advanced_search_results(
                    search_result["current"], 
                    search_result["new"],
                    search_query, 
                    search_result["is_repeat_search"]
                )
            
            else:
                st.error(f"❌ **Keine Papers für '{search_query}' gefunden!**")
    
    # Display Previous Results
    if st.session_state["paper_search_results_advanced"] and not search_button:
        st.markdown("---")
        st.header("📚 **Gespeicherte Intelligente Suchergebnisse**")
        
        search_tabs = st.tabs(list(st.session_state["paper_search_results_advanced"].keys()))
        
        for idx, (search_term, data) in enumerate(st.session_state["paper_search_results_advanced"].items()):
            with search_tabs[idx]:
                papers = data["papers"]
                new_papers = data["new_papers"]
                timestamp = data["timestamp"]
                is_repeat = data["is_repeat_search"]
                
                search_type = "Wiederholte Suche" if is_repeat else "Erste Suche"
                st.info(f"📅 {search_type} vom: {timestamp[:19]} | 📄 Papers: {len(papers)} | 🆕 Neue: {len(new_papers)}")
                
                display_advanced_search_results(papers, new_papers, search_term, is_repeat, show_controls=False)

def display_advanced_search_results(all_papers: List[Dict], new_papers: List[Dict], search_query: str, is_repeat_search: bool, show_controls: bool = True):
    """Zeigt erweiterte Suchergebnisse mit Neu-Paper-Hervorhebung"""
    
    # Advanced Statistics Dashboard
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    with col_stat1:
        st.metric("📄 **Gesamt Papers**", len(all_papers))
    
    with col_stat2:
        st.metric("🆕 **Neue Papers**", len(new_papers), delta=len(new_papers) if is_repeat_search else None)
    
    with col_stat3:
        with_abstract = len([p for p in all_papers if p.get("Abstract", "") != "No abstract available"])
        st.metric("📝 **Mit Abstract**", with_abstract)
    
    with col_stat4:
        search_type = "🔄 Wiederholte Suche" if is_repeat_search else "🆕 Erste Suche"
        st.metric("🔍 **Such-Typ**", search_type)
    
    # Filter: Nur neue Papers anzeigen
    show_only_new = False
    if is_repeat_search and new_papers:
        show_only_new = st.checkbox(
            f"🆕 **Nur die {len(new_papers)} neuen Papers anzeigen**", 
            value=True, 
            key=f"show_new_{search_query}"
        )
    
    # Bestimme welche Papers angezeigt werden
    display_papers = new_papers if (show_only_new and is_repeat_search) else all_papers
    
    if not display_papers:
        st.info("📭 Keine Papers zum Anzeigen")
        return
    
    # Paper Display
    st.subheader(f"📋 **Papers für '{search_query}' ({'Nur neue' if show_only_new else 'Alle'})**")
    
    for idx, paper in enumerate(display_papers[:20]):  # Zeige max 20 Papers
        is_new = paper.get("Is_New", False)
        
        # Icons basierend auf Status
        status_icon = "🆕" if is_new else "📄"
        selected_icon = "✅" if paper.get("Selected", False) else "☐"
        
        # Paper Header mit Hervorhebung
        header_style = "**🆕 NEU:**" if is_new else ""
        header = f"{status_icon} {selected_icon} {header_style} **{idx + 1}.** {paper.get('Title', 'Unbekannter Titel')[:70]}..."
        
        with st.expander(header):
            col_paper1, col_paper2 = st.columns([3, 1])
            
            with col_paper1:
                # Paper Details
                st.markdown(f"**📄 Titel:** {paper.get('Title', 'n/a')}")
                st.markdown(f"**👥 Autoren:** {paper.get('Authors', 'n/a')}")
                st.markdown(f"**📚 Journal:** {paper.get('Journal', 'n/a')} ({paper.get('Year', 'n/a')})")
                st.markdown(f"**🆔 PMID:** {paper.get('PMID', 'n/a')}")
                st.markdown(f"**🔗 DOI:** {paper.get('DOI', 'n/a')}")
                
                # Abstract
                if paper.get('Abstract') and paper.get('Abstract') != "No abstract available":
                    with st.expander("📝 Abstract anzeigen"):
                        st.write(paper.get('Abstract', 'Kein Abstract verfügbar'))
                
                # Links
                if paper.get('URL'):
                    st.markdown(f"🔗 [**PubMed ansehen**]({paper.get('URL')})")
            
            with col_paper2:
                # Neu-Status
                if is_new:
                    st.success("🆕 **NEUES PAPER**")
                else:
                    st.info("📄 Bereits bekannt")
                
                # Selection
                paper["Selected"] = st.checkbox(
                    "**Auswählen**",
                    value=paper.get("Selected", False),
                    key=f"adv_select_{paper.get('PMID', idx)}_{search_query}"
                )
                
                # Individual Actions
                if st.button("💾 **Speichern**", key=f"adv_save_{paper.get('PMID', idx)}"):
                    save_individual_paper(paper, search_query, is_new)
                
                if st.button("📧 **Email**", key=f"adv_email_{paper.get('PMID', idx)}"):
                    send_individual_paper_email(paper, search_query, is_new)

def save_individual_paper(paper: Dict, search_query: str, is_new: bool):
    """Speichert einzelnes Paper mit Neu-Status"""
    if "saved_individual_papers_advanced" not in st.session_state:
        st.session_state["saved_individual_papers_advanced"] = []
    
    paper_entry = {
        **paper,
        "search_query": search_query,
        "saved_at": datetime.datetime.now().isoformat(),
        "was_new_when_saved": is_new
    }
    
    st.session_state["saved_individual_papers_advanced"].append(paper_entry)
    
    status = "NEUES" if is_new else "bekanntes"
    st.success(f"💾 **{status} Paper gespeichert:** {paper.get('Title', 'Unbekannt')[:50]}...")

def send_individual_paper_email(paper: Dict, search_query: str, is_new: bool):
    """Sendet Email für einzelnes Paper"""
    try:
        from modules.email_module import trigger_email_notification
        
        email_subject = f"{'Neues' if is_new else 'Einzelnes'} Paper: {paper.get('Title', 'Unknown')[:30]}..."
        success = trigger_email_notification(email_subject, 1)
        
        if success:
            status = "NEUES" if is_new else "Paper"
            st.success(f"📧 **Email gesendet** für {status}: {paper.get('Title', 'Unknown')[:40]}...")
        else:
            st.info("📧 Email-Benachrichtigung erstellt (simuliert)")
    except:
        st.info("📧 Email-Funktionalität nicht verfügbar")

# Zusätzliche Hilfsfunktionen (gleich wie vorher, aber mit "advanced" Suffix)
def sort_papers(papers: List[Dict], sort_option: str) -> List[Dict]:
    """Sortiert Papers nach gewählter Option"""
    try:
        if sort_option == "Jahr (neu-alt)":
            return sorted(papers, key=lambda x: int(x.get("Year", "0")) if x.get("Year", "0").isdigit() else 0, reverse=True)
        elif sort_option == "Jahr (alt-neu)":
            return sorted(papers, key=lambda x: int(x.get("Year", "0")) if x.get("Year", "0").isdigit() else 0)
        elif sort_option == "Titel":
            return sorted(papers, key=lambda x: x.get("Title", "").lower())
        elif sort_option == "Neu zuerst":
            return sorted(papers, key=lambda x: x.get("Is_New", False), reverse=True)
        else:  # Relevanz (Standard)
            return papers
    except:
        return papers
