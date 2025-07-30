# modules/email_module.py
import streamlit as st
import os
import json
import datetime
import pandas as pd
import re

def module_email():
    """Haupt-Email-Modul Funktion - Diese Funktion wird vom Hauptskript importiert"""
    st.subheader("📧 Email-System mit Paper-Suche Integration")
    
    st.info("⚠️ Email-Funktionalität mit vereinfachter Implementierung")
    
    # Initialize session state
    if "email_search_terms" not in st.session_state:
        st.session_state["email_search_terms"] = {}
    if "email_notifications_history" not in st.session_state:
        st.session_state["email_notifications_history"] = []
    if "email_settings" not in st.session_state:
        st.session_state["email_settings"] = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "",
            "default_recipient": "",
            "auto_notifications": False
        }
    
    # Tabs für verschiedene Funktionen
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Suchbegriff-Management", 
        "📤 Email Konfiguration", 
        "📊 Verlauf",
        "⚙️ Einstellungen"
    ])
    
    with tab1:
        search_terms_management()
    
    with tab2:
        email_configuration_interface()
    
    with tab3:
        notification_history_interface()
    
    with tab4:
        email_settings_interface()

def search_terms_management():
    """Suchbegriff-Management Interface"""
    st.subheader("🔍 Suchbegriff-Management für Email-Benachrichtigungen")
    
    # Neue Suchbegriffe hinzufügen
    st.write("**Neue Suchbegriffe hinzufügen:**")
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        new_search_term = st.text_input("Suchbegriff", placeholder="z.B. 'diabetes genetics'")
    with col2:
        search_frequency = st.selectbox("Email-Frequenz", ["Bei jeder Suche", "Täglich", "Wöchentlich", "Monatlich"])
    with col3:
        if st.button("➕ Hinzufügen"):
            if new_search_term and new_search_term not in st.session_state["email_search_terms"]:
                st.session_state["email_search_terms"][new_search_term] = {
                    "frequency": search_frequency,
                    "created": datetime.datetime.now().isoformat(),
                    "last_notification": None,
                    "active": True,
                    "email_enabled": True
                }
                st.success(f"Suchbegriff '{new_search_term}' hinzugefügt!")
                st.rerun()
    
    # Bestehende Suchbegriffe anzeigen
    if st.session_state["email_search_terms"]:
        st.write("**Aktuelle Suchbegriffe mit Email-Benachrichtigung:**")
        
        for term, info in st.session_state["email_search_terms"].items():
            with st.expander(f"🔍 {term}"):
                col_info1, col_info2, col_info3 = st.columns(3)
                
                with col_info1:
                    st.write(f"**Frequenz:** {info.get('frequency', 'N/A')}")
                    st.write(f"**Erstellt:** {info.get('created', 'N/A')[:10]}")
                
                with col_info2:
                    last_notification = info.get('last_notification', 'Nie')
                    st.write(f"**Letzte Email:** {last_notification[:19] if last_notification != 'Nie' else last_notification}")
                    st.write(f"**Status:** {'🟢 Aktiv' if info.get('active', True) else '🔴 Inaktiv'}")
                
                with col_info3:
                    if st.button(f"🗑️ Löschen", key=f"delete_{term}"):
                        del st.session_state["email_search_terms"][term]
                        st.success(f"Suchbegriff '{term}' gelöscht!")
                        st.rerun()
                    
                    info["active"] = st.checkbox("Aktiv", value=info.get("active", True), key=f"active_{term}")
                    info["email_enabled"] = st.checkbox("Email aktiviert", value=info.get("email_enabled", True), key=f"email_{term}")
        
        # Testbenachrichtigung senden
        st.markdown("---")
        if st.button("📧 Test-Benachrichtigung senden"):
            send_test_notification()
    else:
        st.info("Noch keine Suchbegriffe für Email-Benachrichtigungen definiert.")

def email_configuration_interface():
    """Email-Konfiguration Interface"""
    st.subheader("📧 Email-Konfiguration")
    
    # Grundlegende Email-Einstellungen
    with st.form("email_config_form"):
        col_email1, col_email2 = st.columns(2)
        
        with col_email1:
            sender_email = st.text_input("Absender Email", value=st.session_state["email_settings"].get("sender_email", ""))
            subject_template = st.text_input("Email-Betreff Vorlage", value="🔬 Neue Papers gefunden: {count} Ergebnisse")
        
        with col_email2:
            recipient_email = st.text_input("Empfänger Email", value=st.session_state["email_settings"].get("default_recipient", ""))
            notification_threshold = st.number_input("Min. Papers für Benachrichtigung", min_value=1, value=5)
        
        # Email-Inhalt Vorlage
        email_template = st.text_area(
            "Email-Inhalt Vorlage",
            value="""🔍 Paper-Suche Ergebnisse

📅 Datum: {date}
🔍 Suchbegriff: {search_term}
📊 Gefundene Papers: {count}

🔗 Top Papers:
{top_papers}

Vollständige Ergebnisse sind im Dashboard verfügbar.

Mit freundlichen Grüßen,
Ihr automatisches Paper-Suche System""",
            height=200
        )
        
        submitted = st.form_submit_button("💾 Email-Konfiguration speichern")
        
        if submitted:
            # Speichere Konfiguration
            st.session_state["email_settings"].update({
                "sender_email": sender_email,
                "default_recipient": recipient_email,
                "subject_template": subject_template,
                "email_template": email_template,
                "notification_threshold": notification_threshold
            })
            
            st.success("✅ Email-Konfiguration gespeichert!")
            
            # Zeige Vorschau
            st.info("📧 **Email-Vorschau:**")
            preview = generate_email_preview(
                search_term="diabetes genetics",
                count=12,
                top_papers=["Paper 1: Diabetes and genetic markers", "Paper 2: Genetic variants in T2D", "Paper 3: GWAS study results"]
            )
            st.code(preview, language="text")

def generate_email_preview(search_term, count, top_papers):
    """Generiert Email-Vorschau"""
    settings = st.session_state["email_settings"]
    
    subject = settings.get("subject_template", "Neue Papers gefunden").format(count=count)
    
    body = settings.get("email_template", "Standard Template").format(
        date=datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
        search_term=search_term,
        count=count,
        top_papers="\n".join([f"• {paper}" for paper in top_papers])
    )
    
    return f"""Betreff: {subject}
Von: {settings.get('sender_email', 'system@example.com')}
An: {settings.get('default_recipient', 'user@example.com')}

{body}"""

def notification_history_interface():
    """Benachrichtigungs-Verlauf Interface"""
    st.subheader("📊 Email-Benachrichtigungs-Verlauf")
    
    if st.session_state["email_notifications_history"]:
        # Filter und Anzeige-Optionen
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            date_filter = st.date_input("Ab Datum:", value=datetime.datetime.now() - datetime.timedelta(days=30))
        
        with col_f2:
            show_count = st.number_input("Anzahl anzeigen:", min_value=5, max_value=100, value=20)
        
        # Gefilterte Historie
        filtered_history = []
        for notification in st.session_state["email_notifications_history"]:
            notification_date = datetime.datetime.fromisoformat(notification["timestamp"]).date()
            if notification_date >= date_filter:
                filtered_history.append(notification)
        
        filtered_history = filtered_history[-show_count:]
        
        if filtered_history:
            # Historie als Tabelle
            history_data = []
            for notification in reversed(filtered_history):
                timestamp = datetime.datetime.fromisoformat(notification["timestamp"])
                history_data.append({
                    "Datum": timestamp.strftime("%d.%m.%Y %H:%M"),
                    "Empfänger": notification.get("recipient", "N/A"),
                    "Suchbegriff": notification.get("search_term", "N/A"),
                    "Papers": notification.get("paper_count", 0),
                    "Status": notification.get("status", "Gesendet")
                })
            
            df = pd.DataFrame(history_data)
            st.dataframe(df, use_container_width=True)
            
            # Statistiken
            col_s1, col_s2, col_s3 = st.columns(3)
            
            with col_s1:
                st.metric("Gesamt Benachrichtigungen", len(st.session_state["email_notifications_history"]))
            
            with col_s2:
                recent_count = len([n for n in st.session_state["email_notifications_history"] 
                                  if datetime.datetime.fromisoformat(n["timestamp"]).date() >= datetime.datetime.now().date() - datetime.timedelta(days=7)])
                st.metric("Diese Woche", recent_count)
            
            with col_s3:
                today_count = len([n for n in st.session_state["email_notifications_history"] 
                                 if datetime.datetime.fromisoformat(n["timestamp"]).date() == datetime.datetime.now().date()])
                st.metric("Heute", today_count)
        else:
            st.info("Keine Benachrichtigungen im ausgewählten Zeitraum.")
    else:
        st.info("Noch keine Email-Benachrichtigungen versendet.")
    
    # Verlauf löschen
    if st.session_state["email_notifications_history"]:
        st.markdown("---")
        if st.button("🗑️ Verlauf löschen"):
            if st.checkbox("Löschung des Email-Verlaufs bestätigen"):
                st.session_state["email_notifications_history"] = []
                st.success("Email-Verlauf gelöscht!")
                st.rerun()

def email_settings_interface():
    """Email-Einstellungen Interface"""
    st.subheader("⚙️ Email-System Einstellungen")
    
    settings = st.session_state["email_settings"]
    
    # SMTP-Konfiguration
    with st.expander("📧 SMTP-Konfiguration", expanded=True):
        col_smtp1, col_smtp2 = st.columns(2)
        
        with col_smtp1:
            settings["smtp_server"] = st.text_input("SMTP Server:", value=settings.get("smtp_server", "smtp.gmail.com"))
            settings["use_tls"] = st.checkbox("TLS verwenden", value=settings.get("use_tls", True))
        
        with col_smtp2:
            settings["smtp_port"] = st.number_input("SMTP Port:", value=settings.get("smtp_port", 587))
            settings["smtp_timeout"] = st.number_input("Timeout (Sekunden):", value=settings.get("smtp_timeout", 30))
    
    # Automatisierung
    with st.expander("🤖 Automatisierung", expanded=True):
        settings["auto_notifications"] = st.checkbox("Automatische Benachrichtigungen", value=settings.get("auto_notifications", False))
        
        if settings["auto_notifications"]:
            col_auto1, col_auto2 = st.columns(2)
            
            with col_auto1:
                settings["check_interval"] = st.selectbox(
                    "Prüfungsintervall:",
                    ["Jede Stunde", "Alle 6 Stunden", "Täglich", "Wöchentlich"],
                    index=2
                )
            
            with col_auto2:
                settings["batch_notifications"] = st.checkbox("Sammel-Benachrichtigungen", value=settings.get("batch_notifications", True))
    
    # Template-Verwaltung
    with st.expander("📋 Email-Vorlagen", expanded=False):
        template_options = {
            "Standard": "🔬 Neue Papers gefunden: {count} Ergebnisse",
            "Kurz": "📊 {count} neue Papers für '{search_term}'",
            "Detailliert": "🔍 Paper-Suche Update: {count} Ergebnisse zu '{search_term}' vom {date}"
        }
        
        selected_template = st.selectbox("Betreff-Vorlage wählen:", list(template_options.keys()))
        if selected_template:
            settings["subject_template"] = template_options[selected_template]
            st.code(template_options[selected_template])
    
    # Speichern
    if st.button("💾 Alle Einstellungen speichern"):
        st.session_state["email_settings"] = settings
        st.success("✅ Einstellungen gespeichert!")
    
    # Debug-Informationen
    with st.expander("🔧 Debug-Informationen", expanded=False):
        st.json(settings)

def send_test_notification():
    """Sendet eine Test-Benachrichtigung"""
    settings = st.session_state["email_settings"]
    
    # Erstelle Test-Benachrichtigung
    test_notification = {
        "timestamp": datetime.datetime.now().isoformat(),
        "recipient": settings.get("default_recipient", "test@example.com"),
        "search_term": "Test-Suchbegriff",
        "paper_count": 5,
        "status": "Test-Benachrichtigung",
        "type": "test"
    }
    
    # Füge zur Historie hinzu
    st.session_state["email_notifications_history"].append(test_notification)
    
    # Zeige Vorschau
    preview = generate_email_preview(
        search_term="Test-Suchbegriff",
        count=5,
        top_papers=[
            "Test Paper 1: Example title about genetics",
            "Test Paper 2: Another example paper",
            "Test Paper 3: Third test paper"
        ]
    )
    
    st.success("✅ Test-Benachrichtigung erstellt!")
    st.info("📧 **Test-Email Vorschau:**")
    st.code(preview, language="text")

# Zusätzliche Hilfsfunktionen für Integration mit Paper-Suche
def trigger_email_notification(search_term, papers_found, search_results=None):
    """Wird von anderen Modulen aufgerufen, um Email-Benachrichtigung auszulösen"""
    settings = st.session_state.get("email_settings", {})
    search_terms = st.session_state.get("email_search_terms", {})
    
    # Prüfe ob Email für diesen Suchbegriff aktiviert ist
    if search_term in search_terms and search_terms[search_term].get("email_enabled", False):
        threshold = settings.get("notification_threshold", 5)
        
        if papers_found >= threshold:
            # Erstelle Benachrichtigung
            notification = {
                "timestamp": datetime.datetime.now().isoformat(),
                "recipient": settings.get("default_recipient", ""),
                "search_term": search_term,
                "paper_count": papers_found,
                "status": "Automatisch gesendet",
                "type": "automatic"
            }
            
            # Füge zur Historie hinzu
            if "email_notifications_history" not in st.session_state:
                st.session_state["email_notifications_history"] = []
            
            st.session_state["email_notifications_history"].append(notification)
            
            # Update letzte Benachrichtigung
            search_terms[search_term]["last_notification"] = datetime.datetime.now().isoformat()
            
            return True
    
    return False

def get_email_configuration():
    """Gibt aktuelle Email-Konfiguration zurück für andere Module"""
    return st.session_state.get("email_settings", {})

def is_email_enabled_for_term(search_term):
    """Prüft ob Email für einen Suchbegriff aktiviert ist"""
    search_terms = st.session_state.get("email_search_terms", {})
    return search_terms.get(search_term, {}).get("email_enabled", False)
