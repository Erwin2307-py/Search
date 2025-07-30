# modules/email_module.py - FUNKTIONIERENDE VERSION
import streamlit as st
import datetime

def module_email():
    """DIESE FUNKTION MUSS EXISTIEREN - Haupt-Email-Modul"""
    st.subheader("📧 Email-Benachrichtigungen für Paper-Suche")
    st.success("✅ Email-Modul erfolgreich geladen!")
    
    # Sichere Session State Initialisierung
    if "email_settings" not in st.session_state:
        st.session_state["email_settings"] = {
            "sender_email": "",
            "recipient_email": "",
            "auto_notifications": False,
            "min_papers": 5
        }
    
    if "email_history" not in st.session_state:
        st.session_state["email_history"] = []
    
    # Tabs für Email-Funktionen
    tab1, tab2, tab3 = st.tabs(["📧 Konfiguration", "📋 Verlauf", "🧪 Tests"])
    
    with tab1:
        show_email_config()
    
    with tab2:
        show_email_history()
    
    with tab3:
        show_email_tests()

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
            # Speichere Einstellungen
            st.session_state["email_settings"] = {
                "sender_email": sender_email,
                "recipient_email": recipient_email,
                "auto_notifications": auto_notifications,
                "min_papers": min_papers,
                "subject_template": subject_template,
                "message_template": message_template
            }
            
            st.success("✅ Email-Einstellungen erfolgreich gespeichert!")
            
            # Zeige Vorschau
            if sender_email and recipient_email:
                preview = generate_email_preview(
                    st.session_state["email_settings"], 
                    "diabetes genetics", 
                    7
                )
                st.info("📧 **Email-Vorschau:**")
                st.code(preview, language="text")

def show_email_history():
    """Email-Verlauf anzeigen"""
    st.write("**📊 Email-Benachrichtigungs-Verlauf:**")
    
    history = st.session_state.get("email_history", [])
    
    if history:
        # Statistiken
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📧 Gesamt Emails", len(history))
        
        with col2:
            today = datetime.datetime.now().date().isoformat()
            today_count = len([h for h in history if h.get("date", "").startswith(today)])
            st.metric("📅 Heute", today_count)
        
        with col3:
            unique_terms = len(set(h.get("search_term", "") for h in history))
            st.metric("🔍 Suchbegriffe", unique_terms)
        
        # Verlaufsliste
        st.write("**📋 Letzte 10 Email-Benachrichtigungen:**")
        
        for i, email in enumerate(reversed(history[-10:]), 1):
            search_term = email.get("search_term", "Unbekannt")
            paper_count = email.get("paper_count", 0)
            timestamp = email.get("timestamp", "Unbekannt")[:19]
            
            with st.expander(f"📧 {i}. {search_term} - {paper_count} Papers ({timestamp})"):
                col_detail1, col_detail2 = st.columns(2)
                
                with col_detail1:
                    st.write(f"**Suchbegriff:** {search_term}")
                    st.write(f"**Papers gefunden:** {paper_count}")
                    st.write(f"**Zeitstempel:** {timestamp}")
                
                with col_detail2:
                    st.write(f"**An:** {email.get('recipient', 'N/A')}")
                    st.write(f"**Status:** {email.get('status', 'N/A')}")
                    st.write(f"**Typ:** {email.get('type', 'Standard')}")
        
        # Verlauf löschen
        if st.button("🗑️ Email-Verlauf löschen"):
            st.session_state["email_history"] = []
            st.success("Email-Verlauf gelöscht!")
            st.rerun()
    
    else:
        st.info("📭 Noch keine Email-Benachrichtigungen versendet.")

def show_email_tests():
    """Email-Test-Funktionen"""
    st.write("**🧪 Email-System testen:**")
    
    settings = st.session_state.get("email_settings", {})
    
    # Konfigurationsstatus
    sender_ok = bool(settings.get("sender_email"))
    recipient_ok = bool(settings.get("recipient_email"))
    auto_ok = settings.get("auto_notifications", False)
    
    st.write("**📋 Konfigurations-Status:**")
    
    col_status1, col_status2 = st.columns(2)
    
    with col_status1:
        st.write(f"{'✅' if sender_ok else '❌'} **Absender Email:** {'Konfiguriert' if sender_ok else 'Fehlt'}")
        st.write(f"{'✅' if recipient_ok else '❌'} **Empfänger Email:** {'Konfiguriert' if recipient_ok else 'Fehlt'}")
    
    with col_status2:
        st.write(f"{'✅' if auto_ok else '❌'} **Auto-Benachrichtigungen:** {'Aktiviert' if auto_ok else 'Deaktiviert'}")
        st.write(f"**Min. Papers:** {settings.get('min_papers', 5)}")
    
    # Test-Funktionen
    st.write("**🧪 Test-Aktionen:**")
    
    col_test1, col_test2, col_test3 = st.columns(3)
    
    with col_test1:
        if st.button("📧 Test-Email senden"):
            if sender_ok and recipient_ok:
                send_test_email()
            else:
                st.error("❌ Email-Konfiguration unvollständig!")
    
    with col_test2:
        if st.button("🔧 Konfiguration prüfen"):
            check_configuration()
    
    with col_test3:
        if st.button("📊 Statistiken anzeigen"):
            show_statistics()

def send_test_email():
    """Sendet Test-Email (simuliert)"""
    settings = st.session_state.get("email_settings", {})
    
    # Test-Email zur Historie hinzufügen
    test_email = {
        "timestamp": datetime.datetime.now().isoformat(),
        "date": datetime.datetime.now().date().isoformat(),
        "search_term": "System-Test",
        "paper_count": 3,
        "recipient": settings.get("recipient_email", ""),
        "status": "Test erfolgreich (simuliert)",
        "type": "Test"
    }
    
    if "email_history" not in st.session_state:
        st.session_state["email_history"] = []
    
    st.session_state["email_history"].append(test_email)
    
    st.success("✅ Test-Email erfolgreich erstellt und zur Historie hinzugefügt!")
    
    # Email-Vorschau anzeigen
    preview = generate_email_preview(settings, "System-Test", 3)
    
    with st.expander("📧 Test-Email Vorschau anzeigen"):
        st.code(preview, language="text")

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

def check_configuration():
    """Prüft Email-Konfiguration"""
    settings = st.session_state.get("email_settings", {})
    
    st.write("**🔍 Detaillierte Konfigurationsprüfung:**")
    
    checks = [
        ("Absender Email", bool(settings.get("sender_email"))),
        ("Empfänger Email", bool(settings.get("recipient_email"))),
        ("Betreff-Vorlage", bool(settings.get("subject_template"))),
        ("Nachricht-Vorlage", bool(settings.get("message_template"))),
        ("Auto-Benachrichtigungen", settings.get("auto_notifications", False))
    ]
    
    all_configured = True
    for check_name, is_configured in checks:
        icon = "✅" if is_configured else "❌"
        status = "OK" if is_configured else "Fehlt/Deaktiviert"
        st.write(f"{icon} **{check_name}:** {status}")
        
        if not is_configured and check_name in ["Absender Email", "Empfänger Email"]:
            all_configured = False
    
    if all_configured:
        st.success("🎉 **Email-System ist vollständig konfiguriert und einsatzbereit!**")
    else:
        st.warning("⚠️ **Email-System benötigt noch Konfiguration.**")

def show_statistics():
    """Zeigt Email-Statistiken"""
    history = st.session_state.get("email_history", [])
    settings = st.session_state.get("email_settings", {})
    
    st.write("**📊 Email-System Statistiken:**")
    
    if history:
        total_emails = len(history)
        total_papers = sum(email.get("paper_count", 0) for email in history)
        avg_papers = total_papers / total_emails if total_emails > 0 else 0
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        
        with col_stat1:
            st.metric("📧 Gesamt Emails", total_emails)
        
        with col_stat2:
            st.metric("📄 Gesamt Papers", total_papers)
        
        with col_stat3:
            st.metric("📊 Ø Papers/Email", f"{avg_papers:.1f}")
        
        # Zeitstatistiken
        if total_emails > 1:
            first_email = min(email.get("timestamp", "") for email in history)
            last_email = max(email.get("timestamp", "") for email in history)
            
            st.write(f"**📅 Erste Email:** {first_email[:19] if first_email else 'N/A'}")
            st.write(f"**📅 Letzte Email:** {last_email[:19] if last_email else 'N/A'}")
    
    else:
        st.info("📭 Keine Email-Statistiken verfügbar - noch keine Emails versendet.")
    
    # Konfigurationsstatistiken
    st.write("**⚙️ Konfiguration:**")
    st.write(f"• **Auto-Benachrichtigungen:** {'Aktiviert' if settings.get('auto_notifications') else 'Deaktiviert'}")
    st.write(f"• **Min. Papers Schwelle:** {settings.get('min_papers', 5)}")

# Integration-Funktionen für andere Module
def trigger_email_notification(search_term, paper_count):
    """Wird von anderen Modulen aufgerufen um Email-Benachrichtigungen zu senden"""
    try:
        settings = st.session_state.get("email_settings", {})
        
        # Prüfe ob Auto-Benachrichtigungen aktiviert sind
        if not settings.get("auto_notifications", False):
            return False
        
        # Prüfe ob Mindest-Paper-Anzahl erreicht ist
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
            "type": "Automatisch"
        }
        
        # Zur Historie hinzufügen
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
