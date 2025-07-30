# modules/email_module.py - ERWEITERTE VERSION MIT PAPER-SUCHE
import streamlit as st
import datetime
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
import re
import io
import openpyxl
import os
from typing import List, Dict, Any

def module_email():
    """ERWEITERTE FUNKTION - Email-Modul mit integrierter Paper-Suche"""
    st.subheader("📧 Email-System mit integrierter Paper-Suche")
    st.success("✅ Erweitertes Email- und Paper-Suche-Modul geladen!")
    
    # Sichere Session State Initialisierung
    initialize_session_state()
    
    # Erweiterte Tabs mit Paper-Suche
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📧 Email-Konfiguration", 
        "🔍 Paper-Suche", 
        "📊 Excel-Management",
        "📋 Email-Verlauf", 
        "🧪 Tests"
    ])
    
    with tab1:
        show_email_config()
    
    with tab2:
        show_paper_search()
    
    with tab3:
        show_excel_management()
    
    with tab4:
        show_email_history()
    
    with tab5:
        show_email_tests()

def initialize_session_state():
    """Erweiterte Session State Initialisierung"""
    if "email_settings" not in st.session_state:
        st.session_state["email_settings"] = {
            "sender_email": "",
            "recipient_email": "",
            "auto_notifications": False,
            "min_papers": 5,
            "subject_template": "🔬 {count} neue Papers für '{search_term}'",
            "message_template": """🔍 Neue wissenschaftliche Papers gefunden!

📅 Datum: {date}
🔍 Suchbegriff: '{search_term}'
📊 Anzahl Papers: {count}

Die vollständigen Ergebnisse sind im Paper-Suche System verfügbar.

Mit freundlichen Grüßen,
Ihr automatisches Paper-Suche System"""
        }
    
    if "email_history" not in st.session_state:
        st.session_state["email_history"] = []
    
    if "paper_search_results" not in st.session_state:
        st.session_state["paper_search_results"] = {}
    
    if "paper_search_history" not in st.session_state:
        st.session_state["paper_search_history"] = []
    
    # Erstelle Ordner für Excel-Dateien
    if not os.path.exists("saved_searches"):
        os.makedirs("saved_searches")

# EMAIL-KONFIGURATION (wie vorher)
def show_email_config():
    """Email-Konfiguration Interface"""
    st.write("**📧 Email-Einstellungen konfigurieren:**")
    
    settings = st.session_state.get("email_settings", {})
    
    with st.form("email_config_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            sender_email = st.text_input(
                "Absender Email", 
                value=settings.get("sender_email", ""),
                placeholder="absender@example.com"
            )
            
            auto_notifications = st.checkbox(
                "Automatische Benachrichtigungen aktivieren", 
                value=settings.get("auto_notifications", False)
            )
        
        with col2:
            recipient_email = st.text_input(
                "Empfänger Email", 
                value=settings.get("recipient_email", ""),
                placeholder="empfaenger@example.com"
            )
            
            min_papers = st.number_input(
                "Min. Papers für Benachrichtigung", 
                value=settings.get("min_papers", 5),
                min_value=1,
                max_value=100
            )
        
        subject_template = st.text_input(
            "Email-Betreff Vorlage",
            value=settings.get("subject_template", "🔬 {count} neue Papers für '{search_term}'"),
            help="Verwenden Sie {count} und {search_term} als Platzhalter"
        )
        
        message_template = st.text_area(
            "Email-Nachricht Vorlage",
            value=settings.get("message_template", """🔍 Neue wissenschaftliche Papers gefunden!

📅 Datum: {date}
🔍 Suchbegriff: '{search_term}'
📊 Anzahl Papers: {count}

Die vollständigen Ergebnisse sind im Paper-Suche System verfügbar.

Mit freundlichen Grüßen,
Ihr automatisches Paper-Suche System"""),
            height=200,
            help="Verwenden Sie {date}, {search_term}, {count} als Platzhalter"
        )
        
        if st.form_submit_button("💾 Email-Einstellungen speichern"):
            st.session_state["email_settings"] = {
                "sender_email": sender_email,
                "recipient_email": recipient_email,
                "auto_notifications": auto_notifications,
                "min_papers": min_papers,
                "subject_template": subject_template,
                "message_template": message_template
            }
            
            st.success("✅ Email-Einstellungen erfolgreich gespeichert!")
            
            if sender_email and recipient_email:
                preview = generate_email_preview(
                    st.session_state["email_settings"], 
                    "diabetes genetics", 
                    7
                )
                st.info("📧 **Email-Vorschau:**")
                st.code(preview, language="text")

# NEUE PAPER-SUCHE FUNKTIONALITÄT
def show_paper_search():
    """Integrierte Paper-Suche mit Email-Benachrichtigung"""
    st.write("**🔍 Paper-Suche mit automatischer Email-Benachrichtigung**")
    
    # Email-Status anzeigen
    settings = st.session_state.get("email_settings", {})
    email_enabled = (settings.get("auto_notifications", False) and 
                    bool(settings.get("sender_email")) and 
                    bool(settings.get("recipient_email")))
    
    if email_enabled:
        st.success("✅ **Email-Benachrichtigungen sind aktiviert**")
    else:
        st.warning("⚠️ **Email-Benachrichtigungen sind deaktiviert** - Konfigurieren Sie sie im Tab 'Email-Konfiguration'")
    
    # Such-Interface
    with st.form("paper_search_form"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_query = st.text_input(
                "**PubMed Suchbegriff:**",
                placeholder="z.B. 'diabetes genetics', 'BRCA1 mutations', 'COVID-19 treatment'",
                help="Führt automatisch PubMed-Suche durch und sendet Email-Benachrichtigung"
            )
        
        with col2:
            max_results = st.number_input(
                "Max. Ergebnisse", 
                min_value=10, 
                max_value=200, 
                value=50
            )
        
        # Erweiterte Optionen
        with st.expander("🔧 Erweiterte Suchoptionen"):
            col_adv1, col_adv2 = st.columns(2)
            
            with col_adv1:
                date_filter = st.selectbox(
                    "Zeitraum:",
                    ["Alle", "Letztes Jahr", "Letzte 5 Jahre", "Letzte 10 Jahre"],
                    index=0
                )
            
            with col_adv2:
                send_email_override = st.checkbox(
                    "Email senden (auch wenn deaktiviert)", 
                    value=False
                )
        
        search_button = st.form_submit_button("🔍 **PAPER-SUCHE STARTEN**", type="primary")
    
    # Such-Verlauf anzeigen
    if st.session_state["paper_search_history"]:
        with st.expander("📊 Such-Verlauf anzeigen"):
            for search in st.session_state["paper_search_history"][-5:]:
                search_date = search["timestamp"][:19]
                st.write(f"• **{search['query']}**: {search['results_count']} Papers ({search_date})")
    
    # Suche ausführen
    if search_button and search_query:
        execute_paper_search(search_query, max_results, date_filter, send_email_override)

def execute_paper_search(query: str, max_results: int, date_filter: str, force_email: bool):
    """Führt PubMed-Suche durch mit Email-Integration"""
    st.markdown("---")
    st.subheader(f"🔍 **Suche nach:** '{query}'")
    
    # Build query mit Filtern
    advanced_query = build_search_query(query, date_filter)
    
    with st.spinner("🔍 Durchsuche PubMed-Datenbank..."):
        # 1. Prüfe ob wiederholte Suche
        previous_papers = load_previous_search_results(query)
        is_repeat_search = len(previous_papers) > 0
        
        if is_repeat_search:
            st.info(f"🔄 **Wiederholte Suche erkannt!** Vergleiche mit {len(previous_papers)} bekannten Papers...")
        
        # 2. Führe aktuelle Suche durch
        current_papers = perform_pubmed_search(advanced_query, max_results)
        
        if not current_papers:
            st.error(f"❌ **Keine Papers für '{query}' gefunden!**")
            return
        
        # 3. Vergleiche mit vorherigen Ergebnissen
        if is_repeat_search:
            new_papers = find_new_papers(current_papers, previous_papers)
            
            if new_papers:
                st.success(f"🆕 **{len(new_papers)} NEUE Papers gefunden** (von {len(current_papers)} gesamt)")
                st.balloons()
                
                # Email für neue Papers
                send_paper_notification(query, len(new_papers), new_papers, is_new_papers=True, force_send=force_email)
                
                # Excel aktualisieren
                update_excel_file(query, current_papers, new_papers)
                
                # Zeige nur neue Papers hervorgehoben
                display_papers_with_highlights(current_papers, new_papers, query)
            else:
                st.info(f"ℹ️ **Keine neuen Papers** - Alle {len(current_papers)} Papers bereits bekannt")
                display_papers_with_highlights(current_papers, [], query)
        else:
            st.success(f"🎉 **Erste Suche:** {len(current_papers)} Papers gefunden!")
            st.balloons()
            
            # Email für alle Papers
            send_paper_notification(query, len(current_papers), current_papers, is_new_papers=False, force_send=force_email)
            
            # Neue Excel-Datei erstellen
            create_excel_file(query, current_papers)
            
            # Zeige alle Papers
            display_papers_with_highlights(current_papers, current_papers, query)
        
        # Speichere Suchergebnisse
        save_search_results(query, current_papers, is_repeat_search)

def perform_pubmed_search(query: str, max_results: int) -> List[Dict[str, Any]]:
    """Führt PubMed-Suche durch"""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    # 1. esearch - hole PMIDs
    search_url = f"{base_url}esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": max_results,
        "email": "research@example.com",
        "tool": "IntegratedPaperSearch"
    }
    
    try:
        response = requests.get(search_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        pmids = data.get("esearchresult", {}).get("idlist", [])
        total_count = int(data.get("esearchresult", {}).get("count", 0))
        
        st.write(f"📊 **PubMed Datenbank:** {total_count:,} Papers verfügbar, {len(pmids)} werden abgerufen")
        
        if not pmids:
            return []
        
        # 2. efetch - hole Details
        return fetch_paper_details(pmids)
        
    except Exception as e:
        st.error(f"❌ **PubMed Suchfehler:** {str(e)}")
        return []

def fetch_paper_details(pmids: List[str]) -> List[Dict[str, Any]]:
    """Holt vollständige Paper-Details"""
    if not pmids:
        return []
    
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    fetch_url = f"{base_url}efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "email": "research@example.com",
        "tool": "IntegratedPaperSearch"
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
            
            paper_data = parse_article(article)
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
        st.error(f"❌ **Fehler beim Abrufen der Paper-Details:** {str(e)}")
        return []

def parse_article(article) -> Dict[str, Any]:
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
            "Is_New": True
        }
        
    except Exception as e:
        return None

def build_search_query(base_query: str, date_filter: str) -> str:
    """Baut erweiterte PubMed-Suche auf"""
    query_parts = [base_query]
    
    if date_filter != "Alle":
        current_year = datetime.datetime.now().year
        if date_filter == "Letztes Jahr":
            query_parts.append(f"AND {current_year-1}:{current_year}[dp]")
        elif date_filter == "Letzte 5 Jahre":
            query_parts.append(f"AND {current_year-5}:{current_year}[dp]")
        elif date_filter == "Letzte 10 Jahre":
            query_parts.append(f"AND {current_year-10}:{current_year}[dp]")
    
    return " ".join(query_parts)

def load_previous_search_results(query: str) -> List[Dict[str, Any]]:
    """Lädt vorherige Suchergebnisse"""
    excel_filename = get_excel_filename(query)
    excel_path = os.path.join("saved_searches", excel_filename)
    
    if not os.path.exists(excel_path):
        return []
    
    try:
        df = pd.read_excel(excel_path)
        previous_papers = []
        
        for _, row in df.iterrows():
            paper = {
                "PMID": str(row.get("PMID", "")),
                "Title": str(row.get("Titel", "")),
                "Authors": str(row.get("Autoren", "")),
                "Journal": str(row.get("Journal", "")),
                "Year": str(row.get("Jahr", "")),
                "DOI": str(row.get("DOI", "")),
                "URL": str(row.get("URL", ""))
            }
            previous_papers.append(paper)
        
        return previous_papers
        
    except Exception as e:
        st.warning(f"⚠️ Fehler beim Laden der Excel-Datei: {str(e)}")
        return []

def find_new_papers(current_papers: List[Dict], previous_papers: List[Dict]) -> List[Dict]:
    """Findet neue Papers durch PMID-Vergleich"""
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

def get_excel_filename(query: str) -> str:
    """Generiert Excel-Dateinamen"""
    clean_query = re.sub(r'[^\w\s-]', '', query).strip()
    clean_query = re.sub(r'[-\s]+', '_', clean_query)
    return f"papers_{clean_query}.xlsx"

def create_excel_file(query: str, papers: List[Dict]):
    """Erstellt neue Excel-Datei"""
    excel_filename = get_excel_filename(query)
    excel_path = os.path.join("saved_searches", excel_filename)
    
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
        
        wb.save(excel_path)
        
        st.success(f"✅ **Excel-Datei erstellt:** {excel_filename}")
        
        # Download-Button
        with open(excel_path, 'rb') as f:
            st.download_button(
                label="📥 **Excel-Datei herunterladen**",
                data=f.read(),
                file_name=excel_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
    except Exception as e:
        st.error(f"❌ **Fehler beim Erstellen der Excel-Datei:** {str(e)}")

def update_excel_file(query: str, all_papers: List[Dict], new_papers: List[Dict]):
    """Aktualisiert Excel-Datei mit neuen Papers"""
    excel_filename = get_excel_filename(query)
    excel_path = os.path.join("saved_searches", excel_filename)
    
    try:
        wb = openpyxl.load_workbook(excel_path)
        ws = wb.active
        
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
                current_time,
                current_time
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
                key="updated_excel"
            )
        
    except Exception as e:
        st.error(f"❌ **Fehler beim Aktualisieren der Excel-Datei:** {str(e)}")

def send_paper_notification(query: str, paper_count: int, papers: List[Dict], is_new_papers: bool = False, force_send: bool = False):
    """Sendet Email-Benachrichtigung"""
    settings = st.session_state.get("email_settings", {})
    
    # Prüfe ob Email gesendet werden soll
    should_send = (force_send or 
                  (settings.get("auto_notifications", False) and 
                   paper_count >= settings.get("min_papers", 5)))
    
    if not should_send:
        return
    
    # Email-Typ bestimmen
    email_type = "Neue Papers" if is_new_papers else "Paper-Suche"
    subject_template = settings.get("subject_template", "Papers für '{search_term}'")
    
    try:
        subject = subject_template.format(count=paper_count, search_term=query)
    except:
        subject = f"{email_type}: {paper_count} Papers für '{query}'"
    
    # Email-Nachricht erstellen
    message_template = settings.get("message_template", "Papers gefunden")
    
    try:
        message = message_template.format(
            date=datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
            search_term=query,
            count=paper_count
        )
    except:
        message = f"{email_type}: {paper_count} Papers für '{query}' gefunden"
    
    # Top Papers zur Nachricht hinzufügen
    if papers:
        message += "\n\n📋 Top Papers:\n"
        for i, paper in enumerate(papers[:5], 1):
            title = paper.get('Title', 'Unbekannt')[:60]
            message += f"\n{i}. {title}..."
            message += f"\n   PMID: {paper.get('PMID', 'n/a')}"
        
        if len(papers) > 5:
            message += f"\n\n... und {len(papers) - 5} weitere Papers"
    
    # Email zur Historie hinzufügen
    email_notification = {
        "timestamp": datetime.datetime.now().isoformat(),
        "date": datetime.datetime.now().date().isoformat(),
        "search_term": query,
        "paper_count": paper_count,
        "recipient": settings.get("recipient_email", ""),
        "status": "Gesendet (simuliert)",
        "type": email_type,
        "subject": subject,
        "message": message
    }
    
    if "email_history" not in st.session_state:
        st.session_state["email_history"] = []
    
    st.session_state["email_history"].append(email_notification)
    
    st.info(f"📧 **Email-Benachrichtigung erstellt:** {email_type} für '{query}'")
    
    # Email-Vorschau
    with st.expander("📧 Email-Vorschau anzeigen"):
        preview = f"""Von: {settings.get('sender_email', 'system@example.com')}
An: {settings.get('recipient_email', 'user@example.com')}
Betreff: {subject}

{message}"""
        st.code(preview, language="text")

def display_papers_with_highlights(all_papers: List[Dict], new_papers: List[Dict], query: str):
    """Zeigt Papers mit Hervorhebung neuer Papers"""
    st.subheader(f"📋 **Papers für '{query}' ({len(all_papers)} gesamt, {len(new_papers)} neu)**")
    
    # Statistiken
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📄 Gesamt Papers", len(all_papers))
    
    with col2:
        st.metric("🆕 Neue Papers", len(new_papers))
    
    with col3:
        with_abstract = len([p for p in all_papers if p.get("Abstract", "") != "No abstract available"])
        st.metric("📝 Mit Abstract", with_abstract)
    
    with col4:
        current_year = datetime.datetime.now().year
        recent = len([p for p in all_papers if p.get("Year", "0").isdigit() and int(p.get("Year", "0")) >= current_year - 5])
        st.metric("🆕 Letzte 5 Jahre", recent)
    
    # Papers anzeigen (erste 10)
    display_papers = all_papers[:10]
    
    for idx, paper in enumerate(display_papers):
        is_new = paper.get("Is_New", False)
        status_icon = "🆕" if is_new else "📄"
        
        # Titel mit Hervorhebung
        header_style = "**🆕 NEU:** " if is_new else ""
        header = f"{status_icon} {header_style}**{idx + 1}.** {paper.get('Title', 'Unbekannt')[:70]}..."
        
        with st.expander(header):
            col_paper1, col_paper2 = st.columns([3, 1])
            
            with col_paper1:
                st.write(f"**📄 Titel:** {paper.get('Title', 'n/a')}")
                st.write(f"**👥 Autoren:** {paper.get('Authors', 'n/a')}")
                st.write(f"**📚 Journal:** {paper.get('Journal', 'n/a')} ({paper.get('Year', 'n/a')})")
                st.write(f"**🆔 PMID:** {paper.get('PMID', 'n/a')}")
                
                if paper.get('URL'):
                    st.markdown(f"🔗 [**PubMed ansehen**]({paper.get('URL')})")
            
            with col_paper2:
                if is_new:
                    st.success("🆕 **NEUES PAPER**")
                else:
                    st.info("📄 Bereits bekannt")
                
                if st.button("📧 **Email senden**", key=f"email_single_{paper.get('PMID', idx)}"):
                    send_single_paper_email(paper, query)

def send_single_paper_email(paper: Dict, search_term: str):
    """Sendet Email für einzelnes Paper"""
    settings = st.session_state.get("email_settings", {})
    
    subject = f"📄 Einzelnes Paper: {paper.get('Title', 'Unknown')[:40]}..."
    
    message = f"""📄 Einzelnes Paper aus der Suche '{search_term}':

Titel: {paper.get('Title', 'Unbekannt')}
Autoren: {paper.get('Authors', 'n/a')}
Journal: {paper.get('Journal', 'n/a')} ({paper.get('Year', 'n/a')})
PMID: {paper.get('PMID', 'n/a')}

PubMed Link: {paper.get('URL', 'n/a')}

Gesendet am: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}"""
    
    # Zur Historie hinzufügen
    email_notification = {
        "timestamp": datetime.datetime.now().isoformat(),
        "date": datetime.datetime.now().date().isoformat(),
        "search_term": f"Einzelpaper: {search_term}",
        "paper_count": 1,
        "recipient": settings.get("recipient_email", ""),
        "status": "Einzelpaper gesendet (simuliert)",
        "type": "Einzelpaper"
    }
    
    st.session_state["email_history"].append(email_notification)
    st.success(f"📧 **Email gesendet** für: {paper.get('Title', 'Unknown')[:40]}...")

def save_search_results(query: str, papers: List[Dict], is_repeat: bool):
    """Speichert Suchergebnisse"""
    st.session_state["paper_search_results"][query] = {
        "papers": papers,
        "timestamp": datetime.datetime.now().isoformat(),
        "is_repeat_search": is_repeat
    }
    
    st.session_state["paper_search_history"].append({
        "query": query,
        "timestamp": datetime.datetime.now().isoformat(),
        "results_count": len(papers)
    })

# EXCEL-MANAGEMENT
def show_excel_management():
    """Excel-Dateien verwalten"""
    st.write("**📊 Excel-Dateien verwalten**")
    
    excel_dir = "saved_searches"
    if not os.path.exists(excel_dir):
        st.info("📁 Noch keine Excel-Dateien gespeichert")
        return
    
    excel_files = [f for f in os.listdir(excel_dir) if f.endswith('.xlsx')]
    
    if not excel_files:
        st.info("📁 Noch keine Excel-Dateien gespeichert")
        return
    
    st.write(f"**📁 {len(excel_files)} Excel-Dateien gefunden:**")
    
    for file in excel_files:
        file_path = os.path.join(excel_dir, file)
        file_size = os.path.getsize(file_path)
        file_date = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        
        with st.expander(f"📄 {file} ({file_size:,} bytes, {file_date.strftime('%d.%m.%Y %H:%M')})"):
            col_file1, col_file2, col_file3 = st.columns(3)
            
            with col_file1:
                with open(file_path, 'rb') as f:
                    st.download_button(
                        label="📥 Herunterladen",
                        data=f.read(),
                        file_name=file,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"download_{file}"
                    )
            
            with col_file2:
                if st.button("👁️ Vorschau", key=f"preview_{file}"):
                    show_excel_preview(file_path)
            
            with col_file3:
                if st.button("🗑️ Löschen", key=f"delete_{file}"):
                    os.remove(file_path)
                    st.success(f"Datei {file} gelöscht!")
                    st.rerun()

def show_excel_preview(file_path: str):
    """Zeigt Excel-Vorschau"""
    try:
        df = pd.read_excel(file_path, nrows=10)
        st.write("**📊 Excel-Vorschau (erste 10 Zeilen):**")
        st.dataframe(df)
        st.write(f"**Gesamt Zeilen:** {len(pd.read_excel(file_path))}")
    except Exception as e:
        st.error(f"Fehler beim Laden der Excel-Datei: {str(e)}")

# EMAIL-VERLAUF UND TESTS (wie vorher, aber erweitert)
def show_email_history():
    """Email-Verlauf mit Such-Integration"""
    st.write("**📊 Email-Benachrichtigungs-Verlauf:**")
    
    history = st.session_state.get("email_history", [])
    
    if history:
        # Erweiterte Statistiken
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📧 Gesamt Emails", len(history))
        
        with col2:
            paper_emails = len([h for h in history if h.get("type", "") in ["Paper-Suche", "Neue Papers"]])
            st.metric("🔍 Paper-Emails", paper_emails)
        
        with col3:
            new_paper_emails = len([h for h in history if h.get("type", "") == "Neue Papers"])
            st.metric("🆕 Neue-Paper-Emails", new_paper_emails)
        
        with col4:
            total_papers = sum(h.get("paper_count", 0) for h in history)
            st.metric("📄 Gesamt Papers", total_papers)
        
        # Email-Liste mit erweiterten Details
        st.write("**📋 Email-Verlauf:**")
        
        for i, email in enumerate(reversed(history[-15:]), 1):
            email_type = email.get("type", "Standard")
            search_term = email.get("search_term", "Unbekannt")
            paper_count = email.get("paper_count", 0)
            timestamp = email.get("timestamp", "Unbekannt")[:19]
            
            # Icon basierend auf Typ
            type_icon = "🆕" if email_type == "Neue Papers" else "🔍" if email_type == "Paper-Suche" else "📧"
            
            with st.expander(f"{type_icon} {i}. {email_type}: {search_term} - {paper_count} Papers ({timestamp})"):
                col_detail1, col_detail2 = st.columns(2)
                
                with col_detail1:
                    st.write(f"**Typ:** {email_type}")
                    st.write(f"**Suchbegriff:** {search_term}")
                    st.write(f"**Papers:** {paper_count}")
                
                with col_detail2:
                    st.write(f"**Empfänger:** {email.get('recipient', 'N/A')}")
                    st.write(f"**Status:** {email.get('status', 'N/A')}")
                    st.write(f"**Zeit:** {timestamp}")
                
                # Vollständige Email anzeigen
                if st.button("📧 Vollständige Email anzeigen", key=f"show_full_{i}"):
                    subject = email.get("subject", "Kein Betreff")
                    message = email.get("message", "Keine Nachricht")
                    
                    full_email = f"""Betreff: {subject}

{message}"""
                    st.code(full_email, language="text")
        
        # Verlauf löschen
        if st.button("🗑️ Email-Verlauf löschen"):
            st.session_state["email_history"] = []
            st.success("Email-Verlauf gelöscht!")
            st.rerun()
    
    else:
        st.info("📭 Noch keine Email-Benachrichtigungen versendet.")

def show_email_tests():
    """Erweiterte Email-Tests"""
    st.write("**🧪 Email-System testen:**")
    
    settings = st.session_state.get("email_settings", {})
    
    # Konfigurationsstatus
    sender_ok = bool(settings.get("sender_email"))
    recipient_ok = bool(settings.get("recipient_email"))
    auto_ok = settings.get("auto_notifications", False)
    
    st.write("**📋 System-Status:**")
    
    col_status1, col_status2 = st.columns(2)
    
    with col_status1:
        st.write(f"{'✅' if sender_ok else '❌'} **Absender Email:** {'Konfiguriert' if sender_ok else 'Fehlt'}")
        st.write(f"{'✅' if recipient_ok else '❌'} **Empfänger Email:** {'Konfiguriert' if recipient_ok else 'Fehlt'}")
    
    with col_status2:
        st.write(f"{'✅' if auto_ok else '❌'} **Auto-Benachrichtigungen:** {'Aktiviert' if auto_ok else 'Deaktiviert'}")
        st.write(f"**Min. Papers:** {settings.get('min_papers', 5)}")
    
    # Erweiterte Test-Funktionen
    st.write("**🧪 Test-Aktionen:**")
    
    col_test1, col_test2, col_test3 = st.columns(3)
    
    with col_test1:
        if st.button("📧 Test-Email"):
            if sender_ok and recipient_ok:
                send_test_email()
            else:
                st.error("❌ Email-Konfiguration unvollständig!")
    
    with col_test2:
        if st.button("🔍 Test Paper-Email"):
            send_test_paper_email()
    
    with col_test3:
        if st.button("📊 System-Statistiken"):
            show_system_statistics()

def send_test_email():
    """Sendet Standard-Test-Email"""
    settings = st.session_state.get("email_settings", {})
    
    test_email = {
        "timestamp": datetime.datetime.now().isoformat(),
        "date": datetime.datetime.now().date().isoformat(),
        "search_term": "System-Test",
        "paper_count": 3,
        "recipient": settings.get("recipient_email", ""),
        "status": "Test erfolgreich (simuliert)",
        "type": "Test"
    }
    
    st.session_state["email_history"].append(test_email)
    st.success("✅ Test-Email erfolgreich erstellt!")
    
    preview = generate_email_preview(settings, "System-Test", 3)
    with st.expander("📧 Test-Email Vorschau"):
        st.code(preview, language="text")

def send_test_paper_email():
    """Sendet Test-Email für Paper-Suche"""
    settings = st.session_state.get("email_settings", {})
    
    test_papers = [
        {"Title": "Test Paper 1", "PMID": "12345", "Authors": "Smith, J. et al."},
        {"Title": "Test Paper 2", "PMID": "67890", "Authors": "Jones, A. et al."},
        {"Title": "Test Paper 3", "PMID": "13579", "Authors": "Brown, K. et al."}
    ]
    
    send_paper_notification("Test-Suchbegriff", 3, test_papers, is_new_papers=True, force_send=True)
    st.success("✅ Test-Paper-Email erstellt!")

def show_system_statistics():
    """Zeigt erweiterte System-Statistiken"""
    st.write("**📊 Erweiterte System-Statistiken:**")
    
    # Email-Statistiken
    history = st.session_state.get("email_history", [])
    search_history = st.session_state.get("paper_search_history", [])
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    
    with col_stat1:
        st.write("**📧 Email-System:**")
        st.write(f"• Gesamt Emails: {len(history)}")
        
        if history:
            paper_emails = len([h for h in history if "paper" in h.get("type", "").lower()])
            st.write(f"• Paper-Emails: {paper_emails}")
            
            total_papers = sum(h.get("paper_count", 0) for h in history)
            st.write(f"• Gesamt Papers: {total_papers}")
    
    with col_stat2:
        st.write("**🔍 Paper-Suche:**")
        st.write(f"• Gesamt Suchen: {len(search_history)}")
        
        if search_history:
            total_results = sum(s.get("results_count", 0) for s in search_history)
            st.write(f"• Gesamt Ergebnisse: {total_results}")
            
            avg_results = total_results / len(search_history) if search_history else 0
            st.write(f"• Ø Ergebnisse/Suche: {avg_results:.1f}")
    
    with col_stat3:
        st.write("**📁 Excel-System:**")
        excel_files = []
        if os.path.exists("saved_searches"):
            excel_files = [f for f in os.listdir("saved_searches") if f.endswith('.xlsx')]
        
        st.write(f"• Excel-Dateien: {len(excel_files)}")
        
        if excel_files:
            total_size = sum(os.path.getsize(os.path.join("saved_searches", f)) for f in excel_files)
            st.write(f"• Gesamt Größe: {total_size:,} bytes")

# HILFSFUNKTIONEN (wie vorher)
def generate_email_preview(settings, search_term, count):
    """Generiert Email-Vorschau"""
    try:
        sender = settings.get("sender_email", "system@example.com")
        recipient = settings.get("recipient_email", "user@example.com")
        
        subject_template = settings.get("subject_template", "Neue Papers für '{search_term}'")
        subject = subject_template.format(count=count, search_term=search_term)
        
        message_template = settings.get("message_template", "Es wurden {count} neue Papers gefunden.")
        message = message_template.format(
            date=datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
            search_term=search_term,
            count=count
        )
        
        return f"""Von: {sender}
An: {recipient}
Betreff: {subject}

{message}"""
    
    except Exception as e:
        return f"Email-Vorschau Fehler: {str(e)}"

# Integration-Funktionen für andere Module (erweitert)
def trigger_email_notification(search_term, paper_count):
    """Erweiterte Integration für andere Module"""
    try:
        settings = st.session_state.get("email_settings", {})
        
        if not settings.get("auto_notifications", False):
            return False
        
        min_papers = settings.get("min_papers", 5)
        if paper_count < min_papers:
            return False
        
        # Erstelle Email-Benachrichtigung
        email_notification = {
            "timestamp": datetime.datetime.now().isoformat(),
            "date": datetime.datetime.now().date().isoformat(),
            "search_term": search_term,
            "paper_count": paper_count,
            "recipient": settings.get("recipient_email", ""),
            "status": "Automatisch gesendet (simuliert)",
            "type": "Automatisch (von anderem Modul)"
        }
        
        if "email_history" not in st.session_state:
            st.session_state["email_history"] = []
        
        st.session_state["email_history"].append(email_notification)
        return True
    
    except Exception:
        return False

def get_email_settings():
    """Gibt aktuelle Email-Einstellungen zurück"""
    return st.session_state.get("email_settings", {})

def is_email_enabled():
    """Prüft ob Email-System aktiviert und konfiguriert ist"""
    settings = st.session_state.get("email_settings", {})
    return (settings.get("auto_notifications", False) and 
            bool(settings.get("sender_email")) and 
            bool(settings.get("recipient_email")))
