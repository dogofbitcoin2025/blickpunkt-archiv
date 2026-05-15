"""
BlickPUNKT Archiv – Anzeigen-/Inhaltstyp-Erkennung
Erkennt ob ein Textblock redaktionell, Anzeige, Advertorial, Veranstaltungshinweis
oder Leseraktion ist. Nutzt Text- und Layout-Signale.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================================
#  Signal-Definitionen
# ============================================================

AD_PHRASES = [
    "wir bieten", "ihr fachbetrieb", "besuchen sie uns",
    "vereinbaren sie einen termin", "ihr partner für",
    "meisterbetrieb", "seit über", "neueröffnung",
    "das team freut sich auf sie", "freut sich auf ihren besuch",
    "wir freuen uns auf sie", "rufen sie uns an",
    "jetzt bestellen", "jetzt anfragen", "jetzt informieren",
    "kostenlose beratung", "kostenloses angebot",
    "unverbindlich", "sonderangebot", "rabatt",
    "% rabatt", "angebot gültig", "aktion gültig",
    "gutschein", "uvp", "gratis", "kostenlos",
    "kompetent und zuverlässig", "qualität aus der region",
    "alles aus einer hand", "full service",
    "montage und lieferung", "lieferung frei haus",
    "individuell nach ihren wünschen", "maßanfertigung",
    "faire preise", "top qualität", "erstklassig",
    "professionell und preiswert",
]

AD_PATTERNS = [
    # Telefonnummern
    (r'\b(?:tel\.?|telefon|fon|mobil|handy)[\s:]*[\d\s/\-\(\)]{7,}', "Telefonnummer gefunden"),
    # E-Mail
    (r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', "E-Mail-Adresse gefunden"),
    # Webseiten
    (r'(?:www\.[a-zA-Z0-9\-]+\.[a-z]{2,}|https?://[^\s]+)', "Website gefunden"),
    # Öffnungszeiten
    (r'(?:öffnungszeiten|geöffnet|mo[\.\s]*[\-–]|di[\.\s]*[\-–]|montag\s*[\-–]|dienstag)', "Öffnungszeiten gefunden"),
    # Preisangaben
    (r'(?:\d+[,\.]\d{2}\s*€|\d+\s*€|€\s*\d+|euro|EUR)', "Preisangabe gefunden"),
    # Rabatte
    (r'\d+\s*%\s*(?:rabatt|nachlass|ersparnis|günstiger|reduziert)', "Rabatthinweis gefunden"),
]

EDITORIAL_PHRASES = [
    "am vergangenen", "berichtete", "erklärte", "sagte",
    "die organisatoren", "der verein", "die gemeinde",
    "besucherinnen und besucher", "fand statt", "im rahmen von",
    "so berichtet", "wie die redaktion erfuhr",
    "teilnehmerinnen und teilnehmer", "das programm umfasste",
    "die veranstaltung", "zum wiederholten mal",
    "ehrenamtlich", "engagieren sich", "feierlich eröffnet",
    "gratulierte", "überreichte", "würdigte",
    "bei der jahreshauptversammlung", "der vorstand berichtete",
    "die mitglieder beschlossen", "der bürgermeister",
    "in seiner rede", "hielt eine ansprache",
    "rückblick auf", "ein gelungener abend",
    "zahlreiche gäste", "großer andrang",
    "die redaktion sprach mit", "im interview",
    "erzählt von", "blickt zurück",
]

ADVERTORIAL_PHRASES = [
    "firmenjubiläum", "unternehmensjubiläum",
    "jahre kompetenz", "jahre erfahrung", "jahre am markt",
    "seit der gründung", "geschäftsführer", "geschäftsführerin",
    "das unternehmen bietet", "die firma bietet",
    "das team um", "das team von",
    "servicevorstellung", "leistungsspektrum",
    "rundum-service", "full-service",
    "teamvorstellung", "mitarbeiter stellen sich vor",
    "einladung zum", "laden herzlich ein",
    "tag der offenen tür", "hausmesse",
    "betriebsbesichtigung", "firmenrundgang",
    "anzeige", "advertorial", "sponsored", "pr-beitrag",
    "in kooperation mit", "präsentiert von",
]

EVENT_PHRASES = [
    "veranstaltungshinweis", "terminankündigung",
    "einladung zur", "einladung zum",
    "wir laden ein", "herzlich eingeladen",
    "findet statt am", "am .* um .* uhr",
    "eintritt frei", "eintritt:", "kartenvorverkauf",
    "anmeldung unter", "anmeldung bis",
    "veranstaltungsort:", "ort:", "termin:",
    "datum:", "uhrzeit:", "beginn:",
    "flohmarkt", "weihnachtsmarkt", "ostermarkt",
    "sommerfest", "hafenfest", "stadtfest",
    "konzert", "theater", "lesung",
    "basar", "ausstellung",
]

READER_ACTION_PHRASES = [
    "leserfrühstück", "leseraktion", "leserreise",
    "gewinnspiel", "mitmachen und gewinnen",
    "teilnahmebedingungen", "einsendeschluss",
    "leserfoto", "leserfotos", "schicken sie uns",
    "senden sie uns", "mitmachaktion",
    "leserausflug", "leserfahrt",
    "quiz", "rätsel", "kreuzworträtsel",
    "coupon", "teilnahmecoupon",
    "ihre meinung ist gefragt", "schreiben sie uns",
    "blickpunkt leser", "blickpunkt-leser",
]


# ============================================================
#  Layout-Analyse (PyMuPDF)
# ============================================================

def analyze_layout_signals(pdf_path: str, page_num: int) -> dict:
    """
    Analysiert Layout-Signale einer PDF-Seite mit PyMuPDF.
    Gibt erkannte Layout-Signale zurück.
    """
    signals = []
    scores = {"frame_score": 0, "short_blocks": 0, "contact_density": 0}

    try:
        import fitz
    except ImportError:
        return {"signals": [], "scores": scores}

    try:
        doc = fitz.open(pdf_path)
        if page_num < 1 or page_num > len(doc):
            doc.close()
            return {"signals": [], "scores": scores}

        page = doc[page_num - 1]

        # Rahmen / Rechtecke erkennen
        drawings = page.get_drawings()
        rect_count = 0
        for d in drawings:
            if d.get("type") == "re" or (d.get("items") and any(
                item[0] == "re" for item in d.get("items", [])
            )):
                rect_count += 1

        if rect_count >= 2:
            signals.append("Text liegt in Rahmen/Boxen")
            scores["frame_score"] = min(rect_count * 15, 40)

        # Textblöcke analysieren
        blocks = page.get_text("dict")["blocks"]
        text_blocks = [b for b in blocks if b.get("type") == 0]
        short_blocks = sum(1 for b in text_blocks
                          if len("".join(s.get("text", "")
                                        for l in b.get("lines", [])
                                        for s in l.get("spans", []))) < 80)

        if len(text_blocks) > 0:
            short_ratio = short_blocks / len(text_blocks)
            if short_ratio > 0.6 and len(text_blocks) >= 4:
                signals.append("Viele kurze Textblöcke")
                scores["short_blocks"] = int(short_ratio * 30)

        doc.close()

    except Exception as e:
        logger.debug(f"Layout-Analyse Fehler: {e}")

    return {"signals": signals, "scores": scores}


# ============================================================
#  Hauptfunktion: Inhaltstyp erkennen
# ============================================================

def detect_content_type(article: dict, pdf_path: str = None) -> dict:
    """
    Bestimmt den Inhaltstyp eines Artikels.

    Returns:
        {
            "content_type": "redaktionell" | "anzeige" | "advertorial" | "veranstaltungshinweis" | "leseraktion" | "unklar",
            "content_type_confidence": 0-100,
            "ad_score": 0-100,
            "editorial_score": 0-100,
            "detected_signals": ["Signal 1", "Signal 2", ...]
        }
    """
    text = (article.get("full_text", "") or "").lower()
    title = (article.get("title", "") or "").lower()
    combined = f"{title} {text}"
    text_length = len(text)

    signals = []
    ad_score = 0
    editorial_score = 0
    advertorial_score = 0
    event_score = 0
    reader_score = 0

    # ---- 1. Textsignale für Anzeigen ----
    for phrase in AD_PHRASES:
        if phrase in combined:
            ad_score += 8
            if len(signals) < 20:
                signals.append(f"Werbeformulierung: '{phrase}'")

    for pattern, label in AD_PATTERNS:
        matches = re.findall(pattern, combined, re.IGNORECASE)
        if matches:
            ad_score += 12
            signals.append(label)

    # Kurzer Text mit vielen Kontaktdaten = sehr wahrscheinlich Anzeige
    if text_length < 300:
        ad_score += 15
        if text_length < 150:
            ad_score += 10

    # ---- 2. Redaktionelle Signale ----
    for phrase in EDITORIAL_PHRASES:
        if phrase in combined:
            editorial_score += 8
            if len(signals) < 20:
                signals.append(f"Redaktionelles Signal: '{phrase}'")

    # Langer Fließtext = eher redaktionell
    if text_length > 800:
        editorial_score += 15
    if text_length > 1500:
        editorial_score += 10
    if text_length > 3000:
        editorial_score += 10

    # Sätze zählen (journalistischer Stil hat längere Sätze)
    sentences = re.split(r'[.!?]+\s+', text)
    avg_sentence_len = (sum(len(s) for s in sentences) / max(len(sentences), 1))
    if avg_sentence_len > 60:
        editorial_score += 10

    # ---- 3. Advertorial-Signale ----
    for phrase in ADVERTORIAL_PHRASES:
        if phrase in combined:
            advertorial_score += 10
            if len(signals) < 20:
                signals.append(f"Advertorial-Signal: '{phrase}'")

    # Explizit markiert
    if "anzeige" in title or "advertorial" in title or "sponsored" in title:
        advertorial_score += 40
        signals.append("Im Titel als Anzeige/Advertorial markiert")

    # ---- 4. Veranstaltungshinweis-Signale ----
    for phrase in EVENT_PHRASES:
        if re.search(phrase, combined):
            event_score += 10
            if len(signals) < 20:
                signals.append(f"Veranstaltungssignal: '{phrase}'")

    # ---- 5. Leseraktions-Signale ----
    for phrase in READER_ACTION_PHRASES:
        if phrase in combined:
            reader_score += 12
            if len(signals) < 20:
                signals.append(f"Leseraktions-Signal: '{phrase}'")

    # ---- 6. Layout-Signale (optional, wenn PDF verfügbar) ----
    if pdf_path and article.get("page_start"):
        layout = analyze_layout_signals(pdf_path, article["page_start"])
        signals.extend(layout["signals"])
        ad_score += layout["scores"].get("frame_score", 0)
        ad_score += layout["scores"].get("short_blocks", 0)

    # ---- Entscheidung ----
    scores = {
        "redaktionell": editorial_score,
        "anzeige": ad_score,
        "advertorial": advertorial_score,
        "veranstaltungshinweis": event_score,
        "leseraktion": reader_score,
    }

    # Advertorial = hat sowohl Anzeigen- als auch redaktionelle Merkmale
    if advertorial_score > 20 or (ad_score > 30 and editorial_score > 20):
        scores["advertorial"] = max(scores["advertorial"],
                                     int((ad_score + editorial_score) * 0.6))

    max_type = max(scores, key=scores.get)
    max_score = scores[max_type]
    total_score = sum(scores.values()) or 1

    # Konfidenz berechnen
    confidence = min(int((max_score / total_score) * 100), 99) if max_score > 0 else 10

    # Bei sehr niedrigem Score: unklar
    if max_score < 15:
        content_type = "unklar"
        confidence = max(confidence, 10)
    else:
        content_type = max_type

    # Sicherheitscheck: wenn sowohl Anzeige als auch Redaktionell hoch → Advertorial
    if (content_type == "anzeige" and editorial_score > 25 and text_length > 500):
        content_type = "advertorial"
        confidence = min(confidence + 5, 95)

    # Kürze die Signalliste auf max. 10
    signals = signals[:10]

    return {
        "content_type": content_type,
        "content_type_confidence": confidence,
        "ad_score": min(ad_score, 100),
        "editorial_score": min(editorial_score, 100),
        "detected_signals": signals,
    }


def classify_articles(articles: list, pdf_path: str = None) -> list:
    """
    Klassifiziert eine Liste von Artikeln.
    Fügt jedem Artikel die Inhaltstyp-Felder hinzu.
    """
    for article in articles:
        result = detect_content_type(article, pdf_path)
        article["content_type"] = result["content_type"]
        article["content_type_confidence"] = result["content_type_confidence"]
        article["ad_score"] = result["ad_score"]
        article["editorial_score"] = result["editorial_score"]
        article["detected_signals"] = result["detected_signals"]
        # article_type bleibt für Abwärtskompatibilität
        article["article_type"] = result["content_type"]
    return articles
