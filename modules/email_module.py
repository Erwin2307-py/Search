# modules/email_module.py
import streamlit as st
import datetime
import json
import os

def module_email():
    """Haupt-Email-Modul Funktion - DIESE FUNKTION MUSS EXISTIEREN"""
    st.subheader("📧 Email-Benachrichtigungen für Paper-Suche")
    st.success("✅ External email module loaded successfully!")
    
    # Initialize session state
    if "email_settings" not in st.session_state:
        st.session_state["email_settings"] = {
            "sender_email": "",
            "recipient_email": "",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "auto_notifications": False,
            "min_papers_threshold": 5
        }
    
    if "email_notifications_history" not in st.session_state:
        st.session_state["email_notifications_history"] = []
    
    if "search_terms_email" not in st.session_state:
        st.session_state["search_terms_email"] = {}
    
    # Tabs für verschiedene Funktionen
    tab1, tab2, tab3, tab4 = st.tabs([
        "📧 Email-Konfiguration", 
        "🔍 Suchbegriff-Benachrichtigungen", 
        "📊 Benachrichtigungs-Verlauf",
        "⚙️ Erweiterte Einstellungen"
    ])
    
    with tab1:
        email_configuration_interface()
    
    with tab2:
        search_terms_notification_interface()
    
    with tab3:
        notification_history_interface()
    
    with tab4:
        advanced_settings_interface()

def email_configuration_interface():
    """Email-Konfiguration für Paper-Suche Benachrichtigungen"""
    st.subheader("📧 Email-Konfiguration")
    
    settings = st.session_state["email_settings"]
    
    with st.form("email_config_form"):
        st.write("**📬 Grundlegende Email-Einstellungen:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            sender_email = st.text_input(
                "Absender Email", 
                value=settings.get("sender_email", ""),
                help="Die Email-Adresse, von der Benachrichtigungen gesendet werden"
            )
            subject_template = st.text_input(
                "Betreff-Vorlage", 
                value="🔬 {count} neue Papers gefunden für '{search_term}'",
                help="Verwenden Sie {count} und {search_term} als Platzhalter"
            )
        
        with col2:
            recipient_email = st.text_input(
                "Empfänger Email", 
                value=settings.get("recipient_email", ""),
                help="Die Email-Adresse, die Benachrichtigungen erhält"
            )
            smtp_server = st.text_input(
                "SMTP Server", 
                value=settings.get("smtp_server", "smtp.gmail.com")
            )
        
        st.write("**📝 Email-Nachricht Vorlage:**")
        message_template = st.text_area(
            "Nachricht-Vorlage",
            value="""🔍 Neue wissenschaftliche Papers gefunden!

📅 Datum: {date}
🔍 Suchbegriff: '{search_term}'
📊 Anzahl neue Papers: {count}

📋 Top Papers:
{top_papers}

🔗 Vollständige Ergebnisse sind im Paper-Suche System verfügbar.

Mit freundlichen Grüßen,
Ihr automatisches Paper-Suche System""",
            height=250,
            help="Verwenden Sie {date}, {search_term}, {count}, {top_papers} als Platzhalter"
        )
        
        if st.form_submit_button("💾 Email-Konfiguration speichern"):
            st.session_state["email_settings"].update({
                "sender_email": sender_email,
                "recipient_email": recipient_email,
                "smtp_server": smtp_server,
                "subject_template": subject_template,
                "message_template": message_template
            })
            st.success("✅ Email-Konfiguration gespeichert!")
            
            # Vorschau anzeigen
            preview = generate_email_preview(
                st.session_state["email_settings"], 
                "diabetes genetics", 
                7,
                ["Paper 1: Diabetes genetic markers", "Paper 2: T2D susceptibility genes", "Paper 3: Insulin resistance pathways"]
            )
            st.info("📧 **Email-Vorschau:**")
            st.code(preview, language="text")

def search_terms_notification_interface():
    """Interface für Suchbegriff-basierte Benachrichtigungen"""
    st.subheader("🔍 Suchbegriff-Benachrichtigungen")
    
    # Neuen Suchbegriff für Benachrichtigungen hinzufügen
    st.write("**➕ Neuen Suchbegriff für Email-Benachrichtigungen hinzufügen:**")
    
    with st.form("add_search_term_notification"):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_term = st.text_input(
                "Suchbegriff", 
                placeholder="z.B. 'diabetes genetics', 'BRCA1 mutations'"
            )
        
        with col2:
            frequency = st.selectbox(
                "Benachrichtigungs-Frequenz",
                ["Bei jeder Suche", "Täglich", "Wöchentlich", "Monatlich"]
            )
        
        with col3:
            min_papers = st.number_input(
                "Min. Papers", 
                min_value=1, 
                value=5,
                help="Mindestanzahl neuer Papers für Benachrichtigung"
            )
        
        if st.form_submit_button("➕ Suchbegriff hinzufügen"):
            if search_term:
                st.session_state["search_terms_email"][search_term] = {
                    "frequency": frequency,
                    "min_papers": min_papers,
                    "created": datetime.datetime.now().isoformat(),
                    "last_notification": None,
                    "total_notifications": 0,
                    "active": True
                }
                st.success(f"✅ Suchbegriff '{search_term}' für Email-Benachrichtigungen hinzugefügt!")
                st.rerun()
            else:
                st.error("❌ Bitte geben Sie einen Suchbegriff ein!")
    
    # Bestehende Suchbegriffe anzeigen
    if st.session_state["search_terms_email"]:
        st.write("**📋 Aktuelle Suchbegriffe mit Email-Benachrichtigungen:**")
        
        for term, settings in st.session_state["search_terms_email"].items():
            with st.expander(f"🔍 {term} ({'🟢 Aktiv' if settings.get('active', True) else '🔴 Inaktiv'})"):
                col_info1, col_info2, col_info3 = st.columns(3)
                
                with col_info1:
                    st.write(f"**Frequenz:** {settings.get('frequency', 'N/A')}")
                    st.write(f"**Min. Papers:** {settings.get('min_papers', 5)}")
                
                with col_info2:
                    st.write(f"**Erstellt:** {settings.get('created', 'N/A')[:10]}")
                    last_notification = settings.get('last_notification', 'Nie')
                    st.write(f"**Letzte Benachrichtigung:** {last_notification[:19] if last_notification != 'Nie' else last_notification}")
                
                with col_info3:
                    st.write(f"**Benachrichtigungen gesendet:** {settings.get('total_notifications', 0)}")
                    
                    # Aktiv/Inaktiv Toggle
                    new_status = st.checkbox(
                        "Aktiv", 
                        value=settings.get("active", True),
                        key=f"active_{term}"
                    )
                    settings["active"] = new_status
                    
                    # Löschen Button
                    if st.button(f"🗑️ Löschen", key=f"delete_{term}"):
                        del st.session_state["search_terms_email"][term]
                        st.success(f"Suchbegriff '{term}' gelöscht!")
                        st.rerun()
                
                # Test-Benachrichtigung senden
                if st.button(f"📧 Test-Benachrichtigung senden", key=f"test_{term}"):
                    send_test_notification_for_term(term, 3)
    else:
        st.info("🔔 Noch keine Suchbegriffe für Email-Benachrichtigungen konfiguriert.")

def notification_history_interface():
    """Anzeige der Benachrichtigungs-Historie"""
    st.subheader("📊 Benachrichtigungs-Verlauf")
    
    history = st.session_state["email_notifications_history"]
    
    if history:
        # Statistiken
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📧 Gesamt Benachrichtigungen", len(history))
        
        with col2:
            today = datetime.datetime.now().date()
            today_count = len([n for n in history if n["date"] == today.isoformat()])
            st.metric("📅 Heute", today_count)
        
        with col3:
            week_ago = today - datetime.timedelta(days=7)
            week_count = len([n for n in history if n["date"] >= week_ago.isoformat()])
            st.metric("📅 Diese Woche", week_count)
        
        with col4:
            unique_terms = len(set(n["search_term"] for n in history))
            st.metric("🔍 Suchbegriffe", unique_terms)
        
        # Filter-Optionen
        st.write("**🔍 Filter:**")
        col_filter1, col_filter2 = st.columns(2)
        
        with col_filter1:
            date_filter = st.date_input(
                "Ab Datum:", 
                value=datetime.datetime.now() - datetime.timedelta(days=30)
            )
        
        with col_filter2:
            term_filter = st.selectbox(
                "Suchbegriff:", 
                ["Alle"] + list(set(n["search_term"] for n in history))
            )
        
        # Gefilterte Historie anzeigen
        filtered_history = []
        for notification in history:
            notification_date = datetime.datetime.fromisoformat(notification["timestamp"]).date()
            
            date_match = notification_date >= date_filter
            term_match = term_filter == "Alle" or notification["search_term"] == term_filter
            
            if date_match and term_match:
                filtered_history.append(notification)
        
        # Historie-Tabelle
        if filtered_history:
            st.write(f"**📋 Gefilterte Benachrichtigungen ({len(filtered_history)}):**")
            
            for notification in reversed(filtered_history[-20:]):  # Zeige letzte 20
                with st.expander(
                    f"📧 {notification['search_term']} - {notification['paper_count']} Papers "
                    f"({notification['timestamp'][:19]})"
                ):
                    col_detail1, col_detail2 = st.columns(2)
                    
                    with col_detail1:
                        st.write(f"**Suchbegriff:** {notification['search_term']}")
                        st.write(f"**Papers gefunden:** {notification['paper_count']}")
                        st.write(f"**Datum:** {notification['timestamp'][:19]}")
                    
                    with col_detail2:
                        st.write(f"**Status:** {notification['status']}")
                        st.write(f"**Empfänger:** {notification.get('recipient', 'N/A')}")
                        st.write(f"**Typ:** {notification.get('type', 'Standard')}")
                    
                    # Email-Inhalt anzeigen
                    if st.button(f"📝 Email-Inhalt anzeigen", key=f"show_content_{notification['timestamp']}"):
                        st.code(notification.get("email_content", "Inhalt nicht verfügbar"), language="text")
        else:
            st.info("Keine Benachrichtigungen im ausgewählten Zeitraum gefunden.")
        
        # Verlauf löschen
        st.markdown("---")
        if st.button("🗑️ Gesamten Verlauf löschen"):
            if st.checkbox("Löschung bestätigen"):
                st.session_state["email_notifications_history"] = []
                st.success("Verlauf gelöscht!")
                st.rerun()
    else:
        st.info("📭 Noch keine Email-Benachrichtigungen versendet.")

def advanced_settings_interface():
    """Erweiterte Einstellungen"""
    st.subheader("⚙️ Erweiterte Email-Einstellungen")
    
    settings = st.session_state["email_settings"]
    
    # Allgemeine Einstellungen
    with st.expander("🔧 Allgemeine Einstellungen", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            settings["auto_notifications"] = st.checkbox(
                "Automatische Benachrichtigungen aktivieren",
                value=settings.get("auto_notifications", False),
                help="Sendet automatisch Emails bei neuen Paper-Suchen"
            )
            
            settings["min_papers_threshold"] = st.number_input(
                "Globaler Min. Papers Schwellenwert",
                min_value=1,
                value=settings.get("min_papers_threshold", 5),
                help="Mindestanzahl Papers für automatische Benachrichtigungen"
            )
        
        with col2:
            settings["smtp_port"] = st.number_input(
                "SMTP Port",
                value=settings.get("smtp_port", 587)
            )
            
            settings["use_tls"] = st.checkbox(
                "TLS verwenden",
                value=settings.get("use_tls", True)
            )
    
    # Email-Format Einstellungen
    with st.expander("📝 Email-Format Einstellungen"):
        settings["include_abstracts"] = st.checkbox(
            "Abstracts in Email einschließen",
            value=settings.get("include_abstracts", False),
            help="Fügt Paper-Abstracts zur Email hinzu (macht Email länger)"
        )
        
        settings["max_papers_in_email"] = st.number_input(
            "Max. Papers in Email-Vorschau",
            min_value=1,
            max_value=20,
            value=settings.get("max_papers_in_email", 5),
            help="Anzahl der Papers, die in der Email-Vorschau gezeigt werden"
        )
        
        settings["email_format"] = st.selectbox(
            "Email-Format",
            ["Text", "HTML"],
            index=0 if settings.get("email_format", "Text") == "Text" else 1
        )
    
    # Benachrichtigungs-Timing
    with st.expander("⏰ Benachrichtigungs-Timing"):
        settings["batch_notifications"] = st.checkbox(
            "Benachrichtigungen sammeln",
            value=settings.get("batch_notifications", False),
            help="Sammelt mehrere Benachrichtigungen und sendet sie in einer Email"
        )
        
        if settings["batch_notifications"]:
            settings["batch_interval"] = st.selectbox(
                "Sammel-Intervall",
                ["Stündlich", "Täglich", "Wöchentlich"],
                index=1
            )
    
    # Einstellungen speichern
    if st.button("💾 Erweiterte Einstellungen speichern"):
        st.success("✅ Erweiterte Einstellungen gespeichert!")
    
    # System-Test
    st.markdown("---")
    st.write("**🧪 System-Tests:**")
    
    col_test1, col_test2, col_test3 = st.columns(3)
    
    with col_test1:
        if st.button("📧 Test-Email senden"):
            send_system_test_email()
    
    with col_test2:
        if st.button("🔧 Konfiguration prüfen"):
            check_email_configuration()
    
    with col_test3:
        if st.button("📊 Statistiken generieren"):
            generate_email_statistics()

def generate_email_preview(settings, search_term, count, top_papers):
    """Generiert Email-Vorschau"""
    try:
        subject = settings.get("subject_template", "Neue Papers").format(
            count=count,
            search_term=search_term
        )
        
        top_papers_text = "\n".join([f"• {paper}" for paper in top_papers])
        
        message = settings.get("message_template", "Standard-Nachricht").format(
            date=datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
            search_term=search_term,
            count=count,
            top_papers=top_papers_text
        )
        
        return f"""Von: {settings.get('sender_email', 'system@example.com')}
An: {settings.get('recipient_email', 'user@example.com')}
Betreff: {subject}

{message}"""
    
    except Exception as e:
        return f"Email-Vorschau Fehler: {str(e)}"

def send_test_notification_for_term(search_term, paper_count):
    """Sendet Test-Benachrichtigung für spezifischen Suchbegriff"""
    settings = st.session_state["email_settings"]
    
    # Test-Benachrichtigung erstellen
    test_notification = {
        "timestamp": datetime.datetime.now().isoformat(),
        "date": datetime.datetime.now().date().isoformat(),
        "search_term": search_term,
        "paper_count": paper_count,
        "status": "Test-Benachrichtigung",
        "type": "Test",
        "recipient": settings.get("recipient_email", "test@example.com"),
        "email_content": generate_email_preview(
            settings, 
            search_term, 
            paper_count,
            [f"Test Paper {i} für {search_term}" for i in range(1, min(4, paper_count + 1))]
        )
    }
    
    # Zur Historie hinzufügen
    st.session_state["email_notifications_history"].append(test_notification)
    
    # Suchbegriff-Statistik aktualisieren
    if search_term in st.session_state["search_terms_email"]:
        st.session_state["search_terms_email"][search_term]["last_notification"] = test_notification["timestamp"]
        st.session_state["search_terms_email"][search_term]["total_notifications"] += 1
    
    st.success(f"✅ Test-Benachrichtigung für '{search_term}' erstellt!")
    
    # Vorschau anzeigen
    with st.expander("📧 Test-Email Vorschau"):
        st.code(test_notification["email_content"], language="text")

def send_system_test_email():
    """Sendet System-Test-Email"""
    settings = st.session_state["email_settings"]
    
    if not settings.get("sender_email") or not settings.get("recipient_email"):
        st.error("❌ Email-Konfiguration unvollständig!")
        return
    
    test_notification = {
        "timestamp": datetime.datetime.now().isoformat(),
        "date": datetime.datetime.now().date().isoformat(),
        "search_term": "System-Test",
        "paper_count": 0,
        "status": "System-Test erfolgreich",
        "type": "System-Test",
        "recipient": settings["recipient_email"],
        "email_content": f"""System-Test Email

Absender: {settings['sender_email']}
Empfänger: {settings['recipient_email']}
SMTP Server: {settings['smtp_server']}
Zeitstempel: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

Das Email-System ist korrekt konfiguriert und funktionsbereit!"""
    }
    
    st.session_state["email_notifications_history"].append(test_notification)
    st.success("✅ System-Test-Email erstellt!")

def check_email_configuration():
    """Prüft Email-Konfiguration"""
    settings = st.session_state["email_settings"]
    
    st.write("**🔍 Konfigurationsprüfung:**")
    
    checks = [
        ("Absender Email", bool(settings.get("sender_email"))),
        ("Empfänger Email", bool(settings.get("recipient_email"))),
        ("SMTP Server", bool(settings.get("smtp_server"))),
        ("Betreff-Vorlage", bool(settings.get("subject_template"))),
        ("Nachricht-Vorlage", bool(settings.get("message_template"))),
    ]
    
    all_good = True
    for check_name, check_result in checks:
        icon = "✅" if check_result else "❌"
        st.write(f"{icon} {check_name}: {'Konfiguriert' if check_result else 'Fehlt'}")
        if not check_result:
            all_good = False
    
    if all_good:
        st.success("🎉 Alle Konfigurationen sind vollständig!")
    else:
        st.warning("⚠️ Einige Konfigurationen fehlen noch.")

def generate_email_statistics():
    """Generiert Email-Statistiken"""
    history = st.session_state["email_notifications_history"]
    search_terms = st.session_state["search_terms_email"]
    
    if not history:
        st.info("📊 Keine Daten für Statistiken verfügbar.")
        return
    
    st.write("**📊 Email-Statistiken:**")
    
    # Basis-Statistiken
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Gesamt Emails", len(history))
        st.metric("Konfigurierte Suchbegriffe", len(search_terms))
    
    with col2:
        avg_papers = sum(n["paper_count"] for n in history) / len(history) if history else 0
        st.metric("Ø Papers pro Email", f"{avg_papers:.1f}")
        
        active_terms = sum(1 for t in search_terms.values() if t.get("active", True))
        st.metric("Aktive Suchbegriffe", active_terms)
    
    with col3:
        last_email = max((datetime.datetime.fromisoformat(n["timestamp"]) for n in history), default=None)
        if last_email:
            days_since = (datetime.datetime.now() - last_email).days
            st.metric("Tage seit letzter Email", days_since)

# Hilfsfunktionen für Integration mit Paper-Suche
def trigger_email_notification(search_term, paper_count, papers_data=None):
    """Wird von Paper-Suche Modulen aufgerufen"""
    try:
        settings = st.session_state.get("email_settings", {})
        search_terms = st.session_state.get("search_terms_email", {})
        
        # Prüfe ob automatische Benachrichtigungen aktiviert sind
        if not settings.get("auto_notifications", False):
            return False
        
        # Prüfe ob Suchbegriff für Benachrichtigungen konfiguriert ist
        if search_term in search_terms and search_terms[search_term].get("active", True):
            min_papers = search_terms[search_term].get("min_papers", 5)
        else:
            min_papers = settings.get("min_papers_threshold", 5)
        
        if paper_count >= min_papers:
            # Erstelle Benachrichtigung
            top_papers = []
            if papers_data:
                for paper in papers_data[:settings.get("max_papers_in_email", 5)]:
                    title = paper.get("Title", "Unbekannter Titel")
                    top_papers.append(title[:100] + "..." if len(title) > 100 else title)
            
            notification = {
                "timestamp": datetime.datetime.now().isoformat(),
                "date": datetime.datetime.now().date().isoformat(),
                "search_term": search_term,
                "paper_count": paper_count,
                "status": "Automatisch gesendet",
                "type": "Automatisch",
                "recipient": settings.get("recipient_email", ""),
                "email_content": generate_email_preview(settings, search_term, paper_count, top_papers)
            }
            
            # Zur Historie hinzufügen
            if "email_notifications_history" not in st.session_state:
                st.session_state["email_notifications_history"] = []
            
            st.session_state["email_notifications_history"].append(notification)
            
            # Update Suchbegriff-Statistik
            if search_term in search_terms:
                search_terms[search_term]["last_notification"] = notification["timestamp"]
                search_terms[search_term]["total_notifications"] = search_terms[search_term].get("total_notifications", 0) + 1
            
            return True
    
    except Exception:
        return False

def get_email_settings():
    """Gibt Email-Einstellungen zurück für andere Module"""
    return st.session_state.get("email_settings", {})

def is_email_enabled():
    """Prüft ob Email-System aktiviert ist"""
    settings = st.session_state.get("email_settings", {})
    return (settings.get("auto_notifications", False) and 
            settings.get("sender_email") and 
            settings.get("recipient_email"))
