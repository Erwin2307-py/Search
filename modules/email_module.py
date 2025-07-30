# modules/email_module.py
import streamlit as st
import os
import json
import datetime
import pandas as pd

def module_email():
    """Haupt-Email-Modul Funktion - DIESE FUNKTION MUSS EXISTIEREN"""
    st.subheader("📧 Email-System")
    st.info("✅ Email-Modul erfolgreich geladen!")
    
    # Sichere Initialisierung
    initialize_email_session_state()
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["🔍 Suchbegriffe", "📧 Email-Config", "⚙️ Einstellungen"])
    
    with tab1:
        search_terms_interface()
    
    with tab2:
        email_configuration_interface()
    
    with tab3:
        email_settings_interface()

def initialize_email_session_state():
    """Sichere Initialisierung des Session State"""
    defaults = {
        "email_search_terms": {},
        "email_notifications_history": [],
        "email_settings": {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "",
            "default_recipient": "",
            "auto_notifications": False
        }
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def search_terms_interface():
    """Suchbegriff-Management für Email-Benachrichtigungen"""
    st.subheader("🔍 Suchbegriff-Management")
    
    # Neuen Suchbegriff hinzufügen
    with st.form("add_email_search_term"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            new_term = st.text_input("Email-Suchbegriff", placeholder="z.B. 'diabetes genetics'")
        
        with col2:
            frequency = st.selectbox("Email-Frequenz", ["Bei jeder Suche", "Täglich", "Wöchentlich"])
        
        if st.form_submit_button("➕ Hinzufügen"):
            if new_term and new_term not in st.session_state["email_search_terms"]:
                st.session_state["email_search_terms"][new_term] = {
                    "frequency": frequency,
                    "created": datetime.datetime.now().isoformat(),
                    "active": True,
                    "email_enabled": True
                }
                st.success(f"✅ Email-Suchbegriff '{new_term}' hinzugefügt!")
                st.rerun()
    
    # Bestehende Suchbegriffe anzeigen
    if st.session_state["email_search_terms"]:
        st.write("**Aktuelle Email-Suchbegriffe:**")
        for term, settings in st.session_state["email_search_terms"].items():
            with st.expander(f"🔍 {term}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Frequenz:** {settings.get('frequency', 'N/A')}")
                    st.write(f"**Status:** {'🟢 Aktiv' if settings.get('active', True) else '🔴 Inaktiv'}")
                
                with col2:
                    if st.button(f"🗑️ Löschen", key=f"delete_email_{term}"):
                        del st.session_state["email_search_terms"][term]
                        st.success(f"Email-Suchbegriff '{term}' gelöscht!")
                        st.rerun()
                    
                    settings["active"] = st.checkbox("Aktiv", value=settings.get("active", True), key=f"active_email_{term}")
    else:
        st.info("Noch keine Email-Suchbegriffe definiert.")

def email_configuration_interface():
    """Email-Konfiguration Interface"""
    st.subheader("📧 Email-Konfiguration")
    
    with st.form("email_config"):
        col1, col2 = st.columns(2)
        
        with col1:
            sender_email = st.text_input("Absender Email", value=get_safe_secret("sender_email", ""))
            subject_template = st.text_input("Betreff-Vorlage", value="🔬 Neue Papers gefunden: {count}")
        
        with col2:
            recipient_email = st.text_input("Empfänger Email", value=get_safe_secret("recipient_email", ""))
            min_papers = st.number_input("Min. Papers für Email", min_value=1, value=5)
        
        message_template = st.text_area(
            "Email-Nachricht Vorlage",
            value="""🔍 Neue wissenschaftliche Papers gefunden!

📅 Datum: {date}
🔍 Suchbegriff: {search_term}
📊 Anzahl Papers: {count}

Die vollständigen Ergebnisse sind im System verfügbar.

Mit freundlichen Grüßen,
Ihr Paper-Suche System""",
            height=200
        )
        
        if st.form_submit_button("💾 Email-Konfiguration speichern"):
            config = {
                "sender_email": sender_email,
                "recipient_email": recipient_email,
                "subject_template": subject_template,
                "message_template": message_template,
                "min_papers": min_papers,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            st.session_state["email_config"] = config
            st.success("✅ Email-Konfiguration gespeichert!")
            
            # Vorschau
            preview = generate_email_preview(config, "test search", 7)
            st.info("📧 **Email-Vorschau:**")
            st.code(preview)

def email_settings_interface():
    """Email-Einstellungen Interface"""
    st.subheader("⚙️ Email-Einstellungen")
    
    settings = st.session_state["email_settings"]
    
    # SMTP-Einstellungen
    with st.expander("📧 SMTP-Konfiguration", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            settings["smtp_server"] = st.text_input("SMTP Server", value=settings.get("smtp_server", "smtp.gmail.com"))
            settings["sender_email"] = st.text_input("Standard Absender", value=settings.get("sender_email", ""))
        
        with col2:
            settings["smtp_port"] = st.number_input("SMTP Port", value=settings.get("smtp_port", 587))
            settings["default_recipient"] = st.text_input("Standard Empfänger", value=settings.get("default_recipient", ""))
    
    # Automatisierung
    with st.expander("🤖 Automatisierung"):
        settings["auto_notifications"] = st.checkbox("Automatische Email-Benachrichtigungen", value=settings.get("auto_notifications", False))
        
        if settings["auto_notifications"]:
            settings["notification_frequency"] = st.selectbox(
                "Benachrichtigungs-Frequenz",
                ["Sofort", "Täglich", "Wöchentlich"],
                index=1
            )
    
    if st.button("💾 Einstellungen speichern"):
        st.session_state["email_settings"] = settings
        st.success("✅ Email-Einstellungen gespeichert!")
    
    # Test-Email
    if st.button("📧 Test-Email senden"):
        send_test_email()

def get_safe_secret(key, default=""):
    """Sichere Secrets-Abfrage"""
    try:
        if hasattr(st, 'secrets') and st.secrets is not None:
            return st.secrets.get(key, default)
        else:
            return default
    except Exception:
        return default

def generate_email_preview(config, search_term, count):
    """Generiert Email-Vorschau"""
    try:
        subject = config.get("subject_template", "Neue Papers").format(count=count)
        message = config.get("message_template", "Standard-Nachricht")
        
        formatted_message = message.format(
            date=datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
            search_term=search_term,
            count=count
        )
        
        return f"""Von: {config.get('sender_email', 'system@example.com')}
An: {config.get('recipient_email', 'user@example.com')}
Betreff: {subject}

{formatted_message}"""
    
    except Exception as e:
        return f"Email-Vorschau-Fehler: {str(e)}"

def send_test_email():
    """Sendet Test-Email (Simulation)"""
    config = st.session_state.get("email_config", {})
    
    if not config:
        st.warning("⚠️ Bitte konfigurieren Sie zuerst die Email-Einstellungen!")
        return
    
    # Erstelle Test-Benachrichtigung
    test_notification = {
        "timestamp": datetime.datetime.now().isoformat(),
        "recipient": config.get("recipient_email", "test@example.com"),
        "search_term": "Test-Suchbegriff",
        "paper_count": 3,
        "status": "Test-Email gesendet",
        "type": "test"
    }
    
    # Zur Historie hinzufügen
    if "email_notifications_history" not in st.session_state:
        st.session_state["email_notifications_history"] = []
    
    st.session_state["email_notifications_history"].append(test_notification)
    
    st.success("✅ Test-Email wurde simuliert und zur Historie hinzugefügt!")
    
    # Zeige Vorschau
    preview = generate_email_preview(config, "Test-Suchbegriff", 3)
    st.info("📧 **Test-Email Vorschau:**")
    st.code(preview)

# Hilfsfunktionen für andere Module
def trigger_email_notification(search_term, papers_found):
    """Wird von anderen Modulen aufgerufen"""
    try:
        settings = st.session_state.get("email_settings", {})
        config = st.session_state.get("email_config", {})
        
        min_papers = config.get("min_papers", 5)
        
        if papers_found >= min_papers:
            notification = {
                "timestamp": datetime.datetime.now().isoformat(),
                "search_term": search_term,
                "paper_count": papers_found,
                "status": "Automatisch gesendet",
                "type": "automatic"
            }
            
            if "email_notifications_history" not in st.session_state:
                st.session_state["email_notifications_history"] = []
            
            st.session_state["email_notifications_history"].append(notification)
            return True
    except Exception:
        return False

def get_email_settings():
    """Gibt Email-Einstellungen zurück"""
    return st.session_state.get("email_settings", {})
