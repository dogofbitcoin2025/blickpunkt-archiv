"""
BlickPUNKT Archiv – API Server
FastAPI-basiertes Backend mit allen Endpunkten.
"""

import os
import sys
import json
import csv
import io
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("blickpunkt")

# Pfade
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
PDF_DIR = DATA_DIR / "pdfs"
EXPORT_DIR = BASE_DIR / "exports"
FRONTEND_DIR = BASE_DIR / "frontend"

# Sicherstellen dass Verzeichnisse existieren
for d in [DATA_DIR, PDF_DIR, DATA_DIR / "text", DATA_DIR / "previews", EXPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Umgebungsvariablen
os.environ.setdefault("DB_PATH", str(DATA_DIR / "archive.db"))
os.environ.setdefault("PDF_DIR", str(PDF_DIR))

# Module importieren
import database as db
import crawler
import pdf_processor
import ocr
import categorizer
import similarity
import ad_detector

# App
app = FastAPI(
    title="BlickPUNKT Archiv",
    description="Redaktionelles Archiv für BlickPUNKT Magazine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Frontend static files
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# === Startup ===

@app.on_event("startup")
def startup():
    db.init_db()
    logger.info("🚀 BlickPUNKT Archiv gestartet")


# === Pydantic Models ===

class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    gemeinde: Optional[str] = None
    saison: Optional[str] = None
    jahr: Optional[int] = None
    article_type: Optional[str] = None
    content_type: Optional[str] = None
    content_type_confidence: Optional[int] = None
    status: Optional[str] = None
    categories: Optional[list] = None
    keywords: Optional[list] = None


class ScanRequest(BaseModel):
    url: Optional[str] = None


# === Frontend Routes ===

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    f = FRONTEND_DIR / "index.html"
    if f.exists():
        return f.read_text(encoding="utf-8")
    return "<h1>BlickPUNKT Archiv</h1><p>Frontend nicht gefunden. Bitte Datei frontend/index.html erstellen.</p>"

@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    f = FRONTEND_DIR / "dashboard.html"
    if f.exists():
        return f.read_text(encoding="utf-8")
    return HTMLResponse(status_code=404)

@app.get("/admin", response_class=HTMLResponse)
async def serve_admin():
    f = FRONTEND_DIR / "admin.html"
    if f.exists():
        return f.read_text(encoding="utf-8")
    return HTMLResponse(status_code=404)

@app.get("/article/{article_id}", response_class=HTMLResponse)
async def serve_article_page(article_id: int):
    f = FRONTEND_DIR / "article.html"
    if f.exists():
        return f.read_text(encoding="utf-8")
    return HTMLResponse(status_code=404)


# === API: Dashboard ===

@app.get("/api/dashboard")
async def api_dashboard():
    return db.get_dashboard_stats()


# === API: Crawler ===

@app.post("/api/scan")
async def api_scan(bg: BackgroundTasks, req: ScanRequest = None):
    """Scannt die BlickPUNKT-Webseite nach neuen Ausgaben."""
    url = req.url if req and req.url else None
    bg.add_task(_run_scan, url)
    return {"message": "Scan gestartet", "status": "running"}


def _run_scan(url=None):
    try:
        found = crawler.scan_website(url or crawler.BASE_URL)
        count = 0
        for info in found:
            issue_id = db.upsert_issue(info)
            db.log_processing(issue_id, "scan", "success", f"PDF gefunden: {info.get('pdf_url')}")
            count += 1
        logger.info(f"✅ Scan abgeschlossen: {count} Ausgaben gefunden/aktualisiert")
    except Exception as e:
        logger.error(f"❌ Scan fehlgeschlagen: {e}")


@app.get("/api/issues")
async def api_issues(
    status: Optional[str] = None,
    gemeinde: Optional[str] = None,
    jahr: Optional[int] = None
):
    return db.get_issues(status=status, gemeinde=gemeinde, jahr=jahr)


# === API: PDF-Verarbeitung ===

@app.post("/api/process/{issue_id}")
async def api_process_issue(issue_id: int, bg: BackgroundTasks):
    """Verarbeitet eine einzelne Ausgabe: Download + Textextraktion + Artikelerkennung."""
    bg.add_task(_process_issue, issue_id)
    return {"message": f"Verarbeitung von Ausgabe {issue_id} gestartet"}


@app.post("/api/process-all")
async def api_process_all(bg: BackgroundTasks):
    """Verarbeitet alle unverarbeiteten Ausgaben."""
    bg.add_task(_process_all)
    return {"message": "Verarbeitung aller Ausgaben gestartet"}


def _process_issue(issue_id: int):
    try:
        with db.get_db() as conn:
            issue = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
            if not issue:
                logger.error(f"Ausgabe {issue_id} nicht gefunden")
                return

            issue = dict(issue)

        # 1. PDF herunterladen
        if not issue.get("local_path") or not os.path.exists(issue.get("local_path", "")):
            local_path = crawler.download_pdf(issue["pdf_url"])
            if not local_path:
                db.update_issue_status(issue_id, "fehler")
                db.log_processing(issue_id, "download", "error", "Download fehlgeschlagen")
                return
            db.update_issue_status(issue_id, "heruntergeladen", local_path)
            issue["local_path"] = local_path

        # 2. Text extrahieren
        logger.info(f"📖 Extrahiere Text aus: {issue['local_path']}")
        pages = pdf_processor.extract_text_from_pdf(issue["local_path"])

        # 3. OCR falls nötig
        if pdf_processor.needs_ocr(pages):
            logger.info("  🔍 Starte OCR...")
            ocr_pages = ocr.ocr_pdf(issue["local_path"])
            if ocr_pages:
                pages = ocr_pages

        if not pages:
            db.update_issue_status(issue_id, "fehler")
            db.log_processing(issue_id, "extract", "error", "Kein Text extrahiert")
            return

        # 4. Seitenzahl speichern
        with db.get_db() as conn:
            conn.execute("UPDATE issues SET page_count = ? WHERE id = ?",
                         (len(pages), issue_id))

        # 5. Artikel erkennen
        articles = pdf_processor.detect_articles(pages, issue)

        # 5b. Inhaltstyp erkennen (Anzeige/Redaktionell/Advertorial)
        ad_detector.classify_articles(articles, issue.get("local_path"))

        # 6. Kategorisieren und speichern
        sim_engine = similarity.get_engine()
        for article_data in articles:
            # Kategorisierung
            cat_result = categorizer.categorize_article(article_data)
            article_data["categories"] = cat_result["categories"]

            # Entitäten extrahieren
            entities = categorizer.extract_entities(article_data.get("full_text", ""))
            article_data["people"] = entities["people"]
            article_data["companies"] = entities["companies"]
            article_data["clubs"] = entities["clubs"]
            article_data["locations"] = entities["locations"]

            # Issue-Referenz
            article_data["issue_id"] = issue_id

            # Speichern
            article_id = db.insert_article(article_data)

            # Embedding
            embedding = sim_engine.compute_embedding(
                article_data.get("title", "") + " " + article_data.get("full_text", "")
            )
            if embedding:
                db.update_article_embedding(article_id, embedding)

        db.update_issue_status(issue_id, "verarbeitet")
        db.log_processing(issue_id, "process", "success",
                          f"{len(articles)} Artikel erkannt")
        logger.info(f"✅ Ausgabe {issue_id} verarbeitet: {len(articles)} Artikel")

    except Exception as e:
        logger.error(f"❌ Fehler bei Ausgabe {issue_id}: {e}", exc_info=True)
        db.update_issue_status(issue_id, "fehler")
        db.log_processing(issue_id, "process", "error", str(e))


def _process_all():
    issues = db.get_issues(status="neu") + db.get_issues(status="heruntergeladen")
    logger.info(f"Verarbeite {len(issues)} Ausgaben...")
    for issue in issues:
        _process_issue(issue["id"])


# === API: Ähnlichkeiten berechnen ===

@app.post("/api/compute-similarities")
async def api_compute_similarities(bg: BackgroundTasks):
    bg.add_task(_compute_similarities)
    return {"message": "Ähnlichkeitsberechnung gestartet"}


def _compute_similarities():
    articles = db.search_articles(limit=10000)
    engine = similarity.get_engine()
    logger.info(f"Berechne Ähnlichkeiten für {len(articles)} Artikel...")
    for i, article in enumerate(articles):
        similar = engine.find_similar(article, articles)
        for s in similar:
            db.store_similar(
                article["id"], s["article_id"],
                s["score"] / 100, s.get("shared_keywords", "")
            )
        if (i + 1) % 50 == 0:
            logger.info(f"  {i+1}/{len(articles)} verarbeitet")
    logger.info("✅ Ähnlichkeitsberechnung abgeschlossen")


# === API: Artikel ===

@app.get("/api/articles")
async def api_articles(
    q: Optional[str] = None,
    kategorie: Optional[str] = None,
    gemeinde: Optional[str] = None,
    jahr: Optional[int] = None,
    saison: Optional[str] = None,
    article_type: Optional[str] = None,
    content_type: Optional[str] = None,
    keyword: Optional[str] = None,
    exclude_ads: bool = False,
    limit: int = Query(50, le=500),
    offset: int = 0
):
    try:
        return db.search_articles(
            query=q, kategorie=kategorie, gemeinde=gemeinde,
            jahr=jahr, saison=saison, article_type=article_type,
            content_type=content_type, keyword=keyword,
            exclude_ads=exclude_ads, limit=limit, offset=offset
        )
    except Exception as e:
        logger.error(f"Artikel-Suche Fehler: {e}")
        return []


@app.get("/api/articles/{article_id}")
async def api_article_detail(article_id: int):
    article = db.get_article(article_id)
    if not article:
        raise HTTPException(404, "Artikel nicht gefunden")
    return article


@app.put("/api/articles/{article_id}")
async def api_update_article(article_id: int, data: ArticleUpdate):
    update_data = data.dict(exclude_none=True)
    db.update_article(article_id, update_data)
    return {"message": "Artikel aktualisiert"}


@app.delete("/api/articles/{article_id}")
async def api_delete_article(article_id: int):
    db.delete_article(article_id)
    return {"message": "Artikel gelöscht"}


# === API: Kategorien ===

@app.get("/api/categories")
async def api_categories():
    return db.get_categories()


# === API: Export ===

@app.get("/api/export/json")
async def api_export_json():
    data = db.export_articles("json")
    return StreamingResponse(
        io.BytesIO(data.encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=blickpunkt-archiv.json"}
    )


@app.get("/api/export/csv")
async def api_export_csv():
    articles = db.search_articles(limit=100000)
    output = io.StringIO()
    if articles:
        writer = csv.DictWriter(output, fieldnames=articles[0].keys())
        writer.writeheader()
        writer.writerows(articles)
    content = output.getvalue()
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=blickpunkt-archiv.csv"}
    )


@app.get("/api/export/excel")
async def api_export_excel():
    try:
        import openpyxl
        articles = db.search_articles(limit=100000)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Artikel"
        if articles:
            headers = list(articles[0].keys())
            ws.append(headers)
            for a in articles:
                ws.append([str(a.get(h, "")) for h in headers])
        filepath = str(EXPORT_DIR / "blickpunkt-archiv.xlsx")
        wb.save(filepath)
        return FileResponse(filepath, filename="blickpunkt-archiv.xlsx")
    except ImportError:
        raise HTTPException(500, "openpyxl nicht installiert. Bitte: pip install openpyxl")


# === API: Upload ===

@app.post("/api/upload")
async def api_upload_pdf(
    file: UploadFile = File(...),
    gemeinde: str = "",
    saison: str = "",
    jahr: int = 0,
    bg: BackgroundTasks = None
):
    """Manueller PDF-Upload."""
    filename = file.filename or "upload.pdf"
    filepath = PDF_DIR / filename
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    issue_data = {
        "title": filename,
        "gemeinde": gemeinde or None,
        "saison": saison or None,
        "jahr": jahr or None,
        "pdf_url": f"local://{filename}",
        "local_path": str(filepath),
        "status": "heruntergeladen",
    }
    issue_id = db.upsert_issue(issue_data)

    if bg:
        bg.add_task(_process_issue, issue_id)

    return {"message": f"PDF hochgeladen", "issue_id": issue_id, "filename": filename}


# === API: Gemeinden ===

@app.get("/api/gemeinden")
async def api_gemeinden():
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT gemeinde FROM articles WHERE gemeinde IS NOT NULL ORDER BY gemeinde"
        ).fetchall()
        return [r["gemeinde"] for r in rows]


@app.get("/api/saisons")
async def api_saisons():
    return ["Frühling", "Sommer", "Herbst", "Winter"]


@app.get("/api/jahre")
async def api_jahre():
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT jahr FROM articles WHERE jahr IS NOT NULL ORDER BY jahr DESC"
        ).fetchall()
        return [r["jahr"] for r in rows]


# === API: Processing Logs ===

@app.get("/api/logs")
async def api_logs(limit: int = 50):
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM processing_logs ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# === Hauptstart ===

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
