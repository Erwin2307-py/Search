# modules/email_module.py - Erweiterte Version mit Suchbegriff und Datenspeicherung
import streamlit as st
import os
import json
import datetime
import pandas as pd

def module_email():
    """Haupt-Email-Modul Funktion - Erweiterte Version mit Suchbegriff und Datenspeicherung"""
    st.subheader("📧 Email-System mit automatischer Paper-Suche")
    
    st.info("⚠️ Erweiterte Email-Funktionalität mit Suchbegriff-Management und Datenspeicherung")
    
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
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔍 Suchbegriff-Management", 
        "📤 Email Konfiguration", 
        "📋 Vorlagen", 
        "📊 Benachrichtigungs-Verlauf",
        "⚙️ Einstellungen"
    ])
    
    with tab1:
        search_terms_management()
    
    with tab2:
        enhanced_email_interface()
    
    with tab3:
        enhanced_email_templates()
    
    with tab4:
        notification_history_interface()
    
    with tab5:
        enhanced_email_settings()

def search_terms_management():
    """Suchbegriff-Management Interface"""
    st.subheader("🔍 Suchbegriff-Management")
    
    # Neue Suchbegriffe hinzufügen
    st.write("**Neue Suchbegriffe hinzufügen:**")
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        new_search_term = st.text_input("Suchbegriff", placeholder="z.B. 'diabetes genetics'")
    with col2:
        search_frequency = st.selectbox("Suchfrequenz", ["Täglich", "Wöchentlich", "Monatlich"])
    with col3:
        if st.button("➕ Hinzufügen"):
            if new_search_term and new_search_term not in st.session_state["email_search_terms"]:
                st.session_state["email_search_terms"][new_search_term] = {
                    "frequency": search_frequency,
                    "created": datetime.datetime.now().isoformat(),
                    "last_search": None,
                    "paper_count": 0,
                    "active": True,
                    "email_notifications": True
                }
                st.success(f"Suchbegriff '{new_search_term}' hinzugefügt!")
                st.rerun()
    
    # Bestehende Suchbegriffe anzeigen
    if st.session_state["email_search_terms"]:
        st.write("**Bestehende Suchbegriffe:**")
        
        for term, info in st.session_state["email_search_terms"].items():
            with st.expander(f"🔍 {term} (Papers: {info.get('paper_count', 0)})"):
                col_info1, col_info2, col_info3 = st.columns(3)
                
                with col_info1:
                    st.write(f"**Frequenz:** {info.get('frequency', 'N/A')}")
                    st.write(f"**Erstellt:** {info.get('created', 'N/A')[:10]}")
                
                with col_info2:
                    st.write(f"**Letzte Suche:** {info.get('last_search', 'Nie')[:10] if info.get('last_search') else 'Nie'}")
                    st.write(f"**Status:** {'🟢 Aktiv' if info.get('active', True) else '🔴 Inaktiv'}")
                
                with col_info3:
                    if st.button(f"🗑️ Löschen", key=f"delete_{term}"):
                        del st.session_state["email_search_terms"][term]
                        st.success(f"Suchbegriff '{term}' gelöscht!")
                        st.rerun()
                    
                    info["active"] = st.checkbox("Aktiv", value=info.get("active", True), key=f"active_{term}")
                    info["email_notifications"] = st.checkbox("Email-Benachrichtigung", value=info.get("email_notifications", True), key=f"email_{term}")
        
        # Alle Suchbegriffe durchsuchen
        st.markdown("---")
        col_search1, col_search2, col_search3 = st.columns(3)
        
        with col_search1:
            if st.button("🔍 Alle Suchbegriffe durchsuchen"):
                perform_all_searches()
        
        with col_search2:
            if st.button("📧 Benachrichtigung für neue Papers senden"):
                send_new_papers_notification()
        
        with col_search3:
            if st.button("📊 Statistiken anzeigen"):
                show_search_statistics()
    else:
        st.info("Noch keine Suchbegriffe definiert. Fügen Sie welche hinzu!")

def perform_all_searches():
    """Führt alle aktiven Suchen durch"""
    active_terms = {term: info for term, info in st.session_state["email_search_terms"].items() if info.get("active", True)}
    
    if not active_terms:
        st.warning("Keine aktiven Suchbegriffe gefunden!")
        return
    
    with st.spinner("Führe Suchen durch..."):
        progress_bar = st.progress(0)
        results_summary = {}
        
        for idx, (term, info) in enumerate(active_terms.items()):
            progress_bar.progress((idx + 1) / len(active_terms))
            
            # Simuliere Suche (hier würden die echten Such-APIs aufgerufen)
            try:
                # Import der Such-Funktionen vom Hauptscript
                from streamlit_app import search_pubmed_simple
                results = search_pubmed_simple(term)
                results_count = len(results)
                
                # Update search info
                info["last_search"] = datetime.datetime.now().isoformat()
                info["paper_count"] = results_count
                
                results_summary[term] = {
                    "count": results_count,
                    "results": results[:5]  # Nur die ersten 5 für die Anzeige
                }
                
                # Speichere Ergebnisse
                save_search_results(term, results)
                
            except Exception as e:
                st.error(f"Fehler bei Suche für '{term}': {str(e)}")
                results_summary[term] = {"count": 0, "results": []}
        
        progress_bar.empty()
        display_search_results_summary(results_summary)

def save_search_results(search_term, results):
    """Speichert Suchergebnisse in Session State"""
    if "search_results_data" not in st.session_state:
        st.session_state["search_results_data"] = {}
    
    timestamp = datetime.datetime.now().isoformat()
    
    if search_term not in st.session_state["search_results_data"]:
        st.session_state["search_results_data"][search_term] = []
    
    # Füge neue Ergebnisse hinzu
    st.session_state["search_results_data"][search_term].append({
        "timestamp": timestamp,
        "count": len(results),
        "results": results
    })
    
    # Behalte nur die letzten 10 Suchergebnisse pro Begriff
    if len(st.session_state["search_results_data"][search_term]) > 10:
        st.session_state["search_results_data"][search_term] = st.session_state["search_results_data"][search_term][-10:]

def display_search_results_summary(results_summary):
    """Zeigt Zusammenfassung der Suchergebnisse an"""
    st.subheader("📊 Suchergebnisse Zusammenfassung")
    
    total_papers = sum(info["count"] for info in results_summary.values())
    st.metric("Gesamt gefundene Papers", total_papers)
    
    for term, info in results_summary.items():
        with st.expander(f"🔍 {term}: {info['count']} Papers"):
            if info["results"]:
                for i, paper in enumerate(info["results"], 1):
                    st.write(f"**{i}.** {paper.get('Title', 'Unbekannter Titel')} ({paper.get('Year', 'N/A')})")
            else:
                st.info("Keine Papers gefunden.")

def enhanced_email_interface():
    """Erweiterte Email-Interface"""
    st.subheader("📧 Email-Konfiguration")
    
    # Email-Vorschau basierend auf gespeicherten Suchergebnissen
    if "search_results_data" in st.session_state and st.session_state["search_results_data"]:
        st.write("**📋 Automatische Email-Erstellung basierend auf letzten Suchergebnissen:**")
        
        selected_terms = st.multiselect(
            "Wählen Sie Suchbegriffe für die Email:",
            list(st.session_state["search_results_data"].keys()),
            default=list(st.session_state["search_results_data"].keys())
        )
        
        if selected_terms:
            email_content = generate_automatic_email_content(selected_terms)
            
            with st.form("auto_email_form"):
                sender_email = st.text_input("Von (Email)", value=st.session_state["email_settings"].get("sender_email", ""))
                recipient_email = st.text_input("An (Email)", value=st.session_state["email_settings"].get("default_recipient", ""))
                subject = st.text_input("Betreff", value=email_content["subject"])
                message_body = st.text_area("Nachricht", value=email_content["body"], height=300)
                
                submitted = st.form_submit_button("📧 Email-Konfiguration speichern & Vorschau")
                
                if submitted:
                    if sender_email and recipient_email and subject and message_body:
                        # Speichere Email-Konfiguration
                        email_config = {
                            "sender": sender_email,
                            "recipient": recipient_email,
                            "subject": subject,
                            "body": message_body,
                            "timestamp": datetime.datetime.now().isoformat(),
                            "search_terms": selected_terms
                        }
                        
                        # Speichere in Benachrichtigungs-Verlauf
                        st.session_state["email_notifications_history"].append(email_config)
                        
                        st.success("✅ Email-Konfiguration gespeichert!")
                        
                        # Zeige Email-Vorschau
                        st.info("📧 **Email-Vorschau:**")
                        st.code(f"""Von: {sender_email}
An: {recipient_email}
Betreff: {subject}

{message_body}""")
                    else:
                        st.error("Bitte füllen Sie alle Felder aus!")
    else:
        st.info("Führen Sie zuerst eine Suche durch, um automatische Email-Inhalte zu generieren.")

def generate_automatic_email_content(selected_terms):
    """Generiert automatischen Email-Inhalt basierend auf Suchergebnissen"""
    total_papers = 0
    term_summaries = []
    
    for term in selected_terms:
        if term in st.session_state.get("search_results_data", {}):
            latest_search = st.session_state["search_results_data"][term][-1]
            count = latest_search["count"]
            total_papers += count
            term_summaries.append(f"• {term}: {count} Papers")
    
    subject = f"📊 Paper-Suche Ergebnis: {total_papers} Papers in {len(selected_terms)} Kategorien"
    
    body = f"""🔍 **Automatischer Paper-Suche Bericht**

📅 **Datum:** {datetime.datetime.now().strftime("%d.%m.%Y %H:%M")}
📊 **Gesamt gefundene Papers:** {total_papers}
🏷️ **Suchkategorien:** {len(selected_terms)}

**📋 Aufschlüsselung nach Suchbegriffen:**
{chr(10).join(term_summaries)}

**🔗 Weitere Details:**
Die vollständigen Suchergebnisse sind im System verfügbar und können über das Dashboard eingesehen werden.

**⚙️ Nächste Schritte:**
- Überprüfen Sie die relevanten Papers
- Aktualisieren Sie bei Bedarf die Suchkriterien
- Konfigurieren Sie die Benachrichtigungsfrequenz

Mit freundlichen Grüßen,
Ihr automatisches Paper-Suche System
"""
    
    return {"subject": subject, "body": body}

def enhanced_email_templates():
    """Erweiterte Email-Vorlagen"""
    st.subheader("📋 Email-Vorlagen")
    
    templates = {
        "Neue Paper Benachrichtigung": {
            "subject": "🔬 {count} neue wissenschaftliche Papers gefunden!",
            "body": """🔍 **Neue Papers gefunden!**

📅 Datum: {date}
📊 Anzahl neuer Papers: {count}
🏷️ Kategorien: {categories}

**📋 Zusammenfassung:**
{summary}

**🔗 Nächste Schritte:**
- Überprüfen Sie die relevanten Papers
- Die vollständige Liste ist im System verfügbar

Mit freundlichen Grüßen,
Ihr Paper-Suche System"""
        },
        "Wöchentlicher Report": {
            "subject": "📊 Wöchentlicher Paper-Report - KW {week}",
            "body": """📈 **Wöchentlicher Aktivitätsbericht**

📅 Zeitraum: {date_range}
🔍 Durchgeführte Suchen: {search_count}
📊 Gefundene Papers: {total_papers}

**📋 Top Suchbegriffe:**
{top_terms}

**📈 Trends:**
{trends}

Beste Grüße,
Ihr Analyse-System"""
        },
        "System-Update": {
            "subject": "🔔 System-Update verfügbar",
            "body": """🆕 **System-Update Benachrichtigung**

Es ist ein neues Update für das Paper-Suche System verfügbar.

**🔧 Neue Features:**
- Verbesserte Suchfunktionalität
- Erweiterte Email-Vorlagen
- Optimierte Datenverarbeitung

**⏰ Geplante Wartung:**
{maintenance_time}

Bei Fragen wenden Sie sich an den Support.

Ihr System-Team"""
        }
    }
    
    # Template-Auswahl und Bearbeitung
    selected_template = st.selectbox("Vorlage auswählen:", list(templates.keys()))
    
    if selected_template:
        template = templates[selected_template]
        
        col_t1, col_t2 = st.columns([1, 2])
        
        with col_t1:
            st.write("**Template-Variablen:**")
            st.code("""Verfügbare Platzhalter:
{count} - Anzahl Papers
{date} - Aktuelles Datum
{categories} - Kategorien-Liste
{summary} - Zusammenfassung
{week} - Kalenderwoche
{date_range} - Datumsbereich
{search_count} - Anzahl Suchen
{total_papers} - Gesamt Papers
{top_terms} - Top Suchbegriffe
{trends} - Trend-Analyse
{maintenance_time} - Wartungszeit""")
        
        with col_t2:
            edited_subject = st.text_input("Betreff:", value=template["subject"])
            edited_body = st.text_area("Nachricht:", value=template["body"], height=400)
            
            if st.button(f"💾 Template '{selected_template}' speichern"):
                templates[selected_template] = {
                    "subject": edited_subject,
                    "body": edited_body
                }
                st.success("Template gespeichert!")

def notification_history_interface():
    """Benachrichtigungs-Verlauf Interface"""
    st.subheader("📊 Benachrichtigungs-Verlauf")
    
    if st.session_state["email_notifications_history"]:
        # Filter-Optionen
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            date_filter = st.date_input("Ab Datum:", value=datetime.datetime.now() - datetime.timedelta(days=30))
        
        with col_f2:
            search_filter = st.text_input("Suchbegriff filtern:")
        
        with col_f3:
            show_count = st.number_input("Anzahl anzeigen:", min_value=5, max_value=100, value=20)
        
        # Gefilterte Historie anzeigen
        filtered_history = []
        for notification in st.session_state["email_notifications_history"]:
            notification_date = datetime.datetime.fromisoformat(notification["timestamp"]).date()
            
            if notification_date >= date_filter:
                if not search_filter or search_filter.lower() in str(notification.get("search_terms", [])).lower():
                    filtered_history.append(notification)
        
        filtered_history = filtered_history[-show_count:]  # Zeige nur die letzten N
        
        # Historie-Tabelle
        if filtered_history:
            history_data = []
            for notification in reversed(filtered_history):  # Neueste zuerst
                timestamp = datetime.datetime.fromisoformat(notification["timestamp"])
                history_data.append({
                    "Datum": timestamp.strftime("%d.%m.%Y %H:%M"),
                    "Empfänger": notification["recipient"],
                    "Betreff": notification["subject"][:50] + "..." if len(notification["subject"]) > 50 else notification["subject"],
                    "Suchbegriffe": ", ".join(notification.get("search_terms", []))[:40] + "..." if len(", ".join(notification.get("search_terms", []))) > 40 else ", ".join(notification.get("search_terms", []))
                })
            
            df = pd.DataFrame(history_data)
            st.dataframe(df, use_container_width=True)
            
            # Export-Option
            if st.button("📥 Verlauf als CSV herunterladen"):
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"email_history_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("Keine Benachrichtigungen im ausgewählten Zeitraum gefunden.")
        
        # Statistiken
        st.markdown("---")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        
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
        
        with col_s4:
            if st.button("🗑️ Verlauf löschen"):
                st.session_state["email_notifications_history"] = []
                st.success("Verlauf gelöscht!")
                st.rerun()
    else:
        st.info("Noch keine Email-Benachrichtigungen versendet.")

def enhanced_email_settings():
    """Erweiterte Email-Einstellungen"""
    st.subheader("⚙️ Email-Einstellungen")
    
    settings = st.session_state["email_settings"]
    
    # SMTP-Konfiguration
    with st.expander("📧 SMTP-Konfiguration", expanded=True):
        col_smtp1, col_smtp2 = st.columns(2)
        
        with col_smtp1:
            settings["smtp_server"] = st.text_input("SMTP Server:", value=settings["smtp_server"])
            settings["sender_email"] = st.text_input("Standard Absender-Email:", value=settings["sender_email"])
        
        with col_smtp2:
            settings["smtp_port"] = st.number_input("SMTP Port:", value=settings["smtp_port"])
            settings["default_recipient"] = st.text_input("Standard Empfänger:", value=settings["default_recipient"])
    
    # Automatisierung-Einstellungen
    with st.expander("🤖 Automatisierung", expanded=True):
        settings["auto_notifications"] = st.checkbox("Automatische Benachrichtigungen aktivieren", value=settings["auto_notifications"])
        
        if settings["auto_notifications"]:
            col_auto1, col_auto2 = st.columns(2)
            
            with col_auto1:
                settings["notification_frequency"] = st.selectbox(
                    "Benachrichtigungs-Frequenz:",
                    ["Täglich", "Wöchentlich", "Monatlich"],
                    index=["Täglich", "Wöchentlich", "Monatlich"].index(settings.get("notification_frequency", "Wöchentlich"))
                )
            
            with col_auto2:
                settings["min_papers_threshold"] = st.number_input(
                    "Mindestanzahl Papers für Benachrichtigung:",
                    min_value=1,
                    max_value=100,
                    value=settings.get("min_papers_threshold", 5)
                )
    
    # Speichern
    if st.button("💾 Einstellungen speichern"):
        st.session_state["email_settings"] = settings
        st.success("Einstellungen gespeichert!")
    
    # Daten-Export/Import
    st.markdown("---")
    st.write("**💾 Daten-Management:**")
    
    col_data1, col_data2, col_data3 = st.columns(3)
    
    with col_data1:
        if st.button("📤 Alle Daten exportieren"):
            export_data = {
                "search_terms": st.session_state.get("email_search_terms", {}),
                "notifications_history": st.session_state.get("email_notifications_history", []),
                "search_results": st.session_state.get("search_results_data", {}),
                "settings": st.session_state.get("email_settings", {}),
                "export_timestamp": datetime.datetime.now().isoformat()
            }
            
            json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 JSON herunterladen",
                data=json_str,
                file_name=f"email_system_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col_data2:
        uploaded_file = st.file_uploader("📁 Daten importieren", type=["json"])
        if uploaded_file is not None:
            try:
                import_data = json.load(uploaded_file)
                
                if st.button("✅ Import bestätigen"):
                    st.session_state["email_search_terms"] = import_data.get("search_terms", {})
                    st.session_state["email_notifications_history"] = import_data.get("notifications_history", [])
                    st.session_state["search_results_data"] = import_data.get("search_results", {})
                    st.session_state["email_settings"].update(import_data.get("settings", {}))
                    
                    st.success("Daten erfolgreich importiert!")
                    st.rerun()
            except Exception as e:
                st.error(f"Import-Fehler: {str(e)}")
    
    with col_data3:
        if st.button("🗑️ Alle Daten löschen"):
            if st.checkbox("Löschung bestätigen"):
                st.session_state["email_search_terms"] = {}
                st.session_state["email_notifications_history"] = []
                st.session_state["search_results_data"] = {}
                st.session_state["email_settings"] = {
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "sender_email": "",
                    "default_recipient": "",
                    "auto_notifications": False
                }
                st.success("Alle Daten gelöscht!")
                st.rerun()

def send_new_papers_notification():
    """Sendet Benachrichtigung über neue Papers"""
    st.info("📧 Benachrichtigung über neue Papers wird vorbereitet...")
    
    # Simuliere das Senden (hier würde die echte Email-Funktionalität stehen)
    notification = {
        "timestamp": datetime.datetime.now().isoformat(),
        "sender": st.session_state["email_settings"].get("sender_email", "system@example.com"),
        "recipient": st.session_state["email_settings"].get("default_recipient", "user@example.com"),
        "subject": "🔬 Neue Papers gefunden - Automatische Benachrichtigung",
        "body": "Automatisch generierte Benachrichtigung über neue wissenschaftliche Papers.",
        "search_terms": list(st.session_state.get("email_search_terms", {}).keys()),
        "type": "automatic"
    }
    
    st.session_state["email_notifications_history"].append(notification)
    st.success("✅ Benachrichtigung versendet und im Verlauf gespeichert!")

def show_search_statistics():
    """Zeigt Suchstatistiken an"""
    st.subheader("📊 Suchstatistiken")
    
    if not st.session_state.get("search_results_data"):
        st.info("Keine Suchdaten verfügbar.")
        return
    
    # Berechne Statistiken
    total_searches = sum(len(searches) for searches in st.session_state["search_results_data"].values())
    total_papers = 0
    
    stats_data = []
    for term, searches in st.session_state["search_results_data"].items():
        term_papers = sum(search["count"] for search in searches)
        total_papers += term_papers
        
        stats_data.append({
            "Suchbegriff": term,
            "Anzahl Suchen": len(searches),
            "Gesamt Papers": term_papers,
            "Letzte Suche": searches[-1]["timestamp"][:10] if searches else "N/A"
        })
    
    # Metriken anzeigen
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        st.metric("Gesamt Suchen", total_searches)
    with col_m2:
        st.metric("Gesamt Papers", total_papers)
    with col_m3:
        st.metric("Aktive Suchbegriffe", len(st.session_state.get("email_search_terms", {})))
    with col_m4:
        avg_papers = total_papers / len(stats_data) if stats_data else 0
        st.metric("Ø Papers pro Begriff", f"{avg_papers:.1f}")
    
    # Detaillierte Tabelle
    if stats_data:
        df_stats = pd.DataFrame(stats_data)
        st.dataframe(df_stats, use_container_width=True)
