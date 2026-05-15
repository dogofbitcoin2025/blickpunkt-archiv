"""
BlickPUNKT Archiv – Ähnlichkeitserkennung
Berechnet Ähnlichkeiten zwischen Artikeln.
Nutzt TF-IDF als leichtgewichtige Lösung, optional sentence-transformers.
"""

import re
import math
import struct
import logging
from collections import Counter
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

# Thesaurus für Synonym-Normalisierung
try:
    import thesaurus
    HAS_THESAURUS = True
except ImportError:
    HAS_THESAURUS = False

# Optional: sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

# Stoppwörter
STOPWORDS = {
    "der", "die", "das", "und", "in", "von", "zu", "den", "für",
    "mit", "auf", "ist", "im", "dem", "ein", "eine", "es", "sich",
    "des", "als", "an", "auch", "aus", "bei", "hat", "nach", "wird",
    "wie", "noch", "war", "sind", "über", "so", "zum", "aber",
    "sie", "er", "nicht", "oder", "was", "ich", "haben", "dass",
    "wir", "werden", "seine", "einer", "kann", "mehr", "alle",
}


class SimilarityEngine:
    """Berechnet Ähnlichkeiten zwischen Artikeln."""

    def __init__(self, use_transformers: bool = False):
        self.use_transformers = use_transformers and HAS_TRANSFORMERS
        self.model = None
        if self.use_transformers:
            try:
                logger.info("Lade sentence-transformers Modell...")
                self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                logger.info("✅ Modell geladen")
            except Exception as e:
                logger.warning(f"Konnte Modell nicht laden: {e}")
                self.use_transformers = False

    def compute_embedding(self, text: str) -> Optional[bytes]:
        """Berechnet ein Embedding für den gegebenen Text."""
        if self.use_transformers and self.model:
            try:
                embedding = self.model.encode(text[:1000])  # Begrenzung
                return struct.pack(f'{len(embedding)}f', *embedding)
            except Exception as e:
                logger.error(f"Embedding-Fehler: {e}")
        # Fallback: TF-IDF Vektor als bytes
        return self._tfidf_embedding(text)

    def _tfidf_embedding(self, text: str) -> bytes:
        """Einfaches TF-IDF basiertes Embedding."""
        words = self._tokenize(text)
        tf = Counter(words)
        total = len(words) if words else 1
        # Normalisierte Frequenzen als Vektor
        vocab = sorted(tf.keys())[:100]  # Top 100 Wörter
        vector = [tf[w] / total for w in vocab]
        if not vector:
            vector = [0.0]
        return struct.pack(f'{len(vector)}f', *vector)

    def compute_similarity(self, text1: str, text2: str) -> float:
        """Berechnet die Ähnlichkeit zwischen zwei Texten (0-1)."""
        if self.use_transformers and self.model:
            try:
                emb1 = self.model.encode(text1[:1000])
                emb2 = self.model.encode(text2[:1000])
                return float(self._cosine_sim(emb1.tolist(), emb2.tolist()))
            except Exception:
                pass

        # Fallback: Jaccard + Keyword Overlap
        return self._keyword_similarity(text1, text2)

    def _keyword_similarity(self, text1: str, text2: str) -> float:
        """Berechnet Ähnlichkeit basierend auf gemeinsamen Schlüsselwörtern."""
        words1 = set(self._tokenize(text1))
        words2 = set(self._tokenize(text2))

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        jaccard = len(intersection) / len(union) if union else 0

        # Gewichtete Version: seltene gemeinsame Wörter zählen mehr
        # Aber als einfache Version reicht Jaccard
        return round(jaccard, 4)

    def _tokenize(self, text: str) -> list:
        """Tokenisiert Text, entfernt Stoppwörter und normalisiert Synonyme."""
        text = text.lower()
        words = re.findall(r'\b[a-zäöüß\-]{3,}\b', text)
        result = []
        for w in words:
            if w in STOPWORDS:
                continue
            # Synonyme auf kanonischen Begriff normalisieren
            if HAS_THESAURUS:
                w = thesaurus.get_canonical(w)
            result.append(w)
        return result

    @staticmethod
    def _cosine_sim(v1: list, v2: list) -> float:
        """Kosinus-Ähnlichkeit zwischen zwei Vektoren."""
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def find_similar(self, article: dict, all_articles: list,
                     threshold: float = 0.15, max_results: int = 10) -> list:
        """
        Findet ähnliche Artikel.
        Gibt Liste von (article_id, score, shared_keywords) zurück.
        """
        text = article.get("title", "") + " " + article.get("full_text", "")
        article_words = set(self._tokenize(text))
        results = []

        for other in all_articles:
            if other.get("id") == article.get("id"):
                continue

            other_text = other.get("title", "") + " " + other.get("full_text", "")
            score = self.compute_similarity(text, other_text)

            if score >= threshold:
                other_words = set(self._tokenize(other_text))
                shared = article_words & other_words
                # Nur die signifikanten gemeinsamen Wörter
                shared_significant = [w for w in shared
                                      if len(w) > 4 and w not in STOPWORDS]
                results.append({
                    "article_id": other.get("id"),
                    "score": round(score * 100, 1),  # In Prozent
                    "shared_keywords": ", ".join(sorted(shared_significant)[:10]),
                    "title": other.get("title"),
                    "gemeinde": other.get("gemeinde"),
                    "saison": other.get("saison"),
                    "jahr": other.get("jahr"),
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:max_results]


# Singleton
_engine = None

def get_engine(use_transformers: bool = False) -> SimilarityEngine:
    global _engine
    if _engine is None:
        _engine = SimilarityEngine(use_transformers=use_transformers)
    return _engine
