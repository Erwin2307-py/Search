# modules/email_module.py - VOLLSTÄNDIGE VERSION MIT ECHTER EMAIL-FUNKTIONALITÄT
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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import ssl
from typing import List, Dict, Any

def module_email():
    """VOLLSTÄNDIGE FUNKTION - Email-Modul mit echter SMTP-Funktionalität"""
    st.subheader("📧 Email-System mit integrierter Paper-Suche")
    st.success("✅ Vollständiges Email- und Paper-Suche-Modul mit echter SMTP-Funktionalität geladen!")
    
    # Session State initialisieren
    initialize_session_state()
    
    # Erweiterte Tabs
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
    """Vollständige Session State Initialisierung"""
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
Ihr automatisches Paper-Suche System""",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_password": "",
            "use_tls": True
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

def show_email_config():
    """Vollständige Email-Konfiguration mit SMTP"""
    st.write("**📧 Email-Einstellungen konfigurieren:**")
    
    settings = st.session_state.get("email_settings", {})
    
    # Email-Setup Hilfe anzeigen
    show_email_setup_help()
    
    with st.form("email_config_form"):
        st.subheader("📬 Grundeinstellungen")
        col1, col2 = st.columns(2)
        
        with col1:
            sender_email = st.text_input(
                "Absender Email", 
                value=settings.get("sender_email", ""),
                placeholder="absender@gmail.com"
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
        
        # SMTP-Einstellungen
        st.subheader("🔧 SMTP-Server Einstellungen")
        col3, col4 = st.columns(2)
        
        with col3:
            smtp_server = st.text_input(
                "SMTP Server",
                value=settings.get("smtp_server", "smtp.gmail.com"),
                placeholder="smtp.gmail.com"
            )
            
            smtp_port = st.number_input(
                "SMTP Port",
                value=settings.get("smtp_port", 587),
                min_value=1,
                max_value=65535
            )
        
        with col4:
            sender_password = st.text_input(
                "Email Passwort / App-Passwort",
                value=settings.get("sender_password", ""),
                type="password",
                placeholder="Ihr Email-Passwort",
                help="Für Gmail verwenden Sie ein App-spezifisches Passwort"
            )
            
            use_tls = st.checkbox(
                "TLS verwenden (empfohlen)",
                value=settings.get("use_tls", True)
            )
        
        # Email-Vorlagen
        st.subheader("📝 Email-Vorlagen")
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
            height=200
        )
        
        if st.form_submit_button("💾 Email-Einstellungen speichern"):
            st.session_state["email_settings"] = {
                "sender_email": sender_email,
                "recipient_email": recipient_email,
                "auto_notifications": auto_notifications,
                "min_papers": min_papers,
                "subject_template": subject_template,
                "message_template": message_template,
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "sender_password": sender_password,
                "use_tls": use_tls
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

def show_email_setup_help():
    """Zeigt Hilfe für Email-Setup"""
    with st.expander("📖 Email-Setup Hilfe (WICHTIG LESEN!)"):
        st.info("""
        📧 **Email-Setup Anleitung:**
        
        **Für Gmail:**
        1. ✅ Aktivieren Sie 2-Faktor-Authentifizierung in Ihrem Google Account
        2. ✅ Erstellen Sie ein App-spezifisches Passwort:
           - Gehen Sie zu Google Account → Sicherheit → App-Passwörter
           - Wählen Sie "E-Mail" und Ihr Gerät
           - Kopieren Sie das generierte 16-stellige Passwort
        3. ✅ Verwenden Sie: smtp.gmail.com, Port 587, TLS aktiviert
        4. ⚠️ Verwenden Sie NICHT Ihr normales Gmail-Passwort!
        
        **Für Outlook/Hotmail:**
        - SMTP: smtp-mail.outlook.com
        - Port: 587
        - TLS: Aktiviert
        - Passwort: Ihr normales Outlook-Passwort
        
        **Für GMX:**
        - SMTP: mail.gmx.net
        - Port: 587
        - TLS: Aktiviert
        
        **Für Web.de:**
        - SMTP: smtp.web.de
        - Port: 587
        - TLS: Aktiviert
        
        **⚠️ Wichtige Sicherheitshinweise:**
        - Verwenden Sie niemals Ihr Hauptpasswort in Apps
        - App-Passwörter sind sicherer und empfohlen
        - Testen Sie erst mit der Test-Email-Funktion
        """)

def send_real_email(to_email: str, subject: str, message: str, attachment_path: str = None) -> tuple[bool, str]:
    """Sendet echte Email über SMTP"""
    settings = st.session_state.get("email_settings", {})
    
    sender_email = settings.get("sender_email", "")
    sender_password = settings.get("sender_password", "")
    smtp_server = settings.get("smtp_server", "smtp.gmail.com")
    smtp_port = settings.get("smtp_port", 587)
    use_tls = settings.get("use_tls", True)
    
    # Validierung
    if not all([sender_email, sender_password, to_email]):
        return False, "❌ Email-Konfiguration unvollständig (Email/Passwort fehlt)"
    
    try:
        # Email zusammenstellen
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Nachricht hinzufügen
        msg.attach(MIMEText(message, 'plain', 'utf-8'))
        
        # Optional: Attachment hinzufügen
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
        
        # SMTP-Verbindung
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

def show_paper_search():
    """Vollständige Paper-Suche mit Email-Integration"""
    st.write("**🔍 Paper-Suche mit automatischer Email-Benachrichtigung**")
    
    # Email-Status anzeigen
    settings = st.session_state.get("email_settings", {})
    email_enabled = (settings.get("auto_notifications", False) and 
                    bool(settings.get("sender_email")) and 
                    bool(settings.get("recipient_email")) and
                    bool(settings.get("sender_password")))
    
    if email_enabled:
        st.success("✅ **Email-Benachrichtigungen sind aktiviert und konfiguriert**")
    else:
        st.warning("⚠️ **Email-Benachrichtigungen sind deaktiviert oder unvollständig** - Konfigurieren Sie sie im Tab 'Email-Konfiguration'")
    
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
    """Führt PubMed-Suche durch mit vollständiger Email-Integration"""
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
                
                # Email für neue Papers SENDEN
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
            
            # Email für alle Papers SENDEN
            send_paper_notification(query, len(current_papers), current_papers, is_new_papers=False, force_send=force_email)
            
            # Neue Excel-Datei erstellen
            create_excel_file(query, current_papers)
            
            # Zeige alle Papers
            display_papers_with_highlights(current_papers, current_papers, query)
        
        # Speichere Suchergebnisse
        save_search_results(query, current_papers, is_repeat_search)

def perform_pubmed_search(query: str, max_results: int) -> List[Dict[str, Any]]:
    """Führt vollständige PubMed-Suche durch"""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    # 1. esearch - hole PMIDs
    search_url = f"{base_url}esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": max_results,
        "email": "research@paper-search.com",
        "tool": "IntegratedPaperSearchSystem"
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
    """Holt vollständige Paper-Details von PubMed"""
    if not pmids:
        return []
    
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    fetch_url = f"{base_url}efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "email": "research@paper-search.com",
        "tool": "IntegratedPaperSearchSystem"
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
    """Parst einzelnen Artikel aus PubMed XML"""
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
    """Lädt vorherige Suchergebnisse aus Excel"""
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

def send_paper_notification(query: str, paper_count: int, papers: List[Dict], is_new_papers: bool = False, force_send: bool = False):
    """Sendet ECHTE Email-Benachrichtigung"""
    settings = st.session_state.get("email_settings", {})
    
    # Prüfe ob Email gesendet werden soll
    should_send = (force_send or 
                  (settings.get("auto_notifications", False) and 
                   paper_count >= settings.get("min_papers", 5)))
    
    if not should_send:
        return
    
    # Email-Inhalt generieren
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
            message += f"\n   URL: {paper.get('URL', 'n/a')}"
        
        if len(papers) > 5:
            message += f"\n\n... und {len(papers) - 5} weitere Papers"
    
    # ECHTE EMAIL SENDEN
    recipient = settings.get("recipient_email", "")
    
    # Optional: Excel-Datei als Attachment
    excel_filename = get_excel_filename(query)
    excel_path = os.path.join("saved_searches", excel_filename)
    attachment_path = excel_path if os.path.exists(excel_path) else None
    
    success, status_message = send_real_email(recipient, subject, message, attachment_path)
    
    # Email zur Historie hinzufügen
    email_notification = {
        "timestamp": datetime.datetime.now().isoformat(),
        "date": datetime.datetime.now().date().isoformat(),
        "search_term": query,
        "paper_count": paper_count,
        "recipient": recipient,
        "status": status_message,
        "type": email_type,
        "subject": subject,
        "message": message,
        "success": success,
        "has_attachment": attachment_path is not None
    }
    
    if "email_history" not in st.session_state:
        st.session_state["email_history"] = []
    
    st.session_state["email_history"].append(email_notification)
    
    # Status anzeigen
    if success:
        st.success(f"📧 **Email gesendet!** {email_type} für '{query}' an {recipient}")
    else:
        st.error(f"📧 **Email-Fehler:** {status_message}")
    
    # Email-Vorschau
    with st.expander("📧 Gesendete Email anzeigen"):
        preview = f"""Von: {settings.get('sender_email', 'system@example.com')}
An: {recipient}
Betreff: {subject}
Attachment: {'✅ Excel-Datei' if attachment_path else '❌ Keine'}

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
    """Sendet ECHTE Email für einzelnes Paper"""
    settings = st.session_state.get("email_settings", {})
    
    subject = f"📄 Einzelnes Paper: {paper.get('Title', 'Unknown')[:40]}..."
    
    message = f"""📄 Einzelnes Paper aus der Suche '{search_term}':

Titel: {paper.get('Title', 'Unbekannt')}
Autoren: {paper.get('Authors', 'n/a')}
Journal: {paper.get('Journal', 'n/a')} ({paper.get('Year', 'n/a')})
PMID: {paper.get('PMID', 'n/a')}

PubMed Link: {paper.get('URL', 'n/a')}

Abstract:
{paper.get('Abstract', 'No abstract available')[:500]}...

Gesendet am: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}"""
    
    recipient = settings.get("recipient_email", "")
    success, status_message = send_real_email(recipient, subject, message)
    
    # Historie hinzufügen
    test_email = {
        "timestamp": datetime.datetime.now().isoformat(),
        "date": datetime.datetime.now().date().isoformat(),
        "search_term": f"Einzelpaper: {search_term}",
        "paper_count": 1,
        "recipient": recipient,
        "status": status_message,
        "type": "Einzelpaper",
        "success": success
    }
    
    st.session_state["email_history"].append(test_email)
    
    if success:
        st.success(f"📧 **Email erfolgreich gesendet** für: {paper.get('Title', 'Unknown')[:40]}...")
    else:
        st.error(f"📧 **Email-Fehler:** {status_message}")

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

def show_email_history():
    """Vollständiger Email-Verlauf mit Erfolgs-Status"""
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
            successful_emails = len([h for h in history if h.get("success", False)])
            st.metric("✅ Erfolgreich", successful_emails)
        
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
            success = email.get("success", False)
            
            # Status-Icon basierend auf Erfolg
            status_icon = "✅" if success else "❌"
            type_icon = "🆕" if email_type == "Neue Papers" else "🔍" if email_type == "Paper-Suche" else "📧"
            
            with st.expander(f"{status_icon} {type_icon} {i}. {email_type}: {search_term} - {paper_count} Papers ({timestamp})"):
                col_detail1, col_detail2 = st.columns(2)
                
                with col_detail1:
                    st.write(f"**Typ:** {email_type}")
                    st.write(f"**Suchbegriff:** {search_term}")
                    st.write(f"**Papers:** {paper_count}")
                
                with col_detail2:
                    st.write(f"**Empfänger:** {email.get('recipient', 'N/A')}")
                    st.write(f"**✅ Erfolgreich gesendet:** {'Ja' if success else 'Nein'}")
                    st.write(f"**Zeit:** {timestamp}")
                    if email.get("has_attachment"):
                        st.write("📎 **Attachment:** Excel-Datei enthalten")
                
                # Status-Details
                status = email.get("status", "N/A")
                if success:
                    st.success(f"✅ {status}")
                else:
                    st.error(f"❌ {status}")
                
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
    """Vollständige Email-Tests mit echten Emails"""
    st.write("**🧪 Email-System testen:**")
    
    settings = st.session_state.get("email_settings", {})
    
    # Konfigurationsstatus
    sender_ok = bool(settings.get("sender_email"))
    recipient_ok = bool(settings.get("recipient_email"))
    password_ok = bool(settings.get("sender_password"))
    auto_ok = settings.get("auto_notifications", False)
    
    st.write("**📋 System-Status:**")
    
    col_status1, col_status2 = st.columns(2)
    
    with col_status1:
        st.write(f"{'✅' if sender_ok else '❌'} **Absender Email:** {'Konfiguriert' if sender_ok else 'Fehlt'}")
        st.write(f"{'✅' if recipient_ok else '❌'} **Empfänger Email:** {'Konfiguriert' if recipient_ok else 'Fehlt'}")
        st.write(f"{'✅' if password_ok else '❌'} **Email Passwort:** {'Konfiguriert' if password_ok else 'Fehlt'}")
    
    with col_status2:
        st.write(f"{'✅' if auto_ok else '❌'} **Auto-Benachrichtigungen:** {'Aktiviert' if auto_ok else 'Deaktiviert'}")
        st.write(f"**Min. Papers:** {settings.get('min_papers', 5)}")
        st.write(f"**SMTP Server:** {settings.get('smtp_server', 'N/A')}")
    
    # Test-Funktionen
    st.write("**🧪 Test-Aktionen:**")
    
    col_test1, col_test2, col_test3 = st.columns(3)
    
    with col_test1:
        if st.button("📧 **ECHTE Test-Email senden**", type="primary"):
            if sender_ok and recipient_ok and password_ok:
                send_test_email()
            else:
                st.error("❌ Email-Konfiguration unvollständig! Prüfen Sie Email, Empfänger und Passwort.")
    
    with col_test2:
        if st.button("🔍 Test Paper-Email"):
            send_test_paper_email()
    
    with col_test3:
        if st.button("📊 System-Statistiken"):
            show_system_statistics()

def send_test_email():
    """Sendet ECHTE Test-Email"""
    settings = st.session_state.get("email_settings", {})
    
    sender = settings.get("sender_email", "")
    recipient = settings.get("recipient_email", "")
    
    if not sender or not recipient:
        st.error("❌ Email-Konfiguration unvollständig!")
        return
    
    subject = "🧪 Test-Email vom Paper-Suche System"
    message = f"""Dies ist eine ECHTE Test-Email vom integrierten Paper-Suche System.

📅 Gesendet am: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
📧 Von: {sender}
📧 An: {recipient}

✅ Wenn Sie diese Email erhalten, funktioniert das Email-System korrekt!

System-Informationen:
• SMTP Server: {settings.get('smtp_server', 'N/A')}
• Port: {settings.get('smtp_port', 'N/A')}
• TLS: {'Aktiviert' if settings.get('use_tls', False) else 'Deaktiviert'}

🔥 Dies ist eine ECHTE Email, keine Simulation!

Mit freundlichen Grüßen,
Ihr Paper-Suche Email-System"""
    
    success, status_message = send_real_email(recipient, subject, message)
    
    # Historie hinzufügen
    test_email = {
        "timestamp": datetime.datetime.now().isoformat(),
        "date": datetime.datetime.now().date().isoformat(),
        "search_term": "System-Test",
        "paper_count": 0,
        "recipient": recipient,
        "status": status_message,
        "type": "Test",
        "success": success,
        "subject": subject,
        "message": message
    }
    
    st.session_state["email_history"].append(test_email)
    
    if success:
        st.success("✅ **ECHTE Test-Email erfolgreich gesendet!** Prüfen Sie Ihr Postfach.")
        st.balloons()
    else:
        st.error(f"❌ **Test-Email fehlgeschlagen:** {status_message}")
    
    # Vorschau
    with st.expander("📧 Test-Email Vorschau"):
        st.code(f"An: {recipient}\nBetreff: {subject}\n\n{message}", language="text")

def send_test_paper_email():
    """Sendet ECHTE Test-Email für Paper-Suche"""
    settings = st.session_state.get("email_settings", {})
    
    test_papers = [
        {"Title": "Test Paper 1: Machine Learning in Medicine", "PMID": "12345", "Authors": "Smith, J. et al.", "URL": "https://pubmed.ncbi.nlm.nih.gov/12345/"},
        {"Title": "Test Paper 2: AI Applications in Healthcare", "PMID": "67890", "Authors": "Jones, A. et al.", "URL": "https://pubmed.ncbi.nlm.nih.gov/67890/"},
        {"Title": "Test Paper 3: Deep Learning for Diagnosis", "PMID": "13579", "Authors": "Brown, K. et al.", "URL": "https://pubmed.ncbi.nlm.nih.gov/13579/"}
    ]
    
    send_paper_notification("Test-Suchbegriff", 3, test_papers, is_new_papers=True, force_send=True)
    st.success("✅ ECHTE Test-Paper-Email gesendet!")

def show_system_statistics():
    """Zeigt vollständige System-Statistiken"""
    st.write("**📊 Vollständige System-Statistiken:**")
    
    # Email-Statistiken
    history = st.session_state.get("email_history", [])
    search_history = st.session_state.get("paper_search_history", [])
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    
    with col_stat1:
        st.write("**📧 Email-System:**")
        st.write(f"• Gesamt Emails: {len(history)}")
        
        if history:
            successful = len([h for h in history if h.get("success", False)])
            failed = len(history) - successful
            success_rate = (successful / len(history) * 100) if history else 0
            
            st.write(f"• ✅ Erfolgreich: {successful}")
            st.write(f"• ❌ Fehlgeschlagen: {failed}")
            st.write(f"• 📊 Erfolgsrate: {success_rate:.1f}%")
            
            paper_emails = len([h for h in history if "paper" in h.get("type", "").lower()])
            st.write(f"• 🔍 Paper-Emails: {paper_emails}")
            
            total_papers = sum(h.get("paper_count", 0) for h in history)
            st.write(f"• 📄 Gesamt Papers: {total_papers}")
    
    with col_stat2:
        st.write("**🔍 Paper-Suche:**")
        st.write(f"• Gesamt Suchen: {len(search_history)}")
        
        if search_history:
            total_results = sum(s.get("results_count", 0) for s in search_history)
            st.write(f"• 📊 Gesamt Ergebnisse: {total_results}")
            
            avg_results = total_results / len(search_history) if search_history else 0
            st.write(f"• 📈 Ø Ergebnisse/Suche: {avg_results:.1f}")
            
            recent_searches = [s for s in search_history if 
                             (datetime.datetime.now() - datetime.datetime.fromisoformat(s["timestamp"])).days <= 7]
            st.write(f"• 🗓️ Suchen (7 Tage): {len(recent_searches)}")
    
    with col_stat3:
        st.write("**📁 Excel-System:**")
        excel_files = []
        if os.path.exists("saved_searches"):
            excel_files = [f for f in os.listdir("saved_searches") if f.endswith('.xlsx')]
        
        st.write(f"• 📄 Excel-Dateien: {len(excel_files)}")
        
        if excel_files:
            total_size = sum(os.path.getsize(os.path.join("saved_searches", f)) for f in excel_files)
            st.write(f"• 💾 Gesamt Größe: {total_size:,} bytes")
            st.write(f"• 📊 Ø Größe/Datei: {total_size//len(excel_files):,} bytes")

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

# Integration-Funktionen für andere Module
def trigger_email_notification(search_term, paper_count):
    """Integration für andere Module mit echter Email"""
    try:
        settings = st.session_state.get("email_settings", {})
        
        if not settings.get("auto_notifications", False):
            return False
        
        min_papers = settings.get("min_papers", 5)
        if paper_count < min_papers:
            return False
        
        # Sende echte Email
        subject = f"🔬 Automatische Benachrichtigung: {paper_count} Papers für '{search_term}'"
        message = f"""Automatische Paper-Benachrichtigung

📅 Datum: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}
🔍 Suchbegriff: '{search_term}'
📊 Anzahl Papers: {paper_count}

Diese Benachrichtigung wurde automatisch von einem anderen Modul ausgelöst.

Mit freundlichen Grüßen,
Ihr automatisches Paper-Suche System"""
        
        recipient = settings.get("recipient_email", "")
        success, status_message = send_real_email(recipient, subject, message)
        
        # Erstelle Email-Benachrichtigung
        email_notification = {
            "timestamp": datetime.datetime.now().isoformat(),
            "date": datetime.datetime.now().date().isoformat(),
            "search_term": search_term,
            "paper_count": paper_count,
            "recipient": recipient,
            "status": status_message,
            "type": "Automatisch (von anderem Modul)",
            "success": success,
            "subject": subject,
            "message": message
        }
        
        if "email_history" not in st.session_state:
            st.session_state["email_history"] = []
        
        st.session_state["email_history"].append(email_notification)
        return success
    
    except Exception:
        return False

def get_email_settings():
    """Gibt aktuelle Email-Einstellungen zurück"""
    return st.session_state.get("email_settings", {})

def is_email_enabled():
    """Prüft ob Email-System aktiviert und vollständig konfiguriert ist"""
    settings = st.session_state.get("email_settings", {})
    return (settings.get("auto_notifications", False) and 
            bool(settings.get("sender_email")) and 
            bool(settings.get("recipient_email")) and
            bool(settings.get("sender_password")))

# Hauptfunktion für externe Verwendung
if __name__ == "__main__":
    module_email()
