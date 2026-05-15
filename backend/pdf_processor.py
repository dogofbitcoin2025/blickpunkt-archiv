"""
BlickPUNKT Archiv - PDF-Verarbeitung
Extrahiert Text aus PDFs, erkennt Artikel UND Anzeigen als eigenstaendige Eintraege.
Auch kleine Anzeigenbloecke (z.B. Hamel Elektro, Physiopraxis) werden erfasst.
"""

import os
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Versuche verschiedene PDF-Bibliotheken
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


# Signalwoerter die auf Anzeigen hindeuten
AD_SIGNALS = [
    "tel.", "telefon", "fon:", "mobil:", "fax:",
    "www.", "http", ".de", ".com",
    "gmbh", "e.k.", "ohg", "gbr", "ug ",
    "oeffnungszeiten", "geoeffnet",
    "ihr partner", "ihr fachbetrieb", "meisterbetrieb",
    "besuchen sie", "rufen sie", "vereinbaren sie",
    "wir bieten", "wir freuen uns",
    "info@", "kontakt@", "mail@",
]


def extract_text_from_pdf(pdf_path: str) -> list:
    """
    Extrahiert Text seitenweise aus einem PDF.
    Gibt eine Liste von dicts zurueck: [{"page": 1, "text": "...", "blocks": [...]}]
    """
    if not os.path.exists(pdf_path):
        logger.error(f"PDF nicht gefunden: {pdf_path}")
        return []

    if HAS_PYMUPDF:
        return _extract_with_pymupdf(pdf_path)
    elif HAS_PDFPLUMBER:
        return _extract_with_pdfplumber(pdf_path)
    else:
        logger.error("Weder PyMuPDF noch pdfplumber installiert!")
        return []


def _extract_with_pymupdf(pdf_path: str) -> list:
    """Extraktion mit PyMuPDF (fitz). Erfasst auch Layoutdaten fuer Anzeigenerkennung."""
    pages = []
    try:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            text = page.get_text("text")
            blocks_raw = page.get_text("dict")["blocks"]

            # Zeichnungen/Rahmen zaehlen fuer Layouterkennung
            drawings = []
            try:
                drawings = page.get_drawings()
            except Exception:
                pass
            rect_count = sum(1 for d in drawings
                           if d.get("type") == "re" or
                           (d.get("items") and any(
                               item[0] == "re" for item in d.get("items", []))))

            text_blocks = []
            for block in blocks_raw:
                if block.get("type") == 0:  # Text-Block
                    block_text = ""
                    max_font_size = 0
                    min_font_size = 999
                    font_sizes = []
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            span_text = span.get("text", "")
                            block_text += span_text
                            size = span.get("size", 0)
                            if span_text.strip():
                                font_sizes.append(size)
                                max_font_size = max(max_font_size, size)
                                min_font_size = min(min_font_size, size)
                        block_text += "\n"

                    clean_text = block_text.strip()
                    if not clean_text:
                        continue

                    bbox = block.get("bbox", [0, 0, 0, 0])
                    block_width = bbox[2] - bbox[0] if len(bbox) >= 4 else 0
                    block_height = bbox[3] - bbox[1] if len(bbox) >= 4 else 0

                    text_blocks.append({
                        "text": clean_text,
                        "font_size": max_font_size,
                        "min_font_size": min_font_size if min_font_size < 999 else 0,
                        "bbox": bbox,
                        "width": block_width,
                        "height": block_height,
                        "is_heading": max_font_size > 14,
                        "line_count": clean_text.count("\n") + 1,
                        "char_count": len(clean_text),
                    })

            pages.append({
                "page": i + 1,
                "text": text,
                "blocks": text_blocks,
                "char_count": len(text),
                "rect_count": rect_count,
            })
        doc.close()
    except Exception as e:
        logger.error(f"PyMuPDF Fehler bei {pdf_path}: {e}")
    return pages


def _extract_with_pdfplumber(pdf_path: str) -> list:
    """Extraktion mit pdfplumber."""
    pages = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                pages.append({
                    "page": i + 1,
                    "text": text,
                    "blocks": [{"text": text, "font_size": 12, "is_heading": False,
                                "char_count": len(text), "line_count": text.count("\n") + 1}],
                    "char_count": len(text),
                    "rect_count": 0,
                })
    except Exception as e:
        logger.error(f"pdfplumber Fehler bei {pdf_path}: {e}")
    return pages


def needs_ocr(pages: list) -> bool:
    """Prueft ob OCR noetig ist (wenig Text pro Seite)."""
    if not pages:
        return True
    avg_chars = sum(p["char_count"] for p in pages) / len(pages)
    return avg_chars < 100


def detect_articles(pages: list, issue_info: dict = None) -> list:
    """
    Erkennt einzelne Artikel UND Anzeigen aus den extrahierten Seiten.
    Auch kleine Anzeigenbloecke werden als eigenstaendige Eintraege erfasst.
    """
    articles = []

    for page_data in pages:
        page_num = page_data["page"]
        blocks = page_data.get("blocks", [])

        if not blocks:
            blocks = [{"text": page_data["text"], "font_size": 12,
                       "is_heading": False, "char_count": len(page_data["text"]),
                       "line_count": 1}]

        # Schritt 1: Bloecke in Segmente gruppieren
        # Ein Segment ist eine zusammenhaengende Gruppe von Bloecken
        # die zu einem Artikel oder einer Anzeige gehoeren
        segments = _segment_blocks(blocks, page_num)

        for segment in segments:
            if not segment.get("full_text", "").strip():
                continue

            # Minimale Laenge: 20 Zeichen (auch kurze Anzeigen erfassen)
            if len(segment.get("full_text", "").strip()) < 20:
                continue

            articles.append(segment)

    # Anzeigen erkennen (vorlaeufig, wird spaeter von ad_detector ueberschrieben)
    for article in articles:
        article["article_type"] = _detect_article_type(article)

    # Metadaten von Issue uebernehmen
    if issue_info:
        for article in articles:
            article["gemeinde"] = issue_info.get("gemeinde")
            article["saison"] = issue_info.get("saison")
            article["jahr"] = issue_info.get("jahr")
            article["pdf_source"] = issue_info.get("local_path")
            article["original_url"] = issue_info.get("pdf_url")

    # Zusammenfassungen und Keywords erzeugen
    for article in articles:
        article["summary"] = _generate_summary(article["full_text"])
        article["keywords"] = _extract_keywords(article["full_text"])

    logger.info(f"  {len(articles)} Eintraege erkannt (Artikel + Anzeigen)")
    return articles


def _segment_blocks(blocks: list, page_num: int) -> list:
    """
    Gruppiert Textbloecke in logische Segmente (Artikel oder Anzeigen).
    Nutzt Ueberschriften, raeumliche Naehe und Anzeigen-Signale.
    """
    segments = []
    current_segment = None

    for block in blocks:
        text = block.get("text", "").strip()
        if not text or len(text) < 5:
            continue

        is_heading = block.get("is_heading", False)
        font_size = block.get("font_size", 12)
        char_count = block.get("char_count", len(text))
        has_ad_signals = _has_ad_signals(text)

        # Entscheidung: Neues Segment starten?
        start_new = False

        # 1. Ueberschrift = neues Segment
        if is_heading or (font_size > 13 and len(text) < 200 and len(text) > 5):
            start_new = True

        # 2. Block mit Anzeigen-Signalen und der vorherige war redaktionell
        elif has_ad_signals and current_segment and not _has_ad_signals(current_segment.get("full_text", "")):
            start_new = True

        # 3. Block ohne Anzeigen-Signale und der vorherige war eine Anzeige
        elif not has_ad_signals and current_segment and _has_ad_signals(current_segment.get("full_text", "")):
            # Nur wenn der vorherige Block kurz war (typisch fuer Anzeigen)
            if len(current_segment.get("full_text", "")) < 500:
                start_new = True

        # 4. Raeumlicher Abstand (Y-Position) - wenn bbox vorhanden
        elif current_segment and block.get("bbox") and current_segment.get("_last_bbox"):
            last_bottom = current_segment["_last_bbox"][3]
            current_top = block["bbox"][1]
            gap = current_top - last_bottom
            # Grosser vertikaler Abstand = neues Segment
            if gap > 40:
                start_new = True

        # 5. Erster Block auf der Seite
        elif current_segment is None:
            start_new = True

        if start_new:
            # Vorheriges Segment speichern
            if current_segment and current_segment["full_text"].strip():
                current_segment["full_text"] = current_segment["full_text"].strip()
                segments.append(current_segment)

            # Neues Segment
            title = _clean_title(text) if (is_heading or font_size > 13) else _extract_title_from_text(text)
            current_segment = {
                "title": title,
                "full_text": "" if (is_heading or font_size > 13) else text + "\n",
                "page_start": page_num,
                "page_end": page_num,
                "article_type": "redaktionell",
                "_last_bbox": block.get("bbox"),
            }
        elif current_segment:
            current_segment["full_text"] += text + "\n"
            current_segment["page_end"] = page_num
            current_segment["_last_bbox"] = block.get("bbox")
        else:
            # Fallback: neues Segment ohne Ueberschrift
            title = _extract_title_from_text(text)
            current_segment = {
                "title": title,
                "full_text": text + "\n",
                "page_start": page_num,
                "page_end": page_num,
                "article_type": "redaktionell",
                "_last_bbox": block.get("bbox"),
            }

    # Letztes Segment speichern
    if current_segment and current_segment["full_text"].strip():
        current_segment["full_text"] = current_segment["full_text"].strip()
        segments.append(current_segment)

    # Interne Felder entfernen
    for seg in segments:
        seg.pop("_last_bbox", None)

    return segments


def _has_ad_signals(text: str) -> bool:
    """Prueft ob ein Textblock Anzeigen-Signale enthaelt."""
    text_lower = text.lower()
    count = 0
    for signal in AD_SIGNALS:
        if signal in text_lower:
            count += 1
    return count >= 2


def _clean_title(text: str) -> str:
    """Bereinigt einen Titel."""
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    if len(text) > 150:
        text = text[:147] + "..."
    return text


def _extract_title_from_text(text: str) -> str:
    """Extrahiert einen Titel aus den ersten Zeilen."""
    lines = text.strip().split('\n')
    for line in lines[:3]:
        line = line.strip()
        if 5 < len(line) < 150:
            return _clean_title(line)
    return _clean_title(lines[0][:100]) if lines else "Ohne Titel"


def _detect_article_type(article: dict) -> str:
    """Vorlaeufige Erkennung ob ein Artikel eine Anzeige ist."""
    text_lower = (article.get("full_text", "") + " " + article.get("title", "")).lower()
    ad_count = sum(1 for signal in AD_SIGNALS if signal in text_lower)
    text_len = len(article.get("full_text", ""))

    if ad_count >= 3 or (ad_count >= 2 and text_len < 500):
        return "anzeige"
    if ad_count >= 1 and text_len < 200:
        return "anzeige"
    return "redaktionell"


def _generate_summary(text: str, max_len: int = 200) -> str:
    """Erzeugt eine einfache Zusammenfassung aus dem Text."""
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = re.split(r'[.!?]\s+', text)
    summary = ""
    for sent in sentences[:3]:
        if len(summary) + len(sent) < max_len:
            summary += sent + ". "
        else:
            break
    return summary.strip() or text[:max_len]


def _extract_keywords(text: str, max_keywords: int = 10) -> list:
    """Extrahiert einfache Schlagwoerter aus dem Text."""
    text_lower = text.lower()
    stopwords = {
        "der", "die", "das", "und", "in", "von", "zu", "den", "fuer",
        "mit", "auf", "ist", "im", "dem", "ein", "eine", "es", "sich",
        "des", "als", "an", "auch", "aus", "bei", "hat", "nach", "wird",
        "wie", "noch", "war", "sind", "ueber", "so", "zum", "aber",
        "sie", "er", "nicht", "oder", "was", "ich", "haben", "dass",
        "wir", "werden", "seine", "einer", "kann", "mehr", "alle",
        "diese", "schon", "wurde", "zur", "vor", "bis", "nur", "sehr",
        "wenn", "dann", "hier", "man", "sein", "vom", "durch", "uns",
        "gibt", "seit", "neue", "neuen", "viele", "ganz", "hatte",
        "doch", "wieder", "denn", "etwa", "dabei", "sagt", "teil",
        "diesem", "dieser", "anderen", "recht", "fuer", "ueber",
    }

    words = re.findall(r'\b[a-zA-Z\u00e4\u00f6\u00fc\u00df]{4,}\b', text_lower)
    word_count = {}
    for w in words:
        if w not in stopwords:
            word_count[w] = word_count.get(w, 0) + 1

    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    keywords = [w.capitalize() for w, c in sorted_words[:max_keywords] if c >= 1]

    # Bekannte Entitaeten hinzufuegen
    known_entities = [
        "Feuerwehr", "Schuetzenverein", "Sportverein", "Heimatverein",
        "DRK", "Kirche", "Schule", "Kindergarten", "Gemeinde",
        "Buergermeister", "Rathaus", "Weihnachtsmarkt", "Hafenfest",
        "GmbH", "Elektro", "Sanitaer", "Heizung", "Solar",
        "Immobilien", "Physiotherapie", "Praxis",
    ]
    for entity in known_entities:
        if entity.lower() in text_lower and entity not in keywords:
            keywords.append(entity)

    return keywords[:max_keywords]


def get_page_count(pdf_path: str) -> int:
    """Gibt die Seitenzahl eines PDFs zurueck."""
    if HAS_PYMUPDF:
        try:
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count
        except Exception:
            pass
    if HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return len(pdf.pages)
        except Exception:
            pass
    return 0
