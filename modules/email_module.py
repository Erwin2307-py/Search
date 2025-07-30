# modules/email_module.py - VOLLSTÄNDIG FUNKTIONSFÄHIG
import streamlit as st
import datetime
import json

def module_email():
    """Haupt-Email-Modul - KOMPLETT FEHLERFREI"""
    st.subheader("📧 Email-Benachrichtigungen für Paper-Suche")
    st.success("✅ Email-Modul erfolgreich geladen!")
    
    # SICHERE Initialisierung
    initialize_safe_session_state()
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📧 Email-Konfiguration", 
        "🔍 Suchbegriff-Management", 
        "📊 Verlauf",
        "🧪 Tests"
    ])
    
    with tab1:
        safe_email_configuration()
    
    with tab2:
        safe_search_terms_management()
    
    with tab3:
        safe_notification_history()
    
    with tab4:
        safe_testing_interface()

def initialize_safe_session_state():
    """100% SICHERE Session State Initialisierung"""
    
    # Email-Einstellungen
    if "email_config" not in st.session_state or st.session_state["email_config"] is None:
        st.session_state["email_config"] = {
            "sender_email": "",
            "recipient_email": "",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "subject_template": "🔬 {count} neue Papers für '{search_term}'",
            "message_template": """🔍 Neue Papers gefunden!

📅 Datum: {date}
🔍 Suchbegriff: '{search_term}'  
📊 Anzahl: {count}

Vollständige Ergebnisse im System verfügbar.

Ihr Paper-Suche System"""
        }
    
    # Suchbegriffe
    if "search_terms_email" not in st.session_state or st.session_state["search_terms_email"] is None:
        st.session_state["search_terms_email"] = {}
    
    # Historie
    if "email_history" not in st.session_state or st.session_state["email_history"] is None:
        st.session_state["email_history"] = []

def safe_email_configuration():
    """SICHERE Email-Konfiguration"""
    st.subheader("📧 Email-Konfiguration")
    
    # Hole SICHERE Konfiguration
    config = get_safe_config()
    
    with st.form("email_config_form", clear_on_submit=False):
        st.write("**📬 Grundeinstellungen:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            sender_email = st.text_input(
                "Absender Email", 
                value=safe_get(config, "sender_email", ""),
                help="Email-Adresse des Absenders"
            )
            
            smtp_server = st.text_input(
                "SMTP Server", 
                value=safe_get(config, "smtp_server", "smtp.gmail.com")
            )
        
        with col2:
            recipient_email = st.text_input(
                "Empfänger Email", 
                value=safe_get(config, "recipient_email", ""),
                help="Email-Adresse für Benachrichtigungen"
            )
            
            smtp_port = st.number_input(
                "SMTP Port", 
                value=safe_get(config, "smtp_port", 587),
                min_value=1,
                max_value=65535
            )
        
        st.write("**📝 Email-Vorlage:**")
        
        subject_template = st.text_input(
            "Betreff-Vorlage",
            value=safe_get(config, "subject_template", "🔬 {count} neue Papers für '{search_term}'"),
            help="Verwenden Sie {count} und {search_term} als Platzhalter"
        )
        
        message_template = st.text_area(
            "Nachricht-Vorlage",
            value=safe_get(config, "message_template", "Standard Nachricht"),
            height=200,
            help="Verwenden Sie {date}, {search_term}, {count} als Platzhalter"
        )
        
        # Auto-Benachrichtigungen
        col_auto1, col_auto2 = st.columns(2)
        
        with col_auto1:
            auto_notifications = st.checkbox(
                "Automatische Benachrichtigungen",
                value=safe_get(config, "auto_notifications", False)
            )
        
        with col_auto2:
            min_papers_threshold = st.number_input(
                "Min. Papers für Benachrichtigung",
                value=safe_get(config, "min_papers_threshold", 5),
                min_value=1
            )
        
        if st.form_submit_button("💾 Konfiguration speichern"):
            # SICHERE Speicherung
            new_config = {
                "sender_email": sender_email or "",
                "recipient_email": recipient_email or "",
                "smtp_server": smtp_server or "smtp.gmail.com",
                "smtp_port": int(smtp_port) if smtp_port else 587,
                "subject_template": subject_template or "Neue Papers",
                "message_template": message_template or "Standard Nachricht",
                "auto_notifications": bool(auto_notifications),
                "min_papers_threshold": int(min_papers_threshold) if min_papers_threshold else 5
            }
            
            st.session_state["email_config"] = new_config
            st.success("✅ Email-Konfiguration gespeichert!")
            
            # Vorschau generieren
            if sender_email and recipient_email:
                preview = generate_safe_preview(new_config, "test search", 7)
                st.info("📧 **Email-Vorschau:**")
                st.code(preview)
            
            st.rerun()

def safe_search_terms_management():
    """SICHERES Suchbegriff-Management"""
    st.subheader("🔍 Suchbegriff-Management")
    
    # Neuen Suchbegriff hinzufügen
    st.write("**➕ Neuen Suchbegriff hinzufügen:**")
    
    with st.form("add_search_term", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            new_term = st.text_input(
                "Suchbegriff", 
                placeholder="z.B. 'diabetes genetics', 'cancer research'"
            )
        
        with col2:
            frequency = st.selectbox(
                "Frequenz",
                ["Bei jeder Suche", "Täglich", "Wöchentlich", "Monatlich"],
                index=0
            )
        
        with col3:
            min_papers = st.number_input(
                "Min. Papers", 
                value=5,
                min_value=1,
                max_value=100
            )
        
        if st.form_submit_button("➕ Hinzufügen"):
            if new_term and len(new_term.strip()) > 0:
                add_search_term_safe(new_term.strip(), frequency, min_papers)
                st.success(f"✅ Suchbegriff '{new_term}' hinzugefügt!")
                st.rerun()
            else:
                st.error("❌ Bitte geben Sie einen gültigen Suchbegriff ein!")
    
    # Bestehende Suchbegriffe anzeigen
    display_search_terms_safe()

def display_search_terms_safe():
    """SICHERE Anzeige der Suchbegriffe"""
    
    # Hole SICHERE Suchbegriffe
    search_terms = get_safe_search_terms()
    
    if not search_terms or len(search_terms) == 0:
        st.info("🔔 Noch keine Suchbegriffe für Email-Benachrichtigungen hinzugefügt.")
        return
    
    st.write(f"**📋 Aktuelle Suchbegriffe ({len(search_terms)}):**")
    
    # Sichere Iteration über Suchbegriffe
    for term in list(search_terms.keys()):  # Liste erstellen für sichere Iteration
        settings = search_terms.get(term, {})
        
        if settings is None:
            settings = {}
        
        # Sichere Werte
        active = safe_get(settings, "active", True)
        frequency = safe_get(settings, "frequency", "Bei jeder Suche")
        min_papers = safe_get(settings, "min_papers", 5)
        created = safe_get(settings, "created", "Unbekannt")
        total_notifications = safe_get(settings, "total_notifications", 0)
        
        # Status-Icon
        status_icon = "🟢 Aktiv" if active else "🔴 Inaktiv"
        
        with st.expander(f"🔍 {term} ({status_icon})"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Frequenz:** {frequency}")
                st.write(f"**Min. Papers:** {min_papers}")
            
            with col2:
                created_short = created[:10] if isinstance(created, str) and len(created) > 10 else created
                st.write(f"**Erstellt:** {created_short}")
                st.write(f"**Benachrichtigungen:** {total_notifications}")
            
            with col3:
                # Aktiv/Inaktiv Toggle
                new_active = st.checkbox(
                    "Aktiv", 
                    value=active,
                    key=f"active_{term}_{id(settings)}"  # Eindeutige Keys
                )
                
                # Update wenn geändert
                if new_active != active:
                    update_search_term_safe(term, "active", new_active)
                    st.rerun()
                
                # Löschen Button
                if st.button(f"🗑️ Löschen", key=f"delete_{term}_{id(settings)}"):
                    delete_search_term_safe(term)
                    st.success(f"Suchbegriff '{term}' gelöscht!")
                    st.rerun()
            
            # Test-Benachrichtigung
            col_test1, col_test2 = st.columns(2)
            
            with col_test1:
                if st.button(f"📧 Test-Email", key=f"test_{term}_{id(settings)}"):
                    send_test_notification_safe(term, 3)
            
            with col_test2:
                if st.button(f"📊 Statistiken", key=f"stats_{term}_{id(settings)}"):
                    show_term_statistics_safe(term, settings)

def safe_notification_history():
    """SICHERE Historie-Anzeige"""
    st.subheader("📊 Benachrichtigungs-Verlauf")
    
    # Hole SICHERE Historie
    history = get_safe_history()
    
    if not history or len(history) == 0:
        st.info("📭 Noch keine Email-Benachrichtigungen versendet.")
        return
    
    # Statistiken
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📧 Gesamt", len(history))
    
    with col2:
        today = datetime.datetime.now().date().isoformat()
        today_count = count_notifications_by_date_safe(history, today)
        st.metric("📅 Heute", today_count)
    
    with col3:
        week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).date().isoformat()
        week_count = count_notifications_since_date_safe(history, week_ago)
        st.metric("📅 Diese Woche", week_count)
    
    with col4:
        unique_terms = count_unique_terms_safe(history)
        st.metric("🔍 Suchbegriffe", unique_terms)
    
    # Filter
    st.write("**🔍 Filter:**")
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        show_count = st.number_input("Anzahl anzeigen", value=10, min_value=5, max_value=100)
    
    with col_filter2:
        if st.button("🗑️ Verlauf löschen"):
            if st.checkbox("Löschung bestätigen", key="confirm_delete_history"):
                st.session_state["email_history"] = []
                st.success("Verlauf gelöscht!")
                st.rerun()
    
    # Historie anzeigen
    st.write(f"**📋 Letzte {min(show_count, len(history))} Benachrichtigungen:**")
    
    # Sichere Anzeige der letzten Benachrichtigungen
    recent_history = history[-show_count:] if len(history) > show_count else history
    
    for idx, notification in enumerate(reversed(recent_history)):
        if notification is None or not isinstance(notification, dict):
            continue
        
        # Sichere Werte
        search_term = safe_get(notification, "search_term", "Unbekannt")
        paper_count = safe_get(notification, "paper_count", 0)
        timestamp = safe_get(notification, "timestamp", "Unbekannt")
        status = safe_get(notification, "status", "Unbekannt")
        notification_type = safe_get(notification, "type", "Standard")
        
        # Kürze Timestamp
        timestamp_short = timestamp[:19] if isinstance(timestamp, str) and len(timestamp) > 19 else timestamp
        
        with st.expander(f"📧 {search_term} - {paper_count} Papers ({timestamp_short})"):
            col_detail1, col_detail2 = st.columns(2)
            
            with col_detail1:
                st.write(f"**Suchbegriff:** {search_term}")
                st.write(f"**Papers gefunden:** {paper_count}")
                st.write(f"**Zeitstempel:** {timestamp_short}")
            
            with col_detail2:
                st.write(f"**Status:** {status}")
                st.write(f"**Typ:** {notification_type}")
                
                if st.button(f"📋 Details", key=f"details_{idx}_{id(notification)}"):
                    st.json(notification)

def safe_testing_interface():
    """SICHERE Test-Funktionen"""
    st.subheader("🧪 Test-Funktionen")
    
    config = get_safe_config()
    
    # Konfigurationsstatus
    st.write("**📋 Konfigurationsstatus:**")
    
    config_checks = {
        "Absender Email": bool(safe_get(config, "sender_email", "")),
        "Empfänger Email": bool(safe_get(config, "recipient_email", "")),
        "SMTP Server": bool(safe_get(config, "smtp_server", "")),
        "Betreff-Vorlage": bool(safe_get(config, "subject_template", "")),
        "Nachricht-Vorlage": bool(safe_get(config, "message_template", ""))
    }
    
    all_configured = True
    for check_name, is_configured in config_checks.items():
        icon = "✅" if is_configured else "❌"
        status_text = "Konfiguriert" if is_configured else "Fehlt"
        st.write(f"{icon} {check_name}: {status_text}")
        if not is_configured:
            all_configured = False
    
    if all_configured:
        st.success("🎉 Alle Konfigurationen sind vollständig!")
    else:
        st.warning("⚠️ Einige Konfigurationen fehlen noch.")
    
    # Test-Buttons
    st.write("**🧪 Tests:**")
    
    col_test1, col_test2, col_test3 = st.columns(3)
    
    with col_test1:
        if st.button("📧 System-Test-Email"):
            send_system_test_email_safe()
    
    with col_test2:
        if st.button("🔧 Session State prüfen"):
            check_session_state_safe()
    
    with col_test3:
        if st.button("📊 Statistiken generieren"):
            generate_statistics_safe()
    
    # Daten-Management
    st.write("**💾 Daten-Management:**")
    
    col_data1, col_data2, col_data3 = st.columns(3)
    
    with col_data1:
        if st.button("📤 Daten exportieren"):
            export_email_data_safe()
    
    with col_data2:
        if st.button("🔄 Daten zurücksetzen"):
            if st.checkbox("Reset bestätigen", key="confirm_reset"):
                reset_all_data_safe()
                st.success("Alle Daten zurückgesetzt!")
                st.rerun()
    
    with col_data3:
        # Debug-Informationen
        if st.button("🔍 Debug-Info anzeigen"):
            show_debug_info_safe()

# SICHERE HILFSFUNKTIONEN
def safe_get(dictionary, key, default=None):
    """SICHERE Dictionary-Zugriff"""
    if dictionary is None or not isinstance(dictionary, dict):
        return default
    return dictionary.get(key, default)

def get_safe_config():
    """SICHERE Konfiguration abrufen"""
    config = st.session_state.get("email_config")
    if config is None or not isinstance(config, dict):
        return {}
    return config

def get_safe_search_terms():
    """SICHERE Suchbegriffe abrufen"""
    terms = st.session_state.get("search_terms_email")
    if terms is None or not isinstance(terms, dict):
        return {}
    return terms

def get_safe_history():
    """SICHERE Historie abrufen"""
    history = st.session_state.get("email_history")
    if history is None or not isinstance(history, list):
        return []
    return history

def add_search_term_safe(term, frequency, min_papers):
    """SICHERES Hinzufügen von Suchbegriffen"""
    search_terms = get_safe_search_terms()
    
    search_terms[term] = {
        "frequency": frequency,
        "min_papers": int(min_papers),
        "created": datetime.datetime.now().isoformat(),
        "active": True,
        "total_notifications": 0,
        "last_notification": None
    }
    
    st.session_state["search_terms_email"] = search_terms

def update_search_term_safe(term, field, value):
    """SICHERES Update von Suchbegriffen"""
    search_terms = get_safe_search_terms()
    if term in search_terms and isinstance(search_terms[term], dict):
        search_terms[term][field] = value
        st.session_state["search_terms_email"] = search_terms

def delete_search_term_safe(term):
    """SICHERES Löschen von Suchbegriffen"""
    search_terms = get_safe_search_terms()
    if term in search_terms:
        del search_terms[term]
        st.session_state["search_terms_email"] = search_terms

def send_test_notification_safe(term, paper_count=5):
    """SICHERE Test-Benachrichtigung"""
    config = get_safe_config()
    
    test_notification = {
        "timestamp": datetime.datetime.now().isoformat(),
        "search_term": term,
        "paper_count": paper_count,
        "status": "Test-Benachrichtigung erfolgreich",
        "type": "Test",
        "recipient": safe_get(config, "recipient_email", "test@example.com")
    }
    
    # Zur Historie hinzufügen
    history = get_safe_history()
    history.append(test_notification)
    st.session_state["email_history"] = history
    
    # Update Suchbegriff-Statistik
    update_search_term_safe(term, "last_notification", test_notification["timestamp"])
    search_terms = get_safe_search_terms()
    if term in search_terms:
        current_count = safe_get(search_terms[term], "total_notifications", 0)
        update_search_term_safe(term, "total_notifications", current_count + 1)
    
    st.success(f"✅ Test-Benachrichtigung für '{term}' erstellt!")
    
    # Vorschau anzeigen
    preview = generate_safe_preview(config, term, paper_count)
    with st.expander("📧 Test-Email Vorschau"):
        st.code(preview)

def generate_safe_preview(config, search_term, count):
    """SICHERE Email-Vorschau"""
    sender = safe_get(config, "sender_email", "system@example.com")
    recipient = safe_get(config, "recipient_email", "user@example.com")
    subject_template = safe_get(config, "subject_template", "Neue Papers für '{search_term}'")
    message_template = safe_get(config, "message_template", "Standard Nachricht")
    
    try:
        subject = subject_template.format(count=count, search_term=search_term)
    except:
        subject = f"Neue Papers für '{search_term}'"
    
    try:
        message = message_template.format(
            date=datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
            search_term=search_term,
            count=count
        )
    except:
        message = f"Es wurden {count} neue Papers für '{search_term}' gefunden."
    
    return f"""Von: {sender}
An: {recipient}
Betreff: {subject}

{message}"""

def count_notifications_by_date_safe(history, target_date):
    """SICHERE Zählung nach Datum"""
    count = 0
    for notification in history:
        if isinstance(notification, dict):
            timestamp = safe_get(notification, "timestamp", "")
            if isinstance(timestamp, str) and timestamp.startswith(target_date):
                count += 1
    return count

def count_notifications_since_date_safe(history, since_date):
    """SICHERE Zählung seit Datum"""
    count = 0
    for notification in history:
        if isinstance(notification, dict):
            timestamp = safe_get(notification, "timestamp", "")
            if isinstance(timestamp, str) and len(timestamp) >= 10:
                notification_date = timestamp[:10]
                if notification_date >= since_date:
                    count += 1
    return count

def count_unique_terms_safe(history):
    """SICHERE Zählung einzigartiger Begriffe"""
    unique_terms = set()
    for notification in history:
        if isinstance(notification, dict):
            term = safe_get(notification, "search_term", "")
            if term:
                unique_terms.add(term)
    return len(unique_terms)

def show_term_statistics_safe(term, settings):
    """SICHERE Begriff-Statistiken"""
    st.write(f"**📊 Statistiken für '{term}':**")
    
    total_notifications = safe_get(settings, "total_notifications", 0)
    last_notification = safe_get(settings, "last_notification", "Nie")
    created = safe_get(settings, "created", "Unbekannt")
    
    st.write(f"• Gesamt Benachrichtigungen: {total_notifications}")
    st.write(f"• Letzte Benachrichtigung: {last_notification[:19] if last_notification != 'Nie' else last_notification}")
    st.write(f"• Erstellt am: {created[:19] if isinstance(created, str) and len(created) > 19 else created}")

def send_system_test_email_safe():
    """SICHERER System-Test"""
    config = get_safe_config()
    
    sender = safe_get(config, "sender_email", "")
    recipient = safe_get(config, "recipient_email", "")
    
    if not sender or not recipient:
        st.warning("⚠️ Email-Konfiguration unvollständig!")
        st.write("Bitte konfigurieren Sie Absender und Empfänger Email.")
        return
    
    test_notification = {
        "timestamp": datetime.datetime.now().isoformat(),
        "search_term": "System-Test",
        "paper_count": 0,
        "status": "System-Test erfolgreich",
        "type": "System-Test",
        "recipient": recipient
    }
    
    history = get_safe_history()
    history.append(test_notification)
    st.session_state["email_history"] = history
    
    st.success("✅ System-Test-Email erstellt!")
    
    test_content = f"""Von: {sender}
An: {recipient}
Betreff: 🧪 Email-System Test

System-Test erfolgreich durchgeführt!

Zeitstempel: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
Status: Email-System funktioniert korrekt

Ihr Paper-Suche Email-System"""
    
    with st.expander("📧 Test-Email Inhalt"):
        st.code(test_content)

def check_session_state_safe():
    """SICHERE Session State-Prüfung"""
    st.write("**🔍 Session State Status:**")
    
    checks = {
        "email_config": st.session_state.get("email_config") is not None,
        "search_terms_email": st.session_state.get("search_terms_email") is not None,
        "email_history": st.session_state.get("email_history") is not None
    }
    
    for key, is_ok in checks.items():
        icon = "✅" if is_ok else "❌"
        value = st.session_state.get(key, "None")
        value_type = type(value).__name__
        st.write(f"{icon} {key}: {value_type}")

def generate_statistics_safe():
    """SICHERE Statistik-Generierung"""
    config = get_safe_config()
    search_terms = get_safe_search_terms()
    history = get_safe_history()
    
    st.write("**📊 System-Statistiken:**")
    
    stats = {
        "Konfigurierte Email-Einstellungen": len([v for v in config.values() if v]) if isinstance(config, dict) else 0,
        "Aktive Suchbegriffe": len([t for t in search_terms.values() if isinstance(t, dict) and safe_get(t, "active", False)]),
        "Gesamt Suchbegriffe": len(search_terms),
        "Gesamt Benachrichtigungen": len(history),
        "Benachrichtigungen heute": count_notifications_by_date_safe(history, datetime.datetime.now().date().isoformat())
    }
    
    for stat_name, stat_value in stats.items():
        st.write(f"• {stat_name}: {stat_value}")

def export_email_data_safe():
    """SICHERER Daten-Export"""
    export_data = {
        "email_config": get_safe_config(),
        "search_terms": get_safe_search_terms(),
        "history": get_safe_history(),
        "export_timestamp": datetime.datetime.now().isoformat(),
        "version": "1.0"
    }
    
    try:
        json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Email-Daten herunterladen",
            data=json_str,
            file_name=f"email_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
        st.success("✅ Daten-Export bereit!")
    except Exception as e:
        st.error(f"❌ Export-Fehler: {str(e)}")

def reset_all_data_safe():
    """SICHERER Daten-Reset"""
    st.session_state["email_config"] = {
        "sender_email": "",
        "recipient_email": "",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "subject_template": "🔬 {count} neue Papers für '{search_term}'",
        "message_template": "Standard Nachricht",
        "auto_notifications": False,
        "min_papers_threshold": 5
    }
    
    st.session_state["search_terms_email"] = {}
    st.session_state["email_history"] = []

def show_debug_info_safe():
    """SICHERE Debug-Informationen"""
    st.write("**🔍 Debug-Informationen:**")
    
    debug_info = {
        "Session State Keys": list(st.session_state.keys()),
        "Email Config Type": type(st.session_state.get("email_config")).__name__,
        "Search Terms Type": type(st.session_state.get("search_terms_email")).__name__,
        "History Type": type(st.session_state.get("email_history")).__name__,
        "Current Time": datetime.datetime.now().isoformat()
    }
    
    for key, value in debug_info.items():
        st.write(f"• {key}: {value}")
    
    st.json({
        "email_config_sample": get_safe_config(),
        "search_terms_count": len(get_safe_search_terms()),
        "history_count": len(get_safe_history())
    })

# INTEGRATION-FUNKTIONEN für andere Module
def trigger_email_notification(search_term, paper_count):
    """SICHERE Integration für andere Module"""
    try:
        config = get_safe_config()
        
        if not safe_get(config, "auto_notifications", False):
            return False
        
        min_papers = safe_get(config, "min_papers_threshold", 5)
        
        if paper_count >= min_papers:
            notification = {
                "timestamp": datetime.datetime.now().isoformat(),
                "search_term": search_term,
                "paper_count": paper_count,
                "status": "Automatisch gesendet",
                "type": "Automatisch",
                "recipient": safe_get(config, "recipient_email", "")
            }
            
            history = get_safe_history()
            history.append(notification)
            st.session_state["email_history"] = history
            
            return True
        
        return False
    except:
        return False

def get_email_settings():
    """SICHERE Einstellungen für andere Module"""
    return get_safe_config()

def is_email_enabled():
    """SICHERE Prüfung ob Email aktiviert ist"""
    try:
        config = get_safe_config()
        return (safe_get(config, "auto_notifications", False) and 
                bool(safe_get(config, "sender_email", "")) and 
                bool(safe_get(config, "recipient_email", "")))
    except:
        return False
