# modules/email_module.py
import streamlit as st
import os

# Versuche verschiedene Import-Methoden für email
try:
    import smtplib
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    from email.mime.base import MimeBase
    from email import encoders
    EMAIL_IMPORTS_OK = True
except ImportError as e:
    st.error(f"Email-Import-Fehler: {e}")
    EMAIL_IMPORTS_OK = False

def module_email():
    """Haupt-Email-Modul Funktion"""
    st.subheader("📧 Email-Funktionen")
    
    if not EMAIL_IMPORTS_OK:
        st.error("⚠️ Email-Bibliotheken konnten nicht importiert werden.")
        st.info("Verwende Fallback-Modus ohne echte Email-Funktionalität.")
        create_fallback_email_interface()
        return
    
    # Tabs für verschiedene Funktionen
    tab1, tab2, tab3 = st.tabs(["📤 Email senden", "📋 Vorlagen", "⚙️ Einstellungen"])
    
    with tab1:
        send_email_interface()
    
    with tab2:
        email_templates_interface()
    
    with tab3:
        email_settings_interface()

def send_email_interface():
    """Interface zum Senden von Emails"""
    st.subheader("Email senden")
    
    # Email-Formular
    with st.form("email_form"):
        sender_email = st.text_input("Von (Email)", value=st.secrets.get("sender_email", ""))
        recipient_email = st.text_input("An (Email)")
        subject = st.text_input("Betreff")
        message_body = st.text_area("Nachricht", height=200)
        
        # Erweiterte Einstellungen
        with st.expander("Erweiterte Einstellungen"):
            smtp_server = st.text_input("SMTP Server", value="smtp.gmail.com")
            smtp_port = st.number_input("SMTP Port", value=587)
            sender_password = st.text_input("Email Passwort", type="password")
        
        submitted = st.form_submit_button("📤 Email senden")
        
        if submitted:
            if sender_email and recipient_email and subject and message_body:
                if EMAIL_IMPORTS_OK:
                    try:
                        send_email(
                            sender_email, sender_password, recipient_email, 
                            subject, message_body, smtp_server, smtp_port
                        )
                        st.success("✅ Email erfolgreich gesendet!")
                    except Exception as e:
                        st.error(f"❌ Fehler beim Senden: {str(e)}")
                else:
                    st.info("🔧 Fallback-Modus: Email würde gesendet werden")
                    show_email_preview(sender_email, recipient_email, subject, message_body)
            else:
                st.error("Bitte füllen Sie alle Pflichtfelder aus!")

def email_templates_interface():
    """Interface für Email-Vorlagen"""
    st.subheader("Email-Vorlagen")
    
    templates = {
        "Neue Paper Benachrichtigung": {
            "subject": "🔬 Neue wissenschaftliche Papers gefunden!",
            "body": """Liebe/r Nutzer/in,

die automatische Paper-Suche hat neue interessante wissenschaftliche Papers gefunden:

{paper_count} neue Papers in folgenden Kategorien:
{categories}

Die vollständige Liste finden Sie in der angehängten Excel-Datei.

Mit freundlichen Grüßen,
Ihr Automated Paper Search System"""
        },
        "Allgemeine Benachrichtigung": {
            "subject": "📄 Paper-Analyse abgeschlossen",
            "body": """Ihre Paper-Analyse wurde erfolgreich abgeschlossen.

Details:
- Analysierte Papers: {count}
- Datum: {date}
- Status: Erfolgreich

Beste Grüße"""
        }
    }
    
    selected_template = st.selectbox("Vorlage auswählen:", list(templates.keys()))
    
    if selected_template:
        template = templates[selected_template]
        st.text_input("Betreff:", value=template["subject"])
        st.text_area("Nachricht:", value=template["body"], height=300)

def email_settings_interface():
    """Interface für Email-Einstellungen"""
    st.subheader("Email-Einstellungen")
    
    st.write("**SMTP-Konfiguration**")
    
    # Einstellungen in Session State speichern
    if "email_settings" not in st.session_state:
        st.session_state["email_settings"] = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "",
            "use_tls": True
        }
    
    settings = st.session_state["email_settings"]
    
    settings["smtp_server"] = st.text_input("SMTP Server:", value=settings["smtp_server"])
    settings["smtp_port"] = st.number_input("SMTP Port:", value=settings["smtp_port"])
    settings["sender_email"] = st.text_input("Standard Absender-Email:", value=settings["sender_email"])
    settings["use_tls"] = st.checkbox("TLS verwenden", value=settings["use_tls"])
    
    if st.button("Einstellungen speichern"):
        st.session_state["email_settings"] = settings
        st.success("Einstellungen gespeichert!")
    
    # Test-Verbindung
    st.write("---")
    st.write("**Verbindung testen**")
    if st.button("📡 SMTP-Verbindung testen"):
        if EMAIL_IMPORTS_OK:
            try:
                import smtplib
                server = smtplib.SMTP(settings["smtp_server"], settings["smtp_port"])
                if settings["use_tls"]:
                    server.starttls()
                server.quit()
                st.success("✅ Verbindung erfolgreich!")
            except Exception as e:
                st.error(f"❌ Verbindungsfehler: {str(e)}")
        else:
            st.warning("⚠️ Email-Bibliotheken nicht verfügbar - Test nicht möglich")

def send_email(sender_email, sender_password, recipient_email, subject, body, smtp_server="smtp.gmail.com", smtp_port=587):
    """Sendet eine Email"""
    if not EMAIL_IMPORTS_OK:
        raise Exception("Email-Bibliotheken nicht verfügbar")
    
    try:
        import smtplib
        from email.mime.text import MimeText
        from email.mime.multipart import MimeMultipart
        
        # Email-Objekt erstellen
        msg = MimeMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Body anhängen
        msg.attach(MimeText(body, 'plain'))
        
        # SMTP-Verbindung
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        
        # Email senden
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        
        return True
    except Exception as e:
        raise Exception(f"Email-Versand fehlgeschlagen: {str(e)}")

def create_fallback_email_interface():
    """Erstellt ein einfaches Email-Interface als Fallback"""
    st.subheader("📤 Email senden (Fallback-Modus)")
    st.warning("⚠️ Email-Bibliotheken nicht verfügbar. Nur Vorschau möglich.")
    
    with st.form("fallback_email_form"):
        sender_email = st.text_input("Von (Email)")
        recipient_email = st.text_input("An (Email)")
        subject = st.text_input("Betreff")
        message_body = st.text_area("Nachricht", height=200)
        
        submitted = st.form_submit_button("📤 Email-Vorschau anzeigen")
        
        if submitted:
            if sender_email and recipient_email and subject and message_body:
                show_email_preview(sender_email, recipient_email, subject, message_body)
            else:
                st.error("Bitte füllen Sie alle Felder aus!")

def show_email_preview(sender_email, recipient_email, subject, message_body):
    """Zeigt eine Email-Vorschau an"""
    st.success("📧 Email-Vorschau:")
    st.code(f"""Von: {sender_email}
An: {recipient_email}
Betreff: {subject}

Nachricht:
{message_body}""", language="text")

# Zusätzliche Hilfsfunktionen
def send_paper_notification_email(new_papers_count, categories, recipient_email, attachment_data=None):
    """Spezielle Funktion für Paper-Benachrichtigungen"""
    if not EMAIL_IMPORTS_OK:
        st.warning("📧 Email-Bibliotheken nicht verfügbar - Benachrichtigung nicht möglich")
        return False
    
    try:
        sender_email = st.secrets.get("sender_email", "")
        sender_password = st.secrets.get("sender_password", "")
        
        if not sender_email or not sender_password:
            st.error("Email-Konfiguration fehlt in secrets!")
            return False
        
        subject = f"🔬 {new_papers_count} neue wissenschaftliche Papers gefunden!"
        
        body = f"""Neue Papers wurden gefunden!

Anzahl neuer Papers: {new_papers_count}
Kategorien: {', '.join(categories) if categories else 'Verschiedene'}

Die vollständige Liste wurde automatisch generiert und ist verfügbar.

Mit freundlichen Grüßen,
Ihr Automated Paper Search System"""
        
        # Email senden
        send_email(sender_email, sender_password, recipient_email, subject, body)
        return True
    except Exception as e:
        st.error(f"Fehler beim Senden der Benachrichtigung: {str(e)}")
        return False
