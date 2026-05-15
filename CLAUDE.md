# BlickPUNKT Archiv – Umbau für Online-Betrieb

## Projektbeschreibung

Das BlickPUNKT-Archiv ist ein redaktionelles Werkzeug für das Magazin "BlickPUNKT" – ein regionales Anzeigenblatt für die Gemeinden Westoverledingen, Rhauderfehn/Ostrhauderfehn, Saterland, Barßel, Apen/Augustfehn und Stadt Leer.

Das Programm scannt die Webseite https://www.unser-blickpunkt.de/blickpunkt-ausgaben/, lädt PDF-Ausgaben herunter, extrahiert Text (mit OCR-Fallback via Tesseract), erkennt einzelne Artikel und Anzeigen, kategorisiert sie automatisch in 12 Hauptkategorien, erkennt ähnliche Artikel und macht alles durchsuchbar.

## Aktueller Stand

Das Projekt funktioniert lokal mit:
- Python / FastAPI Backend
- SQLite Datenbank
- HTML/CSS/JS Frontend
- Tesseract OCR für gescannte PDFs
- TF-IDF Ähnlichkeitssuche
- Thesaurus mit 40+ Synonymgruppen
- Anzeigen-Erkennung (ad_detector.py) mit Text- und Layout-Signalen

Die komplette lokale Version liegt in diesem Ordner.

## Aufgabe: Online-Version mit Supabase + Vercel

Baue das Projekt so um, dass es online verfügbar ist:

### Architektur

1. **Lokale Verarbeitung bleibt auf dem Mac:**
   - PDF-Download und OCR laufen weiterhin lokal
   - Nach der Verarbeitung werden die Ergebnisse nach Supabase hochgeladen
   - Erstelle dafür ein Script: `sync_to_supabase.py`

2. **Supabase (PostgreSQL Datenbank):**
   - Erstelle alle nötigen Tabellen (issues, articles, categories, article_categories, keywords, article_keywords, people, companies, clubs, locations, similar_articles, processing_logs)
   - Migriere das SQLite-Schema nach PostgreSQL
   - Nutze die Supabase Python-Bibliothek (`supabase-py`) für den Upload
   - Erstelle eine Datei `supabase_setup.sql` mit dem kompletten Schema

3. **Vercel Frontend (Next.js oder statisch):**
   - Erstelle eine neue Web-App die direkt Supabase liest
   - Suchseite mit Filtern (Kategorie, Gemeinde, Jahr, Saison, Inhaltstyp)
   - Checkbox "Anzeigen ausblenden" (Standard: aktiv)
   - Artikel-Detailseite mit Inhaltstyp-Erkennung-Panel
   - Dashboard mit Statistiken
   - Kein Admin-Bereich nötig (der bleibt lokal)
   - Responsive Design (auch Handy)
   - Nutze Supabase JS Client (`@supabase/supabase-js`)

### Datenbankstruktur (Supabase/PostgreSQL)

Die wichtigsten Tabellen:

```sql
-- issues: Alle Ausgaben
CREATE TABLE issues (
    id SERIAL PRIMARY KEY,
    title TEXT,
    gemeinde TEXT,
    saison TEXT,
    jahr INTEGER,
    ausgabe_nr TEXT,
    pdf_url TEXT,
    local_path TEXT,
    status TEXT DEFAULT 'neu',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- articles: Alle erkannten Artikel und Anzeigen
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    issue_id INTEGER REFERENCES issues(id),
    title TEXT,
    summary TEXT,
    full_text TEXT,
    gemeinde TEXT,
    saison TEXT,
    jahr INTEGER,
    page_start INTEGER,
    page_end INTEGER,
    article_type TEXT DEFAULT 'redaktionell',
    content_type TEXT DEFAULT 'unklar',
    content_type_confidence INTEGER DEFAULT 0,
    ad_score INTEGER DEFAULT 0,
    editorial_score INTEGER DEFAULT 0,
    detected_signals JSONB DEFAULT '[]',
    status TEXT DEFAULT 'automatisch',
    pdf_source TEXT,
    original_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- categories, keywords, etc. analog
```

### Projektstruktur (Ziel)

```
blickpunkt-archiv/
├── backend/                    # Bleibt lokal
│   ├── app.py                  # Lokaler FastAPI Server
│   ├── crawler.py
│   ├── pdf_processor.py
│   ├── ocr.py
│   ├── ad_detector.py
│   ├── categorizer.py
│   ├── similarity.py
│   ├── thesaurus.py
│   ├── database.py
│   ├── models.py
│   └── sync_to_supabase.py     # NEU: Upload nach Supabase
├── web/                        # NEU: Vercel Frontend
│   ├── package.json
│   ├── next.config.js          # oder vite.config.js
│   ├── vercel.json
│   ├── .env.example
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx        # Suchseite
│   │   │   ├── article/[id]/page.tsx
│   │   │   ├── dashboard/page.tsx
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── SearchBar.tsx
│   │   │   ├── FilterBar.tsx
│   │   │   ├── ArticleCard.tsx
│   │   │   ├── ArticleDetail.tsx
│   │   │   ├── ContentTypeBadge.tsx
│   │   │   ├── DetectionPanel.tsx
│   │   │   └── Dashboard.tsx
│   │   └── lib/
│   │       └── supabase.ts
│   └── public/
├── supabase_setup.sql          # NEU: Datenbank-Schema
├── data/
├── .env.example
├── requirements.txt
└── README.md
```

### Wichtige Details

- Supabase URL und Key kommen aus `.env` / `.env.local`
- Das Frontend soll den Supabase anon key nutzen (read-only)
- Row Level Security (RLS) in Supabase aktivieren: nur Lesen erlaubt
- Die Synonym-Suche (Thesaurus) soll auch im Frontend funktionieren
- Design soll modern und klar sein, passend für ein Redaktionsteam
- Farben: warme Töne, #c0392b als Akzent, heller Hintergrund

### Reihenfolge

1. Erstelle `supabase_setup.sql`
2. Erstelle `sync_to_supabase.py`
3. Erstelle das Vercel Frontend in `web/`
4. Erstelle `vercel.json`
5. Aktualisiere `README.md` mit Deployment-Anleitung
6. Aktualisiere `requirements.txt` (füge `supabase` hinzu)
7. Erstelle `.env.example` mit Supabase-Variablen

### Supabase Credentials

Die Credentials werden später in .env eingetragen:
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
```

Erstelle die Dateien mit Platzhaltern.
