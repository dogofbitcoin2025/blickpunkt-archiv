# 📰 BlickPUNKT Archiv

**Redaktionelles Magazin-Archiv** – Automatische Erfassung, Analyse, Kategorisierung und Durchsuchung aller BlickPUNKT-Ausgaben.

---

## Was macht dieses Programm?

Das BlickPUNKT Archiv scannt automatisch die Webseite mit den Magazin-Ausgaben, lädt die PDFs herunter, extrahiert den Text, erkennt einzelne Artikel, kategorisiert sie und macht alles durchsuchbar.

**Für die Redaktion bedeutet das:**
- Sofort sehen, welche Themen schon behandelt wurden
- Nach Gemeinde, Kategorie, Jahr und Saison filtern
- Ähnliche Artikel finden (Duplikat-Erkennung)
- Themen-Lücken entdecken für zukünftige Ausgaben
- CSV/Excel/JSON-Export für weitere Auswertungen

---

## Systemvoraussetzungen

- **Python 3.10+**
- **Tesseract OCR** (für gescannte PDFs)
- **macOS, Linux oder Windows**

---

## Installation (Mac)

### 1. Tesseract OCR installieren

```bash
brew install tesseract tesseract-lang
```

Prüfen, ob es funktioniert:
```bash
tesseract --version
```

### 2. Projekt einrichten

```bash
cd blickpunkt-archiv

# Virtuelle Umgebung erstellen
python3 -m venv venv
source venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Konfiguration anlegen
cp .env.example .env
```

### 3. Starten

```bash
cd backend
python app.py
```

Das Programm startet auf **http://127.0.0.1:8000**

---

## Bedienung

### Weboberfläche

| Seite | URL | Beschreibung |
|-------|-----|--------------|
| **Suche** | `/` | Volltextsuche mit Filtern |
| **Dashboard** | `/dashboard` | Statistiken und Diagramme |
| **Admin** | `/admin` | Ausgaben scannen, verarbeiten, bearbeiten |
| **Artikel** | `/article/{id}` | Artikeldetail mit ähnlichen Artikeln |

### Typischer Workflow

1. **Admin → „Webseite scannen"** klicken
   - Scannt die BlickPUNKT-Seite und findet alle PDF-Links
2. **Admin → „Alle verarbeiten"** klicken
   - Lädt PDFs herunter und extrahiert Artikel
3. **Admin → „Ähnlichkeiten berechnen"** klicken
   - Berechnet Ähnlichkeitswerte zwischen Artikeln
4. **Suche** nutzen, um Artikel zu finden
5. **Dashboard** für den Überblick ansehen

### Manueller Upload

Im Admin-Bereich können PDFs auch manuell hochgeladen werden. Wähle Gemeinde, Saison und Jahr aus, dann ziehe die PDF in den Upload-Bereich.

---

## Projektstruktur

```
blickpunkt-archiv/
├── backend/
│   ├── app.py              # FastAPI-Server & API-Endpunkte
│   ├── crawler.py           # Webseiten-Scanner
│   ├── pdf_processor.py     # PDF-Textextraktion & Artikelerkennung
│   ├── ocr.py               # Tesseract OCR Fallback
│   ├── categorizer.py       # Automatische Kategorisierung
│   ├── similarity.py        # Ähnlichkeitserkennung (TF-IDF)
│   ├── database.py          # SQLite-Datenbank & CRUD
│   └── models.py            # Datenmodelle & Kategorien
├── frontend/
│   ├── index.html           # Suchseite
│   ├── dashboard.html       # Dashboard
│   ├── admin.html           # Verwaltung
│   ├── article.html         # Artikeldetail
│   ├── styles.css           # Stylesheet
│   └── app.js               # Frontend-Logik
├── data/
│   ├── pdfs/                # Heruntergeladene PDFs
│   ├── text/                # Extrahierter Text
│   └── previews/            # Seitenvorschauen
├── exports/                 # CSV/Excel/JSON-Exporte
├── .env.example             # Konfigurationsvorlage
├── requirements.txt         # Python-Abhängigkeiten
└── README.md                # Diese Datei
```

---

## API-Endpunkte

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| `POST` | `/api/scan` | Webseite scannen |
| `GET` | `/api/issues` | Alle Ausgaben auflisten |
| `POST` | `/api/process/{id}` | Einzelne Ausgabe verarbeiten |
| `POST` | `/api/process-all` | Alle neuen Ausgaben verarbeiten |
| `GET` | `/api/articles` | Artikel suchen (mit Filtern) |
| `GET` | `/api/articles/{id}` | Artikeldetail |
| `PUT` | `/api/articles/{id}` | Artikel bearbeiten |
| `DELETE` | `/api/articles/{id}` | Artikel löschen |
| `POST` | `/api/upload` | PDF manuell hochladen |
| `POST` | `/api/compute-similarities` | Ähnlichkeiten berechnen |
| `GET` | `/api/dashboard` | Dashboard-Daten |
| `GET` | `/api/export/csv` | CSV-Export |
| `GET` | `/api/export/json` | JSON-Export |
| `GET` | `/api/export/excel` | Excel-Export |
| `GET` | `/api/categories` | Kategorien auflisten |
| `GET` | `/api/gemeinden` | Gemeinden auflisten |
| `GET` | `/api/logs` | Verarbeitungs-Logs |

### Suchparameter für `/api/articles`

- `q` – Volltextsuche
- `kategorie` – Nach Kategorie filtern
- `gemeinde` – Nach Gemeinde filtern
- `jahr` – Nach Jahr filtern
- `saison` – Nach Saison filtern
- `article_type` – `redaktionell` oder `anzeige`
- `keyword` – Nach Schlagwort filtern
- `limit` / `offset` – Paginierung

---

## Kategorien

Das System verwendet 12 Hauptkategorien mit Unterkategorien:

1. Menschen & Porträts
2. Vereine & Ehrenamt
3. Veranstaltungen
4. Region & Heimat
5. Wirtschaft & Unternehmen
6. Schule, Bildung & Jugend
7. Senioren & Soziales
8. Freizeit, Ausflug & Genuss
9. Bauen, Wohnen & Garten
10. Sonderthemen
11. Leseraktionen
12. Anzeigen / Advertorials

Kategorien können im Admin-Bereich angepasst werden.

---

## KI-Funktionen (optional)

Wenn ein Anthropic API-Key in der `.env` hinterlegt wird, kann die KI-Kategorisierung aktiviert werden. Diese erzeugt:

- Bessere Überschriften
- Zusammenfassungen
- Präzisere Kategorien
- Schlagwort-Vorschläge
- Hinweise auf ähnliche bereits vorhandene Themen

**Ohne API-Key** funktioniert alles mit regelbasierter Kategorisierung.

---

## Datenexport

Über die Suchseite oder die API können alle Artikel exportiert werden:

- **CSV** – Für Excel-Tabellen
- **JSON** – Für technische Weiterverarbeitung
- **Excel** – Formatierte .xlsx-Datei

---

## Fehlerbehandlung

- PDFs, die nicht geladen werden können, werden als „Fehler" markiert
- OCR wird automatisch als Fallback eingesetzt
- Bereits heruntergeladene PDFs werden nicht erneut geladen
- Wartezeiten zwischen Downloads respektieren den Server
- Alle Verarbeitungsschritte werden in den Logs dokumentiert

---

## Tipps

- **Erster Scan dauert**: Beim ersten Mal werden viele PDFs heruntergeladen. Das kann je nach Verbindung einige Minuten dauern.
- **OCR braucht Zeit**: Gescannte PDFs brauchen länger für die Textextraktion.
- **Artikel nachbearbeiten**: Die automatische Erkennung ist nicht perfekt. Prüfe und korrigiere Artikel im Admin-Bereich.
- **Regelmäßig scannen**: Starte den Scan regelmäßig, um neue Ausgaben zu erfassen.

---

---

## Online-Deployment (Supabase + Vercel)

### Architektur

```
Mac (lokal)          Supabase (Cloud DB)        Vercel (Frontend)
───────────          ───────────────────        ─────────────────
PDF-Download    →    PostgreSQL                 Next.js App
OCR / Analyse   →    (issues, articles,         Suche + Filter
sync_to_supabase.py  kategorien…)           →   Artikel-Detail
                                                Dashboard
```

### 1. Supabase einrichten

1. Projekt anlegen auf [supabase.com](https://supabase.com)
2. Im **SQL Editor** die Datei `supabase_setup.sql` ausführen
3. Unter **Settings → API** die Credentials kopieren

### 2. `.env` befüllen

```bash
cp .env.example .env
# Dann SUPABASE_URL, SUPABASE_KEY und SUPABASE_SERVICE_KEY eintragen
```

### 3. Daten nach Supabase hochladen

```bash
source venv/bin/activate
pip install supabase  # falls noch nicht installiert

cd backend

# Erstmalig alles hochladen
python sync_to_supabase.py

# Nur die letzten 7 Tage (für regelmäßige Sync-Läufe)
python sync_to_supabase.py --since 7

# Nur Ausgaben oder Artikel
python sync_to_supabase.py --issues
python sync_to_supabase.py --articles
```

### 4. Vercel-Frontend deployen

```bash
cd web
cp .env.example .env.local
# NEXT_PUBLIC_SUPABASE_URL und NEXT_PUBLIC_SUPABASE_ANON_KEY eintragen

npm install
npm run dev   # Lokaler Test auf http://localhost:3000
```

**Deployment auf Vercel:**

```bash
npm i -g vercel
vercel  # Im Projekt-Root ausführen
```

Oder per GitHub-Integration: Repository verbinden, Vercel erkennt `vercel.json` automatisch.

**Umgebungsvariablen in Vercel setzen:**
- `NEXT_PUBLIC_SUPABASE_URL` → Supabase Project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` → Supabase Anon Key (public, read-only)

### Sicherheit

- Row Level Security (RLS) ist in `supabase_setup.sql` aktiviert
- Anonyme Nutzer können nur lesen
- Schreiben funktioniert nur mit dem Service-Role Key (lokal, nie im Frontend)
- Den Service-Key niemals ins Repository committen

---

## Lizenz

Nur für interne redaktionelle Nutzung. Keine automatische Veröffentlichung von Inhalten.
