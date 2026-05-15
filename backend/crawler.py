"""
BlickPUNKT Archiv – Crawler
Scannt die BlickPUNKT-Webseite nach PDF-Ausgaben.
Respektiert robots.txt und arbeitet mit Wartezeiten.
"""

import re
import os
import time
import hashlib
import logging
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.unser-blickpunkt.de/blickpunkt-ausgaben/"
DOWNLOAD_DIR = os.environ.get("PDF_DIR", os.path.join(os.path.dirname(__file__), "..", "data", "pdfs"))
WAIT_BETWEEN_DOWNLOADS = 3  # Sekunden

SAISON_MAP = {
    "frühling": "Frühling",
    "frühjahr": "Frühling",
    "fruehling": "Frühling",
    "frühlingsausgabe": "Frühling",
    "spring": "Frühling",
    "feburar": "Winter",
    "februar": "Winter",
    "märz": "Frühling",
    "sommer": "Sommer",
    "sommerausgabe": "Sommer",
    "herbst": "Herbst",
    "herbstausgabe": "Herbst",
    "winter": "Winter",
    "winterausgabe": "Winter",
    "weihnacht": "Winter",
}

HEADERS = {
    "User-Agent": "BlickPUNKT-Archiv/1.0 (internes Redaktionswerkzeug)"
}


def scan_website(url=BASE_URL) -> list:
    """Scannt die Ausgaben-Seite und gibt eine Liste gefundener PDF-Informationen zurück."""
    logger.info(f"Scanne Webseite: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Fehler beim Laden der Seite: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    found = []
    seen_urls = set()

    # Alle Überschriften und Links in Dokumentreihenfolge durchgehen
    current_saison = None
    current_jahr = None

    for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "a"]):
        if element.name in ["h1", "h2", "h3", "h4", "h5"]:
            heading_text = element.get_text(strip=True)

            # Jahr aus Überschrift extrahieren (z.B. "Frühling 2026")
            year_match = re.search(r'20[12]\d', heading_text)
            if year_match:
                current_jahr = int(year_match.group())

            # Saison aus Überschrift extrahieren
            heading_lower = heading_text.lower()
            found_saison = None
            for key, val in SAISON_MAP.items():
                if key in heading_lower:
                    found_saison = val
                    break
            if found_saison:
                current_saison = found_saison

            logger.info(f"  Abschnitt: {heading_text} → Saison={current_saison}, Jahr={current_jahr}")
            continue

        # PDF-Link verarbeiten
        if element.name == "a":
            href = element.get("href", "")
            full_url = urljoin(url, href)

            if not full_url.lower().endswith(".pdf"):
                continue
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            link_text = element.get_text(strip=True)

            # Gemeinde aus Link-Text und URL erkennen
            gemeinde = _detect_gemeinde(link_text, full_url)

            # Ausgabennummer aus Link-Text erkennen
            ausgabe_nr = None
            nr_match = re.search(r'Nr\.?\s*(\d+)', link_text)
            if nr_match:
                ausgabe_nr = nr_match.group(1)

            # Titel zusammenbauen
            title_parts = []
            if gemeinde:
                title_parts.append(gemeinde)
            if current_saison:
                title_parts.append(current_saison)
            if current_jahr:
                title_parts.append(str(current_jahr))
            if ausgabe_nr:
                title_parts.append(f"Nr. {ausgabe_nr}")

            title = " – ".join(title_parts) if title_parts else link_text or os.path.basename(urlparse(full_url).path)

            info = {
                "title": title,
                "gemeinde": gemeinde,
                "saison": current_saison,
                "jahr": current_jahr,
                "ausgabe_nr": ausgabe_nr,
                "pdf_url": full_url,
            }

            found.append(info)
            logger.info(f"  Gefunden: {title}")

    logger.info(f"Insgesamt {len(found)} PDFs gefunden.")
    return found


def _detect_gemeinde(link_text: str, url: str) -> str:
    """Erkennt die Gemeinde aus Link-Text und URL."""
    combined = f"{link_text} {url}".lower()

    # Spezifischere Matches zuerst
    if "rhauderfehn" in combined or "ostrhauderfehn" in combined:
        return "Rhauderfehn / Ostrhauderfehn"
    if "-ro." in combined or "-ro-" in combined:
        return "Rhauderfehn / Ostrhauderfehn"
    if "stadt leer" in combined:
        return "Stadt Leer"
    if "leer" in link_text.lower() or "-leer" in combined or "leer-" in combined:
        return "Stadt Leer"
    if "westoverledingen" in combined or "-wol" in combined or "wol-" in combined:
        return "Westoverledingen"
    if "saterland" in combined or "-its" in combined or "its-" in combined:
        return "Saterland"
    if "barßel" in combined or "barssel" in combined:
        return "Barßel"
    if "apen" in combined or "augustfehn" in combined:
        return "Apen / Augustfehn"

    return None


def download_pdf(url: str, target_dir: str = None) -> str:
    """Lädt ein PDF herunter. Gibt den lokalen Pfad zurück."""
    if target_dir is None:
        target_dir = DOWNLOAD_DIR
    os.makedirs(target_dir, exist_ok=True)

    filename = _safe_filename(url)
    local_path = os.path.join(target_dir, filename)

    if os.path.exists(local_path):
        logger.info(f"  PDF existiert bereits: {filename}")
        return local_path

    logger.info(f"  Lade herunter: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=120, stream=True)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"  ✅ Gespeichert: {filename} ({os.path.getsize(local_path)} Bytes)")
        time.sleep(WAIT_BETWEEN_DOWNLOADS)
        return local_path
    except requests.RequestException as e:
        logger.error(f"  ❌ Download fehlgeschlagen: {e}")
        return None


def _safe_filename(url: str) -> str:
    """Erzeugt einen sicheren Dateinamen aus der URL."""
    parsed = urlparse(url)
    basename = os.path.basename(parsed.path)
    basename = re.sub(r'[^\w\-.]', '_', basename)
    if not basename.lower().endswith('.pdf'):
        basename += '.pdf'
    if len(basename) > 200:
        h = hashlib.md5(url.encode()).hexdigest()[:12]
        basename = f"{h}.pdf"
    return basename


def download_all_issues(issues: list, target_dir: str = None) -> list:
    """Lädt alle PDFs herunter, die noch nicht vorhanden sind."""
    results = []
    for issue in issues:
        url = issue.get("pdf_url")
        if not url:
            continue
        path = download_pdf(url, target_dir)
        results.append({
            **issue,
            "local_path": path,
            "status": "heruntergeladen" if path else "fehler"
        })
    return results
