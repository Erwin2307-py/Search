"""
Label Studio Scientific Image Analysis Module
===========================================
Analysiert Grafiken und Bilder aus wissenschaftlichen Papers mit Label Studio SDK
Ermöglicht automatische Extraktion, Annotation und Analyse von visuellen Elementen
"""

import streamlit as st
import requests
import pandas as pd
import re
import datetime
import os
import PyPDF2
import time
import json
import io
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pdfplumber
from PIL import Image, ImageEnhance, ImageFilter
import base64
import uuid

# Label Studio SDK Integration
try:
    from label_studio_sdk import Client
    from label_studio_sdk.data_manager import Filters, Column, Type, Operator
    LABELSTUDIO_AVAILABLE = True
    print("✅ Label Studio SDK erfolgreich geladen")
except ImportError:
    LABELSTUDIO_AVAILABLE = False
    print("⚠️ Label Studio SDK nicht verfügbar - installiere mit: pip install label-studio-sdk")
    
    # Mock-Klasse für Fallback
    class MockLabelStudioClient:
        def __init__(self, url, api_key):
            self.url = url
            self.api_key = api_key
        
        def check_connection(self):
            return False, "Label Studio SDK nicht installiert"
        
        def get_projects(self):
            return []
    
    Client = MockLabelStudioClient

# Zusätzliche Dependencies für Bildverarbeitung
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("⚠️ OpenCV nicht verfügbar - installiere mit: pip install opencv-python")

try:
    import fitz  # PyMuPDF für bessere PDF-Bild-Extraktion
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("⚠️ PyMuPDF nicht verfügbar - installiere mit: pip install PyMuPDF")

class ScientificImageAnalyzer:
    """
    Hauptklasse für wissenschaftliche Bildanalyse mit Label Studio
    """
    
    def __init__(self):
        self.labelstudio_available = LABELSTUDIO_AVAILABLE
        self.client = None
        self.projects = {}
        self.extracted_images = []
        self.analysis_results = {}
        
        # Vordefinierte Label-Konfigurationen für wissenschaftliche Bilder
        self.label_configs = {
            'scientific_figures': self._get_scientific_figures_config(),
            'tables_charts': self._get_tables_charts_config(),
            'microscopy': self._get_microscopy_config(),
            'molecular_structures': self._get_molecular_structures_config(),
            'medical_images': self._get_medical_images_config()
        }
    
    def connect_to_labelstudio(self, url: str, api_key: str) -> Tuple[bool, str]:
        """Verbindet sich mit Label Studio"""
        try:
            if not self.labelstudio_available:
                return False, "Label Studio SDK nicht verfügbar"
            
            self.client = Client(url=url, api_key=api_key)
            
            # Test der Verbindung
            projects = self.client.get_projects()
            return True, f"Verbindung erfolgreich! {len(projects)} Projekte gefunden."
            
        except Exception as e:
            return False, f"Verbindung fehlgeschlagen: {str(e)}"
    
    def _get_scientific_figures_config(self) -> str:
        """Label-Konfiguration für allgemeine wissenschaftliche Abbildungen"""
        return """
        <View>
            <Header value="Scientific Figure Analysis"/>
            <Image name="image" value="$image" zoom="true" zoomControl="true"/>
            
            <RectangleLabels name="figure_elements" toName="image" strokeWidth="3">
                <Label value="Graph/Chart" background="#FF6B6B" hotkey="1"/>
                <Label value="Diagram" background="#4ECDC4" hotkey="2"/>
                <Label value="Photo/Microscopy" background="#45B7D1" hotkey="3"/>
                <Label value="Table" background="#FFA07A" hotkey="4"/>
                <Label value="Caption" background="#98D8C8" hotkey="5"/>
                <Label value="Legend" background="#F7DC6F" hotkey="6"/>
                <Label value="Axis_Label" background="#BB8FCE" hotkey="7"/>
                <Label value="Data_Point" background="#85C1E9" hotkey="8"/>
                <Label value="Scale_Bar" background="#F8C471" hotkey="9"/>
                <Label value="Annotation_Arrow" background="#82E0AA" hotkey="0"/>
            </RectangleLabels>
            
            <Choices name="figure_type" toName="image" choice="single">
                <Choice value="Bar_Chart"/>
                <Choice value="Line_Graph"/>
                <Choice value="Scatter_Plot"/>
                <Choice value="Pie_Chart"/>
                <Choice value="Histogram"/>
                <Choice value="Box_Plot"/>
                <Choice value="Heatmap"/>
                <Choice value="Flow_Chart"/>
                <Choice value="Schematic"/>
                <Choice value="Microscopy_Image"/>
                <Choice value="Photograph"/>
                <Choice value="Composite_Figure"/>
            </Choices>
            
            <Rating name="image_quality" toName="image" maxRating="5" icon="star" size="medium"/>
            
            <TextArea name="description" toName="image" 
                     placeholder="Beschreibe die Hauptinhalte der Abbildung..."
                     rows="3"/>
                     
            <Number name="data_points_count" toName="image" 
                    placeholder="Anzahl Datenpunkte (falls anwendbar)"/>
        </View>
        """
    
    def _get_tables_charts_config(self) -> str:
        """Spezialisierte Konfiguration für Tabellen und Diagramme"""
        return """
        <View>
            <Header value="Table and Chart Analysis"/>
            <Image name="image" value="$image" zoom="true"/>
            
            <RectangleLabels name="table_elements" toName="image" strokeWidth="2">
                <Label value="Table_Header" background="#3498DB" hotkey="1"/>
                <Label value="Table_Row" background="#E74C3C" hotkey="2"/>
                <Label value="Table_Cell" background="#2ECC71" hotkey="3"/>
                <Label value="Chart_Title" background="#F39C12" hotkey="4"/>
                <Label value="X_Axis" background="#9B59B6" hotkey="5"/>
                <Label value="Y_Axis" background="#1ABC9C" hotkey="6"/>
                <Label value="Data_Series" background="#E67E22" hotkey="7"/>
                <Label value="Legend_Item" background="#34495E" hotkey="8"/>
            </RectangleLabels>
            
            <Number name="rows_count" toName="image" placeholder="Anzahl Zeilen"/>
            <Number name="columns_count" toName="image" placeholder="Anzahl Spalten"/>
            
            <Choices name="chart_type" toName="image" choice="single">
                <Choice value="Bar_Chart"/>
                <Choice value="Line_Chart"/>
                <Choice value="Pie_Chart"/>
                <Choice value="Scatter_Plot"/>
                <Choice value="Area_Chart"/>
                <Choice value="Data_Table"/>
                <Choice value="Mixed_Chart"/>
            </Choices>
            
            <TextArea name="extracted_data" toName="image" 
                     placeholder="Extrahierte Daten oder wichtige Zahlen..."
                     rows="4"/>
        </View>
        """
    
    def _get_microscopy_config(self) -> str:
        """Konfiguration für Mikroskopie-Bilder"""
        return """
        <View>
            <Header value="Microscopy Image Analysis"/>
            <Image name="image" value="$image" zoom="true"/>
            
            <PolygonLabels name="microscopy_regions" toName="image" strokeWidth="3">
                <Label value="Cell" background="#FF6B6B" hotkey="1"/>
                <Label value="Nucleus" background="#4ECDC4" hotkey="2"/>
                <Label value="Organelle" background="#45B7D1" hotkey="3"/>
                <Label value="Membrane" background="#FFA07A" hotkey="4"/>
                <Label value="Protein_Structure" background="#98D8C8" hotkey="5"/>
                <Label value="Tissue" background="#F7DC6F" hotkey="6"/>
                <Label value="Artifact" background="#BB8FCE" hotkey="7"/>
                <Label value="Background" background="#85C1E9" hotkey="8"/>
            </PolygonLabels>
            
            <Choices name="microscopy_type" toName="image" choice="single">
                <Choice value="Light_Microscopy"/>
                <Choice value="Electron_Microscopy"/>
                <Choice value="Fluorescence"/>
                <Choice value="Confocal"/>
                <Choice value="Phase_Contrast"/>
                <Choice value="DIC"/>
                <Choice value="Immunofluorescence"/>
            </Choices>
            
            <TextArea name="staining_method" toName="image" 
                     placeholder="Färbungsmethode oder Marker..."
                     rows="2"/>
        </View>
        """
    
    def _get_molecular_structures_config(self) -> str:
        """Konfiguration für molekulare Strukturen"""
        return """
        <View>
            <Header value="Molecular Structure Analysis"/>
            <Image name="image" value="$image" zoom="true"/>
            
            <PolygonLabels name="molecular_elements" toName="image" strokeWidth="2">
                <Label value="Protein" background="#E74C3C" hotkey="1"/>
                <Label value="DNA_RNA" background="#3498DB" hotkey="2"/>
                <Label value="Ligand" background="#2ECC71" hotkey="3"/>
                <Label value="Active_Site" background="#F39C12" hotkey="4"/>
                <Label value="Secondary_Structure" background="#9B59B6" hotkey="5"/>
                <Label value="Domain" background="#1ABC9C" hotkey="6"/>
                <Label value="Bond" background="#E67E22" hotkey="7"/>
                <Label value="Metal_Ion" background="#34495E" hotkey="8"/>
            </PolygonLabels>
            
            <Choices name="structure_type" toName="image" choice="single">
                <Choice value="Crystal_Structure"/>
                <Choice value="NMR_Structure"/>
                <Choice value="Cryo_EM"/>
                <Choice value="Molecular_Model"/>
                <Choice value="Pathway_Diagram"/>
                <Choice value="Chemical_Formula"/>
            </Choices>
            
            <TextArea name="pdb_id" toName="image" 
                     placeholder="PDB-ID oder andere Identifikatoren..."
                     rows="1"/>
        </View>
        """
    
    def _get_medical_images_config(self) -> str:
        """Konfiguration für medizinische Bilder"""
        return """
        <View>
            <Header value="Medical Image Analysis"/>
            <Image name="image" value="$image" zoom="true"/>
            
            <RectangleLabels name="medical_regions" toName="image" strokeWidth="3">
                <Label value="Normal_Tissue" background="#2ECC71" hotkey="1"/>
                <Label value="Abnormal_Tissue" background="#E74C3C" hotkey="2"/>
                <Label value="Lesion" background="#F39C12" hotkey="3"/>
                <Label value="Organ" background="#3498DB" hotkey="4"/>
                <Label value="Bone" background="#95A5A6" hotkey="5"/>
                <Label value="Vessel" background="#E91E63" hotkey="6"/>
                <Label value="Measurement" background="#9C27B0" hotkey="7"/>
                <Label value="Annotation" background="#FF5722" hotkey="8"/>
            </RectangleLabels>
            
            <Choices name="imaging_modality" toName="image" choice="single">
                <Choice value="X_Ray"/>
                <Choice value="CT_Scan"/>
                <Choice value="MRI"/>
                <Choice value="Ultrasound"/>
                <Choice value="PET_Scan"/>
                <Choice value="Mammography"/>
                <Choice value="Endoscopy"/>
                <Choice value="Histopathology"/>
            </Choices>
            
            <Rating name="diagnostic_confidence" toName="image" maxRating="5" icon="star"/>
        </View>
        """
    
    def extract_images_from_pdf(self, pdf_file, extraction_method: str = "pdfplumber") -> List[Dict]:
        """Extrahiert Bilder aus PDF mit verschiedenen Methoden"""
        
        extracted_images = []
        
        if extraction_method == "pymupdf" and PYMUPDF_AVAILABLE:
            extracted_images = self._extract_with_pymupdf(pdf_file)
        elif extraction_method == "pdfplumber":
            extracted_images = self._extract_with_pdfplumber(pdf_file)
        else:
            extracted_images = self._extract_with_pypdf2(pdf_file)
        
        self.extracted_images.extend(extracted_images)
        return extracted_images
    
    def _extract_with_pymupdf(self, pdf_file) -> List[Dict]:
        """Extrahiert Bilder mit PyMuPDF (bessere Qualität)"""
        images = []
        
        try:
            # Speichere PDF temporär
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(pdf_file.read())
                tmp_path = tmp_file.name
            
            # Öffne mit fitz
            doc = fitz.open(tmp_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    # Extrahiere Bild
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    if pix.n - pix.alpha < 4:  # Nur RGB/Grayscale
                        img_data = pix.tobytes("png")
                        img_pil = Image.open(io.BytesIO(img_data))
                        
                        # Metadaten sammeln
                        images.append({
                            'image': img_pil,
                            'page': page_num + 1,
                            'index': img_index + 1,
                            'filename': f"page_{page_num+1}_img_{img_index+1}.png",
                            'size': img_pil.size,
                            'format': 'PNG',
                            'extraction_method': 'PyMuPDF',
                            'quality_score': self._assess_image_quality(img_pil)
                        })
                    
                    pix = None
            
            doc.close()
            os.unlink(tmp_path)  # Lösche temporäre Datei
            
        except Exception as e:
            st.error(f"PyMuPDF-Extraktion fehlgeschlagen: {e}")
        
        return images
    
    def _extract_with_pdfplumber(self, pdf_file) -> List[Dict]:
        """Extrahiert Bilder mit pdfplumber"""
        images = []
        
        try:
            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_images = page.images
                    
                    for img_index, img_dict in enumerate(page_images):
                        try:
                            # Crop-Bereich definieren
                            x0, y0, x1, y1 = img_dict['x0'], img_dict['y0'], img_dict['x1'], img_dict['y1']
                            
                            # Bild croppen
                            cropped_page = page.crop((x0, y0, x1, y1))
                            img_pil = cropped_page.to_image().original
                            
                            images.append({
                                'image': img_pil,
                                'page': page_num + 1,
                                'index': img_index + 1,
                                'filename': f"page_{page_num+1}_img_{img_index+1}.png",
                                'size': img_pil.size,
                                'format': img_pil.format or 'PNG',
                                'extraction_method': 'pdfplumber',
                                'bbox': (x0, y0, x1, y1),
                                'quality_score': self._assess_image_quality(img_pil)
                            })
                            
                        except Exception as e:
                            st.warning(f"Fehler bei Bild {img_index+1} auf Seite {page_num+1}: {e}")
                            
        except Exception as e:
            st.error(f"pdfplumber-Extraktion fehlgeschlagen: {e}")
        
        return images
    
    def _extract_with_pypdf2(self, pdf_file) -> List[Dict]:
        """Fallback-Extraktion mit PyPDF2 (begrenzte Bildextraktion)"""
        images = []
        # PyPDF2 hat sehr begrenzte Bildextraktions-Funktionalität
        # Hier würde eine grundlegende Implementierung stehen
        st.info("PyPDF2 hat begrenzte Bildextraktions-Funktionalität. Verwende PyMuPDF für bessere Ergebnisse.")
        return images
    
    def _assess_image_quality(self, image: Image.Image) -> float:
        """Bewertet Bildqualität mit einfachen Metriken"""
        try:
            # Bildgröße bewerten
            width, height = image.size
            size_score = min(1.0, (width * height) / (500 * 500))  # Normalisiert auf 500x500
            
            # Farbraumvielfalt (vereinfacht)
            if image.mode == 'RGB':
                color_score = 1.0
            elif image.mode == 'L':
                color_score = 0.7
            else:
                color_score = 0.5
            
            # Einfache Schärfe-Bewertung (Kantenstärke)
            if OPENCV_AVAILABLE:
                import numpy as np
                gray = np.array(image.convert('L'))
                laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
                sharpness_score = min(1.0, laplacian_var / 1000)  # Normalisiert
            else:
                sharpness_score = 0.8  # Default wenn OpenCV nicht verfügbar
            
            # Gesamtscore
            quality_score = (size_score + color_score + sharpness_score) / 3
            return round(quality_score, 2)
            
        except Exception:
            return 0.5  # Default-Score bei Fehlern
    
    def enhance_image(self, image: Image.Image, enhancement_settings: Dict) -> Image.Image:
        """Verbessert Bildqualität für bessere Analyse"""
        try:
            enhanced = image.copy()
            
            # Helligkeit
            if 'brightness' in enhancement_settings:
                enhancer = ImageEnhance.Brightness(enhanced)
                enhanced = enhancer.enhance(enhancement_settings['brightness'])
            
            # Kontrast
            if 'contrast' in enhancement_settings:
                enhancer = ImageEnhance.Contrast(enhanced)
                enhanced = enhancer.enhance(enhancement_settings['contrast'])
            
            # Schärfe
            if 'sharpness' in enhancement_settings:
                enhancer = ImageEnhance.Sharpness(enhanced)
                enhanced = enhancer.enhance(enhancement_settings['sharpness'])
            
            # Filter anwenden
            if enhancement_settings.get('apply_filter'):
                if enhancement_settings.get('filter_type') == 'blur':
                    enhanced = enhanced.filter(ImageFilter.BLUR)
                elif enhancement_settings.get('filter_type') == 'sharpen':
                    enhanced = enhanced.filter(ImageFilter.SHARPEN)
                elif enhancement_settings.get('filter_type') == 'edge_enhance':
                    enhanced = enhanced.filter(ImageFilter.EDGE_ENHANCE)
            
            return enhanced
            
        except Exception as e:
            st.error(f"Bildverbesserung fehlgeschlagen: {e}")
            return image
    
    def create_labelstudio_project(self, project_name: str, project_type: str, description: str = "") -> Optional[Dict]:
        """Erstellt ein neues Label Studio Projekt"""
        if not self.client:
            return None
        
        try:
            label_config = self.label_configs.get(project_type, self.label_configs['scientific_figures'])
            
            project = self.client.start_project(
                title=project_name,
                description=description,
                label_config=label_config
            )
            
            project_info = {
                'id': project.id,
                'title': project.title,
                'description': project.description,
                'created_at': datetime.datetime.now().isoformat(),
                'type': project_type,
                'label_config': label_config
            }
            
            self.projects[project.id] = project_info
            return project_info
            
        except Exception as e:
            st.error(f"Projekt-Erstellung fehlgeschlagen: {e}")
            return None
    
    def upload_images_to_project(self, project_id: int, images: List[Dict], batch_size: int = 10) -> bool:
        """Lädt Bilder in Label Studio Projekt hoch"""
        if not self.client:
            return False
        
        try:
            project = self.client.get_project(project_id)
            
            # Bilder in Batches verarbeiten
            for i in range(0, len(images), batch_size):
                batch = images[i:i + batch_size]
                tasks = []
                
                for img_data in batch:
                    # Konvertiere Bild zu Base64
                    img_buffer = io.BytesIO()
                    img_data['image'].save(img_buffer, format='PNG')
                    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
                    
                    task = {
                        'data': {
                            'image': f"data:image/png;base64,{img_base64}"
                        },
                        'meta': {
                            'filename': img_data['filename'],
                            'page': img_data['page'],
                            'index': img_data['index'],
                            'extraction_method': img_data['extraction_method'],
                            'quality_score': img_data['quality_score']
                        }
                    }
                    tasks.append(task)
                
                # Upload Batch
                project.import_tasks(tasks)
                st.success(f"Batch {i//batch_size + 1} hochgeladen: {len(batch)} Bilder")
            
            return True
            
        except Exception as e:
            st.error(f"Upload fehlgeschlagen: {e}")
            return False
    
    def analyze_annotations(self, project_id: int) -> Dict:
        """Analysiert Annotations aus Label Studio Projekt"""
        if not self.client:
            return {}
        
        try:
            project = self.client.get_project(project_id)
            annotations = project.get_annotations()
            
            analysis = {
                'total_tasks': len(project.get_tasks()),
                'total_annotations': len(annotations),
                'completion_rate': 0,
                'label_distribution': {},
                'quality_metrics': {},
                'annotation_details': []
            }
            
            # Analyse der Annotations
            label_counts = {}
            quality_scores = []
            
            for annotation in annotations:
                if annotation.get('result'):
                    for result in annotation['result']:
                        # Label-Zählung
                        if 'value' in result and 'rectanglelabels' in result['value']:
                            for label in result['value']['rectanglelabels']:
                                label_counts[label] = label_counts.get(label, 0) + 1
                        
                        # Qualitätsbewertung
                        if 'value' in result and 'rating' in result['value']:
                            quality_scores.append(result['value']['rating'])
            
            # Berechne Statistiken
            analysis['label_distribution'] = label_counts
            analysis['completion_rate'] = len(annotations) / analysis['total_tasks'] * 100 if analysis['total_tasks'] > 0 else 0
            
            if quality_scores:
                analysis['quality_metrics'] = {
                    'average_rating': sum(quality_scores) / len(quality_scores),
                    'total_ratings': len(quality_scores)
                }
            
            return analysis
            
        except Exception as e:
            st.error(f"Annotations-Analyse fehlgeschlagen: {e}")
            return {}
    
    def export_analysis_results(self, project_id: int, format_type: str = 'json') -> Optional[str]:
        """Exportiert Analyse-Ergebnisse"""
        if not self.client:
            return None
        
        try:
            project = self.client.get_project(project_id)
            
            if format_type == 'json':
                export_data = project.export_tasks(export_type='JSON')
            elif format_type == 'csv':
                export_data = project.export_tasks(export_type='CSV')
            else:
                export_data = project.export_tasks(export_type='JSON')
            
            return export_data
            
        except Exception as e:
            st.error(f"Export fehlgeschlagen: {e}")
            return None

def module_scientific_images():
    """Hauptfunktion für Scientific Images Module mit Label Studio"""
    st.title("🖼️ Wissenschaftliche Bildanalyse mit Label Studio")
    
    # Initialisiere Analyzer
    analyzer = ScientificImageAnalyzer()
    
    # Status-Anzeige
    if analyzer.labelstudio_available:
        st.success("✅ Label Studio SDK verfügbar!")
    else:
        st.error("❌ Label Studio SDK nicht verfügbar!")
        st.info("Installation: `pip install label-studio-sdk`")
        st.info("Eingeschränkte Funktionalität ohne Label Studio SDK")
    
    # Sidebar-Konfiguration
    st.sidebar.header("🔧 Label Studio Konfiguration")
    
    # Label Studio Verbindung
    ls_url = st.sidebar.text_input("Label Studio URL:", value="http://localhost:8080")
    ls_api_key = st.sidebar.text_input("API Key:", type="password")
    
    if st.sidebar.button("🔗 Verbindung testen"):
        if ls_url and ls_api_key:
            success, message = analyzer.connect_to_labelstudio(ls_url, ls_api_key)
            if success:
                st.sidebar.success(message)
                st.session_state['labelstudio_connected'] = True
            else:
                st.sidebar.error(message)
                st.session_state['labelstudio_connected'] = False
        else:
            st.sidebar.warning("URL und API Key erforderlich")
    
    # Tab-Interface
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📄 PDF Upload", 
        "🖼️ Bildextraktion", 
        "🏷️ Label Studio", 
        "📊 Analyse", 
        "📥 Export"
    ])
    
    with tab1:
        st.header("Wissenschaftliche Papers hochladen")
        
        uploaded_files = st.file_uploader(
            "PDF-Dateien für Bildextraktion:",
            type="pdf",
            accept_multiple_files=True,
            help="Wähle wissenschaftliche Papers für die Bildanalyse"
        )
        
        # Extraktions-Einstellungen
        st.subheader("⚙️ Extraktions-Einstellungen")
        
        col1, col2 = st.columns(2)
        with col1:
            extraction_method = st.selectbox(
                "Extraktions-Methode:",
                ["pdfplumber", "pymupdf", "pypdf2"],
                help="PyMuPDF bietet die beste Qualität"
            )
        
        with col2:
            min_image_size = st.slider(
                "Min. Bildgröße (Pixel):",
                50, 500, 100,
                help="Filtert sehr kleine Bilder aus"
            )
        
        quality_filter = st.checkbox(
            "Qualitätsfilter anwenden",
            value=True,
            help="Entfernt Bilder mit niedriger Qualität"
        )
        
        # Speichere Upload-Einstellungen
        if uploaded_files:
            st.session_state['uploaded_pdfs'] = uploaded_files
            st.session_state['extraction_settings'] = {
                'method': extraction_method,
                'min_size': min_image_size,
                'quality_filter': quality_filter
            }
            
            st.success(f"✅ {len(uploaded_files)} PDF-Dateien hochgeladen")
            
            # PDF-Info anzeigen
            total_size = sum(len(f.read()) for f in uploaded_files) / (1024 * 1024)
            for f in uploaded_files:
                f.seek(0)  # Reset file pointer
            
            st.info(f"Gesamtgröße: {total_size:.1f} MB")
    
    with tab2:
        st.header("🖼️ Bilder aus PDFs extrahieren")
        
        if 'uploaded_pdfs' not in st.session_state:
            st.info("Bitte erst PDFs in Tab 'PDF Upload' hochladen")
            return
        
        if st.button("🚀 Bildextraktion starten", type="primary"):
            
            uploaded_files = st.session_state['uploaded_pdfs']
            settings = st.session_state.get('extraction_settings', {})
            
            all_extracted_images = []
            progress_bar = st.progress(0)
            
            for i, pdf_file in enumerate(uploaded_files):
                st.subheader(f"📄 Verarbeite: {pdf_file.name}")
                
                with st.spinner(f"Extrahiere Bilder aus {pdf_file.name}..."):
                    pdf_file.seek(0)  # Reset file pointer
                    
                    extracted = analyzer.extract_images_from_pdf(
                        pdf_file, 
                        settings.get('method', 'pdfplumber')
                    )
                    
                    # Filter anwenden
                    filtered_images = []
                    for img_data in extracted:
                        # Größenfilter
                        width, height = img_data['size']
                        if width >= settings.get('min_size', 100) and height >= settings.get('min_size', 100):
                            # Qualitätsfilter
                            if not settings.get('quality_filter', True) or img_data['quality_score'] >= 0.3:
                                filtered_images.append(img_data)
                    
                    all_extracted_images.extend(filtered_images)
                    
                    st.success(f"✅ {len(filtered_images)}/{len(extracted)} Bilder extrahiert (nach Filterung)")
                
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            # Speichere Ergebnisse
            st.session_state['extracted_images'] = all_extracted_images
            
            st.header("📊 Extraktions-Ergebnisse")
            st.success(f"🎯 Gesamt: {len(all_extracted_images)} Bilder aus {len(uploaded_files)} PDFs extrahiert")
            
            # Statistiken
            if all_extracted_images:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    avg_quality = sum(img['quality_score'] for img in all_extracted_images) / len(all_extracted_images)
                    st.metric("Ø Qualität", f"{avg_quality:.2f}")
                
                with col2:
                    total_size = sum(img['size'][0] * img['size'][1] for img in all_extracted_images)
                    st.metric("Pixel gesamt", f"{total_size:,}")
                
                with col3:
                    methods_used = set(img['extraction_method'] for img in all_extracted_images)
                    st.metric("Methoden", len(methods_used))
                
                with col4:
                    pages_with_images = set(img['page'] for img in all_extracted_images)
                    st.metric("Seiten", len(pages_with_images))
                
                # Bildvorschau
                st.subheader("🖼️ Bildvorschau")
                
                cols = st.columns(min(4, len(all_extracted_images)))
                for i, img_data in enumerate(all_extracted_images[:8]):  # Erste 8 Bilder
                    with cols[i % 4]:
                        st.image(
                            img_data['image'], 
                            caption=f"{img_data['filename']}\nQualität: {img_data['quality_score']:.2f}",
                            width=150
                        )
                
                if len(all_extracted_images) > 8:
                    st.info(f"... und {len(all_extracted_images) - 8} weitere Bilder")
    
    with tab3:
        st.header("🏷️ Label Studio Integration")
        
        if not st.session_state.get('labelstudio_connected', False):
            st.warning("Bitte erst Label Studio Verbindung herstellen")
            return
        
        if 'extracted_images' not in st.session_state:
            st.info("Bitte erst Bilder extrahieren")
            return
        
        # Projekt-Management
        st.subheader("📂 Projekt erstellen")
        
        col1, col2 = st.columns(2)
        with col1:
            project_name = st.text_input("Projekt-Name:", value=f"Scientific_Images_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}")
        
        with col2:
            project_type = st.selectbox(
                "Projekt-Typ:",
                list(analyzer.label_configs.keys()),
                format_func=lambda x: x.replace('_', ' ').title()
            )
        
        project_description = st.text_area(
            "Projekt-Beschreibung:",
            value="Automatisch erstelltes Projekt für wissenschaftliche Bildanalyse"
        )
        
        if st.button("🏗️ Projekt erstellen"):
            project_info = analyzer.create_labelstudio_project(
                project_name, 
                project_type, 
                project_description
            )
            
            if project_info:
                st.success(f"✅ Projekt '{project_name}' erstellt (ID: {project_info['id']})")
                st.session_state['current_project'] = project_info
            else:
                st.error("❌ Projekt-Erstellung fehlgeschlagen")
        
        # Bilder hochladen
        if 'current_project' in st.session_state:
            st.subheader("📤 Bilder zu Projekt hinzufügen")
            
            project_info = st.session_state['current_project']
            st.info(f"Aktuelles Projekt: {project_info['title']} (ID: {project_info['id']})")
            
            images = st.session_state['extracted_images']
            
            # Upload-Einstellungen
            col1, col2 = st.columns(2)
            with col1:
                batch_size = st.slider("Batch-Größe:", 1, 20, 10)
            with col2:
                selected_images = st.slider(
                    "Anzahl Bilder:", 
                    1, len(images), 
                    min(len(images), 20)
                )
            
            if st.button("📤 Bilder hochladen"):
                success = analyzer.upload_images_to_project(
                    project_info['id'],
                    images[:selected_images],
                    batch_size
                )
                
                if success:
                    st.success(f"✅ {selected_images} Bilder erfolgreich hochgeladen!")
                    st.info("Du kannst jetzt in Label Studio mit der Annotation beginnen.")
                    st.markdown(f"**Label Studio öffnen:** [{ls_url}]({ls_url})")
        
        # Bestehende Projekte anzeigen
        st.subheader("📋 Bestehende Projekte")
        
        if analyzer.client:
            try:
                projects = analyzer.client.get_projects()
                if projects:
                    for project in projects[:5]:  # Erste 5 Projekte
                        with st.expander(f"📁 {project.title} (ID: {project.id})"):
                            tasks = project.get_tasks()
                            annotations = project.get_annotations()
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Tasks", len(tasks))
                            with col2:
                                st.metric("Annotations", len(annotations))
                            with col3:
                                completion = len(annotations) / len(tasks) * 100 if tasks else 0
                                st.metric("Fortschritt", f"{completion:.1f}%")
                else:
                    st.info("Keine Projekte gefunden")
                    
            except Exception as e:
                st.error(f"Fehler beim Laden der Projekte: {e}")
    
    with tab4:
        st.header("📊 Annotations-Analyse")
        
        if not analyzer.client:
            st.warning("Label Studio Verbindung erforderlich")
            return
        
        # Projekt auswählen für Analyse
        try:
            projects = analyzer.client.get_projects()
            if not projects:
                st.info("Keine Projekte für Analyse verfügbar")
                return
            
            project_options = {f"{p.title} (ID: {p.id})": p.id for p in projects}
            selected_project_key = st.selectbox("Projekt für Analyse:", list(project_options.keys()))
            selected_project_id = project_options[selected_project_key]
            
            if st.button("📊 Analyse durchführen"):
                with st.spinner("Analysiere Annotations..."):
                    analysis = analyzer.analyze_annotations(selected_project_id)
                
                if analysis:
                    st.subheader("🎯 Analyse-Ergebnisse")
                    
                    # Übersichts-Metriken
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Tasks gesamt", analysis['total_tasks'])
                    with col2:
                        st.metric("Annotations", analysis['total_annotations'])
                    with col3:
                        st.metric("Completion Rate", f"{analysis['completion_rate']:.1f}%")
                    with col4:
                        if 'quality_metrics' in analysis and analysis['quality_metrics']:
                            avg_rating = analysis['quality_metrics']['average_rating']
                            st.metric("Ø Bewertung", f"{avg_rating:.2f}/5")
                    
                    # Label-Verteilung
                    if analysis['label_distribution']:
                        st.subheader("🏷️ Label-Verteilung")
                        
                        df_labels = pd.DataFrame(
                            list(analysis['label_distribution'].items()),
                            columns=['Label', 'Anzahl']
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.dataframe(df_labels)
                        with col2:
                            st.bar_chart(df_labels.set_index('Label'))
                    
                    # Detaillierte Statistiken
                    st.subheader("📈 Detaillierte Statistiken")
                    
                    stats_data = []
                    stats_data.append(["Gesamtprojekte", len(projects)])
                    stats_data.append(["Analysiertes Projekt", selected_project_key])
                    stats_data.append(["Tasks", analysis['total_tasks']])
                    stats_data.append(["Annotations", analysis['total_annotations']])
                    stats_data.append(["Completion Rate", f"{analysis['completion_rate']:.2f}%"])
                    
                    if analysis['label_distribution']:
                        stats_data.append(["Unique Labels", len(analysis['label_distribution'])])
                        most_common = max(analysis['label_distribution'], key=analysis['label_distribution'].get)
                        stats_data.append(["Häufigstes Label", f"{most_common} ({analysis['label_distribution'][most_common]}x)"])
                    
                    df_stats = pd.DataFrame(stats_data, columns=['Metrik', 'Wert'])
                    st.dataframe(df_stats, use_container_width=True)
                
        except Exception as e:
            st.error(f"Analyse fehlgeschlagen: {e}")
    
    with tab5:
        st.header("📥 Export und Download")
        
        if not analyzer.client:
            st.warning("Label Studio Verbindung erforderlich")
            return
        
        # Export-Optionen
        st.subheader("📤 Annotations exportieren")
        
        try:
            projects = analyzer.client.get_projects()
            if projects:
                project_options = {f"{p.title} (ID: {p.id})": p.id for p in projects}
                export_project_key = st.selectbox("Projekt für Export:", list(project_options.keys()))
                export_project_id = project_options[export_project_key]
                
                col1, col2 = st.columns(2)
                with col1:
                    export_format = st.selectbox("Export-Format:", ["JSON", "CSV", "YOLO", "COCO"])
                
                with col2:
                    include_images = st.checkbox("Bilder einschließen", value=False)
                
                if st.button("📥 Export erstellen"):
                    with st.spinner("Erstelle Export..."):
                        export_data = analyzer.export_analysis_results(export_project_id, export_format.lower())
                    
                    if export_data:
                        # Download-Button erstellen
                        if export_format == "JSON":
                            file_data = json.dumps(export_data, indent=2) if isinstance(export_data, (dict, list)) else export_data
                            mime_type = "application/json"
                            file_extension = "json"
                        else:
                            file_data = str(export_data)
                            mime_type = "text/plain"
                            file_extension = export_format.lower()
                        
                        st.download_button(
                            label=f"📥 {export_format} herunterladen",
                            data=file_data,
                            file_name=f"labelstudio_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}",
                            mime=mime_type
                        )
                        
                        st.success("✅ Export erfolgreich erstellt!")
                        
                        # Vorschau der Daten
                        st.subheader("📋 Export-Vorschau")
                        if export_format == "JSON":
                            st.code(file_data[:2000] + "..." if len(str(file_data)) > 2000 else file_data, language="json")
                        else:
                            st.text(str(file_data)[:1000] + "..." if len(str(file_data)) > 1000 else str(file_data))
            
            else:
                st.info("Keine Projekte für Export verfügbar")
        
        except Exception as e:
            st.error(f"Export fehlgeschlagen: {e}")
        
        # Batch-Download für extrahierte Bilder
        st.subheader("📦 Extrahierte Bilder herunterladen")
        
        if 'extracted_images' in st.session_state:
            images = st.session_state['extracted_images']
            
            if st.button("📦 Alle Bilder als ZIP herunterladen"):
                with st.spinner("Erstelle ZIP-Archiv..."):
                    
                    # Erstelle ZIP in Memory
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for img_data in images:
                            # Konvertiere Bild zu Bytes
                            img_buffer = io.BytesIO()
                            img_data['image'].save(img_buffer, format='PNG')
                            img_bytes = img_buffer.getvalue()
                            
                            # Füge zu ZIP hinzu
                            zip_file.writestr(img_data['filename'], img_bytes)
                    
                    # Download-Button
                    st.download_button(
                        label="📥 ZIP-Archiv herunterladen",
                        data=zip_buffer.getvalue(),
                        file_name=f"extracted_images_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip"
                    )
                    
                    st.success(f"✅ ZIP-Archiv mit {len(images)} Bildern erstellt!")
        
        else:
            st.info("Keine extrahierten Bilder verfügbar")

# Entry Point für das Modul
if __name__ == "__main__":
    module_scientific_images()
