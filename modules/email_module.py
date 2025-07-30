# modules/email_module.py - Robuste Version
import streamlit as st
import datetime
import json
import os

def module_email():
    """Haupt-Email-Modul Funktion - ROBUSTE VERSION"""
    st.subheader("📧 Email-Benachrichtigungen für Paper-Suche")
    st.success("✅ External email module loaded successfully!")
    
    # ROBUSTE Session State Initialisierung
    initialize_email_session_state()
    
    # Tabs für verschiedene Funktionen
    tab1, tab2, tab3, tab4 = st.tabs([
        "📧 Email-Konfiguration", 
        "🔍 Suchbegriff-Benachrichtigungen", 
        "📊 Benachrichtigungs-Verlauf",
        "⚙️ Erweiterte Einstellungen"
    ])
    
    try:
        with tab1:
            email_configuration_interface()
        
        with tab2:
            search_terms_notification_interface()
        
        with tab3:
            notification_history_interface()
        
        with tab4:
            advanced_settings_interface()
    
    except Exception as e:
        st.error(f"❌ Fehler im Email-Modul: {str(e)}")
        st.write("**Debug-Info:**")
        st.write(f"Fehler-Typ: {type(e).__name__}")
        create_fallback_email_interface()

def initialize_email_session_state():
    """ROBUSTE Session State Initialisierung"""
    try:
        # Email-Einstellungen sicher initialisieren
        if "email_settings" not in st.session_state or st.session_state["email_settings"] is None:
            st.session_state["email_settings"] = {
                "sender_email": "",
                "recipient_email": "",
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "auto_notifications": False,
                "min_papers_threshold": 5,
                "subject_template": "🔬 {count} neue Papers gefunden für '{search_term}'",
                "message_template": """🔍 Neue wissenschaftliche Papers gefunden!

📅 Datum: {date}
🔍 Suchbegriff: '{search_term}'
📊 Anzahl neue Papers: {count}

🔗 Vollständige Ergebnisse im System verfügbar.

Mit freundlichen Grüßen,
Ihr automatisches Paper-Suche System"""
            }
        
        # Benachrichtigungs-Historie sicher initialisieren
        if "email_notifications_history" not in st.session_state or st.session_state["email_notifications_history"] is None:
            st.session_state["email_notifications_history"] = []
        
        # Suchbegriffe sicher initialisieren
        if "search_terms_email" not in st.session_state or st.session_state["search_terms_email"] is None:
            st.session_state["search_terms_email"] = {}
            
    except Exception as e:
        st.error(f"Fehler bei Session State Initialisierung: {str(e)}")
        # Fallback-Initialisierung
        st.session_state["email_settings"] = {}
        st.session_state["email_notifications_history"] = []
        st.session_state["search_terms_email"] = {}

def email_configuration_interface():
    """ROBUSTE Email-Konfiguration"""
    st.subheader("📧 Email-Konfiguration")
    
    try:
        settings = get_safe_email_settings()
        
        with st.form("email_config_form"):
            st.write("**📬 Grundlegende Email-Einstellungen:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                sender_email = st.text_input(
                    "Absender Email", 
                    value=settings.get("sender_email", "")
                )
                subject_template = st.text_input(
                    "Betreff-Vorlage", 
                    value=settings.get("subject_template", "🔬 {count} neue Papers für '{search_term}'")
                )
            
            with col2:
                recipient_email = st.text_input(
                    "Empfänger Email", 
                    value=settings.get("recipient_email", "")
                )
                smtp_server = st.text_input(
                    "SMTP Server", 
                    value=settings.get("smtp_server", "smtp.gmail.com")
                )
            
            message_template = st.text_area(
                "Nachricht-Vorlage",
                value=settings.get("message_template", "Standard Email-Vorlage"),
                height=200
            )
            
            if st.form_submit_button("💾 Email-Konfiguration speichern"):
                update_email_settings({
                    "sender_email": sender_email,
                    "recipient_email": recipient_email,
                    "smtp_server": smtp_server,
                    "subject_template": subject_template,
                    "message_template": message_template
                })
                st.success("✅ Email-Konfiguration gespeichert!")
                
                # Vorschau
                if sender_email and recipient_email:
                    preview = generate_safe_email_preview(
                        get_safe_email_settings(), 
                        "test search", 
                        5
                    )
                    st.info("📧 **Email-Vorschau:**")
                    st.code(preview, language="text")
    
    except Exception as e:
        st.error(f"❌ Fehler in Email-Konfiguration: {str(e)}")

def search_terms_notification_interface():
    """ROBUSTE Suchbegriff-Benachrichtigungen Interface"""
    st.subheader("🔍 Suchbegriff-Benachrichtigungen")
    
    try:
        # Neuen Suchbegriff hinzufügen
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
                    value=5
                )
            
            if st.form_submit_button("➕ Suchbegriff hinzufügen"):
                if search_term and search_term.strip():
                    add_search_term_safely(search_term, frequency, min_papers)
                    st.success(f"✅ Suchbegriff '{search_term}' hinzugefügt!")
                    st.rerun()
                else:
                    st.error("❌ Bitte geben Sie einen Suchbegriff ein!")
        
        # Bestehende Suchbegriffe SICHER anzeigen
        display_existing_search_terms()
    
    except Exception as e:
        st.error(f"❌ Fehler in Suchbegriff-Interface: {str(e)}")
        st.write("**Fallback-Interface:**")
        simple_search_term_interface()

def display_existing_search_terms():
    """SICHERE Anzeige bestehender Suchbegriffe"""
    try:
        search_terms = get_safe_search_terms()
        
        if search_terms and len(search_terms) > 0:
            st.write("**📋 Aktuelle Suchbegriffe mit Email-Benachrichtigungen:**")
            
            for term, settings in search_terms.items():
                if settings is None:  # Sicherheitscheck
                    continue
                
                # Sichere Werte mit Fallbacks
                active = settings.get('active', True) if isinstance(settings, dict) else True
                status_icon = '🟢 Aktiv' if active else '🔴 Inaktiv'
                
                with st.expander(f"🔍 {term} ({status_icon})"):
                    col_info1, col_info2, col_info3 = st.columns(3)
                    
                    with col_info1:
                        frequency = settings.get('frequency', 'N/A') if isinstance(settings, dict) else 'N/A'
                        min_papers = settings.get('min_papers', 5) if isinstance(settings, dict) else 5
                        
                        st.write(f"**Frequenz:** {frequency}")
                        st.write(f"**Min. Papers:** {min_papers}")
                    
                    with col_info2:
                        created = settings.get('created', 'N/A') if isinstance(settings, dict) else 'N/A'
                        if created != 'N/A' and len(created) > 10:
                            created = created[:10]
                        
                        last_notification = settings.get('last_notification', 'Nie') if isinstance(settings, dict) else 'Nie'
                        if last_notification != 'Nie' and len(last_notification) > 19:
                            last_notification = last_notification[:19]
                        
                        st.write(f"**Erstellt:** {created}")
                        st.write(f"**Letzte Benachrichtigung:** {last_notification}")
                    
                    with col_info3:
                        total_notifications = settings.get('total_notifications', 0) if isinstance(settings, dict) else 0
                        st.write(f"**Benachrichtigungen:** {total_notifications}")
                        
                        # Aktiv/Inaktiv Toggle - SICHER
                        try:
                            new_status = st.checkbox(
                                "Aktiv", 
                                value=active,
                                key=f"active_{term}"
                            )
                            if isinstance(settings, dict):
                                settings["active"] = new_status
                        except:
                            st.write("Status-Toggle nicht verfügbar")
                        
                        # Löschen Button - SICHER
                        if st.button(f"🗑️ Löschen", key=f"delete_{term}"):
                            delete_search_term_safely(term)
                            st.success(f"Suchbegriff '{term}' gelöscht!")
                            st.rerun()
                    
                    # Test-Benachrichtigung
                    if st.button(f"📧 Test-Benachrichtigung", key=f"test_{term}"):
                        send_test_notification_safely(term)
        else:
            st.info("🔔 Noch keine Suchbegriffe für Email-Benachrichtigungen konfiguriert.")
            
    except Exception as e:
        st.error(f"❌ Fehler bei Anzeige der Suchbegriffe: {str(e)}")

def notification_history_interface():
    """ROBUSTE Benachrichtigungs-Historie"""
    st.subheader("📊 Benachrichtigungs-Verlauf")
    
    try:
        history = get_safe_notification_history()
        
        if history and len(history) > 0:
            # Statistiken
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("📧 Gesamt", len(history))
            
            with col2:
                today_count = 0
                try:
                    today = datetime.datetime.now().date().isoformat()
                    today_count = len([n for n in history if isinstance(n, dict) and n.get("date") == today])
                except:
                    pass
                st.metric("📅 Heute", today_count)
            
            with col3:
                unique_terms = 0
                try:
                    unique_terms = len(set(n.get("search_term", "") for n in history if isinstance(n, dict)))
                except:
                    pass
                st.metric("🔍 Begriffe", unique_terms)
            
            # Historie anzeigen
            st.write("**📋 Letzte Benachrichtigungen:**")
            
            for notification in reversed(history[-10:]):  # Letzte 10
                if not isinstance(notification, dict):
                    continue
                
                search_term = notification.get("search_term", "Unknown")
                paper_count = notification.get("paper_count", 0)
                timestamp = notification.get("timestamp", "Unknown")
                if len(timestamp) > 19:
                    timestamp = timestamp[:19]
                
                with st.expander(f"📧 {search_term} - {paper_count} Papers ({timestamp})"):
                    st.write(f"**Suchbegriff:** {search_term}")
                    st.write(f"**Papers:** {paper_count}")
                    st.write(f"**Zeit:** {timestamp}")
                    st.write(f"**Status:** {notification.get('status', 'Unknown')}")
        else:
            st.info("📭 Noch keine Email-Benachrichtigungen versendet.")
    
    except Exception as e:
        st.error(f"❌ Fehler in Historie: {str(e)}")

def advanced_settings_interface():
    """ROBUSTE Erweiterte Einstellungen"""
    st.subheader("⚙️ Erweiterte Email-Einstellungen")
    
    try:
        settings = get_safe_email_settings()
        
        # Test-Funktionen
        col_test1, col_test2, col_test3 = st.columns(3)
        
        with col_test1:
            if st.button("📧 Test-Email"):
                send_system_test_email_safely()
        
        with col_test2:
            if st.button("🔧 Konfiguration prüfen"):
                check_configuration_safely()
        
        with col_test3:
            if st.button("🗑️ Alle Daten löschen"):
                if st.checkbox("Löschung bestätigen", key="confirm_delete_all"):
                    reset_all_data_safely()
                    st.success("Alle Daten gelöscht!")
                    st.rerun()
        
        # Einstellungen anzeigen
        st.write("**📋 Aktuelle Einstellungen:**")
        
        config_data = {
            "Absender Email": settings.get("sender_email", "Nicht konfiguriert"),
            "Empfänger Email": settings.get("recipient_email", "Nicht konfiguriert"),
            "SMTP Server": settings.get("smtp_server", "smtp.gmail.com"),
            "Auto-Benachrichtigungen": "Ja" if settings.get("auto_notifications", False) else "Nein",
            "Min. Papers": settings.get("min_papers_threshold", 5)
        }
        
        for key, value in config_data.items():
            st.write(f"**{key}:** {value}")
    
    except Exception as e:
        st.error(f"❌ Fehler in erweiterten Einstellungen: {str(e)}")

# SICHERE HILFSFUNKTIONEN
def get_safe_email_settings():
    """Sichere Email-Einstellungen abrufen"""
    try:
        settings = st.session_state.get("email_settings")
        if settings is None or not isinstance(settings, dict):
            return {
                "sender_email": "",
                "recipient_email": "",
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "auto_notifications": False,
                "min_papers_threshold": 5,
                "subject_template": "🔬 {count} neue Papers für '{search_term}'",
                "message_template": "Standard Nachricht"
            }
        return settings
    except:
        return {}

def get_safe_search_terms():
    """Sichere Suchbegriffe abrufen"""
    try:
        terms = st.session_state.get("search_terms_email")
        if terms is None or not isinstance(terms, dict):
            return {}
        return terms
    except:
        return {}

def get_safe_notification_history():
    """Sichere Historie abrufen"""
    try:
        history = st.session_state.get("email_notifications_history")
        if history is None or not isinstance(history, list):
            return []
        return history
    except:
        return []

def update_email_settings(new_settings):
    """Sichere Email-Einstellungen aktualisieren"""
    try:
        if "email_settings" not in st.session_state:
            st.session_state["email_settings"] = {}
        
        current_settings = st.session_state["email_settings"]
        if isinstance(current_settings, dict) and isinstance(new_settings, dict):
            current_settings.update(new_settings)
    except:
        st.session_state["email_settings"] = new_settings

def add_search_term_safely(term, frequency, min_papers):
    """Sicheres Hinzufügen von Suchbegriffen"""
    try:
        if "search_terms_email" not in st.session_state:
            st.session_state["search_terms_email"] = {}
        
        st.session_state["search_terms_email"][term] = {
            "frequency": frequency,
            "min_papers": min_papers,
            "created": datetime.datetime.now().isoformat(),
            "last_notification": None,
            "total_notifications": 0,
            "active": True
        }
    except Exception as e:
        st.error(f"Fehler beim Hinzufügen: {str(e)}")

def delete_search_term_safely(term):
    """Sicheres Löschen von Suchbegriffen"""
    try:
        terms = st.session_state.get("search_terms_email", {})
        if isinstance(terms, dict) and term in terms:
            del terms[term]
    except Exception as e:
        st.error(f"Fehler beim Löschen: {str(e)}")

def send_test_notification_safely(term):
    """Sichere Test-Benachrichtigung"""
    try:
        notification = {
            "timestamp": datetime.datetime.now().isoformat(),
            "date": datetime.datetime.now().date().isoformat(),
            "search_term": term,
            "paper_count": 3,
            "status": "Test-Benachrichtigung",
            "type": "Test",
            "recipient": get_safe_email_settings().get("recipient_email", "test@example.com")
        }
        
        history = get_safe_notification_history()
        history.append(notification)
        st.session_state["email_notifications_history"] = history
        
        st.success(f"✅ Test-Benachrichtigung für '{term}' erstellt!")
    
    except Exception as e:
        st.error(f"Fehler bei Test-Benachrichtigung: {str(e)}")

def generate_safe_email_preview(settings, search_term, count):
    """Sichere Email-Vorschau"""
    try:
        if not isinstance(settings, dict):
            return "Email-Vorschau nicht verfügbar"
        
        subject = f"Neue Papers für '{search_term}'"
        sender = settings.get("sender_email", "system@example.com")
        recipient = settings.get("recipient_email", "user@example.com")
        
        return f"""Von: {sender}
An: {recipient}
Betreff: {subject}

{count} neue Papers für '{search_term}' gefunden!

Datum: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}

Vollständige Ergebnisse im System verfügbar."""
    
    except:
        return "Email-Vorschau Fehler"

def send_system_test_email_safely():
    """Sicherer System-Test"""
    try:
        settings = get_safe_email_settings()
        
        if not settings.get("sender_email") or not settings.get("recipient_email"):
            st.warning("⚠️ Email-Konfiguration unvollständig!")
            return
        
        send_test_notification_safely("System-Test")
        st.success("✅ System-Test-Email erstellt!")
    
    except Exception as e:
        st.error(f"Fehler bei System-Test: {str(e)}")

def check_configuration_safely():
    """Sichere Konfigurationsprüfung"""
    try:
        settings = get_safe_email_settings()
        
        checks = [
            ("Absender Email", bool(settings.get("sender_email"))),
            ("Empfänger Email", bool(settings.get("recipient_email"))),
            ("SMTP Server", bool(settings.get("smtp_server")))
        ]
        
        st.write("**🔍 Konfigurationsprüfung:**")
        all_good = True
        
        for name, status in checks:
            icon = "✅" if status else "❌"
            st.write(f"{icon} {name}: {'OK' if status else 'Fehlt'}")
            if not status:
                all_good = False
        
        if all_good:
            st.success("🎉 Konfiguration vollständig!")
        else:
            st.warning("⚠️ Konfiguration unvollständig!")
    
    except Exception as e:
        st.error(f"Fehler bei Konfigurationsprüfung: {str(e)}")

def reset_all_data_safely():
    """Sicheres Zurücksetzen aller Daten"""
    try:
        st.session_state["email_settings"] = {}
        st.session_state["search_terms_email"] = {}
        st.session_state["email_notifications_history"] = []
    except Exception as e:
        st.error(f"Fehler beim Zurücksetzen: {str(e)}")

def simple_search_term_interface():
    """Einfaches Fallback-Interface"""
    st.write("**Einfache Suchbegriff-Verwaltung:**")
    
    with st.form("simple_search_form"):
        term = st.text_input("Suchbegriff")
        if st.form_submit_button("Hinzufügen"):
            if term:
                add_search_term_safely(term, "Bei jeder Suche", 5)
                st.success(f"Suchbegriff '{term}' hinzugefügt!")

def create_fallback_email_interface():
    """Fallback-Interface bei schweren Fehlern"""
    st.warning("⚠️ Fallback-Modus aktiviert")
    
    with st.form("fallback_email"):
        sender = st.text_input("Absender Email")
        recipient = st.text_input("Empfänger Email")
        
        if st.form_submit_button("Konfiguration speichern"):
            try:
                st.session_state["email_settings"] = {
                    "sender_email": sender,
                    "recipient_email": recipient
                }
                st.success("Basis-Konfiguration gespeichert!")
            except:
                st.error("Fehler beim Speichern!")

# Integration-Funktionen für andere Module
def trigger_email_notification(search_term, paper_count):
    """Sichere Integration für andere Module"""
    try:
        settings = get_safe_email_settings()
        if not settings.get("auto_notifications"):
            return False
        
        min_papers = settings.get("min_papers_threshold", 5)
        if paper_count >= min_papers:
            send_test_notification_safely(search_term)
            return True
    except:
        return False

def get_email_settings():
    """Sichere Einstellungen für andere Module"""
    return get_safe_email_settings()
