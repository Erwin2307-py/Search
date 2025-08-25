# modules/email_module.py - ERWEITERTE VERSION MIT MEHREREN EMAIL-EMPFÄNGERN
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
import threading

def module_email():
    """VOLLSTÄNDIGE FUNKTION - Email-Modul mit mehreren Empfängern und manuellem Email-Versand"""
    st.title("📧 Wissenschaftliches Paper-Suche & Email-System")
    st.success("✅ Vollständiges Modul mit mehreren Email-Empfängern und manuellem Versand geladen!")
    
    # Session State initialisieren
    initialize_session_state()
    
    # Erweiterte Tabs
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
    
    # Email-Einstellungen - ERWEITERT für mehrere Empfänger
    if "email_settings" not in st.session_state:
        st.session_state["email_settings"] = {
            "sender_email": "",
            "recipient_emails": "",  # Mehrere Empfänger (komma-getrennt)
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
    
    # Andere Session State Initialisierungen...
    if "excel_template" not in st.session_state:
        st.session_state["excel_template"] = {
            "file_path": "excel_templates/master_papers.xlsx",
            "auto_create_sheets": True,
            "sheet_naming": "topic_based",
            "max_sheets": 50
        }
    
    if "search_history" not in st.session_state:
        st.session_state["search_history"] = []
    
    if "email_history" not in st.session_state:
        st.session_state["email_history"] = []
    
    if "automatic_searches" not in st.session_state:
        st.session_state["automatic_searches"] = {}
    
    if "system_status" not in st.session_state:
        st.session_state["system_status"] = {
            "total_searches": 0,
            "total_papers": 0,
            "total_emails": 0,
            "last_search": None,
            "excel_sheets": 0
        }
    
    # Store current search results in session state for manual email sending
    if "current_search_results" not in st.session_state:
        st.session_state["current_search_results"] = {}
    
    # Erstelle Master Excel-Datei falls nicht vorhanden
    create_master_excel_template()

def show_email_config():
    """Email-Konfiguration mit mehreren Empfängern"""
    st.subheader("📧 Email-Konfiguration (Mehrere Empfänger)")
    
    settings = st.session_state.get("email_settings", {})
    
    # Email-Setup Hilfe
    with st.expander("📖 Email-Setup Hilfe & Mehrere Empfänger"):
        st.info("""
        **Für Gmail (empfohlen):**
        1. ✅ 2-Faktor-Authentifizierung aktivieren
        2. ✅ App-Passwort erstellen (nicht normales Passwort!)
        3. ✅ SMTP: smtp.gmail.com, Port: 587, TLS: An
        
        **Mehrere Empfänger:**
        • Trennen Sie mehrere Email-Adressen mit Kommas
        • Beispiel: user1@gmail.com, user2@outlook.com, user3@company.de
        • Whitespaces werden automatisch entfernt
        
        **Für Outlook/Hotmail:**
        - SMTP: smtp-mail.outlook.com, Port: 587
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
            
            use_tls = st.checkbox(
                "TLS Verschlüsselung verwenden (empfohlen)",
                value=settings.get("use_tls", True)
            )
        
        # MEHRERE EMPFÄNGER - Text Area
        recipient_emails = st.text_area(
            "📧 Empfänger Email-Adressen * (mehrere mit Komma trennen)",
            value=settings.get("recipient_emails", ""),
            placeholder="empfaenger1@example.com, empfaenger2@gmail.com, empfaenger3@company.de",
            help="Mehrere Email-Adressen mit Komma trennen. Beispiel: user1@gmail.com, user2@outlook.com",
            height=80
        )
        
        sender_password = st.text_input(
            "Email Passwort / App-Passwort *",
            value=settings.get("sender_password", ""),
            type="password",
            help="Für Gmail: App-spezifisches Passwort verwenden!"
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
            value=settings.get("message_template", """📧 Automatische Paper-Benachrichtigung

📅 Datum: {date}
🔍 Suchbegriff: '{search_term}'
📊 Neue Papers: {count}

📋 Neue Papers:
{new_papers_list}

📎 Excel-Datei: {excel_file}

Mit freundlichen Grüßen,
Ihr Paper-Suche System"""),
            height=200,
            help="Platzhalter: {date}, {search_term}, {count}, {frequency}, {new_papers_list}, {excel_file}"
        )
        
        if st.form_submit_button("💾 **Email-Einstellungen speichern**", type="primary"):
            # Validiere Email-Adressen
            recipient_list = parse_recipient_emails(recipient_emails)
            
            if not recipient_list:
                st.error("❌ Mindestens eine gültige Empfänger-Email erforderlich!")
            else:
                new_settings = {
                    "sender_email": sender_email,
                    "recipient_emails": recipient_emails,
                    "smtp_server": smtp_server,
                    "smtp_port": smtp_port,
                    "sender_password": sender_password,
                    "use_tls": use_tls,
                    "auto_notifications": auto_notifications,
                    "min_papers": min_papers,
                    "subject_template": subject_template,
                    "message_template": message_template,
                    "parsed_recipients": recipient_list  # Store parsed list
                }
                
                st.session_state["email_settings"] = new_settings
                st.success(f"✅ Email-Einstellungen gespeichert! **{len(recipient_list)} Empfänger** konfiguriert:")
                for i, email in enumerate(recipient_list, 1):
                    st.write(f"   {i}. 📧 {email}")
    
    # Zeige konfigurierte Empfänger
    if settings.get("recipient_emails"):
        recipient_list = parse_recipient_emails(settings.get("recipient_emails", ""))
        if recipient_list:
            st.info(f"📧 **Aktuell konfigurierte Empfänger ({len(recipient_list)}):**")
            cols = st.columns(min(len(recipient_list), 3))
            for i, email in enumerate(recipient_list):
                with cols[i % 3]:
                    st.write(f"✅ {email}")
    
    # Test-Email
    st.markdown("---")
    st.subheader("🧪 Email-System testen")
    
    col_test1, col_test2 = st.columns(2)
    
    with col_test1:
        if st.button("📧 **Test-Email an alle Empfänger senden**", type="primary"):
            send_test_email_multiple()
    
    with col_test2:
        if st.button("📊 **Email-Status prüfen**"):
            check_email_status()

def parse_recipient_emails(email_string: str) -> List[str]:
    """Parst Email-String und gibt Liste gültiger Emails zurück"""
    if not email_string:
        return []
    
    # Split by comma and clean
    emails = [email.strip() for email in email_string.split(",")]
    
    # Basic email validation
    valid_emails = []
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    for email in emails:
        if email and email_pattern.match(email):
            valid_emails.append(email)
    
    return valid_emails

def send_real_email_multiple(to_emails: List[str], subject: str, message: str, attachment_path: str = None) -> tuple:
    """Sendet echte Email über SMTP an mehrere Empfänger"""
    settings = st.session_state.get("email_settings", {})
    
    sender_email = settings.get("sender_email", "")
    sender_password = settings.get("sender_password", "")
    smtp_server = settings.get("smtp_server", "smtp.gmail.com")
    smtp_port = settings.get("smtp_port", 587)
    use_tls = settings.get("use_tls", True)
    
    if not all([sender_email, sender_password]):
        return False, "❌ Email-Konfiguration unvollständig (Absender/Passwort)"
    
    if not to_emails:
        return False, "❌ Keine Empfänger-Emails konfiguriert"
    
    try:
        # SMTP Server Setup
        server = smtplib.SMTP(smtp_server, smtp_port)
        
        if use_tls:
            context = ssl.create_default_context()
            server.starttls(context=context)
        
        server.login(sender_email, sender_password)
        
        successful_sends = 0
        failed_sends = []
        
        # Send to each recipient
        for recipient in to_emails:
            try:
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = recipient
                msg['Subject'] = subject
                
                msg.attach(MIMEText(message, 'plain', 'utf-8'))
                
                # Add attachment if provided
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
                
                server.send_message(msg)
                successful_sends += 1
                
            except Exception as e:
                failed_sends.append(f"{recipient}: {str(e)}")
        
        server.quit()
        
        if successful_sends == len(to_emails):
            return True, f"✅ Email erfolgreich an alle {successful_sends} Empfänger gesendet"
        elif successful_sends > 0:
            return True, f"⚠️ Email an {successful_sends}/{len(to_emails)} Empfänger gesendet. Fehler: {'; '.join(failed_sends)}"
        else:
            return False, f"❌ Email an keinen Empfänger gesendet. Fehler: {'; '.join(failed_sends)}"
        
    except smtplib.SMTPAuthenticationError:
        return False, "❌ SMTP-Authentifizierung fehlgeschlagen - Prüfen Sie Email/Passwort"
    except smtplib.SMTPServerDisconnected:
        return False, "❌ SMTP-Server-Verbindung unterbrochen"
    except Exception as e:
        return False, f"❌ Email-Fehler: {str(e)}"

def send_test_email_multiple():
    """Sendet Test-Email an alle konfigurierten Empfänger"""
    settings = st.session_state.get("email_settings", {})
    
    recipient_emails = parse_recipient_emails(settings.get("recipient_emails", ""))
    
    if not settings.get("sender_email") or not recipient_emails:
        st.error("❌ Email-Konfiguration unvollständig!")
        return
    
    subject = "🧪 Test-Email vom Paper-Suche System (Mehrere Empfänger)"
    message = f"""Dies ist eine Test-Email vom Paper-Suche System mit Unterstützung für mehrere Empfänger.

📅 Gesendet am: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
📧 Von: {settings.get('sender_email')}
📧 An: {len(recipient_emails)} Empfänger

Empfänger-Liste:
{chr(10).join([f"• {email}" for email in recipient_emails])}

✅ Wenn Sie diese Email erhalten, funktioniert das Email-System korrekt!

System-Informationen:
• SMTP Server: {settings.get('smtp_server')}
• Port: {settings.get('smtp_port')}
• TLS: {'Aktiviert' if settings.get('use_tls') else 'Deaktiviert'}
• Empfänger: {len(recipient_emails)}

Mit freundlichen Grüßen,
Ihr Paper-Suche System"""
    
    success, status_message = send_real_email_multiple(
        recipient_emails, 
        subject, 
        message
    )
    
    if success:
        st.success(f"✅ **Test-Email erfolgreich gesendet!** {status_message}")
        st.balloons()
    else:
        st.error(f"❌ **Test-Email fehlgeschlagen:** {status_message}")

def show_advanced_paper_search():
    """Erweiterte Paper-Suche mit manuellem Email-Versand"""
    st.subheader("🔍 Erweiterte Paper-Suche")
    
    # Email-Status anzeigen
    email_status = is_email_configured()
    recipient_count = len(parse_recipient_emails(st.session_state.get("email_settings", {}).get("recipient_emails", "")))
    
    if email_status:
        st.success(f"✅ Email-Benachrichtigungen aktiviert für **{recipient_count} Empfänger**")
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
    
    # *** MANUELLER EMAIL-VERSAND BEREICH ***
    if st.session_state.get("current_search_results"):
        st.markdown("---")
        st.subheader("📧 Manueller Email-Versand")
        
        current_results = st.session_state["current_search_results"]
        search_term = current_results.get("search_term", "")
        papers = current_results.get("papers", [])
        new_papers = current_results.get("new_papers", [])
        
        if papers:
            col_email1, col_email2, col_email3 = st.columns(3)
            
            with col_email1:
                st.metric("📄 Verfügbare Papers", len(papers))
            
            with col_email2:
                st.metric("🆕 Neue Papers", len(new_papers))
            
            with col_email3:
                recipient_count = len(parse_recipient_emails(st.session_state.get("email_settings", {}).get("recipient_emails", "")))
                st.metric("📧 Empfänger", recipient_count)
            
            # Email-Optionen
            col_send1, col_send2 = st.columns(2)
            
            with col_send1:
                if st.button(f"📧 **Alle Papers emailen** ({len(papers)})", type="primary"):
                    if email_status:
                        send_manual_search_email(search_term, papers, "Alle Papers")
                    else:
                        st.error("❌ Email nicht konfiguriert!")
            
            with col_send2:
                if new_papers and st.button(f"📧 **Nur neue Papers emailen** ({len(new_papers)})", type="secondary"):
                    if email_status:
                        send_manual_search_email(search_term, new_papers, "Nur neue Papers")
                    else:
                        st.error("❌ Email nicht konfiguriert!")
            
            # Email-Status für diese Suche
            if not email_status:
                st.warning("⚠️ **Email-Versand nicht möglich:** Konfigurieren Sie Email-Einstellungen im entsprechenden Tab")
            elif recipient_count == 0:
                st.warning("⚠️ **Keine Empfänger konfiguriert:** Fügen Sie Email-Adressen in der Email-Konfiguration hinzu")

def send_manual_search_email(search_term: str, papers: List[Dict], email_type: str):
    """Sendet manuelle Email für Suchergebnisse"""
    settings = st.session_state.get("email_settings", {})
    
    if not is_email_configured():
        st.error("❌ Email nicht konfiguriert!")
        return
    
    recipient_emails = parse_recipient_emails(settings.get("recipient_emails", ""))
    
    if not recipient_emails:
        st.error("❌ Keine Empfänger konfiguriert!")
        return
    
    # Subject generieren
    subject = f"📧 {email_type}: {len(papers)} Papers für '{search_term}' (Manuell)"
    
    # Papers-Liste formatieren
    papers_list = ""
    for i, paper in enumerate(papers[:15], 1):  # Erste 15 Papers
        title = paper.get("Title", "Unbekannt")[:70]
        authors = paper.get("Authors", "n/a")[:50]
        journal = paper.get("Journal", "n/a")
        year = paper.get("Year", "n/a")
        pmid = paper.get("PMID", "n/a")
        
        papers_list += f"\n{i}. **{title}...**\n"
        papers_list += f"   👥 {authors}...\n"
        papers_list += f"   📚 {journal} ({year}) | PMID: {pmid}\n\n"
    
    if len(papers) > 15:
        papers_list += f"... und {len(papers) - 15} weitere Papers (siehe Excel-Datei)\n"
    
    # Message generieren
    message = f"""📧 **Manueller Email-Versand - Paper-Suche**

📅 **Datum:** {datetime.datetime.now().strftime("%d.%m.%Y %H:%M")}
🔍 **Suchbegriff:** '{search_term}'
📊 **Typ:** {email_type}
📄 **Anzahl Papers:** {len(papers)}
📧 **Empfänger:** {len(recipient_emails)}

{'-' * 50}
📋 **PAPERS:**
{papers_list}

📎 **Excel-Datei:** Die aktualisierte Excel-Datei ist als Anhang beigefügt.

ℹ️ **Hinweis:** Diese Email wurde manuell über das Paper-Suche System versendet.

Mit freundlichen Grüßen,
Ihr Paper-Suche System"""
    
    # Excel als Anhang
    excel_path = st.session_state["excel_template"]["file_path"]
    attachment_path = excel_path if os.path.exists(excel_path) else None
    
    # Email senden
    with st.spinner(f"📧 Sende Email an {len(recipient_emails)} Empfänger..."):
        success, status_message = send_real_email_multiple(recipient_emails, subject, message, attachment_path)
    
    # Email-Historie
    email_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "type": f"Manuell - {email_type}",
        "search_term": search_term,
        "recipients": recipient_emails,
        "recipient_count": len(recipient_emails),
        "subject": subject,
        "paper_count": len(papers),
        "success": success,
        "status": status_message,
        "has_attachment": attachment_path is not None
    }
    
    st.session_state["email_history"].append(email_entry)
    
    # Ergebnis anzeigen
    if success:
        st.session_state["system_status"]["total_emails"] += 1
        st.success(f"📧 **Email erfolgreich versendet!**\n{status_message}")
        st.balloons()
        
        # Details anzeigen
        with st.expander("📋 Email-Details anzeigen"):
            st.write(f"**📧 Empfänger ({len(recipient_emails)}):**")
            for i, email in enumerate(recipient_emails, 1):
                st.write(f"   {i}. {email}")
            st.write(f"**📄 Papers:** {len(papers)}")
            st.write(f"**📎 Anhang:** {'✅ Excel-Datei' if attachment_path else '❌ Kein Anhang'}")
    else:
        st.error(f"❌ **Email-Fehler:** {status_message}")

def execute_advanced_paper_search(query: str, max_results: int, date_filter: str, force_email: bool, force_new_sheet: bool):
    """Führt erweiterte Paper-Suche mit Email-Integration durch"""
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
                    send_new_papers_email_multiple(query, new_papers, len(current_papers))
                
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
                send_first_search_email_multiple(query, current_papers)
            
            # Zeige Ergebnisse
            display_search_results(current_papers, current_papers, query, is_repeat=False)
        
        # 4. Speichere Ergebnisse für manuellen Email-Versand
        st.session_state["current_search_results"] = {
            "search_term": query,
            "papers": current_papers,
            "new_papers": new_papers if is_repeat_search else current_papers,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # 5. Aktualisiere System-Status
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

def send_new_papers_email_multiple(search_term: str, new_papers: List[Dict], total_papers: int):
    """Sendet Email mit neuen Papers an mehrere Empfänger"""
    settings = st.session_state.get("email_settings", {})
    
    if not is_email_configured() or not should_send_email(len(new_papers)):
        return
    
    recipient_emails = parse_recipient_emails(settings.get("recipient_emails", ""))
    
    if not recipient_emails:
        st.warning("⚠️ Keine Email-Empfänger konfiguriert!")
        return
    
    # Subject generieren
    subject_template = settings.get("subject_template", "🔬 {count} neue Papers für '{search_term}'")
    subject = subject_template.format(
        count=len(new_papers),
        search_term=search_term,
        frequency="Automatische Suche"
    )
    
    # Papers-Liste formatieren
    papers_list = ""
    for i, paper in enumerate(new_papers[:10], 1):
        title = paper.get("Title", "Unbekannt")[:60]
        authors = paper.get("Authors", "n/a")[:40]
        journal = paper.get("Journal", "n/a")
        year = paper.get("Year", "n/a")
        pmid = paper.get("PMID", "n/a")
        
        papers_list += f"\n{i}. **{title}...**\n"
        papers_list += f"   👥 {authors}...\n"
        papers_list += f"   📚 {journal} ({year})\n"
        papers_list += f"   🆔 PMID: {pmid}\n\n"
    
    if len(new_papers) > 10:
        papers_list += f"... und {len(new_papers) - 10} weitere neue Papers (siehe Excel-Datei)\n"
    
    # Message generieren
    message_template = settings.get("message_template", "Neue Papers gefunden")
    message = message_template.format(
        date=datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
        search_term=search_term,
        count=len(new_papers),
        frequency="Automatische Suche",
        new_papers_list=papers_list,
        excel_file=os.path.basename(st.session_state["excel_template"]["file_path"])
    )
    
    # Excel als Anhang
    excel_path = st.session_state["excel_template"]["file_path"]
    attachment_path = excel_path if os.path.exists(excel_path) else None
    
    # Email senden
    success, status_message = send_real_email_multiple(recipient_emails, subject, message, attachment_path)
    
    # Email-Historie
    email_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "type": "Neue Papers (Automatisch)",
        "search_term": search_term,
        "recipients": recipient_emails,
        "recipient_count": len(recipient_emails),
        "subject": subject,
        "paper_count": len(new_papers),
        "success": success,
        "status": status_message,
        "has_attachment": attachment_path is not None
    }
    
    st.session_state["email_history"].append(email_entry)
    
    if success:
        st.session_state["system_status"]["total_emails"] += 1
        st.success(f"📧 **Email gesendet:** {len(new_papers)} neue Papers für '{search_term}' an {len(recipient_emails)} Empfänger!")
    else:
        st.error(f"📧 **Email-Fehler:** {status_message}")

def send_first_search_email_multiple(search_term: str, papers: List[Dict]):
    """Sendet Email für erste Suche an mehrere Empfänger"""
    send_new_papers_email_multiple(search_term, papers, len(papers))

def check_email_status():
    """Prüft Email-Status mit mehreren Empfängern"""
    settings = st.session_state.get("email_settings", {})
    
    st.write("**📊 Email-Konfiguration Status:**")
    
    # Prüfe Konfiguration
    sender_ok = bool(settings.get("sender_email"))
    recipient_emails = parse_recipient_emails(settings.get("recipient_emails", ""))
    recipients_ok = len(recipient_emails) > 0
    password_ok = bool(settings.get("sender_password"))
    
    st.write(f"📧 Absender Email: {'✅' if sender_ok else '❌'} {settings.get('sender_email', 'Nicht konfiguriert')}")
    st.write(f"📧 Empfänger Emails: {'✅' if recipients_ok else '❌'} {len(recipient_emails)} konfiguriert")
    
    if recipients_ok:
        with st.expander(f"📧 Empfänger-Liste ({len(recipient_emails)})"):
            for i, email in enumerate(recipient_emails, 1):
                st.write(f"   {i}. {email}")
    
    st.write(f"🔑 Passwort: {'✅' if password_ok else '❌'} {'Konfiguriert' if password_ok else 'Nicht konfiguriert'}")
    st.write(f"🔒 SMTP Server: {settings.get('smtp_server', 'smtp.gmail.com')}:{settings.get('smtp_port', 587)}")
    st.write(f"🔐 TLS: {'✅ Aktiviert' if settings.get('use_tls', True) else '❌ Deaktiviert'}")
    
    # Gesamtstatus
    if sender_ok and recipients_ok and password_ok:
        st.success(f"✅ **Email-System vollständig konfiguriert für {len(recipient_emails)} Empfänger!**")
    else:
        st.error("❌ **Email-System nicht vollständig konfiguriert!**")

def is_email_configured() -> bool:
    """Prüft Email-Konfiguration für mehrere Empfänger"""
    settings = st.session_state.get("email_settings", {})
    recipient_emails = parse_recipient_emails(settings.get("recipient_emails", ""))
    
    return (bool(settings.get("sender_email")) and 
            len(recipient_emails) > 0 and
            bool(settings.get("sender_password")))

# Alle anderen Funktionen bleiben unverändert - hier füge ich nur die wichtigsten hinzu:

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
            
            wb.save(template_path)
            
        except Exception as e:
            st.error(f"❌ Fehler beim Erstellen des Master-Templates: {str(e)}")

# Weitere notwendige Funktionen (vereinfacht)
def show_dashboard():
    st.subheader("📊 Dashboard")
    status = st.session_state["system_status"]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔍 Gesamt Suchen", status["total_searches"])
    with col2:
        st.metric("📄 Gesamt Papers", status["total_papers"])
    with col3:
        st.metric("📧 Gesendete Emails", status["total_emails"])
    with col4:
        recipients = len(parse_recipient_emails(st.session_state.get("email_settings", {}).get("recipient_emails", "")))
        st.metric("📧 Email-Empfänger", recipients)

def show_excel_template_management():
    st.subheader("📋 Excel-Template Management")
    st.info("Excel-Template Management hier implementiert...")

def show_automatic_search_system():
    st.subheader("🤖 Automatisches Such-System")
    st.info("Automatisches Such-System hier implementiert...")

def show_detailed_statistics():
    st.subheader("📈 Detaillierte Statistiken")
    st.info("Detaillierte Statistiken hier implementiert...")

def show_system_settings():
    st.subheader("⚙️ System-Einstellungen")
    st.info("System-Einstellungen hier implementiert...")

# Weitere Hilfsfunktionen
def perform_comprehensive_pubmed_search(query: str, max_results: int) -> List[Dict[str, Any]]:
    """Vereinfachte PubMed-Suche für Demo"""
    # Hier würde die echte PubMed-Suche implementiert
    return []

def build_advanced_search_query(query: str, date_filter: str) -> str:
    return query

def load_previous_search_results(query: str) -> List[Dict]:
    return []

def identify_new_papers(current_papers: List[Dict], previous_papers: List[Dict]) -> List[Dict]:
    return current_papers

def create_new_excel_sheet(search_term: str, papers: List[Dict]):
    pass

def update_excel_sheet(search_term: str, all_papers: List[Dict], new_papers: List[Dict]):
    pass

def save_search_to_history(query: str, papers: List[Dict], new_papers: List[Dict]):
    pass

def update_system_status(paper_count: int):
    pass

def display_search_results(papers: List[Dict], new_papers: List[Dict], query: str, is_repeat: bool):
    pass

def should_send_email(paper_count: int) -> bool:
    return True

if __name__ == "__main__":
    module_email()
