"""
Chonkie Scientific Analysis Module
Advanced text chunking and analysis for scientific papers using the Chonkie library
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import numpy as np

try:
    from chonkie import (
        TokenChunker, 
        SentenceChunker, 
        RecursiveChunker, 
        SemanticChunker
    )
    CHONKIE_AVAILABLE = True
except ImportError:
    CHONKIE_AVAILABLE = False
    print("Warning: Chonkie library not installed. Install with: pip install chonkie")

@dataclass
class ScientificChunk:
    """Enhanced chunk class for scientific texts"""
    text: str
    token_count: int
    chunk_type: str
    section_type: Optional[str] = None
    citations: List[str] = None
    confidence_score: float = 0.0
    semantic_similarity: float = 0.0

class ChonkieScientificProcessor:
    """Advanced scientific text chunking using Chonkie library"""
    
    def __init__(self, 
                 chunk_size: int = 1000,
                 overlap: int = 200,
                 chunker_type: str = "recursive"):
        
        if not CHONKIE_AVAILABLE:
            raise ImportError("Chonkie library required. Install with: pip install chonkie")
        
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.chunker_type = chunker_type
        
        # Initialize the appropriate chunker
        self._init_chunker()
        
        # Scientific section patterns
        self.section_patterns = {
            'abstract': r'\b(abstract|zusammenfassung)\b',
            'introduction': r'\b(introduction|einleitung|background)\b',
            'methods': r'\b(methods|methodology|methoden|materials)\b',
            'results': r'\b(results|ergebnisse|findings)\b',
            'discussion': r'\b(discussion|diskussion|conclusion|fazit)\b',
            'references': r'\b(references|bibliography|literatur)\b'
        }
    
    def _init_chunker(self):
        """Initialize the appropriate Chonkie chunker"""
        if self.chunker_type == "token":
            self.chunker = TokenChunker(chunk_size=self.chunk_size, chunk_overlap=self.overlap)
        elif self.chunker_type == "sentence":
            self.chunker = SentenceChunker(chunk_size=self.chunk_size, chunk_overlap=self.overlap)
        elif self.chunker_type == "semantic":
            self.chunker = SemanticChunker(chunk_size=self.chunk_size, chunk_overlap=self.overlap)
        else:  # default to recursive
            self.chunker = RecursiveChunker(chunk_size=self.chunk_size, chunk_overlap=self.overlap)
    
    def chunk_scientific_text(self, text: str) -> List[ScientificChunk]:
        """
        Chunk scientific text with enhanced metadata
        """
        # Use Chonkie to create base chunks
        base_chunks = self.chunker(text)
        
        scientific_chunks = []
        
        for chunk in base_chunks:
            # Detect section type
            section_type = self._detect_section_type(chunk.text)
            
            # Extract citations
            citations = self._extract_citations(chunk.text)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(chunk.text)
            
            scientific_chunk = ScientificChunk(
                text=chunk.text,
                token_count=chunk.token_count,
                chunk_type=self.chunker_type,
                section_type=section_type,
                citations=citations,
                confidence_score=confidence_score
            )
            
            scientific_chunks.append(scientific_chunk)
        
        return scientific_chunks
    
    def _detect_section_type(self, text: str) -> Optional[str]:
        """Detect the type of scientific section"""
        text_lower = text.lower()
        
        for section, pattern in self.section_patterns.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                return section
        
        return "general"
    
    def _extract_citations(self, text: str) -> List[str]:
        """Extract citations from text"""
        # Pattern for different citation formats
        patterns = [
            r'\([^)]*\d{4}[^)]*\)',  # (Author, 2023)
            r'\[\d+\]',              # [1]
            r'\b\w+\s+et\s+al\.\s+\(\d{4}\)',  # Smith et al. (2023)
        ]
        
        citations = []
        for pattern in patterns:
            citations.extend(re.findall(pattern, text))
        
        return list(set(citations))  # Remove duplicates
    
    def _calculate_confidence_score(self, text: str) -> float:
        """Calculate confidence score based on scientific indicators"""
        indicators = [
            r'\b(study|research|analysis|experiment)\b',
            r'\b(significant|p\s*[<>=]\s*0\.\d+)\b',
            r'\b(conclusion|result|finding)\b',
            r'\b(hypothesis|theory|model)\b'
        ]
        
        score = 0.0
        word_count = len(text.split())
        
        for pattern in indicators:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            score += matches / word_count if word_count > 0 else 0
        
        return min(1.0, score * 10)  # Normalize to 0-1
    
    def chunk_by_semantic_sections(self, text: str) -> List[ScientificChunk]:
        """Enhanced semantic chunking for scientific papers"""
        if not hasattr(self, 'semantic_chunker'):
            try:
                self.semantic_chunker = SemanticChunker(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.overlap
                )
            except Exception:
                # Fallback to recursive if semantic not available
                return self.chunk_scientific_text(text)
        
        semantic_chunks = self.semantic_chunker(text)
        
        enhanced_chunks = []
        for chunk in semantic_chunks:
            scientific_chunk = ScientificChunk(
                text=chunk.text,
                token_count=chunk.token_count,
                chunk_type="semantic",
                section_type=self._detect_section_type(chunk.text),
                citations=self._extract_citations(chunk.text),
                confidence_score=self._calculate_confidence_score(chunk.text)
            )
            enhanced_chunks.append(scientific_chunk)
        
        return enhanced_chunks
    
    def analyze_chunk_quality(self, chunks: List[ScientificChunk]) -> Dict[str, Any]:
        """Analyze the quality of generated chunks"""
        if not chunks:
            return {"error": "No chunks to analyze"}
        
        total_chunks = len(chunks)
        avg_token_count = np.mean([chunk.token_count for chunk in chunks])
        avg_confidence = np.mean([chunk.confidence_score for chunk in chunks])
        
        section_distribution = {}
        total_citations = 0
        
        for chunk in chunks:
            section_type = chunk.section_type or "unknown"
            section_distribution[section_type] = section_distribution.get(section_type, 0) + 1
            total_citations += len(chunk.citations or [])
        
        return {
            "total_chunks": total_chunks,
            "average_token_count": round(avg_token_count, 2),
            "average_confidence": round(avg_confidence, 3),
            "section_distribution": section_distribution,
            "total_citations_found": total_citations,
            "chunker_type": self.chunker_type
        }

def get_available_chunkers() -> List[str]:
    """Return list of available Chonkie chunkers"""
    if not CHONKIE_AVAILABLE:
        return []
    
    return ["token", "sentence", "recursive", "semantic"]

def create_scientific_processor(chunker_type: str = "recursive", 
                               chunk_size: int = 1000, 
                               overlap: int = 200) -> ChonkieScientificProcessor:
    """Factory function to create a scientific processor"""
    return ChonkieScientificProcessor(
        chunk_size=chunk_size,
        overlap=overlap,
        chunker_type=chunker_type
    )
