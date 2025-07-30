# Zusätzliche Imports für das neue Modul (füge diese zu den bestehenden Imports hinzu)
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from email.mime.base import MimeBase
from email import encoders
import hashlib
from datetime import datetime, timedelta

# ------------------------------------------------------------------
# Neues Modul: Automated Paper Search & Management
# ------------------------------------------------------------------

def page_automated_paper_search():
    st.title("🔍 Automated Paper Search & Management")
    st.write("Automatische Suche und Verwaltung von wissenschaftlichen Papern basierend auf Codewörtern")
    
    # Initialize session state variables
    if "codewords_db" not in st.session_state:
        st.session_state["codewords_db"] = {}
    if "search_history" not in st.session_state:
        st.session_state["search_history"] = []
    if "excel_file_path" not in st.session_state:
        st.session_state["excel_file_path"] = "automated_papers.xlsx"
    
    # Sidebar settings
    with st.sidebar:
        st.header("⚙️ Einstellungen")
        
        # Email settings
        st.subheader("📧 Email-Benachrichtigung")
        email_enabled = st.checkbox("Email-Benachrichtigung aktivieren")
        if email_enabled:
            sender_email = st.text_input("Absender Email", value=st.secrets.get("sender_email", ""))
            sender_password = st.text_input("App Password", type="password", value=st.secrets.get("sender_password", ""))
            recipient_email = st.text_input("Empfänger Email", value=st.secrets.get("recipient_email", ""))
            smtp_server = st.text_input("SMTP Server", value="smtp.gmail.com")
            smtp_port = st.number_input("SMTP Port", value=587)
        
        # Search settings
        st.subheader("🔍 Such-Einstellungen")
        max_results_per_source = st.number_input("Max. Ergebnisse pro Quelle", min_value=10, max_value=500, value=100)
        search_sources = st.multiselect(
            "Suchquellen auswählen",
            ["PubMed", "Europe PMC", "Semantic Scholar", "Google Scholar", "CORE"],
            default=["PubMed", "Europe PMC"]
        )
        
        # Auto-search settings
        st.subheader("⏰ Automatische Suche")
        auto_search_enabled = st.checkbox("Automatische Suche aktivieren")
        if auto_search_enabled:
            search_interval_hours = st.number_input("Suchintervall (Stunden)", min_value=1, max_value=168, value=24)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📝 Codewort-Verwaltung")
        
        # Display existing codewords
        if st.session_state["codewords_db"]:
            st.subheader("Bestehende Codewörter:")
            for i, (codeword, info) in enumerate(st.session_state["codewords_db"].items()):
                col_cw1, col_cw2, col_cw3 = st.columns([3, 2, 1])
                with col_cw1:
                    st.write(f"**{codeword}**")
                with col_cw2:
                    st.write(f"Papers: {info.get('paper_count', 0)}")
                with col_cw3:
                    if st.button("🗑️", key=f"delete_{i}", help="Codewort löschen"):
                        del st.session_state["codewords_db"][codeword]
                        st.rerun()
        else:
            st.info("Noch keine Codewörter angelegt. Erstellen Sie welche unten.")
        
        # Add new codeword
        st.subheader("Neues Codewort hinzufügen:")
        col_new1, col_new2 = st.columns([3, 1])
        with col_new1:
            new_codeword = st.text_input("Codewort eingeben", placeholder="z.B. 'diabetes genetics'")
        with col_new2:
            if st.button("➕ Hinzufügen"):
                if new_codeword and new_codeword not in st.session_state["codewords_db"]:
                    st.session_state["codewords_db"][new_codeword] = {
                        "created": datetime.now().isoformat(),
                        "paper_count": 0,
                        "last_search": None
                    }
                    st.success(f"Codewort '{new_codeword}' hinzugefügt!")
                    st.rerun()
                elif new_codeword in st.session_state["codewords_db"]:
                    st.error("Codewort existiert bereits!")
    
    with col2:
        st.header("📊 Statistiken")
        st.metric("Codewörter", len(st.session_state["codewords_db"]))
        total_papers = sum(info.get('paper_count', 0) for info in st.session_state["codewords_db"].values())
        st.metric("Gesamt Papers", total_papers)
        st.metric("Letzte Suche", st.session_state.get("last_global_search", "Nie"))
    
    st.markdown("---")
    
    # Search buttons
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
    
    with col_btn1:
        if st.button("🔍 Erste Suche starten", help="Führt eine initiale Suche für alle Codewörter durch"):
            if not st.session_state["codewords_db"]:
                st.error("Bitte fügen Sie zuerst Codewörter hinzu!")
            else:
                perform_initial_search(search_sources, max_results_per_source)
    
    with col_btn2:
        if st.button("🔄 Nach neuen Papers suchen", help="Sucht nach neuen Papers basierend auf bestehender Excel"):
            if not st.session_state["codewords_db"]:
                st.error("Bitte fügen Sie zuerst Codewörter hinzu!")
            else:
                search_for_new_papers(search_sources, max_results_per_source, email_enabled, 
                                    sender_email if email_enabled else None,
                                    sender_password if email_enabled else None,
                                    recipient_email if email_enabled else None,
                                    smtp_server if email_enabled else None,
                                    smtp_port if email_enabled else None)
    
    with col_btn3:
        if st.button("📥 Excel herunterladen"):
            download_excel_file()
    
    with col_btn4:
        if st.button("📤 Excel hochladen", help="Bestehende Excel-Datei hochladen"):
            upload_excel_file()
    
    # File upload for existing Excel
    uploaded_excel = st.file_uploader("Bestehende Excel-Datei hochladen", type=['xlsx'], key="excel_upload")
    if uploaded_excel:
        load_existing_excel(uploaded_excel)
    
    # Display recent search history
    if st.session_state["search_history"]:
        st.markdown("---")
        st.header("📈 Such-Verlauf")
        history_df = pd.DataFrame(st.session_state["search_history"])
        st.dataframe(history_df, use_container_width=True)

def perform_initial_search(search_sources, max_results_per_source):
    """Führt die erste Suche für alle Codewörter durch"""
    with st.spinner("Führe initiale Suche durch..."):
        all_results = {}
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        codewords = list(st.session_state["codewords_db"].keys())
        total_codewords = len(codewords)
        
        for idx, codeword in enumerate(codewords):
            status_text.text(f"Suche für Codewort: {codeword}")
            progress_bar.progress((idx + 1) / total_codewords)
            
            results = search_all_sources(codeword, search_sources, max_results_per_source)
            all_results[codeword] = results
            
            # Update codeword info
            st.session_state["codewords_db"][codeword]["paper_count"] = len(results)
            st.session_state["codewords_db"][codeword]["last_search"] = datetime.now().isoformat()
        
        # Create Excel file
        create_excel_with_results(all_results)
        
        # Update search history
        st.session_state["search_history"].append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "Initial Search",
            "codewords": len(codewords),
            "total_papers": sum(len(results) for results in all_results.values())
        })
        
        st.session_state["last_global_search"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        progress_bar.empty()
        status_text.empty()
        st.success(f"Initiale Suche abgeschlossen! {sum(len(results) for results in all_results.values())} Papers gefunden.")

def search_for_new_papers(search_sources, max_results_per_source, email_enabled, sender_email, sender_password, recipient_email, smtp_server, smtp_port):
    """Sucht nach neuen Papers und vergleicht mit bestehender Excel"""
    with st.spinner("Suche nach neuen Papers..."):
        try:
            # Load existing Excel
            existing_papers = load_papers_from_excel()
            
            new_papers = {}
            total_new = 0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            codewords = list(st.session_state["codewords_db"].keys())
            total_codewords = len(codewords)
            
            for idx, codeword in enumerate(codewords):
                status_text.text(f"Suche neue Papers für: {codeword}")
                progress_bar.progress((idx + 1) / total_codewords)
                
                # Search for papers
                current_results = search_all_sources(codeword, search_sources, max_results_per_source)
                
                # Filter out existing papers
                existing_for_codeword = existing_papers.get(codeword, [])
                existing_titles = set(paper.get('Title', '').lower() for paper in existing_for_codeword)
                
                new_for_codeword = []
                for paper in current_results:
                    if paper.get('Title', '').lower() not in existing_titles:
                        new_for_codeword.append(paper)
                
                if new_for_codeword:
                    new_papers[codeword] = new_for_codeword
                    total_new += len(new_for_codeword)
                
                # Update codeword info
                st.session_state["codewords_db"][codeword]["last_search"] = datetime.now().isoformat()
            
            progress_bar.empty()
            status_text.empty()
            
            if new_papers:
                # Add new papers to Excel
                add_new_papers_to_excel(new_papers)
                
                # Send email notification if enabled
                if email_enabled and sender_email and recipient_email:
                    send_email_notification(new_papers, total_new, sender_email, sender_password, 
                                          recipient_email, smtp_server, smtp_port)
                
                # Update search history
                st.session_state["search_history"].append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "New Papers Search",
                    "codewords": len([cw for cw in new_papers.keys()]),
                    "total_papers": total_new
                })
                
                st.success(f"🎉 {total_new} neue Papers gefunden und zur Excel hinzugefügt!")
                
                # Show summary
                st.subheader("Neue Papers Zusammenfassung:")
                for codeword, papers in new_papers.items():
                    st.write(f"**{codeword}**: {len(papers)} neue Papers")
                
            else:
                st.info("Keine neuen Papers gefunden.")
                
        except Exception as e:
            st.error(f"Fehler bei der Suche: {str(e)}")

def search_all_sources(query, sources, max_results):
    """Sucht in allen ausgewählten Quellen"""
    all_results = []
    
    try:
        if "PubMed" in sources:
            pubmed_results = search_pubmed_simple(query)
            for result in pubmed_results[:max_results]:
                result["Source"] = "PubMed"
                # Fetch abstract
                if result.get("PMID") != "n/a":
                    abstract = fetch_pubmed_abstract(result["PMID"])
                    result["Abstract"] = abstract
                all_results.append(result)
        
        if "Europe PMC" in sources:
            epmc_results = search_europe_pmc_simple(query)
            for result in epmc_results[:max_results]:
                result["Source"] = "Europe PMC"
                all_results.append(result)
        
        if "Semantic Scholar" in sources:
            semantic_search = SemanticScholarSearch()
            semantic_search.search_semantic_scholar(query)
            for result in semantic_search.all_results[:max_results]:
                all_results.append(result)
        
        if "Google Scholar" in sources:
            scholar_search = GoogleScholarSearch()
            scholar_search.search_google_scholar(query)
            for result in scholar_search.all_results[:max_results]:
                all_results.append(result)
        
        if "CORE" in sources:
            core_results = search_core_aggregate(query)
            for result in core_results[:max_results]:
                result["Source"] = "CORE"
                all_results.append(result)
    
    except Exception as e:
        st.error(f"Fehler bei der Suche in Quellen: {str(e)}")
    
    return all_results

def create_excel_with_results(all_results):
    """Erstellt eine neue Excel-Datei mit den Suchergebnissen"""
    try:
        wb = openpyxl.Workbook()
        
        # Remove default sheet
        if "Sheet" in wb.sheetnames:
            wb.remove(wb["Sheet"])
        
        # Create overview sheet
        overview_sheet = wb.create_sheet("Übersicht")
        overview_headers = ["Codewort", "Anzahl Papers", "Letzte Suche", "Sheet Name"]
        overview_sheet.append(overview_headers)
        
        for codeword, results in all_results.items():
            # Create sheet for each codeword
            safe_sheet_name = create_safe_sheet_name(codeword)
            sheet = wb.create_sheet(safe_sheet_name)
            
            # Headers
            headers = ["Title", "Authors", "Year", "Journal", "Source", "PMID", "DOI", "Abstract", "URL"]
            sheet.append(headers)
            
            # Add papers
            for result in results:
                row = [
                    result.get("Title", ""),
                    result.get("Authors/Description", ""),
                    result.get("Year", ""),
                    result.get("Journal", ""),
                    result.get("Source", ""),
                    result.get("PMID", ""),
                    result.get("DOI", ""),
                    result.get("Abstract", ""),
                    result.get("URL", "")
                ]
                sheet.append(row)
            
            # Add to overview
            overview_sheet.append([
                codeword,
                len(results),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                safe_sheet_name
            ])
        
        # Save file
        file_path = st.session_state["excel_file_path"]
        wb.save(file_path)
        
        # Store in session state for download
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        st.session_state["excel_buffer"] = buffer.getvalue()
        
    except Exception as e:
        st.error(f"Fehler beim Erstellen der Excel-Datei: {str(e)}")

def create_safe_sheet_name(name):
    """Erstellt einen sicheren Sheet-Namen"""
    # Remove invalid characters
    invalid_chars = [':', '\\', '/', '?', '*', '[', ']']
    safe_name = name
    for char in invalid_chars:
        safe_name = safe_name.replace(char, '_')
    
    # Limit length
    if len(safe_name) > 31:
        safe_name = safe_name[:31]
    
    return safe_name

def load_papers_from_excel():
    """Lädt bestehende Papers aus Excel-Datei"""
    existing_papers = {}
    
    try:
        if os.path.exists(st.session_state["excel_file_path"]):
            wb = openpyxl.load_workbook(st.session_state["excel_file_path"])
            
            for sheet_name in wb.sheetnames:
                if sheet_name == "Übersicht":
                    continue
                
                # Find corresponding codeword
                codeword = None
                for cw in st.session_state["codewords_db"].keys():
                    if create_safe_sheet_name(cw) == sheet_name:
                        codeword = cw
                        break
                
                if not codeword:
                    continue
                
                sheet = wb[sheet_name]
                papers = []
                
                # Skip header row
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    if row[0]:  # If title exists
                        paper = {
                            "Title": row[0] or "",
                            "Authors/Description": row[1] or "",
                            "Year": row[2] or "",
                            "Journal": row[3] or "",
                            "Source": row[4] or "",
                            "PMID": row[5] or "",
                            "DOI": row[6] or "",
                            "Abstract": row[7] or "",
                            "URL": row[8] or ""
                        }
                        papers.append(paper)
                
                existing_papers[codeword] = papers
    
    except Exception as e:
        st.error(f"Fehler beim Laden der Excel-Datei: {str(e)}")
    
    return existing_papers

def add_new_papers_to_excel(new_papers):
    """Fügt neue Papers zur bestehenden Excel hinzu"""
    try:
        if os.path.exists(st.session_state["excel_file_path"]):
            wb = openpyxl.load_workbook(st.session_state["excel_file_path"])
        else:
            wb = openpyxl.Workbook()
            if "Sheet" in wb.sheetnames:
                wb.remove(wb["Sheet"])
        
        for codeword, papers in new_papers.items():
            safe_sheet_name = create_safe_sheet_name(codeword)
            
            if safe_sheet_name in wb.sheetnames:
                sheet = wb[safe_sheet_name]
            else:
                sheet = wb.create_sheet(safe_sheet_name)
                headers = ["Title", "Authors", "Year", "Journal", "Source", "PMID", "DOI", "Abstract", "URL"]
                sheet.append(headers)
            
            # Add new papers
            for result in papers:
                row = [
                    result.get("Title", ""),
                    result.get("Authors/Description", ""),
                    result.get("Year", ""),
                    result.get("Journal", ""),
                    result.get("Source", ""),
                    result.get("PMID", ""),
                    result.get("DOI", ""),
                    result.get("Abstract", ""),
                    result.get("URL", "")
                ]
                sheet.append(row)
        
        # Update overview sheet
        update_overview_sheet(wb)
        
        # Save file
        wb.save(st.session_state["excel_file_path"])
        
        # Update buffer for download
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        st.session_state["excel_buffer"] = buffer.getvalue()
        
    except Exception as e:
        st.error(f"Fehler beim Hinzufügen neuer Papers: {str(e)}")

def update_overview_sheet(wb):
    """Aktualisiert das Übersichts-Sheet"""
    try:
        if "Übersicht" in wb.sheetnames:
            wb.remove(wb["Übersicht"])
        
        overview_sheet = wb.create_sheet("Übersicht", 0)  # Insert at beginning
        overview_headers = ["Codewort", "Anzahl Papers", "Letzte Suche", "Sheet Name"]
        overview_sheet.append(overview_headers)
        
        for codeword in st.session_state["codewords_db"].keys():
            safe_sheet_name = create_safe_sheet_name(codeword)
            
            if safe_sheet_name in wb.sheetnames:
                sheet = wb[safe_sheet_name]
                paper_count = sheet.max_row - 1  # Exclude header
                
                overview_sheet.append([
                    codeword,
                    paper_count,
                    st.session_state["codewords_db"][codeword].get("last_search", ""),
                    safe_sheet_name
                ])
                
                # Update paper count in codewords_db
                st.session_state["codewords_db"][codeword]["paper_count"] = paper_count
    
    except Exception as e:
        st.error(f"Fehler beim Aktualisieren der Übersicht: {str(e)}")

def send_email_notification(new_papers, total_new, sender_email, sender_password, recipient_email, smtp_server, smtp_port):
    """Sendet Email-Benachrichtigung über neue Papers"""
    try:
        msg = MimeMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"📚 {total_new} neue wissenschaftliche Papers gefunden!"
        
        body = f"""
        <html>
        <body>
        <h2>Neue Papers gefunden!</h2>
        <p>Die automatische Suche hat <strong>{total_new}</strong> neue wissenschaftliche Papers gefunden.</p>
        
        <h3>Zusammenfassung nach Codewörtern:</h3>
        <ul>
        """
        
        for codeword, papers in new_papers.items():
            body += f"<li><strong>{codeword}</strong>: {len(papers)} neue Papers</li>"
        
        body += f"""
        </ul>
        
        <p>Die Papers wurden automatisch zur Excel-Datei hinzugefügt.</p>
        <p><em>Zeitstempel: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
        </body>
        </html>
        """
        
        msg.attach(MimeText(body, 'html'))
        
        # Attach Excel file if available
        if "excel_buffer" in st.session_state:
            attachment = MimeBase('application', 'octet-stream')
            attachment.set_payload(st.session_state["excel_buffer"])
            encoders.encode_base64(attachment)
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename= "automated_papers_{datetime.now().strftime("%Y%m%d")}.xlsx"'
            )
            msg.attach(attachment)
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        
        st.success("📧 Email-Benachrichtigung gesendet!")
        
    except Exception as e:
        st.error(f"Fehler beim Senden der Email: {str(e)}")

def download_excel_file():
    """Ermöglicht Download der Excel-Datei"""
    if "excel_buffer" in st.session_state:
        st.download_button(
            label="📥 Excel-Datei herunterladen",
            data=st.session_state["excel_buffer"],
            file_name=f"automated_papers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("Keine Excel-Datei zum Download verfügbar. Führen Sie zuerst eine Suche durch.")

def upload_excel_file():
    """Placeholder für Excel-Upload"""
    st.info("Excel-Upload-Funktionalität wird über den File-Uploader oben bereitgestellt.")

def load_existing_excel(uploaded_file):
    """Lädt eine hochgeladene Excel-Datei"""
    try:
        wb = openpyxl.load_workbook(uploaded_file)
        
        # Extract codewords from sheet names and overview
        if "Übersicht" in wb.sheetnames:
            overview_sheet = wb["Übersicht"]
            for row in overview_sheet.iter_rows(min_row=2, values_only=True):
                if row[0]:  # Codeword exists
                    codeword = row[0]
                    if codeword not in st.session_state["codewords_db"]:
                        st.session_state["codewords_db"][codeword] = {
                            "created": datetime.now().isoformat(),
                            "paper_count": row[1] or 0,
                            "last_search": row[2] or None
                        }
        
        # Save uploaded file
        wb.save(st.session_state["excel_file_path"])
        
        # Update buffer
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        st.session_state["excel_buffer"] = buffer.getvalue()
        
        st.success("Excel-Datei erfolgreich hochgeladen und geladen!")
        st.rerun()
        
    except Exception as e:
        st.error(f"Fehler beim Laden der Excel-Datei: {str(e)}")

# ------------------------------------------------------------------
# Navigation erweitern (füge dies zur bestehenden sidebar_module_navigation Funktion hinzu)
# ------------------------------------------------------------------

def sidebar_module_navigation():
    st.sidebar.title("Module Navigation")

    pages = {
        "Home": page_home,
        "Online-API_Filter": page_online_api_filter,
        "3) Codewords & PubMed": page_codewords_pubmed,
        "Analyze Paper": page_analyze_paper,
        "🔍 Automated Paper Search": page_automated_paper_search,  # Neue Zeile hinzufügen
    }

    for label, page in pages.items():
        if st.sidebar.button(label, key=label):
            st.session_state["current_page"] = label
    
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Home"
    return pages.get(st.session_state["current_page"], page_home)
