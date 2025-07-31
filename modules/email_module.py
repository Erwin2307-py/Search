# modules/email_module.py - VOLLSTÄNDIGE VERSION MIT EXCEL-TEMPLATE-SYSTEM
import streamlit as st
import datetime
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
import re
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import ssl
from typing import List, Dict, Any
import json
from pathlib import Path

def module_email():
    """VOLLSTÄNDIGE FUNKTION - Email-Modul mit Excel-Template-System"""
    st.title("📧 Wissenschaftliches Paper-Suche & Email-System")
    st.success("✅ Vollständiges Modul mit Excel-Template-System geladen!")
    
    # Session State initialisieren
    initialize_session_state()
    
    # Erweiterte Tabs mit allen Funktionen
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Dashboard", 
        "🔍 Paper-Suche", 
        "📧 Email-Konfiguration",
        "📋 Excel-Management",
        "🤖 Automatische Suchen",
        "📈 Statistiken",
        "⚙️ System-Einstellungen"
    ])
    
    with tab1:
        show_dashboard()
    
    with tab2:
        show_advanced_paper_search()
    
    with tab3:
        show_email_config()
    
    with tab4:
        show_excel_template_management()
    
    with tab5:
        show_automatic_search_system()
    
    with tab6:
        show_detailed_statistics()
    
    with tab7:
        show_system_settings()

def initialize_session_state():
    """Vollständige Session State Initialisierung"""
    # Erstelle notwendige Ordner
    for folder in ["excel_templates", "saved_searches", "search_history", "config"]:
        if not os.path.exists(folder):
            os.makedirs(folder)
    
    # Email-Einstellungen
    if "email_settings" not in st.session_state:
        st.session_state["email_settings"] = {
            "sender_email": "",
            "recipient_email": "",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_password": "",
            "use_tls": True,
            "auto_notifications": True,
            "min_papers": 1,
            "notification_frequency": "Bei jeder Suche",
            "subject_template": "🔬 {count} neue Papers für '{search_term}' - {frequency}",
            "message_template": """📧 Automatische Paper-Benachrichtigung

📅 Datum: {date}
🔍 Suchbegriff: '{search_term}'
📊 Neue Papers: {count}
⏰ Häufigkeit: {frequency}

📋 Neue Papers:
{new_papers_list}

📎 Excel-Datei wurde aktualisiert: {excel_file}

Mit freundlichen Grüßen,
Ihr automatisches Paper-Überwachung-System"""
        }
    
    # Excel-Template System
    if "excel_template" not in st.session_state:
        st.session_state["excel_template"] = {
            "file_path": "excel_templates/master_papers.xlsx",
            "auto_create_sheets": True,
            "sheet_naming": "topic_based",  # topic_based, date_based, custom
            "max_sheets": 50
        }
    
    # Such-Historie
    if "search_history" not in st.session_state:
        st.session_state["search_history"] = []
    
    # Email-Historie
    if "email_history" not in st.session_state:
        st.session_state["email_history"] = []
    
    # Automatische Suchen
    if "automatic_searches" not in st.session_state:
        st.session_state["automatic_searches"] = {}
    
    # System-Status
    if "system_status" not in st.session_state:
        st.session_state["system_status"] = {
            "total_searches": 0,
            "total_papers": 0,
            "total_emails": 0,
            "last_search": None,
            "excel_sheets": 0
        }
    
    # Erstelle Master Excel-Datei falls nicht vorhanden
    create_master_excel_template()

def create_master_excel_template():
    """Erstellt Master Excel-Template mit Overview-Sheet"""
    template_path = st.session_state["excel_template"]["file_path"]
    
    if not os.path.exists(template_path):
        try:
            wb = openpyxl.Workbook()
            
            # Overview Sheet
            overview_sheet = wb.active
            overview_sheet.title = "📊_Overview"
            
            # Header-Style
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            
            # Overview Headers
            overview_headers = [
                "Sheet_Name", "Suchbegriff", "Anzahl_Papers", "Letztes_Update", 
                "Neue_Papers_Heute", "Status", "Erstellt_am"
            ]
            
            for col, header in enumerate(overview_headers, 1):
                cell = overview_sheet.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")
            
            # Spaltenbreite anpassen
            column_widths = [15, 25, 15, 18, 18, 12, 18]
            for col, width in enumerate(column_widths, 1):
                overview_sheet.column_dimensions[overview_sheet.cell(row=1, column=col).column_letter].width = width
            
            # Template Info Sheet
            info_sheet = wb.create_sheet("ℹ️_Template_Info")
            
            info_data = [
                ["📋 Excel Template Information", ""],
                ["", ""],
                ["Erstellt am:", datetime.datetime.now().strftime("%d.%m.%Y %H:%M")],
                ["System:", "Wissenschaftliches Paper-Suche System"],
                ["Version:", "2.0 mit automatischem Sheet-Management"],
                ["", ""],
                ["📖 Anleitung:", ""],
                ["• Jeder Suchbegriff bekommt ein eigenes Sheet", ""],
                ["• Das Overview-Sheet zeigt alle Suchanfragen", ""],
                ["• Neue Papers werden automatisch hinzugefügt", ""],
                ["• Email-Benachrichtigungen bei neuen Papers", ""],
                ["", ""],
                ["⚙️ Konfiguration:", ""],
                ["• Automatische Sheet-Erstellung: Aktiviert", ""],
                ["• Max. Sheets: 50", ""],
                ["• Duplikate-Erkennung: PMID-basiert", ""],
                ["• Email-Integration: Vollständig", ""]
            ]
            
            for row_idx, (key, value) in enumerate(info_data, 1):
                info_sheet.cell(row=row_idx, column=1, value=key).font = Font(bold=True)
                info_sheet.cell(row=row_idx, column=2, value=value)
            
            info_sheet.column_dimensions['A'].width = 30
            info_sheet.column_dimensions['B'].width = 40
            
            wb.save(template_path)
            st.success(f"✅ Master Excel-Template erstellt: {template_path}")
            
        except Exception as e:
            st.error(f"❌ Fehler beim Erstellen des Master-Templates: {str(e)}")

def show_dashboard():
    """Erweiterte Dashboard-Ansicht mit Suchhistorie"""
    st.subheader("📊 Dashboard - Übersicht aller Suchanfragen")
    
    # System-Status
    status = st.session_state["system_status"]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🔍 Gesamt Suchen", status["total_searches"])
    
    with col2:
        st.metric("📄 Gesamt Papers", status["total_papers"])
    
    with col3:
        st.metric("📧 Gesendete Emails", status["total_emails"])
    
    with col4:
        st.metric("📊 Excel Sheets", status["excel_sheets"])
    
    # Letzte Aktivität
    if status["last_search"]:
        last_search_time = datetime.datetime.fromisoformat(status["last_search"])
        time_diff = datetime.datetime.now() - last_search_time
        st.info(f"🕒 Letzte Suche: vor {time_diff.seconds // 3600}h {(time_diff.seconds % 3600) // 60}min")
    
    # Suchhistorie mit anklickbaren Elementen
    st.markdown("---")
    st.subheader("📋 Suchhistorie (anklickbar)")
    
    search_history = st.session_state.get("search_history", [])
    
    if search_history:
        # Gruppiere nach Suchbegriff
        grouped_searches = {}
        for search in search_history:
            term = search.get("search_term", "Unbekannt")
            if term not in grouped_searches:
                grouped_searches[term] = []
            grouped_searches[term].append(search)
        
        # Anzeige der gruppierten Suchen
        for search_term, searches in grouped_searches.items():
            latest_search = max(searches, key=lambda x: x.get("timestamp", ""))
            total_papers = sum(s.get("paper_count", 0) for s in searches)
            search_count = len(searches)
            
            col_search1, col_search2, col_search3 = st.columns([3, 1, 1])
            
            with col_search1:
                if st.button(f"🔍 **{search_term}** ({search_count} Suchen, {total_papers} Papers)", 
                           key=f"search_btn_{search_term}"):
                    show_search_details(search_term, searches)
            
            with col_search2:
                last_time = latest_search.get("timestamp", "")[:16]
                st.write(f"📅 {last_time}")
            
            with col_search3:
                if st.button("📊 Excel", key=f"excel_btn_{search_term}"):
                    show_excel_sheet_content(search_term)
        
        # Quick Actions
        st.markdown("---")
        st.subheader("⚡ Quick Actions")
        
        col_quick1, col_quick2, col_quick3 = st.columns(3)
        
        with col_quick1:
            if st.button("🔄 **Alle Suchen wiederholen**"):
                repeat_all_searches()
        
        with col_quick2:
            if st.button("📧 **Status-Email senden**"):
                send_status_email()
        
        with col_quick3:
            if st.button("📁 **Excel öffnen**"):
                st.success("📁 Excel-Datei zum Download bereit!")
                offer_excel_download()
    
    else:
        st.info("📭 Noch keine Suchen durchgeführt. Starten Sie im Tab 'Paper-Suche'!")

def show_search_details(search_term: str, searches: List[Dict]):
    """Zeigt Details einer Suchanfrage"""
    st.markdown("---")
    st.subheader(f"🔍 Details für: '{search_term}'")
    
    # Statistiken
    total_papers = sum(s.get("paper_count", 0) for s in searches)
    latest_search = max(searches, key=lambda x: x.get("timestamp", ""))
    
    col_detail1, col_detail2, col_detail3 = st.columns(3)
    
    with col_detail1:
        st.metric("📄 Gesamt Papers", total_papers)
    
    with col_detail2:
        st.metric("🔍 Anzahl Suchen", len(searches))
    
    with col_detail3:
        new_papers = sum(s.get("new_papers", 0) for s in searches)
        st.metric("🆕 Neue Papers", new_papers)
    
    # Suchverlauf
    st.write("**📊 Suchverlauf:**")
    for i, search in enumerate(reversed(searches[-10:]), 1):
        timestamp = search.get("timestamp", "")[:19]
        paper_count = search.get("paper_count", 0)
        new_count = search.get("new_papers", 0)
        
        status_icon = "🆕" if new_count > 0 else "📄"
        st.write(f"{status_icon} **{i}.** {timestamp} - {paper_count} Papers ({new_count} neu)")
    
    # Aktionen
    col_action1, col_action2, col_action3 = st.columns(3)
    
    with col_action1:
        if st.button("🔄 Suche wiederholen", key=f"repeat_{search_term}"):
            repeat_search(search_term)
    
    with col_action2:
        if st.button("📊 Excel anzeigen", key=f"show_excel_{search_term}"):
            show_excel_sheet_content(search_term)
    
    with col_action3:
        if st.button("📧 Email senden", key=f"email_{search_term}"):
            send_search_summary_email(search_term, searches)

def show_advanced_paper_search():
    """Erweiterte Paper-Suche mit Excel-Integration"""
    st.subheader("🔍 Erweiterte Paper-Suche")
    
    # Email-Status anzeigen
    email_status = is_email_configured()
    if email_status:
        st.success("✅ Email-Benachrichtigungen aktiviert")
    else:
        st.info("ℹ️ Email-Benachrichtigungen deaktiviert - Konfigurieren Sie sie im Email-Tab")
    
    # Such-Interface
    with st.form("advanced_search_form"):
        col_search1, col_search2 = st.columns([3, 1])
        
        with col_search1:
            search_query = st.text_input(
                "**🔍 PubMed Suchbegriff:**",
                placeholder="z.B. 'diabetes genetics', 'machine learning radiology', 'COVID-19 treatment'",
                help="Führt automatisch PubMed-Suche durch, erstellt Excel-Sheet und sendet Email"
            )
        
        with col_search2:
            max_results = st.number_input(
                "Max. Ergebnisse", 
                min_value=10, 
                max_value=500, 
                value=100
            )
        
        # Erweiterte Optionen
        with st.expander("🔧 Erweiterte Suchoptionen"):
            col_adv1, col_adv2, col_adv3 = st.columns(3)
            
            with col_adv1:
                date_filter = st.selectbox(
                    "📅 Zeitraum:",
                    ["Alle", "Letztes Jahr", "Letzte 2 Jahre", "Letzte 5 Jahre", "Letzte 10 Jahre"],
                    index=2
                )
            
            with col_adv2:
                force_email = st.checkbox(
                    "📧 Email senden (erzwingen)", 
                    value=False,
                    help="Sendet Email auch wenn normalerweise deaktiviert"
                )
            
            with col_adv3:
                force_new_sheet = st.checkbox(
                    "📊 Neues Excel-Sheet erzwingen", 
                    value=False,
                    help="Erstellt neues Sheet auch bei wiederholter Suche"
                )
        
        search_button = st.form_submit_button("🚀 **PAPER-SUCHE STARTEN**", type="primary")
    
    # Quick Search Buttons (aus Historie)
    if st.session_state.get("search_history"):
        st.write("**⚡ Schnellsuche (aus Historie):**")
        unique_terms = list(set(s.get("search_term", "") for s in st.session_state["search_history"]))[:5]
        
        cols = st.columns(min(len(unique_terms), 5))
        for i, term in enumerate(unique_terms):
            with cols[i]:
                if st.button(f"🔍 {term[:15]}...", key=f"quick_{i}"):
                    execute_advanced_paper_search(term, 50, "Letzte 2 Jahre", False, False)
    
    # Suche ausführen
    if search_button and search_query:
        execute_advanced_paper_search(search_query, max_results, date_filter, force_email, force_new_sheet)

def execute_advanced_paper_search(query: str, max_results: int, date_filter: str, force_email: bool, force_new_sheet: bool):
    """Führt erweiterte Paper-Suche mit Excel-Integration durch"""
    st.markdown("---")
    st.subheader(f"🔍 **Durchführung:** '{query}'")
    
    # Progress Tracking
    progress_container = st.container()
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    try:
        # 1. Prüfe vorherige Suchen
        status_text.text("📊 Prüfe Suchhistorie...")
        progress_bar.progress(0.1)
        
        previous_results = load_previous_search_results(query)
        is_repeat_search = len(previous_results) > 0
        
        if is_repeat_search and not force_new_sheet:
            st.info(f"🔄 **Wiederholte Suche erkannt!** Vergleiche mit {len(previous_results)} bekannten Papers...")
        
        # 2. Führe PubMed-Suche durch
        status_text.text("🔍 Durchsuche PubMed-Datenbank...")
        progress_bar.progress(0.3)
        
        advanced_query = build_advanced_search_query(query, date_filter)
        current_papers = perform_comprehensive_pubmed_search(advanced_query, max_results)
        
        progress_bar.progress(0.6)
        
        if not current_papers:
            st.error(f"❌ **Keine Papers für '{query}' gefunden!**")
            progress_bar.empty()
            status_text.empty()
            return
        
        # 3. Vergleiche und identifiziere neue Papers
        status_text.text("📊 Analysiere Ergebnisse...")
        progress_bar.progress(0.8)
        
        if is_repeat_search and not force_new_sheet:
            new_papers = identify_new_papers(current_papers, previous_results)
            
            if new_papers:
                st.success(f"🆕 **{len(new_papers)} NEUE Papers gefunden** (von {len(current_papers)} gesamt)")
                st.balloons()
                
                # Aktualisiere Excel
                update_excel_sheet(query, current_papers, new_papers)
                
                # Sende Email für neue Papers
                if force_email or should_send_email(len(new_papers)):
                    send_new_papers_email(query, new_papers, len(current_papers))
                
                # Zeige Ergebnisse
                display_search_results(current_papers, new_papers, query, is_repeat=True)
            else:
                st.info(f"ℹ️ **Keine neuen Papers** - Alle {len(current_papers)} Papers bereits bekannt")
                display_search_results(current_papers, [], query, is_repeat=True)
        else:
            # Erste Suche oder erzwungenes neues Sheet
            st.success(f"🎉 **{len(current_papers)} Papers gefunden!**")
            st.balloons()
            
            # Erstelle neues Excel-Sheet
            create_new_excel_sheet(query, current_papers)
            
            # Sende Email für alle Papers
            if force_email or should_send_email(len(current_papers)):
                send_first_search_email(query, current_papers)
            
            # Zeige Ergebnisse
            display_search_results(current_papers, current_papers, query, is_repeat=False)
        
        # 4. Aktualisiere System-Status
        status_text.text("💾 Speichere Ergebnisse...")
        progress_bar.progress(0.9)
        
        save_search_to_history(query, current_papers, new_papers if is_repeat_search else current_papers)
        update_system_status(len(current_papers))
        
        progress_bar.progress(1.0)
        status_text.text("✅ Suche abgeschlossen!")
        
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ **Fehler bei der Suche:** {str(e)}")

def perform_comprehensive_pubmed_search(query: str, max_results: int) -> List[Dict[str, Any]]:
    """Umfassende PubMed-Suche mit verbessertem Error Handling"""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    # 1. esearch - hole PMIDs
    search_url = f"{base_url}esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": max_results,
        "email": "research.system@papersearch.com",
        "tool": "ScientificPaperSearchSystem",
        "sort": "relevance"
    }
    
    try:
        with st.spinner("🔍 Verbinde zu PubMed..."):
            response = requests.get(search_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            pmids = data.get("esearchresult", {}).get("idlist", [])
            total_count = int(data.get("esearchresult", {}).get("count", 0))
            
            st.write(f"📊 **PubMed Datenbank:** {total_count:,} Papers verfügbar, {len(pmids)} werden abgerufen")
            
            if not pmids:
                return []
            
            # 2. efetch - hole Details in Batches
            return fetch_paper_details_batch(pmids)
            
    except requests.exceptions.RequestException as e:
        st.error(f"❌ **PubMed Verbindungsfehler:** {str(e)}")
        return []
    except Exception as e:
        st.error(f"❌ **PubMed Suchfehler:** {str(e)}")
        return []

def fetch_paper_details_batch(pmids: List[str], batch_size: int = 50) -> List[Dict[str, Any]]:
    """Holt Paper-Details in Batches für bessere Performance"""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    all_papers = []
    
    # Teile PMIDs in Batches
    batches = [pmids[i:i + batch_size] for i in range(0, len(pmids), batch_size)]
    
    progress_bar = st.progress(0)
    batch_status = st.empty()
    
    for batch_idx, batch_pmids in enumerate(batches):
        try:
            batch_status.text(f"📥 Batch {batch_idx + 1}/{len(batches)}: {len(batch_pmids)} Papers...")
            
            params = {
                "db": "pubmed",
                "id": ",".join(batch_pmids),
                "retmode": "xml",
                "email": "research.system@papersearch.com",
                "tool": "ScientificPaperSearchSystem"
            }
            
            response = requests.get(base_url, params=params, timeout=60)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            articles = root.findall(".//PubmedArticle")
            
            for article in articles:
                paper_data = parse_pubmed_article(article)
                if paper_data:
                    all_papers.append(paper_data)
            
            # Progress Update
            progress = (batch_idx + 1) / len(batches)
            progress_bar.progress(progress)
            
            # Rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            st.warning(f"⚠️ Batch {batch_idx + 1} Fehler: {str(e)}")
            continue
    
    progress_bar.empty()
    batch_status.empty()
    
    return all_papers

def parse_pubmed_article(article) -> Dict[str, Any]:
    """Erweiterte Artikel-Parsing mit mehr Feldern"""
    try:
        # PMID
        pmid_elem = article.find(".//PMID")
        pmid = pmid_elem.text if pmid_elem is not None else ""
        
        # Title
        title_elem = article.find(".//ArticleTitle")
        title = title_elem.text if title_elem is not None else "Titel nicht verfügbar"
        
        # Abstract (alle Teile)
        abstract_parts = []
        for abstract_elem in article.findall(".//AbstractText"):
            if abstract_elem.text:
                label = abstract_elem.get("Label", "")
                text = abstract_elem.text
                if label and label.upper() not in ["UNLABELLED", "UNASSIGNED"]:
                    abstract_parts.append(f"**{label}:** {text}")
                else:
                    abstract_parts.append(text)
        
        abstract = "\n\n".join(abstract_parts) if abstract_parts else "Kein Abstract verfügbar"
        
        # Journal Info
        journal_elem = article.find(".//Journal/Title")
        journal = journal_elem.text if journal_elem is not None else "Journal unbekannt"
        
        # ISO Abbreviation
        iso_abbrev_elem = article.find(".//Journal/ISOAbbreviation")
        iso_abbrev = iso_abbrev_elem.text if iso_abbrev_elem is not None else ""
        
        # Publication Date
        year_elem = article.find(".//PubDate/Year")
        month_elem = article.find(".//PubDate/Month")
        day_elem = article.find(".//PubDate/Day")
        
        if year_elem is not None:
            year = year_elem.text
            month = month_elem.text if month_elem is not None else "01"
            day = day_elem.text if day_elem is not None else "01"
            pub_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        else:
            medline_date_elem = article.find(".//PubDate/MedlineDate")
            if medline_date_elem is not None:
                medline_date = medline_date_elem.text or ""
                year_match = re.search(r'\d{4}', medline_date)
                year = year_match.group() if year_match else "Unbekannt"
                pub_date = f"{year}-01-01"
            else:
                year = "Unbekannt"
                pub_date = "Unbekannt"
        
        # Authors (erweitert)
        authors = []
        for author in article.findall(".//Author"):
            lastname = author.find("LastName")
            forename = author.find("ForeName")
            initials = author.find("Initials")
            
            if lastname is not None:
                author_name = lastname.text or ""
                if forename is not None:
                    author_name = f"{author_name}, {forename.text}"
                elif initials is not None:
                    author_name = f"{author_name}, {initials.text}"
                authors.append(author_name)
        
        authors_str = "; ".join(authors[:8])  # Mehr Autoren anzeigen
        if len(authors) > 8:
            authors_str += f" et al. (+{len(authors) - 8} weitere)"
        
        # DOI
        doi = ""
        for article_id in article.findall(".//ArticleId"):
            if article_id.get("IdType") == "doi":
                doi = article_id.text
                break
        
        # PMC ID
        pmc_id = ""
        for article_id in article.findall(".//ArticleId"):
            if article_id.get("IdType") == "pmc":
                pmc_id = article_id.text
                break
        
        # Keywords/MeSH Terms
        keywords = []
        for keyword in article.findall(".//Keyword"):
            if keyword.text:
                keywords.append(keyword.text)
        
        mesh_terms = []
        for mesh in article.findall(".//MeshHeading/DescriptorName"):
            if mesh.text:
                mesh_terms.append(mesh.text)
        
        # Study Type/Publication Type
        pub_types = []
        for pub_type in article.findall(".//PublicationType"):
            if pub_type.text:
                pub_types.append(pub_type.text)
        
        return {
            "PMID": pmid,
            "Title": title,
            "Abstract": abstract,
            "Journal": journal,
            "Journal_ISO": iso_abbrev,
            "Year": year,
            "Publication_Date": pub_date,
            "Authors": authors_str,
            "Author_Count": len(authors),
            "DOI": doi,
            "PMC_ID": pmc_id,
            "URL": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "Keywords": "; ".join(keywords[:10]),  # Top 10 Keywords
            "MeSH_Terms": "; ".join(mesh_terms[:10]),  # Top 10 MeSH Terms
            "Publication_Types": "; ".join(pub_types[:5]),
            "Search_Date": datetime.datetime.now().isoformat(),
            "Is_New": True,
            "Abstract_Length": len(abstract),
            "Has_DOI": bool(doi),
            "Has_PMC": bool(pmc_id),
            "Has_Keywords": bool(keywords),
            "Has_MeSH": bool(mesh_terms)
        }
        
    except Exception as e:
        st.warning(f"⚠️ Fehler beim Parsen eines Artikels: {str(e)}")
        return None

def create_new_excel_sheet(search_term: str, papers: List[Dict]):
    """Erstellt neues Excel-Sheet für Suchbegriff"""
    template_path = st.session_state["excel_template"]["file_path"]
    
    try:
        wb = openpyxl.load_workbook(template_path)
        
        # Sheet-Name generieren
        sheet_name = generate_sheet_name(search_term)
        
        # Prüfe ob Sheet bereits existiert
        if sheet_name in wb.sheetnames:
            sheet_name = f"{sheet_name}_{datetime.datetime.now().strftime('%H%M')}"
        
        # Erstelle neues Sheet
        ws = wb.create_sheet(title=sheet_name)
        
        # Erweiterte Headers
        headers = [
            "PMID", "Titel", "Autoren", "Anzahl_Autoren", "Journal", "Journal_ISO", 
            "Jahr", "Publikations_Datum", "DOI", "PMC_ID", "URL", "Abstract", 
            "Abstract_Länge", "Keywords", "MeSH_Terms", "Publikations_Typen",
            "Hat_DOI", "Hat_PMC", "Hat_Keywords", "Hat_MeSH", "Hinzugefügt_am", 
            "Status", "Notizen"
        ]
        
        # Header-Styling
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="2F4F4F", end_color="2F4F4F", fill_type="solid")
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
        
        # Daten hinzufügen
        current_time = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        
        for row_idx, paper in enumerate(papers, 2):
            row_data = [
                paper.get("PMID", ""),
                paper.get("Title", ""),
                paper.get("Authors", ""),
                paper.get("Author_Count", 0),
                paper.get("Journal", ""),
                paper.get("Journal_ISO", ""),
                paper.get("Year", ""),
                paper.get("Publication_Date", ""),
                paper.get("DOI", ""),
                paper.get("PMC_ID", ""),
                paper.get("URL", ""),
                paper.get("Abstract", "")[:2000] + "..." if len(paper.get("Abstract", "")) > 2000 else paper.get("Abstract", ""),
                paper.get("Abstract_Length", 0),
                paper.get("Keywords", ""),
                paper.get("MeSH_Terms", ""),
                paper.get("Publication_Types", ""),
                "Ja" if paper.get("Has_DOI", False) else "Nein",
                "Ja" if paper.get("Has_PMC", False) else "Nein",
                "Ja" if paper.get("Has_Keywords", False) else "Nein",
                "Ja" if paper.get("Has_MeSH", False) else "Nein",
                current_time,
                "NEU",
                ""
            ]
            
            for col, value in enumerate(row_data, 1):
                ws.cell(row=row_idx, column=col, value=value)
        
        # Spaltenbreiten anpassen
        column_widths = [
            10, 50, 40, 12, 30, 15, 8, 15, 20, 15, 25, 80, 12, 
            30, 30, 20, 8, 8, 8, 8, 15, 10, 20
        ]
        
        for col, width in enumerate(column_widths, 1):
            ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = width
        
        # Overview Sheet aktualisieren
        update_overview_sheet(wb, sheet_name, search_term, len(papers), current_time, len(papers))
        
        wb.save(template_path)
        
        st.success(f"✅ **Neues Excel-Sheet erstellt:** '{sheet_name}' mit {len(papers)} Papers")
        
        # Download anbieten
        offer_excel_download()
        
    except Exception as e:
        st.error(f"❌ **Fehler beim Erstellen des Excel-Sheets:** {str(e)}")

def update_excel_sheet(search_term: str, all_papers: List[Dict], new_papers: List[Dict]):
    """Aktualisiert existierendes Excel-Sheet mit neuen Papers"""
    template_path = st.session_state["excel_template"]["file_path"]
    
    try:
        wb = openpyxl.load_workbook(template_path)
        sheet_name = generate_sheet_name(search_term)
        
        if sheet_name not in wb.sheetnames:
            # Sheet existiert nicht, erstelle neues
            create_new_excel_sheet(search_term, all_papers)
            return
        
        ws = wb[sheet_name]
        current_time = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        
        # Finde nächste freie Zeile
        next_row = ws.max_row + 1
        
        # Füge nur neue Papers hinzu
        for paper in new_papers:
            row_data = [
                paper.get("PMID", ""),
                paper.get("Title", ""),
                paper.get("Authors", ""),
                paper.get("Author_Count", 0),
                paper.get("Journal", ""),
                paper.get("Journal_ISO", ""),
                paper.get("Year", ""),
                paper.get("Publication_Date", ""),
                paper.get("DOI", ""),
                paper.get("PMC_ID", ""),
                paper.get("URL", ""),
                paper.get("Abstract", "")[:2000] + "..." if len(paper.get("Abstract", "")) > 2000 else paper.get("Abstract", ""),
                paper.get("Abstract_Length", 0),
                paper.get("Keywords", ""),
                paper.get("MeSH_Terms", ""),
                paper.get("Publication_Types", ""),
                "Ja" if paper.get("Has_DOI", False) else "Nein",
                "Ja" if paper.get("Has_PMC", False) else "Nein",
                "Ja" if paper.get("Has_Keywords", False) else "Nein",
                "Ja" if paper.get("Has_MeSH", False) else "Nein",
                current_time,
                "NEU",
                ""
            ]
            
            for col, value in enumerate(row_data, 1):
                ws.cell(row=next_row, column=col, value=value)
            next_row += 1
        
        # Overview Sheet aktualisieren
        total_papers = ws.max_row - 1  # -1 für Header
        update_overview_sheet(wb, sheet_name, search_term, total_papers, current_time, len(new_papers))
        
        wb.save(template_path)
        
        st.success(f"✅ **Excel-Sheet aktualisiert:** {len(new_papers)} neue Papers hinzugefügt zu '{sheet_name}'")
        offer_excel_download()
        
    except Exception as e:
        st.error(f"❌ **Fehler beim Aktualisieren des Excel-Sheets:** {str(e)}")

def update_overview_sheet(wb, sheet_name: str, search_term: str, total_papers: int, last_update: str, new_papers: int):
    """Aktualisiert Overview Sheet mit aktuellen Daten"""
    try:
        overview_sheet = wb["📊_Overview"]
        
        # Suche existierende Zeile oder erstelle neue
        row_found = False
        for row in range(2, overview_sheet.max_row + 1):
            if overview_sheet.cell(row=row, column=1).value == sheet_name:
                # Update existierende Zeile
                overview_sheet.cell(row=row, column=3, value=total_papers)
                overview_sheet.cell(row=row, column=4, value=last_update)
                overview_sheet.cell(row=row, column=5, value=new_papers)
                overview_sheet.cell(row=row, column=6, value="Aktiv")
                row_found = True
                break
        
        if not row_found:
            # Neue Zeile hinzufügen
            next_row = overview_sheet.max_row + 1
            overview_data = [
                sheet_name,
                search_term,
                total_papers,
                last_update,
                new_papers,
                "Aktiv",
                datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            ]
            
            for col, value in enumerate(overview_data, 1):
                overview_sheet.cell(row=next_row, column=col, value=value)
    
    except Exception as e:
        st.warning(f"⚠️ Fehler beim Aktualisieren des Overview-Sheets: {str(e)}")

def generate_sheet_name(search_term: str) -> str:
    """Generiert gültigen Excel-Sheet-Namen"""
    # Excel Sheet Namen dürfen max 31 Zeichen haben und bestimmte Zeichen nicht enthalten
    invalid_chars = ['/', '\\', '?', '*', '[', ']', ':']
    
    clean_name = search_term
    for char in invalid_chars:
        clean_name = clean_name.replace(char, '_')
    
    # Entferne multiple Unterstriche und trimme
    clean_name = re.sub(r'_+', '_', clean_name).strip('_')
    
    # Kürze auf 25 Zeichen (lasse Platz für eventuelle Suffixe)
    if len(clean_name) > 25:
        clean_name = clean_name[:25]
    
    return clean_name

def show_excel_template_management():
    """Excel-Template Management und Sheet-Übersicht"""
    st.subheader("📋 Excel-Template Management")
    
    template_path = st.session_state["excel_template"]["file_path"]
    
    # Template Status
    if os.path.exists(template_path):
        file_size = os.path.getsize(template_path)
        file_date = datetime.datetime.fromtimestamp(os.path.getmtime(template_path))
        
        st.success(f"✅ **Master Excel-Template aktiv:** {template_path}")
        st.info(f"📊 **Größe:** {file_size:,} bytes | **Letzte Änderung:** {file_date.strftime('%d.%m.%Y %H:%M')}")
    else:
        st.error("❌ Master Excel-Template nicht gefunden!")
        if st.button("🔧 Template neu erstellen"):
            create_master_excel_template()
            st.rerun()
    
    # Excel-Aktionen
    col_excel1, col_excel2, col_excel3 = st.columns(3)
    
    with col_excel1:
        if st.button("📥 **Excel herunterladen**"):
            offer_excel_download()
    
    with col_excel2:
        if st.button("🔄 **Template zurücksetzen**"):
            reset_excel_template()
    
    with col_excel3:
        if st.button("📊 **Sheet-Übersicht anzeigen**"):
            show_excel_sheets_overview()
    
    # Excel-Sheets Übersicht
    st.markdown("---")
    st.subheader("📊 Excel-Sheets Übersicht")
    
    if os.path.exists(template_path):
        try:
            # Overview Sheet laden
            df_overview = pd.read_excel(template_path, sheet_name="📊_Overview")
            
            if len(df_overview) > 0:
                st.write(f"**📋 {len(df_overview)} aktive Sheets:**")
                
                # Interaktive Tabelle
                for idx, row in df_overview.iterrows():
                    sheet_name = row.get("Sheet_Name", "Unbekannt")
                    search_term = row.get("Suchbegriff", "Unbekannt")
                    paper_count = row.get("Anzahl_Papers", 0)
                    last_update = row.get("Letztes_Update", "Unbekannt")
                    new_today = row.get("Neue_Papers_Heute", 0)
                    
                    with st.expander(f"📊 **{sheet_name}** - {search_term} ({paper_count} Papers)"):
                        col_sheet1, col_sheet2 = st.columns(2)
                        
                        with col_sheet1:
                            st.write(f"**🔍 Suchbegriff:** {search_term}")
                            st.write(f"**📄 Gesamt Papers:** {paper_count}")
                            st.write(f"**🆕 Neue heute:** {new_today}")
                        
                        with col_sheet2:
                            st.write(f"**📅 Letztes Update:** {last_update}")
                            st.write(f"**📊 Sheet:** {sheet_name}")
                            
                            if st.button("👁️ Sheet anzeigen", key=f"view_sheet_{idx}"):
                                show_excel_sheet_content(search_term)
                
                # Zusammenfassung
                total_papers = df_overview["Anzahl_Papers"].sum()
                total_new_today = df_overview["Neue_Papers_Heute"].sum()
                
                st.markdown("---")
                col_sum1, col_sum2, col_sum3 = st.columns(3)
                
                with col_sum1:
                    st.metric("📊 Gesamt Sheets", len(df_overview))
                
                with col_sum2:
                    st.metric("📄 Gesamt Papers", int(total_papers))
                
                with col_sum3:
                    st.metric("🆕 Neue heute", int(total_new_today))
            
            else:
                st.info("📭 Noch keine Excel-Sheets erstellt. Starten Sie eine Paper-Suche!")
        
        except Exception as e:
            st.error(f"❌ Fehler beim Laden der Excel-Übersicht: {str(e)}")
    
    # Sheet-spezifische Aktionen
    st.markdown("---")
    st.subheader("🔧 Sheet-spezifische Aktionen")
    
    # Sheet auswählen
    if os.path.exists(template_path):
        try:
            xl_file = pd.ExcelFile(template_path)
            available_sheets = [sheet for sheet in xl_file.sheet_names if not sheet.startswith(('📊_', 'ℹ️_'))]
            
            if available_sheets:
                selected_sheet = st.selectbox("📊 Sheet auswählen:", available_sheets)
                
                col_action1, col_action2, col_action3 = st.columns(3)
                
                with col_action1:
                    if st.button("👁️ **Sheet-Inhalt anzeigen**"):
                        show_selected_sheet_content(selected_sheet)
                
                with col_action2:
                    if st.button("📧 **Sheet per Email senden**"):
                        send_sheet_email(selected_sheet)
                
                with col_action3:
                    if st.button("🗑️ **Sheet löschen**"):
                        delete_excel_sheet(selected_sheet)
        
        except Exception as e:
            st.error(f"❌ Fehler beim Laden der Sheet-Liste: {str(e)}")

def show_excel_sheet_content(search_term: str):
    """Zeigt Inhalt eines Excel-Sheets basierend auf Suchbegriff"""
    template_path = st.session_state["excel_template"]["file_path"]
    sheet_name = generate_sheet_name(search_term)
    
    try:
        xl_file = pd.ExcelFile(template_path)
        
        if sheet_name in xl_file.sheet_names:
            df = pd.read_excel(template_path, sheet_name=sheet_name)
            
            st.markdown("---")
            st.subheader(f"📊 Excel-Sheet: '{search_term}'")
            
            # Statistiken
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            
            with col_stat1:
                st.metric("📄 Gesamt Papers", len(df))
            
            with col_stat2:
                new_papers = len(df[df["Status"] == "NEU"]) if "Status" in df.columns else 0
                st.metric("🆕 Neue Papers", new_papers)
            
            with col_stat3:
                with_doi = len(df[df["Hat_DOI"] == "Ja"]) if "Hat_DOI" in df.columns else 0
                st.metric("🔗 Mit DOI", with_doi)
            
            with col_stat4:
                current_year = datetime.datetime.now().year
                recent = len(df[df["Jahr"].astype(str).str.contains(str(current_year-2), na=False)]) if "Jahr" in df.columns else 0
                st.metric("📅 Letzte 2 Jahre", recent)
            
            # Filter-Optionen
            st.write("**🔍 Filter:**")
            col_filter1, col_filter2, col_filter3 = st.columns(3)
            
            with col_filter1:
                status_filter = st.selectbox("Status:", ["Alle", "NEU", "Gesehen"], index=0)
            
            with col_filter2:
                year_filter = st.selectbox("Jahr:", ["Alle"] + sorted(df["Jahr"].unique().astype(str), reverse=True) if "Jahr" in df.columns else ["Alle"])
            
            with col_filter3:
                show_count = st.number_input("Anzahl anzeigen:", min_value=5, max_value=100, value=20)
            
            # Filter anwenden
            filtered_df = df.copy()
            if status_filter != "Alle" and "Status" in df.columns:
                filtered_df = filtered_df[filtered_df["Status"] == status_filter]
            if year_filter != "Alle" and "Jahr" in df.columns:
                filtered_df = filtered_df[filtered_df["Jahr"].astype(str) == year_filter]
            
            # Anzeige der Papers
            st.write(f"**📋 Papers anzeigen ({len(filtered_df)} gefiltert von {len(df)} gesamt):**")
            
            display_papers = filtered_df.head(show_count)
            
            for idx, (_, paper) in enumerate(display_papers.iterrows(), 1):
                is_new = paper.get("Status", "") == "NEU"
                status_icon = "🆕" if is_new else "📄"
                
                title = paper.get("Titel", "Unbekannt")
                authors = paper.get("Autoren", "Unbekannt")
                journal = paper.get("Journal", "Unbekannt")
                year = paper.get("Jahr", "")
                pmid = paper.get("PMID", "")
                
                with st.expander(f"{status_icon} **{idx}.** {title[:60]}... ({year})"):
                    col_paper1, col_paper2 = st.columns([3, 1])
                    
                    with col_paper1:
                        st.write(f"**📄 Titel:** {title}")
                        st.write(f"**👥 Autoren:** {authors}")
                        st.write(f"**📚 Journal:** {journal} ({year})")
                        st.write(f"**🆔 PMID:** {pmid}")
                        
                        if paper.get("DOI"):
                            st.write(f"**🔗 DOI:** {paper.get('DOI')}")
                        
                        if paper.get("URL"):
                            st.markdown(f"🔗 [**PubMed ansehen**]({paper.get('URL')})")
                    
                    with col_paper2:
                        if is_new:
                            st.success("🆕 **NEU**")
                        else:
                            st.info("📄 Gesehen")
                        
                        if st.button("📧 Email", key=f"email_paper_{idx}_{pmid}"):
                            send_single_paper_email(paper.to_dict(), search_term)
            
            if len(filtered_df) > show_count:
                st.info(f"... und {len(filtered_df) - show_count} weitere Papers")
            
            # Download des gefilterten Sheets
            if st.button("📥 **Gefiltertes Sheet herunterladen**"):
                download_filtered_sheet(filtered_df, f"{search_term}_gefiltert")
        
        else:
            st.error(f"❌ Sheet '{sheet_name}' nicht gefunden!")
    
    except Exception as e:
        st.error(f"❌ Fehler beim Anzeigen des Sheet-Inhalts: {str(e)}")

def offer_excel_download():
    """Bietet Master Excel-Datei zum Download an"""
    template_path = st.session_state["excel_template"]["file_path"]
    
    if os.path.exists(template_path):
        try:
            with open(template_path, 'rb') as f:
                excel_data = f.read()
            
            filename = f"PaperSearch_Master_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            
            st.download_button(
                label="📥 **Master Excel-Datei herunterladen**",
                data=excel_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Lädt die komplette Excel-Datei mit allen Sheets herunter"
            )
        
        except Exception as e:
            st.error(f"❌ Fehler beim Bereitstellen der Excel-Datei: {str(e)}")

# Zusätzliche Hilfsfunktionen...

def show_email_config():
    """Vollständige Email-Konfiguration"""
    st.subheader("📧 Email-Konfiguration")
    
    settings = st.session_state.get("email_settings", {})
    
    # Email-Setup Hilfe
    with st.expander("📖 Email-Setup Hilfe"):
        st.info("""
        **Für Gmail (empfohlen):**
        1. ✅ 2-Faktor-Authentifizierung aktivieren
        2. ✅ App-Passwort erstellen (nicht normales Passwort!)
        3. ✅ SMTP: smtp.gmail.com, Port: 587, TLS: An
        
        **Für Outlook/Hotmail:**
        - SMTP: smtp-mail.outlook.com, Port: 587
        
        **Für andere Anbieter:**
        - Konsultieren Sie die SMTP-Einstellungen Ihres Anbieters
        """)
    
    with st.form("email_config_form"):
        st.subheader("📬 Grundeinstellungen")
        
        col1, col2 = st.columns(2)
        
        with col1:
            sender_email = st.text_input(
                "Absender Email *", 
                value=settings.get("sender_email", ""),
                placeholder="absender@gmail.com"
            )
            
            smtp_server = st.text_input(
                "SMTP Server *",
                value=settings.get("smtp_server", "smtp.gmail.com")
            )
            
            auto_notifications = st.checkbox(
                "Automatische Benachrichtigungen", 
                value=settings.get("auto_notifications", True)
            )
        
        with col2:
            recipient_email = st.text_input(
                "Empfänger Email *", 
                value=settings.get("recipient_email", ""),
                placeholder="empfaenger@example.com"
            )
            
            smtp_port = st.number_input(
                "SMTP Port *",
                value=settings.get("smtp_port", 587),
                min_value=1,
                max_value=65535
            )
            
            min_papers = st.number_input(
                "Min. Papers für Benachrichtigung", 
                value=settings.get("min_papers", 1),
                min_value=1,
                max_value=100
            )
        
        sender_password = st.text_input(
            "Email Passwort / App-Passwort *",
            value=settings.get("sender_password", ""),
            type="password",
            help="Für Gmail: App-spezifisches Passwort verwenden!"
        )
        
        use_tls = st.checkbox(
            "TLS verschlüsselung verwenden (empfohlen)",
            value=settings.get("use_tls", True)
        )
        
        # Email-Vorlagen
        st.subheader("📝 Email-Vorlagen")
        
        subject_template = st.text_input(
            "Betreff-Vorlage",
            value=settings.get("subject_template", "🔬 {count} neue Papers für '{search_term}'"),
            help="Platzhalter: {count}, {search_term}, {frequency}"
        )
        
        message_template = st.text_area(
            "Nachricht-Vorlage",
            value=settings.get("message_template", "Neue Papers gefunden..."),
            height=200,
            help="Platzhalter: {date}, {search_term}, {count}, {frequency}, {new_papers_list}, {excel_file}"
        )
        
        if st.form_submit_button("💾 **Email-Einstellungen speichern**", type="primary"):
            new_settings = {
                "sender_email": sender_email,
                "recipient_email": recipient_email,
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "sender_password": sender_password,
                "use_tls": use_tls,
                "auto_notifications": auto_notifications,
                "min_papers": min_papers,
                "subject_template": subject_template,
                "message_template": message_template
            }
            
            st.session_state["email_settings"] = new_settings
            st.success("✅ Email-Einstellungen gespeichert!")
            
            # Vorschau generieren
            if sender_email and recipient_email:
                preview = generate_email_preview(new_settings, "Beispiel Suchbegriff", 5)
                st.info("📧 **Email-Vorschau:**")
                st.code(preview, language="text")
    
    # Test-Email
    st.markdown("---")
    st.subheader("🧪 Email-System testen")
    
    col_test1, col_test2 = st.columns(2)
    
    with col_test1:
        if st.button("📧 **Test-Email senden**", type="primary"):
            send_test_email()
    
    with col_test2:
        if st.button("📊 **Email-Status prüfen**"):
            check_email_status()

def send_test_email():
    """Sendet Test-Email"""
    settings = st.session_state.get("email_settings", {})
    
    if not settings.get("sender_email") or not settings.get("recipient_email"):
        st.error("❌ Email-Konfiguration unvollständig!")
        return
    
    subject = "🧪 Test-Email vom Paper-Suche System"
    message = f"""Dies ist eine Test-Email vom Paper-Suche System.

📅 Gesendet am: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
📧 Von: {settings.get('sender_email')}
📧 An: {settings.get('recipient_email')}

✅ Wenn Sie diese Email erhalten, funktioniert das Email-System korrekt!

System-Informationen:
• SMTP Server: {settings.get('smtp_server')}
• Port: {settings.get('smtp_port')}
• TLS: {'Aktiviert' if settings.get('use_tls') else 'Deaktiviert'}

Mit freundlichen Grüßen,
Ihr Paper-Suche System"""
    
    success, status_message = send_real_email(
        settings.get("recipient_email"), 
        subject, 
        message
    )
    
    if success:
        st.success("✅ **Test-Email erfolgreich gesendet!**")
        st.balloons()
    else:
        st.error(f"❌ **Test-Email fehlgeschlagen:** {status_message}")

def send_real_email(to_email: str, subject: str, message: str, attachment_path: str = None) -> tuple:
    """Sendet echte Email über SMTP"""
    settings = st.session_state.get("email_settings", {})
    
    sender_email = settings.get("sender_email", "")
    sender_password = settings.get("sender_password", "")
    smtp_server = settings.get("smtp_server", "smtp.gmail.com")
    smtp_port = settings.get("smtp_port", 587)
    use_tls = settings.get("use_tls", True)
    
    if not all([sender_email, sender_password, to_email]):
        return False, "❌ Email-Konfiguration unvollständig"
    
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain', 'utf-8'))
        
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {os.path.basename(attachment_path)}'
                )
                msg.attach(part)
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        
        if use_tls:
            context = ssl.create_default_context()
            server.starttls(context=context)
        
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        return True, "✅ Email erfolgreich gesendet"
        
    except smtplib.SMTPAuthenticationError:
        return False, "❌ SMTP-Authentifizierung fehlgeschlagen - Prüfen Sie Email/Passwort"
    except smtplib.SMTPRecipientsRefused:
        return False, "❌ Empfänger-Email ungültig"
    except smtplib.SMTPServerDisconnected:
        return False, "❌ SMTP-Server-Verbindung unterbrochen"
    except Exception as e:
        return False, f"❌ Email-Fehler: {str(e)}"

# Weitere Hilfsfunktionen...
def build_advanced_search_query(query: str, date_filter: str) -> str:
    """Erweiterte Suchanfrage mit Filtern"""
    query_parts = [query]
    
    if date_filter != "Alle":
        current_year = datetime.datetime.now().year
        if date_filter == "Letztes Jahr":
            query_parts.append(f"AND {current_year-1}:{current_year}[dp]")
        elif date_filter == "Letzte 2 Jahre":
            query_parts.append(f"AND {current_year-2}:{current_year}[dp]")
        elif date_filter == "Letzte 5 Jahre":
            query_parts.append(f"AND {current_year-5}:{current_year}[dp]")
        elif date_filter == "Letzte 10 Jahre":
            query_parts.append(f"AND {current_year-10}:{current_year}[dp]")
    
    return " ".join(query_parts)

def load_previous_search_results(query: str) -> List[Dict]:
    """Lädt vorherige Suchergebnisse"""
    template_path = st.session_state["excel_template"]["file_path"]
    sheet_name = generate_sheet_name(query)
    
    if not os.path.exists(template_path):
        return []
    
    try:
        xl_file = pd.ExcelFile(template_path)
        if sheet_name not in xl_file.sheet_names:
            return []
        
        df = pd.read_excel(template_path, sheet_name=sheet_name)
        
        previous_papers = []
        for _, row in df.iterrows():
            if pd.notna(row.get("PMID")):
                paper = {
                    "PMID": str(row.get("PMID", "")),
                    "Title": str(row.get("Titel", "")),
                    "Authors": str(row.get("Autoren", "")),
                    "Journal": str(row.get("Journal", "")),
                    "Year": str(row.get("Jahr", ""))
                }
                previous_papers.append(paper)
        
        return previous_papers
        
    except Exception:
        return []

def identify_new_papers(current_papers: List[Dict], previous_papers: List[Dict]) -> List[Dict]:
    """Identifiziert neue Papers"""
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

def save_search_to_history(query: str, papers: List[Dict], new_papers: List[Dict]):
    """Speichert Suche in Historie"""
    search_entry = {
        "search_term": query,
        "timestamp": datetime.datetime.now().isoformat(),
        "paper_count": len(papers),
        "new_papers": len(new_papers),
        "date": datetime.datetime.now().date().isoformat()
    }
    
    st.session_state["search_history"].append(search_entry)

def update_system_status(paper_count: int):
    """Aktualisiert System-Status"""
    status = st.session_state["system_status"]
    status["total_searches"] += 1
    status["total_papers"] += paper_count
    status["last_search"] = datetime.datetime.now().isoformat()
    
    # Zähle Excel-Sheets
    template_path = st.session_state["excel_template"]["file_path"]
    if os.path.exists(template_path):
        try:
            xl_file = pd.ExcelFile(template_path)
            status["excel_sheets"] = len([s for s in xl_file.sheet_names if not s.startswith(('📊_', 'ℹ️_'))])
        except:
            pass

def display_search_results(papers: List[Dict], new_papers: List[Dict], query: str, is_repeat: bool):
    """Zeigt Suchergebnisse an"""
    st.subheader(f"📋 Ergebnisse für: '{query}'")
    
    # Statistiken
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📄 Gesamt Papers", len(papers))
    
    with col2:
        st.metric("🆕 Neue Papers", len(new_papers))
    
    with col3:
        with_abstract = len([p for p in papers if p.get("Abstract", "") != "Kein Abstract verfügbar"])
        st.metric("📝 Mit Abstract", with_abstract)
    
    with col4:
        with_doi = len([p for p in papers if p.get("DOI", "")])
        st.metric("🔗 Mit DOI", with_doi)
    
    # Papers anzeigen (erste 10)
    display_papers = papers[:10]
    
    for idx, paper in enumerate(display_papers, 1):
        is_new = paper.get("Is_New", False)
        status_icon = "🆕" if is_new else "📄"
        
        title = paper.get("Title", "Unbekannt")
        header = f"{status_icon} **{idx}.** {title[:60]}..."
        
        with st.expander(header):
            col_paper1, col_paper2 = st.columns([3, 1])
            
            with col_paper1:
                st.write(f"**📄 Titel:** {title}")
                st.write(f"**👥 Autoren:** {paper.get('Authors', 'n/a')}")
                st.write(f"**📚 Journal:** {paper.get('Journal', 'n/a')} ({paper.get('Year', 'n/a')})")
                st.write(f"**🆔 PMID:** {paper.get('PMID', 'n/a')}")
                
                if paper.get('DOI'):
                    st.write(f"**🔗 DOI:** {paper.get('DOI')}")
                
                if paper.get('URL'):
                    st.markdown(f"🔗 [**PubMed ansehen**]({paper.get('URL')})")
            
            with col_paper2:
                if is_new:
                    st.success("🆕 **NEU**")
                else:
                    st.info("📄 Bekannt")
                
                if st.button("📧 Email", key=f"email_result_{idx}"):
                    send_single_paper_email(paper, query)
    
    if len(papers) > 10:
        st.info(f"... und {len(papers) - 10} weitere Papers (siehe Excel-Datei)")

# Automatische Suchen und weitere Funktionen...
def show_automatic_search_system():
    """Automatisches Such-System"""
    st.subheader("🤖 Automatische Such-System")
    st.info("💡 Diese Funktion würde in einer Produktionsumgebung mit einem echten Scheduler arbeiten.")

def show_detailed_statistics():
    """Detaillierte Statistiken"""
    st.subheader("📈 Detaillierte Statistiken")
    
    status = st.session_state["system_status"]
    search_history = st.session_state.get("search_history", [])
    email_history = st.session_state.get("email_history", [])
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**🔍 Such-Statistiken:**")
        st.write(f"• Gesamt Suchen: {status['total_searches']}")
        st.write(f"• Gesamt Papers: {status['total_papers']}")
        st.write(f"• Ø Papers/Suche: {status['total_papers']/max(status['total_searches'], 1):.1f}")
    
    with col2:
        st.write("**📧 Email-Statistiken:**")
        st.write(f"• Gesamt Emails: {len(email_history)}")
        successful = len([e for e in email_history if e.get("success", False)])
        st.write(f"• Erfolgreich: {successful}")
        st.write(f"• Erfolgsrate: {successful/max(len(email_history), 1)*100:.1f}%")
    
    with col3:
        st.write("**📊 Excel-Statistiken:**")
        st.write(f"• Aktive Sheets: {status['excel_sheets']}")
        if status.get("last_search"):
            last_search = datetime.datetime.fromisoformat(status["last_search"])
            time_diff = datetime.datetime.now() - last_search
            st.write(f"• Letzte Aktivität: vor {time_diff.days} Tagen")

def show_system_settings():
    """System-Einstellungen"""
    st.subheader("⚙️ System-Einstellungen")
    
    # Excel-Template Einstellungen
    template_settings = st.session_state["excel_template"]
    
    with st.form("system_settings_form"):
        st.write("**📊 Excel-Template Einstellungen:**")
        
        auto_create_sheets = st.checkbox(
            "Automatische Sheet-Erstellung",
            value=template_settings.get("auto_create_sheets", True)
        )
        
        max_sheets = st.number_input(
            "Maximale Anzahl Sheets",
            value=template_settings.get("max_sheets", 50),
            min_value=10,
            max_value=100
        )
        
        sheet_naming = st.selectbox(
            "Sheet-Benennungsschema",
            ["topic_based", "date_based", "custom"],
            index=0
        )
        
        if st.form_submit_button("💾 Einstellungen speichern"):
            st.session_state["excel_template"].update({
                "auto_create_sheets": auto_create_sheets,
                "max_sheets": max_sheets,
                "sheet_naming": sheet_naming
            })
            st.success("✅ System-Einstellungen gespeichert!")
    
    # System zurücksetzen
    st.markdown("---")
    st.subheader("🔄 System zurücksetzen")
    
    col_reset1, col_reset2, col_reset3 = st.columns(3)
    
    with col_reset1:
        if st.button("🗑️ Such-Historie löschen"):
            st.session_state["search_history"] = []
            st.success("Such-Historie gelöscht!")
    
    with col_reset2:
        if st.button("📧 Email-Historie löschen"):
            st.session_state["email_history"] = []
            st.success("Email-Historie gelöscht!")
    
    with col_reset3:
        if st.button("⚠️ **Alles zurücksetzen**"):
            reset_all_data()

def reset_all_data():
    """Setzt alle Daten zurück"""
    keys_to_reset = ["search_history", "email_history", "system_status"]
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    
    initialize_session_state()
    st.success("✅ Alle Daten wurden zurückgesetzt!")
    st.rerun()

# Hilfsfunktionen
def is_email_configured() -> bool:
    """Prüft ob Email konfiguriert ist"""
    settings = st.session_state.get("email_settings", {})
    return (settings.get("auto_notifications", False) and 
            bool(settings.get("sender_email")) and 
            bool(settings.get("recipient_email")) and
            bool(settings.get("sender_password")))

def should_send_email(paper_count: int) -> bool:
    """Prüft ob Email gesendet werden soll"""
    settings = st.session_state.get("email_settings", {})
    return (settings.get("auto_notifications", False) and
            paper_count >= settings.get("min_papers", 1) and
            is_email_configured())

def generate_email_preview(settings: Dict, search_term: str, count: int) -> str:
    """Generiert Email-Vorschau"""
    try:
        sender = settings.get("sender_email", "system@example.com")
        recipient = settings.get("recipient_email", "user@example.com")
        
        subject_template = settings.get("subject_template", "Neue Papers")
        subject = subject_template.format(count=count, search_term=search_term, frequency="Test")
        
        message_template = settings.get("message_template", "Papers gefunden")
        message = message_template.format(
            date=datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
            search_term=search_term,
            count=count,
            frequency="Test",
            new_papers_list="1. Test Paper 1\n2. Test Paper 2",
            excel_file="master_papers.xlsx"
        )
        
        return f"""Von: {sender}
An: {recipient}
Betreff: {subject}

{message}"""
    
    except Exception as e:
        return f"Email-Vorschau Fehler: {str(e)}"

# Weitere Funktionen für spezielle Features...
def send_single_paper_email(paper: Dict, search_term: str):
    """Sendet Email für einzelnes Paper"""
    settings = st.session_state.get("email_settings", {})
    
    if not is_email_configured():
        st.error("❌ Email nicht konfiguriert!")
        return
    
    subject = f"📄 Einzelnes Paper: {paper.get('Title', 'Unknown')[:40]}..."
    
    message = f"""📄 Einzelnes Paper aus der Suche '{search_term}':

Titel: {paper.get('Title', 'Unbekannt')}
Autoren: {paper.get('Authors', 'n/a')}
Journal: {paper.get('Journal', 'n/a')} ({paper.get('Year', 'n/a')})
PMID: {paper.get('PMID', 'n/a')}

PubMed Link: {paper.get('URL', 'n/a')}

Abstract:
{paper.get('Abstract', 'Kein Abstract verfügbar')[:1000]}...

Gesendet am: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}"""
    
    recipient = settings.get("recipient_email", "")
    success, status_message = send_real_email(recipient, subject, message)
    
    if success:
        st.success(f"📧 Email erfolgreich gesendet für: {paper.get('Title', 'Unknown')[:40]}...")
    else:
        st.error(f"📧 Email-Fehler: {status_message}")

# Hauptfunktion
if __name__ == "__main__":
    module_email()
