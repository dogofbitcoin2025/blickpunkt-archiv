"""
BlickPUNKT Archiv – OCR
Optische Zeichenerkennung für gescannte PDFs.
Nutzt Tesseract OCR als Fallback.
"""

import os
import logging
import tempfile
import subprocess

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF for rendering pages
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def is_tesseract_available() -> bool:
    """Prüft ob Tesseract installiert ist."""
    try:
        result = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def ocr_pdf(pdf_path: str, lang: str = "deu") -> list:
    """
    Führt OCR auf einem PDF durch.
    Rendert jede Seite als Bild und lässt Tesseract den Text erkennen.
    Gibt seitenweise Text zurück.
    """
    if not is_tesseract_available():
        logger.warning("Tesseract nicht installiert – OCR übersprungen")
        return []

    if not HAS_PYMUPDF:
        logger.warning("PyMuPDF nicht verfügbar – kann PDF nicht rendern")
        return []

    pages = []
    try:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            logger.info(f"  OCR Seite {i+1}/{len(doc)}")
            # Seite als Bild rendern (300 DPI)
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat)

            # Temporäres Bild speichern
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                pix.save(tmp.name)
                tmp_path = tmp.name

            try:
                # Tesseract aufrufen
                result = subprocess.run(
                    ["tesseract", tmp_path, "stdout", "-l", lang],
                    capture_output=True, text=True, timeout=120
                )
                text = result.stdout.strip()
                pages.append({
                    "page": i + 1,
                    "text": text,
                    "blocks": [{"text": text, "font_size": 12, "is_heading": False}],
                    "char_count": len(text),
                    "ocr": True,
                })
            finally:
                os.unlink(tmp_path)

        doc.close()
    except Exception as e:
        logger.error(f"OCR Fehler bei {pdf_path}: {e}")

    return pages


def ocr_page_image(image_path: str, lang: str = "deu") -> str:
    """OCR auf einem einzelnen Bild."""
    if not is_tesseract_available():
        return ""
    try:
        result = subprocess.run(
            ["tesseract", image_path, "stdout", "-l", lang],
            capture_output=True, text=True, timeout=120
        )
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"OCR Fehler: {e}")
        return ""
