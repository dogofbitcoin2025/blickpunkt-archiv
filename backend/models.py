"""
BlickPUNKT Archiv – Datenbankmodelle
Definiert alle SQLite-Tabellen für Ausgaben, Artikel, Kategorien etc.
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    gemeinde TEXT,
    saison TEXT,
    jahr INTEGER,
    ausgabe_nr TEXT,
    pdf_url TEXT UNIQUE,
    local_path TEXT,
    download_date TIMESTAMP,
    page_count INTEGER,
    status TEXT DEFAULT 'neu',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER,
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
    detected_signals TEXT DEFAULT '[]',
    status TEXT DEFAULT 'automatisch',
    pdf_source TEXT,
    original_url TEXT,
    embedding BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (issue_id) REFERENCES issues(id)
);

CREATE TABLE IF NOT EXISTS article_categories (
    article_id INTEGER,
    category_id INTEGER,
    PRIMARY KEY (article_id, category_id),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS article_keywords (
    article_id INTEGER,
    keyword_id INTEGER,
    PRIMARY KEY (article_id, keyword_id),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (keyword_id) REFERENCES keywords(id)
);

CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS article_people (
    article_id INTEGER,
    person_id INTEGER,
    PRIMARY KEY (article_id, person_id),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES people(id)
);

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS article_companies (
    article_id INTEGER,
    company_id INTEGER,
    PRIMARY KEY (article_id, company_id),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS clubs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS article_clubs (
    article_id INTEGER,
    club_id INTEGER,
    PRIMARY KEY (article_id, club_id),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (club_id) REFERENCES clubs(id)
);

CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS article_locations (
    article_id INTEGER,
    location_id INTEGER,
    PRIMARY KEY (article_id, location_id),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id)
);

CREATE TABLE IF NOT EXISTS similar_articles (
    article_id INTEGER,
    similar_article_id INTEGER,
    similarity_score REAL,
    shared_keywords TEXT,
    PRIMARY KEY (article_id, similar_article_id),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (similar_article_id) REFERENCES articles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS processing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER,
    action TEXT,
    status TEXT,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (issue_id) REFERENCES issues(id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
    title, summary, full_text, content='articles', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
    INSERT INTO articles_fts(rowid, title, summary, full_text)
    VALUES (new.id, new.title, new.summary, new.full_text);
END;

CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
    INSERT INTO articles_fts(articles_fts, rowid, title, summary, full_text)
    VALUES('delete', old.id, old.title, old.summary, old.full_text);
END;

CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
    INSERT INTO articles_fts(articles_fts, rowid, title, summary, full_text)
    VALUES('delete', old.id, old.title, old.summary, old.full_text);
    INSERT INTO articles_fts(rowid, title, summary, full_text)
    VALUES (new.id, new.title, new.summary, new.full_text);
END;
"""

DEFAULT_CATEGORIES = [
    ("Menschen & Porträts", None, [
        "Vereinsmenschen", "Unternehmerporträts", "Ehrenamt",
        "Jubilare", "Familiengeschichten", "Leserporträts"
    ]),
    ("Vereine & Ehrenamt", None, [
        "Sportvereine", "Schützenvereine", "Kulturvereine",
        "Feuerwehr", "DRK / soziale Gruppen", "Fördervereine"
    ]),
    ("Veranstaltungen", None, [
        "Feste", "Märkte", "Konzerte", "Sportevents",
        "Jubiläen", "Saisonveranstaltungen",
        "Hafenfest / Stadtfest / Weihnachtsmarkt"
    ]),
    ("Region & Heimat", None, [
        "Dorfgeschichten", "Historisches", "plattdeutsche Themen",
        "regionale Besonderheiten", "Fehn, Moor, Marsch", "Ortsentwicklung"
    ]),
    ("Wirtschaft & Unternehmen", None, [
        "Firmenporträts", "Neueröffnungen", "Handwerk",
        "Gastronomie", "Dienstleistungen", "Landwirtschaft", "Tourismus"
    ]),
    ("Schule, Bildung & Jugend", None, [
        "Schulen", "Kitas", "Jugendgruppen",
        "Schülerprojekte", "Ausbildung", "Ferienaktionen"
    ]),
    ("Senioren & Soziales", None, [
        "Seniorenheime", "Pflege", "Begegnungsangebote",
        "soziale Projekte", "Gesundheit", "Generationenthemen"
    ]),
    ("Freizeit, Ausflug & Genuss", None, [
        "Restaurants", "Cafés", "Ausflugstipps",
        "Fahrradstrecken", "Natur", "regionale Rezepte"
    ]),
    ("Bauen, Wohnen & Garten", None, [
        "Immobilien", "Handwerk", "Renovierung",
        "Garten", "Energie", "Wärmepumpen", "regionale Baubetriebe"
    ]),
    ("Sonderthemen", None, [
        "Hochzeit", "Weihnachten", "Ostern", "Frühling",
        "Sommer", "Herbst", "Winter", "Gesundheit",
        "Mobilität", "Fußball-WM / EM", "lokale Sonderaktionen"
    ]),
    ("Leseraktionen", None, [
        "Leserfrühstück", "Gewinnspiele", "Leserfotos",
        "Ausflüge", "Mitmachaktionen"
    ]),
    ("Anzeigen / Advertorials", None, [
        "Anzeige", "Unternehmensanzeige", "bezahlter Beitrag",
        "Veranstaltungshinweis", "Produktwerbung"
    ]),
]
