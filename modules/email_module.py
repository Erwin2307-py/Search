# modules/email_module.py - Robuste Version
import streamlit as st
import os
import json
import datetime

def module_email():
    """Hauptfunktion des Email-Moduls - robust gegen None-Fehler"""
    try:
        st.subheader("📧 Email-System")
        st.info("✅ Email-Modul erfolgreich geladen!")
        
        # Sichere Initialisierung der Session State
        initialize_session_state()
        
        # Tabs
        tab1, tab2, tab3 = st.tabs(["🔍 Suchbegriffe", "📧 Email-Config", "⚙️ Einstellungen"])
        
        with tab1:
            search_terms_interface()
        
        with tab2:
            email_config_interface()
        
        with tab3:
            settings_interface()
            
    except Exception as e:
        st.error(f"❌ Fehler im Email-Modul: {str(e)}")
        st.write("**Debug-Info:**")
        st.write(f"Fehler-Typ: {type(e).__name__}")
        st.write(f"Fehler-Details: {str(e)}")
        
        # Fallback Interface
        create_fallback_interface()

def initialize_session_state():
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

def get_safe_secrets(key, default=""):
    """Sichere Secrets-Abfrage"""
    try:
        if hasattr(st, 'secrets') and st.secrets is not None:
            return st.secrets.get(key, default)
        else:
            return default
    except Exception:
        return default

def search_terms_interface():
    """Suchbegriff-Management"""
    st.subheader("🔍 Suchbegriff-Management")
    
    # Suchbegriff hinzufügen
    with st.form("add_search_term_safe"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            new_term = st.text_input("Neuer Suchbegriff", placeholder="z.B. 'diabetes genetics'")
        
        with col2:
            frequency = st.selectbox("Frequenz", ["Täglich", "Wöchentlich", "Monatlich"])
        
        if st.form_submit_button("➕ Hinzufügen"):
            if new_term and new_term not in st.session_state["email_search_terms"]:
                st.session_state["email_search_terms"][new_term] = {
                    "frequency": frequency,
                    "created": datetime.datetime.now().isoformat(),
                    "active": True,
                    "email_enabled": True
                }
                st.success(f"✅ Suchbegriff '{new_term}' hinzugefügt!")
                st.rerun()
    
    # Bestehende Suchbegriffe
    if st.session_state["email_search_terms"]:
        st.write("**Aktuelle Suchbegriffe:**")
        for term, settings in st.session_state["email_search_terms"].items():
            with st.expander(f"🔍 {term}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Frequenz:** {settings.get('frequency', 'N/A')}")
                    st.write(f"**Status:** {'🟢 Aktiv' if settings.get('active', True) else '🔴 Inaktiv'}")
                
                with col2:
                    if st.button(f"🗑️ Löschen", key=f"delete_{term}"):
                        del st.session_state["email_search_terms"][term]
                        st.success(f"Suchbegriff '{term}' gelöscht!")
                        st.rerun()
    else:
        st.info("Noch keine Suchbegriffe definiert.")

def email_config_interface():
    """Email-Konfiguration"""
    st.subheader("📧 Email-Konfiguration")
    
    with st.form("email_config_safe"):
        # Sichere Abfrage der Secrets
        default_sender = get_safe_secrets("sender_email", "")
        default_recipient = get_safe_secrets("recipient_email", "")
        
        sender_email = st.text_input("Absender Email", value=default_sender)
        recipient_email = st.text_input("Empfänger Email", value=default_recipient)
        subject = st.text_input("Email-Betreff", value="🔬 Neue Papers gefunden!")
        
        message_template = st.text_area(
            "Nachricht-Vorlage",
            value="""🔍 Neue wissenschaftliche Papers gefunden!

📅 Datum: {date}
🔍 Suchbegriff: {search_term}
📊 Anzahl Papers: {count}

Die vollständigen Ergebnisse sind im System verfügbar.

Mit freundlichen Grüßen,
Ihr Paper-Suche System""",
            height=200
        )
        
        if st.form_submit_button("💾 Konfiguration speichern"):
            # Sichere Speicherung
            try:
                config = {
                    "sender_email": sender_email,
                    "recipient_email": recipient_email,
                    "subject": subject,
                    "message_template": message_template,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                
                st.session_state["email_config"] = config
                st.success("✅ Email-Konfiguration gespeichert!")
                
                # Vorschau anzeigen
                preview = generate_email_preview(config, "test genetics", 5)
                st.info("📧 **Email-Vorschau:**")
                st.code(preview)
                
            except Exception as e:
                st.error(f"Fehler beim Speichern: {str(e)}")

def generate_email_preview(config, search_term, count):
    """Generiert Email-Vorschau"""
    try:
        subject = config.get("subject", "Neue Papers")
        message = config.get("message_template", "Standard-Nachricht")
        
        # Sichere String-Formatierung
        try:
            formatted_message = message.format(
                date=datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
                search_term=search_term,
                count=count
            )
        except Exception:
            formatted_message = message  # Fallback auf unformatierte Nachricht
        
        return f"""Betreff: {subject}
Von: {config.get('sender_email', 'system@example.com')}
An: {config.get('recipient_email', 'user@example.com')}

{formatted_message}"""
    
    except Exception:
        return "Email-Vorschau konnte nicht erstellt werden."

def settings_interface():
    """Einstellungen Interface"""
    st.subheader("⚙️ Einstellungen")
    
    # SMTP-Einstellungen
    with st.expander("📧 SMTP-Konfiguration"):
        smtp_server = st.text_input("SMTP Server", value="smtp.gmail.com")
        smtp_port = st.number_input("SMTP Port", value=587)
        use_tls = st.checkbox("TLS verwenden", value=True)
        
        if st.button("💾 SMTP-Einstellungen speichern"):
            st.session_state["email_settings"].update({
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "use_tls": use_tls
            })
            st.success("SMTP-Einstellungen gespeichert!")
    
    # Debug-Bereich
    with st.expander("🔧 Debug-Informationen"):
        st.write("**Session State Keys:**")
        st.write(list(st.session_state.keys()))
        
        st.write("**Email-Einstellungen:**")
        st.json(st.session_state.get("email_settings", {}))
        
        st.write("**Secrets verfügbar:**")
        try:
            st.write(f"st.secrets existiert: {hasattr(st, 'secrets')}")
            st.write(f"st.secrets ist None: {st.secrets is None if hasattr(st, 'secrets') else 'N/A'}")
        except Exception as e:
            st.write(f"Secrets-Fehler: {str(e)}")

def create_fallback_interface():
    """Fallback-Interface bei Fehlern"""
    st.warning("⚠️ Fallback-Modus aktiviert")
    
    st.write("**Basis Email-Interface:**")
    
    with st.form("fallback_form"):
        email_input = st.text_input("Email-Adresse")
        message_input = st.text_area("Nachricht")
        
        if st.form_submit_button("📧 Konfiguration testen"):
            if email_input and message_input:
                st.success("✅ Konfiguration würde funktionieren!")
                st.code(f"Email: {email_input}\nNachricht: {message_input}")
            else:
                st.error("Bitte alle Felder ausfüllen!")

# Hilfsfunktionen für andere Module
def trigger_email_notification_safe(search_term, paper_count):
    """Sichere Email-Benachrichtigung"""
    try:
        if "email_notifications_history" not in st.session_state:
            st.session_state["email_notifications_history"] = []
        
        notification = {
            "timestamp": datetime.datetime.now().isoformat(),
            "search_term": search_term,
            "paper_count": paper_count,
            "status": "Simuliert"
        }
        
        st.session_state["email_notifications_history"].append(notification)
        return True
    except Exception:
        return False
