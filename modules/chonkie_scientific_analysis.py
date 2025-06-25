"""
Chonkie Scientific Paper Analysis Module
=======================================
Erweiterte wissenschaftliche Paper-Analyse mit Chonkie-Chunking-Strategien
Unterstützt verschiedene Chunking-Methoden für optimale RAG-Performance
"""

import streamlit as st
import requests
import pandas as pd
import re
import datetime
import os
import PyPDF2
import openai
import time
import json
import io
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import zipfile

# Chonkie Imports mit Fallback
try:
    from chonkie import (
        TokenChunker, 
        SemanticChunker, 
        SentenceChunker,
        RecursiveChunker
    )
    # Erweiterte Chonkie Features
    try:
        from chonkie import SemanticDoublePassChunker, LateChunker
        ADVANCED_CHONKIE = True
    except ImportError:
        ADVANCED_CHONKIE = False
    
    CHONKIE_AVAILABLE = True
    print("✅ Chonkie erfolgreich geladen")
except ImportError:
    CHONKIE_AVAILABLE = False
    print("⚠️ Chonkie nicht verfügbar - installiere mit: pip install chonkie")
    
    # Fallback-Implementierung
    class FallbackChunker:
        def __init__(self, chunk_size=1000, chunk_overlap=100):
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap
        
        def chunk(self, text):
            words = text.split()
            chunks = []
            for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
                chunk_words = words[i:i + self.chunk_size]
                chunk_text = ' '.join(chunk_words)
                chunks.append(type('Chunk', (), {'text': chunk_text, 'token_count': len(chunk_words)})())
            return chunks
    
    TokenChunker = SentenceChunker = SemanticChunker = RecursiveChunker = FallbackChunker
    ADVANCED_CHONKIE = False

class ChonkieScientificAnalyzer:
    """
    Wissenschaftliche Paper-Analyse mit Chonkie-Integration
    """
    
    def __init__(self):
        self.chonkie_available = CHONKIE_AVAILABLE
        self.advanced_features = ADVANCED_CHONKIE
        self.analysis_results = {}
        self.chunk_cache = {}
        
        # Konfiguration für verschiedene Chunking-Strategien
        self.chunker_configs = {
            'token': {
                'chunk_size': 512,
                'chunk_overlap': 50,
                'description': 'Optimal für OpenAI API, respektiert Token-Limits'
            },
            'sentence': {
                'chunk_size': 800,
                'chunk_overlap': 100,
                'description': 'Respektiert Satzgrenzen, gut für semantische Kohärenz'
            },
            'semantic': {
                'similarity_threshold': 0.7,
                'min_chunk_size': 200,
                'max_chunk_size': 1000,
                'description': 'Semantisch zusammenhängende Konzepte'
            },
            'recursive': {
                'chunk_size': 1000,
                'chunk_overlap': 200,
                'separators': ["\n\n", "\n", ". ", " "],
                'description': 'Hierarchische Aufteilung mit verschiedenen Separatoren'
            }
        }
    
    def get_chunker(self, chunker_type: str, custom_config: dict = None):
        """Erstellt Chunker basierend auf Typ und Konfiguration"""
        config = self.chunker_configs.get(chunker_type, {})
        if custom_config:
            config.update(custom_config)
        
        if not self.chonkie_available:
            return FallbackChunker(
                chunk_size=config.get('chunk_size', 1000),
                chunk_overlap=config.get('chunk_overlap', 100)
            )
        
        try:
            if chunker_type == 'token':
                return TokenChunker(
                    chunk_size=config.get('chunk_size', 512),
                    chunk_overlap=config.get('chunk_overlap', 50)
                )
            elif chunker_type == 'sentence':
                return SentenceChunker(
                    chunk_size=config.get('chunk_size', 800),
                    chunk_overlap=config.get('chunk_overlap', 100)
                )
            elif chunker_type == 'semantic':
                return SemanticChunker(
                    similarity_threshold=config.get('similarity_threshold', 0.7),
                    min_chunk_size=config.get('min_chunk_size', 200),
                    max_chunk_size=config.get('max_chunk_size', 1000)
                )
            elif chunker_type == 'recursive':
                return RecursiveChunker(
                    chunk_size=config.get('chunk_size', 1000),
                    chunk_overlap=config.get('chunk_overlap', 200),
                    separators=config.get('separators', ["\n\n", "\n", ". ", " "])
                )
            else:
                # Fallback zu Token Chunker
                return TokenChunker(chunk_size=512, chunk_overlap=50)
                
        except Exception as e:
            st.warning(f"Fehler beim Erstellen des {chunker_type}-Chunkers: {e}")
            return FallbackChunker()
    
    def extract_text_from_pdf(self, pdf_file) -> str:
        """Extrahiert Text aus PDF"""
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        except Exception as e:
            st.error(f"PDF-Extraktion fehlgeschlagen: {e}")
            return ""
    
    def chunk_text_with_strategy(self, text: str, strategy: str, config: dict = None) -> dict:
        """Chunked Text mit gewählter Strategie"""
        if not text.strip():
            return {'chunks': [], 'metadata': {'error': 'Leerer Text'}}
        
        try:
            chunker = self.get_chunker(strategy, config)
            start_time = time.time()
            
            chunks = chunker.chunk(text)
            processing_time = time.time() - start_time
            
            # Statistiken berechnen
            total_chunks = len(chunks)
            avg_chunk_size = sum(len(chunk.text) for chunk in chunks) / total_chunks if chunks else 0
            total_tokens = sum(getattr(chunk, 'token_count', len(chunk.text.split())) for chunk in chunks)
            
            return {
                'chunks': chunks,
                'metadata': {
                    'strategy': strategy,
                    'total_chunks': total_chunks,
                    'avg_chunk_size': avg_chunk_size,
                    'total_tokens': total_tokens,
                    'processing_time': processing_time,
                    'original_length': len(text),
                    'compression_ratio': len(text) / total_tokens if total_tokens > 0 else 0
                }
            }
            
        except Exception as e:
            st.error(f"Chunking fehlgeschlagen: {e}")
            return {'chunks': [], 'metadata': {'error': str(e)}}
    
    def analyze_paper_with_chunking(self, text: str, chunker_type: str, api_key: str, 
                                   analysis_types: List[str]) -> dict:
        """Analysiert Paper mit spezifischer Chunking-Strategie"""
        
        # Text chunken
        chunk_result = self.chunk_text_with_strategy(text, chunker_type)
        chunks = chunk_result['chunks']
        metadata = chunk_result['metadata']
        
        if not chunks:
            return {'error': 'Keine Chunks erstellt', 'metadata': metadata}
        
        # Optimale Chunks für verschiedene Analysen auswählen
        analysis_results = {}
        
        for analysis_type in analysis_types:
            try:
                if analysis_type == 'summary':
                    result = self._create_summary_from_chunks(chunks, api_key)
                elif analysis_type == 'key_findings':
                    result = self._extract_key_findings_from_chunks(chunks, api_key)
                elif analysis_type == 'methodology':
                    result = self._identify_methodology_from_chunks(chunks, api_key)
                elif analysis_type == 'relevance_score':
                    result = self._calculate_relevance_score(chunks, api_key)
                elif analysis_type == 'research_quality':
                    result = self._assess_research_quality(chunks, api_key)
                elif analysis_type == 'citations_analysis':
                    result = self._analyze_citations(chunks)
                elif analysis_type == 'statistical_analysis':
                    result = self._extract_statistical_info(chunks)
                else:
                    result = f"Unbekannter Analyse-Typ: {analysis_type}"
                
                analysis_results[analysis_type] = result
                
            except Exception as e:
                analysis_results[analysis_type] = f"Fehler bei {analysis_type}: {str(e)}"
        
        return {
            'analysis_results': analysis_results,
            'chunk_metadata': metadata,
            'chunker_type': chunker_type
        }
    
    def _create_summary_from_chunks(self, chunks, api_key: str) -> str:
        """Erstellt Zusammenfassung aus optimalen Chunks"""
        # Wähle die besten Chunks für Zusammenfassung (erste und letzte)
        selected_chunks = []
        if len(chunks) > 0:
            selected_chunks.append(chunks[0])  # Einleitung
        if len(chunks) > 2:
            selected_chunks.extend(chunks[-2:])  # Ergebnisse und Fazit
        elif len(chunks) > 1:
            selected_chunks.append(chunks[-1])
        
        combined_text = "\n\n".join([chunk.text for chunk in selected_chunks])
        
        prompt = f"""
        Erstelle eine strukturierte wissenschaftliche Zusammenfassung des folgenden Papers.
        Gliederung:
        1. Forschungsziel und Hintergrund
        2. Methodik
        3. Hauptergebnisse
        4. Schlussfolgerungen und Implikationen
        
        Verwende maximal 500 Wörter und fokussiere auf die wichtigsten wissenschaftlichen Erkenntnisse.
        
        Text: {combined_text[:8000]}
        """
        
        return self._call_openai_api(prompt, api_key)
    
    def _extract_key_findings_from_chunks(self, chunks, api_key: str) -> str:
        """Extrahiert Schlüsselerkenntnisse aus relevanten Chunks"""
        # Finde Chunks mit Results, Findings, Conclusions
        relevant_chunks = []
        for chunk in chunks:
            text_lower = chunk.text.lower()
            if any(keyword in text_lower for keyword in 
                   ['results', 'findings', 'conclusion', 'discussion', 'ergebnisse', 'schlussfolgerung']):
                relevant_chunks.append(chunk)
        
        if not relevant_chunks:
            relevant_chunks = chunks[-3:]  # Letzte 3 Chunks als Fallback
        
        combined_text = "\n\n".join([chunk.text for chunk in relevant_chunks[:3]])
        
        prompt = f"""
        Extrahiere die 5 wichtigsten wissenschaftlichen Erkenntnisse aus diesem Paper.
        Für jede Erkenntnis gib an:
        - Die Hauptaussage
        - Statistische Evidenz (falls vorhanden)
        - Wissenschaftliche Bedeutung
        
        Formatiere als nummerierte Liste.
        
        Text: {combined_text[:8000]}
        """
        
        return self._call_openai_api(prompt, api_key)
    
    def _identify_methodology_from_chunks(self, chunks, api_key: str) -> str:
        """Identifiziert Methodik aus relevanten Chunks"""
        # Finde Chunks mit Methodology, Methods, Materials
        method_chunks = []
        for chunk in chunks:
            text_lower = chunk.text.lower()
            if any(keyword in text_lower for keyword in 
                   ['method', 'methodology', 'material', 'procedure', 'analysis', 'study design']):
                method_chunks.append(chunk)
        
        if not method_chunks:
            # Fallback: mittlere Chunks (oft Methods-Sektion)
            mid_point = len(chunks) // 2
            method_chunks = chunks[max(0, mid_point-1):mid_point+2]
        
        combined_text = "\n\n".join([chunk.text for chunk in method_chunks[:3]])
        
        prompt = f"""
        Analysiere und beschreibe die wissenschaftliche Methodik dieses Papers.
        Fokussiere auf:
        1. Studiendesign und Ansatz
        2. Datensammlung und -quellen
        3. Analysemethoden und Tools
        4. Stichprobengröße und -charakteristika
        5. Statistische Verfahren
        
        Text: {combined_text[:8000]}
        """
        
        return self._call_openai_api(prompt, api_key)
    
    def _calculate_relevance_score(self, chunks, api_key: str) -> str:
        """Berechnet Relevanz-Score basierend auf wissenschaftlichen Kriterien"""
        # Verwende Abstract/Introduction und Conclusion
        first_chunk = chunks[0].text if chunks else ""
        last_chunk = chunks[-1].text if len(chunks) > 1 else ""
        
        prompt = f"""
        Bewerte dieses wissenschaftliche Paper auf einer Skala von 1-10 bezüglich:
        
        1. Wissenschaftliche Rigorosität (1-10)
        2. Methodische Qualität (1-10)
        3. Praktische Relevanz (1-10)
        4. Originalität der Forschung (1-10)
        5. Klarheit der Darstellung (1-10)
        
        Gib für jeden Punkt eine Bewertung mit kurzer Begründung.
        Berechne dann den Gesamt-Score als Durchschnitt.
        
        Abstract/Einleitung: {first_chunk[:3000]}
        
        Fazit/Diskussion: {last_chunk[:3000]}
        """
        
        return self._call_openai_api(prompt, api_key)
    
    def _assess_research_quality(self, chunks, api_key: str) -> str:
        """Bewertet Forschungsqualität"""
        sample_text = "\n\n".join([chunk.text for chunk in chunks[:2]])
        
        prompt = f"""
        Bewerte die Qualität dieser wissenschaftlichen Arbeit:
        
        1. Hypothesen klar formuliert? (Ja/Nein + Erklärung)
        2. Methodik angemessen? (Ja/Nein + Erklärung)
        3. Stichprobengröße ausreichend? (Ja/Nein + Schätzung)
        4. Statistische Analyse korrekt? (Ja/Nein + Details)
        5. Limitationen diskutiert? (Ja/Nein + welche)
        6. Ergebnisse reproduzierbar? (Ja/Nein + Begründung)
        
        Text: {sample_text[:6000]}
        """
        
        return self._call_openai_api(prompt, api_key)
    
    def _analyze_citations(self, chunks) -> str:
        """Analysiert Zitationen im Paper"""
        all_text = "\n".join([chunk.text for chunk in chunks])
        
        # Finde Zitationen
        citation_patterns = [
            r'\([^)]*\d{4}[^)]*\)',  # (Author, 2023)
            r'\[\d+\]',              # [1]
            r'\w+\s+et\s+al\.',      # Smith et al.
        ]
        
        citations = []
        for pattern in citation_patterns:
            citations.extend(re.findall(pattern, all_text))
        
        # Statistiken
        unique_citations = list(set(citations))
        total_citations = len(citations)
        unique_count = len(unique_citations)
        
        # Jahre extrahieren
        years = re.findall(r'\b(19|20)\d{2}\b', all_text)
        recent_citations = len([year for year in years if int(year) >= 2020])
        
        result = f"""
        Zitations-Analyse:
        - Gesamtzahl Zitationen: {total_citations}
        - Eindeutige Zitationen: {unique_count}
        - Aktuelle Zitationen (≥2020): {recent_citations}
        - Durchschnittliches Alter: {2024 - sum(int(y) for y in years)/len(years):.1f} Jahre (falls Jahre gefunden)
        
        Beispiele: {unique_citations[:5]}
        """
        
        return result
    
    def _extract_statistical_info(self, chunks) -> str:
        """Extrahiert statistische Informationen"""
        all_text = "\n".join([chunk.text for chunk in chunks])
        
        # Statistische Begriffe und Werte finden
        stats_patterns = {
            'p_values': r'p\s*[<>=]\s*0\.\d+',
            'confidence_intervals': r'\d+%\s*CI',
            'sample_sizes': r'[nN]\s*=\s*\d+',
            'correlations': r'r\s*=\s*0\.\d+',
            'effect_sizes': r'(Cohen\'s\s*d|effect\s*size)',
            'significance': r'(significant|p\s*<\s*0\.05)'
        }
        
        stats_found = {}
        for stat_type, pattern in stats_patterns.items():
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            stats_found[stat_type] = matches
        
        result = "Statistische Analyse:\n"
        for stat_type, matches in stats_found.items():
            if matches:
                result += f"- {stat_type}: {len(matches)} gefunden\n"
                result += f"  Beispiele: {matches[:3]}\n"
        
        return result
    
    def _call_openai_api(self, prompt: str, api_key: str, max_tokens: int = 1500) -> str:
        """Ruft OpenAI API auf"""
        if not api_key:
            return "Fehler: Kein API-Key verfügbar"
        
        try:
            openai.api_key = api_key
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Du bist ein Experte für wissenschaftliche Paper-Analyse. Antworte präzise und strukturiert."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"OpenAI API Fehler: {str(e)}"
    
    def compare_chunking_strategies(self, text: str, api_key: str) -> dict:
        """Vergleicht verschiedene Chunking-Strategien"""
        strategies = ['token', 'sentence', 'semantic', 'recursive']
        comparison_results = {}
        
        for strategy in strategies:
            if strategy == 'semantic' and not self.chonkie_available:
                continue  # Skip semantic if Chonkie not available
                
            chunk_result = self.chunk_text_with_strategy(text, strategy)
            
            # Kurze Analyse für Vergleich
            chunks = chunk_result['chunks']
            if chunks:
                sample_analysis = self._create_summary_from_chunks(chunks[:3], api_key)
                
                comparison_results[strategy] = {
                    'metadata': chunk_result['metadata'],
                    'sample_analysis': sample_analysis[:200] + "...",
                    'recommendation': self._get_strategy_recommendation(strategy, chunk_result['metadata'])
                }
        
        return comparison_results
    
    def _get_strategy_recommendation(self, strategy: str, metadata: dict) -> str:
        """Gibt Empfehlung für Chunking-Strategie"""
        recommendations = {
            'token': 'Optimal für API-Calls mit Token-Limits. Gut für kostenkontrollierte Analysen.',
            'sentence': 'Erhält semantische Kohärenz. Empfohlen für qualitative Analyse.',
            'semantic': 'Beste Qualität für thematisch zusammenhängende Inhalte. Ideal für komplexe Papers.',
            'recursive': 'Flexibel und robust. Gute Balance zwischen Qualität und Performance.'
        }
        
        base_rec = recommendations.get(strategy, 'Keine spezifische Empfehlung')
        
        # Zusätzliche Empfehlungen basierend auf Metadata
        if metadata.get('total_chunks', 0) > 20:
            base_rec += " Achtung: Viele Chunks erzeugt - möglicherweise zu feingliedrig."
        elif metadata.get('total_chunks', 0) < 3:
            base_rec += " Achtung: Wenige Chunks - möglicherweise zu grob."
        
        return base_rec
    
    def export_analysis_results(self, results: dict, format_type: str = 'json') -> str:
        """Exportiert Analyse-Ergebnisse"""
        if format_type == 'json':
            return json.dumps(results, indent=2, ensure_ascii=False)
        elif format_type == 'markdown':
            return self._convert_to_markdown(results)
        else:
            return str(results)
    
    def _convert_to_markdown(self, results: dict) -> str:
        """Konvertiert Ergebnisse zu Markdown"""
        markdown = "# Chonkie Scientific Paper Analysis Report\n\n"
        markdown += f"**Timestamp:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        if 'chunk_metadata' in results:
            metadata = results['chunk_metadata']
            markdown += "## Chunking Metadata\n\n"
            markdown += f"- **Strategy:** {metadata.get('strategy', 'Unknown')}\n"
            markdown += f"- **Total Chunks:** {metadata.get('total_chunks', 0)}\n"
            markdown += f"- **Average Chunk Size:** {metadata.get('avg_chunk_size', 0):.0f} characters\n"
            markdown += f"- **Processing Time:** {metadata.get('processing_time', 0):.2f} seconds\n\n"
        
        if 'analysis_results' in results:
            markdown += "## Analysis Results\n\n"
            for analysis_type, result in results['analysis_results'].items():
                markdown += f"### {analysis_type.replace('_', ' ').title()}\n\n"
                markdown += f"{result}\n\n"
        
        return markdown

def module_chonkie_search():
    """Hauptfunktion für Chonkie Scientific Analysis Module"""
    st.title("🦛 Chonkie - Wissenschaftliche Paper-Analyse")
    
    # Status-Anzeige
    analyzer = ChonkieScientificAnalyzer()
    
    if analyzer.chonkie_available:
        st.success("✅ Chonkie verfügbar!")
        if analyzer.advanced_features:
            st.info("🚀 Erweiterte Chonkie-Features aktiviert")
    else:
        st.warning("⚠️ Chonkie nicht verfügbar - Fallback-Modus aktiv")
        st.info("Installation: `pip install chonkie`")
    
    # Sidebar-Konfiguration
    st.sidebar.header("🔧 Analyse-Konfiguration")
    
    # API-Key
    api_key = st.sidebar.text_input("OpenAI API Key:", type="password", 
                                   value=st.session_state.get("api_key", ""))
    if api_key:
        st.session_state["api_key"] = api_key
    
    # Chunking-Strategie
    chunking_strategy = st.sidebar.selectbox(
        "Chunking-Strategie:",
        options=["token", "sentence", "semantic", "recursive", "compare_all"],
        help="Wähle die optimale Strategie für deine Analyse"
    )
    
    # Analyse-Typen
    st.sidebar.subheader("Analyse-Typen")
    analysis_types = []
    
    if st.sidebar.checkbox("📄 Zusammenfassung", value=True):
        analysis_types.append("summary")
    if st.sidebar.checkbox("🔍 Schlüsselerkenntnisse", value=True):
        analysis_types.append("key_findings")
    if st.sidebar.checkbox("🧪 Methodik", value=False):
        analysis_types.append("methodology")
    if st.sidebar.checkbox("⭐ Relevanz-Score", value=False):
        analysis_types.append("relevance_score")
    if st.sidebar.checkbox("📊 Forschungsqualität", value=False):
        analysis_types.append("research_quality")
    if st.sidebar.checkbox("📚 Zitations-Analyse", value=False):
        analysis_types.append("citations_analysis")
    if st.sidebar.checkbox("📈 Statistische Analyse", value=False):
        analysis_types.append("statistical_analysis")
    
    # Hauptbereich
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Paper Upload", "🔍 Analyse", "📊 Vergleich", "📥 Export"])
    
    with tab1:
        st.header("Wissenschaftliche Paper hochladen")
        
        # Upload-Optionen
        upload_method = st.radio(
            "Upload-Methode:",
            ["PDF-Datei", "Text direkt eingeben", "Mehrere PDFs (Batch)"]
        )
        
        uploaded_texts = []
        file_names = []
        
        if upload_method == "PDF-Datei":
            uploaded_file = st.file_uploader("PDF-Datei wählen:", type="pdf")
            if uploaded_file:
                with st.spinner("Extrahiere Text aus PDF..."):
                    text = analyzer.extract_text_from_pdf(uploaded_file)
                    if text:
                        uploaded_texts.append(text)
                        file_names.append(uploaded_file.name)
                        st.success(f"✅ Text extrahiert: {len(text)} Zeichen")
                        
                        # Text-Vorschau
                        with st.expander("Text-Vorschau"):
                            st.text(text[:1000] + "..." if len(text) > 1000 else text)
        
        elif upload_method == "Text direkt eingeben":
            text_input = st.text_area("Wissenschaftlichen Text eingeben:", height=300)
            if text_input:
                uploaded_texts.append(text_input)
                file_names.append("Direkteingabe")
        
        elif upload_method == "Mehrere PDFs (Batch)":
            uploaded_files = st.file_uploader(
                "Mehrere PDF-Dateien wählen:", 
                type="pdf", 
                accept_multiple_files=True
            )
            
            if uploaded_files:
                progress_bar = st.progress(0)
                for i, file in enumerate(uploaded_files):
                    progress_bar.progress((i + 1) / len(uploaded_files))
                    
                    text = analyzer.extract_text_from_pdf(file)
                    if text:
                        uploaded_texts.append(text)
                        file_names.append(file.name)
                
                st.success(f"✅ {len(uploaded_texts)} Dateien verarbeitet")
        
        # Speichere in Session State
        if uploaded_texts:
            st.session_state["uploaded_texts"] = uploaded_texts
            st.session_state["file_names"] = file_names
    
    with tab2:
        st.header("🔍 Chonkie-Analyse durchführen")
        
        if "uploaded_texts" not in st.session_state or not st.session_state["uploaded_texts"]:
            st.info("Bitte erst Papers in Tab 'Paper Upload' hochladen")
            return
        
        if not analysis_types:
            st.warning("Bitte mindestens einen Analyse-Typ auswählen")
            return
        
        if not api_key:
            st.warning("Bitte OpenAI API Key eingeben")
            return
        
        # Analyse starten
        if st.button("🚀 Analyse starten", type="primary"):
            
            texts = st.session_state["uploaded_texts"]
            names = st.session_state["file_names"]
            
            for i, (text, name) in enumerate(zip(texts, names)):
                st.subheader(f"📄 Analyse: {name}")
                
                with st.spinner(f"Analysiere {name} mit {chunking_strategy}-Strategie..."):
                    
                    if chunking_strategy == "compare_all":
                        # Vergleiche alle Strategien
                        comparison = analyzer.compare_chunking_strategies(text, api_key)
                        
                        st.write("**Strategien-Vergleich:**")
                        for strategy, results in comparison.items():
                            with st.expander(f"{strategy.title()} Chunker"):
                                st.write(f"**Chunks:** {results['metadata']['total_chunks']}")
                                st.write(f"**Ø Größe:** {results['metadata']['avg_chunk_size']:.0f} Zeichen")
                                st.write(f"**Zeit:** {results['metadata']['processing_time']:.2f}s")
                                st.write(f"**Empfehlung:** {results['recommendation']}")
                                st.write("**Beispiel-Analyse:**")
                                st.write(results['sample_analysis'])
                    
                    else:
                        # Einzelne Strategie
                        results = analyzer.analyze_paper_with_chunking(
                            text, chunking_strategy, api_key, analysis_types
                        )
                        
                        if 'error' in results:
                            st.error(f"Fehler: {results['error']}")
                            continue
                        
                        # Chunking-Metadata anzeigen
                        metadata = results['chunk_metadata']
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Chunks", metadata['total_chunks'])
                        with col2:
                            st.metric("Ø Chunk-Größe", f"{metadata['avg_chunk_size']:.0f}")
                        with col3:
                            st.metric("Tokens", metadata['total_tokens'])
                        with col4:
                            st.metric("Zeit", f"{metadata['processing_time']:.2f}s")
                        
                        # Analyse-Ergebnisse anzeigen
                        st.write("**Analyse-Ergebnisse:**")
                        
                        for analysis_type, result in results['analysis_results'].items():
                            with st.expander(f"{analysis_type.replace('_', ' ').title()}"):
                                st.write(result)
                        
                        # Speichere Ergebnisse
                        if "analysis_results" not in st.session_state:
                            st.session_state["analysis_results"] = {}
                        
                        st.session_state["analysis_results"][name] = results
    
    with tab3:
        st.header("📊 Chunking-Strategien vergleichen")
        
        if "uploaded_texts" not in st.session_state or not st.session_state["uploaded_texts"]:
            st.info("Bitte erst Papers hochladen")
            return
        
        # Auswahl für Vergleich
        text_to_compare = st.selectbox(
            "Paper für Vergleich wählen:",
            options=range(len(st.session_state["file_names"])),
            format_func=lambda x: st.session_state["file_names"][x]
        )
        
        if st.button("🔄 Strategien vergleichen"):
            text = st.session_state["uploaded_texts"][text_to_compare]
            
            with st.spinner("Vergleiche Chunking-Strategien..."):
                comparison = analyzer.compare_chunking_strategies(text, api_key)
            
            # Ergebnisse als Tabelle
            comparison_data = []
            for strategy, results in comparison.items():
                metadata = results['metadata']
                comparison_data.append({
                    'Strategie': strategy.title(),
                    'Chunks': metadata['total_chunks'],
                    'Ø Größe': f"{metadata['avg_chunk_size']:.0f}",
                    'Tokens': metadata['total_tokens'],
                    'Zeit (s)': f"{metadata['processing_time']:.2f}",
                    'Empfehlung': results['recommendation'][:100] + "..."
                })
            
            if comparison_data:
                df = pd.DataFrame(comparison_data)
                st.dataframe(df, use_container_width=True)
            
            # Detaillierte Empfehlungen
            st.subheader("🎯 Empfehlungen")
            for strategy, results in comparison.items():
                with st.expander(f"📋 {strategy.title()} Chunker"):
                    st.write(f"**Vollständige Empfehlung:** {results['recommendation']}")
                    st.write(f"**Beispiel-Output:** {results['sample_analysis']}")
    
    with tab4:
        st.header("📥 Ergebnisse exportieren")
        
        if "analysis_results" not in st.session_state:
            st.info("Bitte erst Analysen durchführen")
            return
        
        # Export-Optionen
        export_format = st.selectbox("Export-Format:", ["JSON", "Markdown", "Excel"])
        
        # Einzelne Analyse wählen oder alle
        available_analyses = list(st.session_state["analysis_results"].keys())
        selected_analyses = st.multiselect(
            "Zu exportierende Analysen:",
            options=available_analyses,
            default=available_analyses
        )
        
        if st.button("📤 Export erstellen"):
            
            export_data = {}
            for analysis_name in selected_analyses:
                export_data[analysis_name] = st.session_state["analysis_results"][analysis_name]
            
            if export_format == "JSON":
                export_content = analyzer.export_analysis_results(export_data, 'json')
                st.download_button(
                    label="📥 JSON herunterladen",
                    data=export_content,
                    file_name=f"chonkie_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            
            elif export_format == "Markdown":
                export_content = analyzer.export_analysis_results(export_data, 'markdown')
                st.download_button(
                    label="📥 Markdown herunterladen",
                    data=export_content,
                    file_name=f"chonkie_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
            
            elif export_format == "Excel":
                # Excel-Export
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    
                    # Summary sheet
                    summary_data = []
                    for name, results in export_data.items():
                        if 'chunk_metadata' in results:
                            metadata = results['chunk_metadata']
                            summary_data.append({
                                'Paper': name,
                                'Chunker': results.get('chunker_type', 'Unknown'),
                                'Chunks': metadata.get('total_chunks', 0),
                                'Tokens': metadata.get('total_tokens', 0),
                                'Zeit': metadata.get('processing_time', 0)
                            })
                    
                    if summary_data:
                        summary_df = pd.DataFrame(summary_data)
                        summary_df.to_excel(writer, sheet_name='Summary', index=False)
                    
                    # Detailsheets pro Analyse
                    for name, results in export_data.items():
                        if 'analysis_results' in results:
                            detail_data = []
                            for analysis_type, result in results['analysis_results'].items():
                                detail_data.append({
                                    'Analyse-Typ': analysis_type,
                                    'Ergebnis': str(result)[:30000]  # Excel-Limit
                                })
                            
                            if detail_data:
                                detail_df = pd.DataFrame(detail_data)
                                safe_name = re.sub(r'[^\w\s-]', '', name)[:31]  # Excel sheet name limit
                                detail_df.to_excel(writer, sheet_name=safe_name, index=False)
                
                st.download_button(
                    label="📥 Excel herunterladen",
                    data=output.getvalue(),
                    file_name=f"chonkie_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            # Vorschau der Ergebnisse
            st.subheader("📋 Export-Vorschau")
            with st.expander("Inhalt anzeigen"):
                if export_format in ["JSON", "Markdown"]:
                    st.code(export_content[:2000] + "..." if len(export_content) > 2000 else export_content)
                else:
                    st.write("Excel-Datei erstellt - Download verfügbar")

# Entry Point für das Modul
if __name__ == "__main__":
    module_chonkie_search()
