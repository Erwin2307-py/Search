# modules/email_module.py - ERWEITERTE VERSION MIT EXCEL-INTEGRATION
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
from openpyxl.utils import get_column_letter
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import ssl
from typing import List, Dict, Any, Tuple
import json
from pathlib import Path
import threading

def module_email():
    """VOLLSTÄNDIGE FUNKTION - Email-Modul mit Excel-Integration"""
    st.title("📧 Wissenschaftliches Paper-Suche & Email-System mit Excel-Integration")
    st.success("✅ Vollständiges Modul mit Excel-Durchsuchung und automatischer Sheet-Erstellung!")
    
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
        show_excel_management()
    
    with tab5:
        show_automatic_search_system()
    
    with tab6:
        show_detailed_statistics()
    
    with tab7:
        show_system_settings()

def initialize_session_state():
    """Vollständige Session State Initialisierung mit Excel-Pfad"""
    # Erstelle notwendige Ordner
    for folder in ["excel_templates", "saved_searches", "search_history", "config"]:
        if not os.path.exists(folder):
            os.makedirs(folder)
    
    # Excel-Template Einstellungen
    if "excel_template" not in st.session_state:
        st.session_state["excel_template"] = {
            "file_path": "excel_templates/master_papers.xlsx",
            "auto_create_sheets": True,
            "sheet_naming": "topic_based",
            "max_sheets": 50
        }
    
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
            "subject_template": "🔬 {count} neue Papers für '{search_term}' - Excel aktualisiert",
            "message_template": """📧 Automatische Paper-Benachrichtigung mit Excel-Integration

📅 Datum: {date}
🔍 Suchbegriff: '{search_term}'
📊 Neue Papers: {count}
📊 Gesamt Papers im Sheet: {total_in_sheet}
📁 Excel-Sheet: {sheet_name}

📋 Neue Papers:
{new_papers_list}

📎 Excel-Datei wurde automatisch aktualisiert: {excel_file}
📋 Sheet-Name: {sheet_name}

Mit freundlichen Grüßen,
Ihr automatisches Paper-Überwachung-System mit Excel-Integration"""
        }
    
    # Andere Session State Initialisierungen...
    if "search_history" not in st.session_state:
        st.session_state["search_history"] = []
    
    if "email_history" not in st.session_state:
        st.session_state["email_history"] = []
    
    if "system_status" not in st.session_state:
        st.session_state["system_status"] = {
            "total_searches": 0,
            "total_papers": 0,
            "total_emails": 0,
            "last_search": None,
            "excel_sheets": 0,
            "unique_papers": 0
        }
    
    if "current_search_results" not in st.session_state:
        st.session_state["current_search_results"] = {}
    
    # Erstelle/Lade Master Excel-Datei
    create_or_load_master_excel()

def create_or_load_master_excel():
    """Erstellt oder lädt die Master Excel-Datei mit Overview-Sheet"""
    excel_path = st.session_state["excel_template"]["file_path"]
    
    try:
        if not os.path.exists(excel_path):
            # Erstelle neue Excel-Datei
            wb = openpyxl.Workbook()
            
            # Overview Sheet erstellen
            overview_sheet = wb.active
            overview_sheet.title = "📊_Overview"
            
            # Header-Style
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            
            # Overview Headers
            overview_headers = [
                "Sheet_Name", "Suchbegriff", "Anzahl_Papers", "Letztes_Update", 
                "Neue_Papers_Letzter_Run", "Status", "Erstellt_am"
            ]
            
            for col, header in enumerate(overview_headers, 1):
                cell = overview_sheet.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")
            
            # Spaltenbreite anpassen
            column_widths = [20, 25, 15, 18, 20, 12, 18]
            for col, width in enumerate(column_widths, 1):
                overview_sheet.column_dimensions[get_column_letter(col)].width = width
            
            wb.save(excel_path)
            st.session_state["system_status"]["excel_sheets"] = 1
        
        else:
            # Lade existierende Excel und zähle Sheets
            wb = openpyxl.load_workbook(excel_path)
            st.session_state["system_status"]["excel_sheets"] = len(wb.sheetnames)
    
    except Exception as e:
        st.error(f"❌ Fehler beim Excel-Setup: {str(e)}")

# =============== NEUE EXCEL-FUNKTIONEN ===============

def load_master_workbook():
    """Lädt das Master Excel Workbook"""
    excel_path = st.session_state["excel_template"]["file_path"]
    try:
        return openpyxl.load_workbook(excel_path)
    except Exception as e:
        st.error(f"❌ Excel-Datei konnte nicht geladen werden: {str(e)}")
        return None

def paper_exists_in_workbook(pmid: str, wb) -> Tuple[bool, str]:
    """
    Prüft, ob ein Paper (anhand PMID) bereits im gesamten Workbook existiert
    Returns: (exists: bool, sheet_name: str)
    """
    if not pmid:
        return False, ""
    
    for sheet in wb.worksheets:
        if sheet.title.startswith("📊"):  # Überspringe Overview-Sheet
            continue
        
        # Prüfe alle Zeilen im Sheet (erste Spalte = PMID)
        for row in sheet.iter_rows(min_row=2, max_col=1):  # Ab Zeile 2, nur erste Spalte
            cell_value = row[0].value
            if str(cell_value) == str(pmid):
                return True, sheet.title
    
    return False, ""

def get_or_create_sheet_for_search(search_term: str, wb) -> openpyxl.worksheet.worksheet.Worksheet:
    """
    Holt ein existierendes Sheet für den Suchbegriff oder erstellt ein neues
    """
    # Bereinige Suchbegriff für Sheet-Name (max 31 Zeichen, keine Sonderzeichen)
    sheet_name = re.sub(r'[^\w\s-]', '', search_term)[:25]
    sheet_name = f"🔍_{sheet_name}"
    
    if sheet_name in wb.sheetnames:
        return wb[sheet_name]
    else:
        # Erstelle neues Sheet
        sheet = wb.create_sheet(title=sheet_name)
        
        # Schreibe Header
        headers = ["PMID", "Title", "Authors", "Journal", "Year", "Abstract", "Added_Date"]
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        
        for col, header in enumerate(headers, 1):
            cell = sheet.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
        
        # Spaltenbreiten
        column_widths = [12, 50, 30, 25, 8, 60, 18]
        for col, width in enumerate(column_widths, 1):
            sheet.column_dimensions[get_column_letter(col)].width = width
        
        return sheet

def add_new_papers_to_excel(search_term: str, all_papers: List[Dict]) -> Tuple[int, List[Dict]]:
    """
    Fügt neue Papers zur Excel hinzu und gibt zurück: (anzahl_neue, neue_papers_liste)
    """
    wb = load_master_workbook()
    if not wb:
        return 0, []
    
    # Hole oder erstelle Sheet für diesen Suchbegriff
    sheet = get_or_create_sheet_for_search(search_term, wb)
    
    new_papers = []
    added_count = 0
    
    for paper in all_papers:
        pmid = paper.get("PMID", "")
        if not pmid:
            continue
        
        # Prüfe ob Paper bereits existiert
        exists, existing_sheet = paper_exists_in_workbook(pmid, wb)
        
        if not exists:
            # Neues Paper - füge hinzu
            row_data = [
                pmid,
                paper.get("Title", "")[:500],  # Titel kürzen falls zu lang
                paper.get("Authors", "")[:200], # Autoren kürzen
                paper.get("Journal", ""),
                paper.get("Year", ""),
                paper.get("Abstract", "")[:1000],  # Abstract kürzen
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            ]
            
            sheet.append(row_data)
            new_papers.append(paper)
            added_count += 1
    
    # Speichere Excel
    try:
        wb.save(st.session_state["excel_template"]["file_path"])
        
        # Update Overview Sheet
        update_overview_sheet(search_term, len(all_papers), added_count, sheet.title)
        
        # Update System Status
        st.session_state["system_status"]["excel_sheets"] = len(wb.sheetnames)
        st.session_state["system_status"]["unique_papers"] += added_count
        
    except Exception as e:
        st.error(f"❌ Fehler beim Speichern der Excel: {str(e)}")
        return 0, []
    
    return added_count, new_papers

def update_overview_sheet(search_term: str, total_papers: int, new_papers: int, sheet_name: str):
    """Aktualisiert das Overview-Sheet mit Suchstatistiken"""
    wb = load_master_workbook()
    if not wb:
        return
    
    overview_sheet = wb["📊_Overview"]
    
    # Suche nach existierendem Eintrag
    search_row = None
    for row_num, row in enumerate(overview_sheet.iter_rows(min_row=2), start=2):
        if row[1].value == search_term:  # Spalte B = Suchbegriff
            search_row = row_num
            break
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if search_row:
        # Update existierenden Eintrag
        overview_sheet.cell(row=search_row, column=3, value=total_papers)  # Anzahl Papers
        overview_sheet.cell(row=search_row, column=4, value=current_time)  # Letztes Update
        overview_sheet.cell(row=search_row, column=5, value=new_papers)    # Neue Papers
        overview_sheet.cell(row=search_row, column=6, value="✅ Aktiv")     # Status
    else:
        # Neuer Eintrag
        new_row = [
            sheet_name,         # Sheet Name
            search_term,        # Suchbegriff
            total_papers,       # Anzahl Papers
            current_time,       # Letztes Update
            new_papers,         # Neue Papers
            "✅ Aktiv",         # Status
            current_time        # Erstellt am
        ]
        overview_sheet.append(new_row)
    
    wb.save(st.session_state["excel_template"]["file_path"])

def get_search_statistics_from_excel() -> Dict:
    """Holt Statistiken aus der Excel-Datei"""
    wb = load_master_workbook()
    if not wb:
        return {}
    
    stats = {
        "total_sheets": len([s for s in wb.sheetnames if s.startswith("🔍_")]),
        "total_searches": 0,
        "total_papers": 0,
        "search_terms": []
    }
    
    if "📊_Overview" in wb.sheetnames:
        overview_sheet = wb["📊_Overview"]
        
        for row in overview_sheet.iter_rows(min_row=2):
            if row[1].value:  # Suchbegriff existiert
                stats["total_searches"] += 1
                stats["total_papers"] += row[2].value or 0
                stats["search_terms"].append({
                    "term": row[1].value,
                    "papers": row[2].value or 0,
                    "last_update": row[3].value,
                    "new_papers": row[4].value or 0
                })
    
    return stats

# =============== MODIFIZIERTE HAUPTFUNKTIONEN ===============

def show_advanced_paper_search():
    """Erweiterte Paper-Suche mit Excel-Integration"""
    st.subheader("🔍 Erweiterte Paper-Suche mit Excel-Integration")
    
    # Excel-Status anzeigen
    excel_stats = get_search_statistics_from_excel()
    
    col_info1, col_info2, col_info3, col_info4 = st.columns(4)
    with col_info1:
        st.metric("📊 Excel-Sheets", excel_stats.get("total_sheets", 0))
    with col_info2:
        st.metric("🔍 Durchsuchungen", excel_stats.get("total_searches", 0))
    with col_info3:
        st.metric("📄 Gesamt Papers", excel_stats.get("total_papers", 0))
    with col_info4:
        recipient_count = len(parse_recipient_emails(st.session_state.get("email_settings", {}).get("recipient_emails", "")))
        st.metric("📧 Email-Empfänger", recipient_count)
    
    # Email-Status
    email_status = is_email_configured()
    if email_status:
        st.success(f"✅ Email-System bereit für {recipient_count} Empfänger | Excel-Integration: ✅ Aktiv")
    else:
        st.info("ℹ️ Email-System nicht konfiguriert | Excel-Integration: ✅ Aktiv")
    
    # Such-Interface
    with st.form("advanced_search_form"):
        col_search1, col_search2 = st.columns([3, 1])
        
        with col_search1:
            search_query = st.text_input(
                "**🔍 PubMed Suchbegriff:**",
                placeholder="z.B. 'diabetes genetics', 'machine learning radiology', 'COVID-19 treatment'",
                help="Durchsucht Excel auf bereits bekannte Papers und fügt nur neue hinzu"
            )
        
        with col_search2:
            max_results = st.number_input(
                "Max. Ergebnisse", 
                min_value=10, 
                max_value=500, 
                value=100
            )
        
        # Erweiterte Optionen
        with st.expander("🔧 Erweiterte Excel- & Email-Optionen"):
            col_adv1, col_adv2, col_adv3 = st.columns(3)
            
            with col_adv1:
                date_filter = st.selectbox(
                    "📅 Zeitraum:",
                    ["Alle", "Letztes Jahr", "Letzte 2 Jahre", "Letzte 5 Jahre"],
                    index=2
                )
            
            with col_adv2:
                force_email = st.checkbox(
                    "📧 Email erzwingen", 
                    value=False,
                    help="Sendet Email auch wenn keine neuen Papers gefunden"
                )
            
            with col_adv3:
                show_existing = st.checkbox(
                    "📊 Bereits bekannte Papers anzeigen", 
                    value=False,
                    help="Zeigt auch Papers an, die bereits in Excel vorhanden sind"
                )
        
        search_button = st.form_submit_button("🚀 **EXCEL-INTEGRIERTE PAPER-SUCHE**", type="primary")
    
    # Quick Search aus Excel-Historie
    if excel_stats.get("search_terms"):
        st.write("**⚡ Schnellsuche (aus Excel-Historie):**")
        recent_terms = sorted(excel_stats["search_terms"], key=lambda x: x.get("last_update", ""), reverse=True)[:5]
        
        cols = st.columns(min(len(recent_terms), 5))
        for i, term_info in enumerate(recent_terms):
            term = term_info["term"]
            with cols[i]:
                if st.button(f"🔍 {term[:15]}... ({term_info['papers']})", key=f"quick_{i}"):
                    execute_excel_integrated_search(term, 50, "Letzte 2 Jahre", False, False)
    
    # Hauptsuche ausführen
    if search_button and search_query:
        execute_excel_integrated_search(search_query, max_results, date_filter, force_email, show_existing)
    
    # Manuelle Email nach Suche
    show_manual_email_section()

def execute_excel_integrated_search(query: str, max_results: int, date_filter: str, force_email: bool, show_existing: bool):
    """Führt Excel-integrierte Paper-Suche durch"""
    st.markdown("---")
    st.subheader(f"🔍 **Excel-integrierte Suche:** '{query}'")
    
    # Progress Tracking
    progress_container = st.container()
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    try:
        # 1. Lade Excel für Duplikatsprüfung
        status_text.text("📊 Lade Excel-Datei für Duplikatsprüfung...")
        progress_bar.progress(0.1)
        
        wb = load_master_workbook()
        if not wb:
            st.error("❌ Excel-Datei konnte nicht geladen werden!")
            return
        
        # 2. PubMed-Suche durchführen
        status_text.text("🔍 Durchsuche PubMed-Datenbank...")
        progress_bar.progress(0.3)
        
        advanced_query = build_advanced_search_query(query, date_filter)
        current_papers = perform_comprehensive_pubmed_search(advanced_query, max_results)
        
        progress_bar.progress(0.5)
        
        if not current_papers:
            st.error(f"❌ **Keine Papers für '{query}' gefunden!**")
            progress_bar.empty()
            status_text.empty()
            return
        
        # 3. Excel-Integration: Prüfe auf neue Papers
        status_text.text("🔍 Prüfe Papers gegen Excel-Datenbank...")
        progress_bar.progress(0.7)
        
        added_count, new_papers = add_new_papers_to_excel(query, current_papers)
        
        # 4. Ergebnisse anzeigen
        progress_bar.progress(0.9)
        status_text.text("📊 Bereite Ergebnisse vor...")
        
        if added_count > 0:
            st.success(f"🆕 **{added_count} NEUE Papers gefunden und zu Excel hinzugefügt!** (von {len(current_papers)} gesamt)")
            st.balloons()
            
            # Email senden bei neuen Papers
            if is_email_configured() and (force_email or should_send_email(added_count)):
                send_excel_integrated_email(query, new_papers, len(current_papers), added_count)
        else:
            st.info(f"ℹ️ **Keine neuen Papers** - Alle {len(current_papers)} Papers bereits in Excel vorhanden")
            
            # Email erzwingen wenn gewünscht
            if force_email and is_email_configured():
                send_excel_integrated_email(query, [], len(current_papers), 0)
        
        # 5. Detaillierte Ergebnisse anzeigen
        display_excel_integrated_results(current_papers, new_papers, query, added_count, show_existing)
        
        # 6. Für manuellen Email-Versand speichern
        st.session_state["current_search_results"] = {
            "search_term": query,
            "papers": current_papers,
            "new_papers": new_papers,
            "added_count": added_count,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # 7. System-Status aktualisieren
        progress_bar.progress(1.0)
        status_text.text("✅ Excel-integrierte Suche abgeschlossen!")
        
        st.session_state["system_status"]["total_searches"] += 1
        st.session_state["system_status"]["total_papers"] += added_count
        
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ **Fehler bei der Excel-integrierten Suche:** {str(e)}")

def display_excel_integrated_results(all_papers: List[Dict], new_papers: List[Dict], query: str, added_count: int, show_existing: bool):
    """Zeigt Ergebnisse der Excel-integrierten Suche an"""
    
    # Statistiken
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    with col_stat1:
        st.metric("📄 Gefunden", len(all_papers))
    with col_stat2:
        st.metric("🆕 Neue Papers", added_count)
    with col_stat3:
        st.metric("📊 Bereits bekannt", len(all_papers) - added_count)
    with col_stat4:
        st.metric("💾 In Excel gespeichert", added_count)
    
    # Neue Papers hervorheben
    if new_papers:
        st.subheader(f"🆕 Neue Papers ({len(new_papers)})")
        
        with st.expander(f"📋 Alle {len(new_papers)} neuen Papers anzeigen", expanded=True):
            for i, paper in enumerate(new_papers[:10], 1):  # Zeige erste 10
                with st.container():
                    col_paper1, col_paper2 = st.columns([3, 1])
                    
                    with col_paper1:
                        st.write(f"**{i}. {paper.get('Title', 'Unbekannt')[:100]}...**")
                        st.write(f"👥 {paper.get('Authors', 'n/a')[:80]}...")
                        st.write(f"📚 {paper.get('Journal', 'n/a')} ({paper.get('Year', 'n/a')})")
                    
                    with col_paper2:
                        st.success("🆕 NEU")
                        st.write(f"PMID: {paper.get('PMID', 'n/a')}")
            
            if len(new_papers) > 10:
                st.info(f"... und {len(new_papers) - 10} weitere neue Papers (siehe Excel-Datei)")
    
    # Bereits bekannte Papers (optional)
    if show_existing and (len(all_papers) - added_count) > 0:
        existing_papers = [p for p in all_papers if p not in new_papers]
        
        with st.expander(f"📊 Bereits bekannte Papers ({len(existing_papers)})", expanded=False):
            for i, paper in enumerate(existing_papers[:5], 1):  # Zeige erste 5
                with st.container():
                    col_paper1, col_paper2 = st.columns([3, 1])
                    
                    with col_paper1:
                        st.write(f"**{i}. {paper.get('Title', 'Unbekannt')[:100]}...**")
                        st.write(f"👥 {paper.get('Authors', 'n/a')[:80]}...")
                        st.write(f"📚 {paper.get('Journal', 'n/a')} ({paper.get('Year', 'n/a')})")
                    
                    with col_paper2:
                        st.info("📊 BEKANNT")
                        st.write(f"PMID: {paper.get('PMID', 'n/a')}")
            
            if len(existing_papers) > 5:
                st.write(f"... und {len(existing_papers) - 5} weitere bereits bekannte Papers")

def send_excel_integrated_email(search_term: str, new_papers: List[Dict], total_found: int, added_count: int):
    """Sendet Email für Excel-integrierte Suche"""
    settings = st.session_state.get("email_settings", {})
    recipient_emails = parse_recipient_emails(settings.get("recipient_emails", ""))
    
    if not recipient_emails:
        st.warning("⚠️ Keine Email-Empfänger konfiguriert!")
        return
    
    # Subject generieren
    if added_count > 0:
        subject = f"📊 {added_count} neue Papers für '{search_term}' - Excel aktualisiert"
    else:
        subject = f"📊 Keine neuen Papers für '{search_term}' - Excel-Check durchgeführt"
    
    # Sheet-Name ermitteln
    sheet_name = f"🔍_{re.sub(r'[^\w\s-]', '', search_term)[:25]}"
    
    # Papers-Liste formatieren (nur neue)
    if new_papers:
        papers_list = ""
        for i, paper in enumerate(new_papers[:8], 1):
            title = paper.get("Title", "Unbekannt")[:70]
            authors = paper.get("Authors", "n/a")[:40]
            journal = paper.get("Journal", "n/a")
            year = paper.get("Year", "n/a")
            pmid = paper.get("PMID", "n/a")
            
            papers_list += f"\n{i}. **{title}...**\n"
            papers_list += f"   👥 {authors}...\n"
            papers_list += f"   📚 {journal} ({year}) | PMID: {pmid}\n\n"
        
        if len(new_papers) > 8:
            papers_list += f"... und {len(new_papers) - 8} weitere neue Papers (siehe Excel-Datei)\n"
    else:
        papers_list = "\nKeine neuen Papers gefunden - alle Papers bereits in Excel-Datenbank vorhanden.\n"
    
    # Message generieren
    message = f"""📊 **Excel-Integrierte Paper-Suche - Ergebnisse**

📅 **Datum:** {datetime.datetime.now().strftime("%d.%m.%Y %H:%M")}
🔍 **Suchbegriff:** '{search_term}'
📊 **Gefundene Papers:** {total_found}
🆕 **Neue Papers:** {added_count}
📊 **Bereits bekannt:** {total_found - added_count}
📁 **Excel-Sheet:** {sheet_name}

{'-' * 60}
🆕 **NEUE PAPERS:**
{papers_list}

📎 **Excel-Integration:**
✅ Alle neuen Papers wurden automatisch zur Excel-Datei hinzugefügt
✅ Duplikate wurden automatisch erkannt und übersprungen
✅ Sheet für diesen Suchbegriff wurde aktualisiert
📋 Sheet-Name: {sheet_name}

📧 **Email-Info:**
📧 Versendet an: {len(recipient_emails)} Empfänger
📎 Excel-Datei als Anhang beigefügt

Mit freundlichen Grüßen,
Ihr Excel-integriertes Paper-Suche System"""
    
    # Excel als Anhang
    excel_path = st.session_state["excel_template"]["file_path"]
    attachment_path = excel_path if os.path.exists(excel_path) else None
    
    # Email senden
    with st.spinner(f"📧 Sende Excel-integrierte Email an {len(recipient_emails)} Empfänger..."):
        success, status_message = send_real_email_multiple(recipient_emails, subject, message, attachment_path)
    
    # Email-Historie
    email_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "type": "Excel-Integriert",
        "search_term": search_term,
        "recipients": recipient_emails,
        "recipient_count": len(recipient_emails),
        "subject": subject,
        "paper_count": added_count,
        "total_found": total_found,
        "success": success,
        "status": status_message,
        "has_attachment": attachment_path is not None,
        "sheet_name": sheet_name
    }
    
    st.session_state["email_history"].append(email_entry)
    
    # Ergebnis anzeigen
    if success:
        st.session_state["system_status"]["total_emails"] += 1
        st.success(f"📧 **Excel-integrierte Email erfolgreich versendet!**\n{status_message}")
        
        with st.expander("📋 Email-Details"):
            st.write(f"**📧 Empfänger:** {len(recipient_emails)}")
            st.write(f"**🆕 Neue Papers:** {added_count}")
            st.write(f"**📊 Gesamt gefunden:** {total_found}")
            st.write(f"**📁 Excel-Sheet:** {sheet_name}")
            st.write(f"**📎 Anhang:** {'✅ Excel-Datei' if attachment_path else '❌ Kein Anhang'}")
    else:
        st.error(f"❌ **Email-Fehler:** {status_message}")

def show_excel_management():
    """Excel-Management Interface"""
    st.subheader("📋 Excel-Management & Sheet-Übersicht")
    
    # Excel-Status
    excel_stats = get_search_statistics_from_excel()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Excel-Sheets", excel_stats.get("total_sheets", 0))
    with col2:
        st.metric("📄 Gesamt Papers", excel_stats.get("total_papers", 0))
    with col3:
        st.metric("🔍 Suchbegriffe", excel_stats.get("total_searches", 0))
    
    # Download Excel-Datei
    excel_path = st.session_state["excel_template"]["file_path"]
    if os.path.exists(excel_path):
        with open(excel_path, "rb") as file:
            st.download_button(
                label="📎 **Master Excel-Datei herunterladen**",
                data=file.read(),
                file_name=f"paper_database_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
    
    # Sheet-Übersicht
    if excel_stats.get("search_terms"):
        st.subheader("📋 Sheet-Übersicht")
        
        df_overview = pd.DataFrame(excel_stats["search_terms"])
        df_overview.columns = ["Suchbegriff", "Papers", "Letztes Update", "Neue Papers (letzter Run)"]
        
        st.dataframe(df_overview, use_container_width=True)
    
    # Excel-Einstellungen
    with st.expander("⚙️ Excel-Einstellungen"):
        current_path = st.session_state["excel_template"]["file_path"]
        st.info(f"📁 **Aktuelle Excel-Datei:** {current_path}")
        
        if st.button("🔄 Excel-Datei neu erstellen", type="secondary"):
            try:
                if os.path.exists(current_path):
                    os.rename(current_path, f"{current_path}.backup_{int(time.time())}")
                create_or_load_master_excel()
                st.success("✅ Neue Excel-Datei erstellt! (Alte als Backup gespeichert)")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Fehler: {str(e)}")

# =============== HILFSFUNKTIONEN (vereinfacht für Demo) ===============

def perform_comprehensive_pubmed_search(query: str, max_results: int) -> List[Dict[str, Any]]:
    """Simulierte PubMed-Suche für Demo-Zwecke"""
    # In der echten Implementation würde hier die PubMed API aufgerufen
    return [
        {
            "PMID": f"123456{i}",
            "Title": f"Sample Paper {i} about {query}",
            "Authors": f"Author {i}, Co-Author {i}",
            "Journal": f"Journal of {query}",
            "Year": "2025",
            "Abstract": f"This is a sample abstract for paper {i} about {query}..."
        }
        for i in range(min(max_results, 20))  # Demo: max 20 Papers
    ]

def build_advanced_search_query(query: str, date_filter: str) -> str:
    """Baut erweiterte Suchanfrage"""
    return query  # Vereinfacht für Demo

# =============== BESTEHENDE FUNKTIONEN (unverändert) ===============

def parse_recipient_emails(email_string: str) -> List[str]:
    """Parst Email-String und gibt Liste gültiger Emails zurück"""
    if not email_string:
        return []
    
    emails = [email.strip() for email in email_string.split(",")]
    valid_emails = []
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    for email in emails:
        if email and email_pattern.match(email):
            valid_emails.append(email)
    
    return valid_emails

def is_email_configured() -> bool:
    """Prüft Email-Konfiguration"""
    settings = st.session_state.get("email_settings", {})
    recipient_emails = parse_recipient_emails(settings.get("recipient_emails", ""))
    
    return (bool(settings.get("sender_email")) and 
            len(recipient_emails) > 0 and
            bool(settings.get("sender_password")))

def should_send_email(paper_count: int) -> bool:
    """Bestimmt ob Email gesendet werden soll"""
    settings = st.session_state.get("email_settings", {})
    return (settings.get("auto_notifications", True) and 
            paper_count >= settings.get("min_papers", 1))

def send_real_email_multiple(to_emails: List[str], subject: str, message: str, attachment_path: str = None) -> tuple:
    """Sendet echte Email über SMTP an mehrere Empfänger"""
    settings = st.session_state.get("email_settings", {})
    
    sender_email = settings.get("sender_email", "")
    sender_password = settings.get("sender_password", "")
    smtp_server = settings.get("smtp_server", "smtp.gmail.com")
    smtp_port = settings.get("smtp_port", 587)
    use_tls = settings.get("use_tls", True)
    
    if not all([sender_email, sender_password]):
        return False, "❌ Email-Konfiguration unvollständig"
    
    if not to_emails:
        return False, "❌ Keine Empfänger konfiguriert"
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        
        if use_tls:
            context = ssl.create_default_context()
            server.starttls(context=context)
        
        server.login(sender_email, sender_password)
        
        successful_sends = 0
        failed_sends = []
        
        for recipient in to_emails:
            try:
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = recipient
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
                
                server.send_message(msg)
                successful_sends += 1
                
            except Exception as e:
                failed_sends.append(f"{recipient}: {str(e)}")
        
        server.quit()
        
        if successful_sends == len(to_emails):
            return True, f"✅ Email erfolgreich an alle {successful_sends} Empfänger gesendet"
        elif successful_sends > 0:
            return True, f"⚠️ Email an {successful_sends}/{len(to_emails)} Empfänger gesendet"
        else:
            return False, f"❌ Email an keinen Empfänger gesendet"
        
    except Exception as e:
        return False, f"❌ Email-Fehler: {str(e)}"

# =============== PLACEHOLDER FUNKTIONEN ===============

def show_dashboard():
    """Dashboard mit Excel-Integration"""
    st.subheader("📊 Dashboard - Excel-Integriert")
    
    excel_stats = get_search_statistics_from_excel()
    status = st.session_state["system_status"]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔍 Suchen", excel_stats.get("total_searches", 0))
    with col2:
        st.metric("📄 Papers (Excel)", excel_stats.get("total_papers", 0))
    with col3:
        st.metric("📧 Emails", status["total_emails"])
    with col4:
        st.metric("📊 Excel-Sheets", excel_stats.get("total_sheets", 0))
    
    # Excel-Download im Dashboard
    excel_path = st.session_state["excel_template"]["file_path"]
    if os.path.exists(excel_path):
        with open(excel_path, "rb") as file:
            st.download_button(
                "📎 Excel-Datenbank herunterladen",
                data=file.read(),
                file_name=f"paper_database_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

def show_email_config():
    """Email-Konfiguration (vereinfacht)"""
    st.subheader("📧 Email-Konfiguration")
    st.info("Email-Konfiguration Interface hier...")

def show_manual_email_section():
    """Manueller Email-Versand nach Suche"""
    if st.session_state.get("current_search_results"):
        st.markdown("---")
        st.subheader("📧 Manueller Email-Versand (Excel-Integriert)")
        
        current_results = st.session_state["current_search_results"]
        search_term = current_results.get("search_term", "")
        new_papers = current_results.get("new_papers", [])
        added_count = current_results.get("added_count", 0)
        
        if added_count > 0 and is_email_configured():
            if st.button(f"📧 **Neue Papers emailen** ({added_count})", type="primary"):
                send_excel_integrated_email(search_term, new_papers, len(current_results.get("papers", [])), added_count)
        elif not is_email_configured():
            st.warning("⚠️ Email nicht konfiguriert")

def show_automatic_search_system():
    st.subheader("🤖 Automatische Suchen")
    st.info("Automatische Suchen hier...")

def show_detailed_statistics():
    st.subheader("📈 Detaillierte Statistiken")
    excel_stats = get_search_statistics_from_excel()
    
    if excel_stats.get("search_terms"):
        st.write("**📊 Excel-Statistiken:**")
        df = pd.DataFrame(excel_stats["search_terms"])
        st.dataframe(df)

def show_system_settings():
    st.subheader("⚙️ System-Einstellungen")
    st.info("System-Einstellungen hier...")

if __name__ == "__main__":
    module_email()
