-- BlickPUNKT Archiv – Supabase/PostgreSQL Schema
-- Ausführen im Supabase SQL Editor

-- ============================================================
-- TABELLEN
-- ============================================================

CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id INTEGER REFERENCES categories(id),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS issues (
    id SERIAL PRIMARY KEY,
    title TEXT,
    gemeinde TEXT,
    saison TEXT,
    jahr INTEGER,
    ausgabe_nr TEXT,
    pdf_url TEXT UNIQUE,
    local_path TEXT,
    download_date TIMESTAMPTZ,
    page_count INTEGER,
    status TEXT DEFAULT 'neu',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS articles (
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

CREATE TABLE IF NOT EXISTS article_categories (
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id),
    PRIMARY KEY (article_id, category_id)
);

CREATE TABLE IF NOT EXISTS keywords (
    id SERIAL PRIMARY KEY,
    word TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS article_keywords (
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    keyword_id INTEGER REFERENCES keywords(id),
    PRIMARY KEY (article_id, keyword_id)
);

CREATE TABLE IF NOT EXISTS people (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS article_people (
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    person_id INTEGER REFERENCES people(id),
    PRIMARY KEY (article_id, person_id)
);

CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS article_companies (
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    company_id INTEGER REFERENCES companies(id),
    PRIMARY KEY (article_id, company_id)
);

CREATE TABLE IF NOT EXISTS clubs (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS article_clubs (
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    club_id INTEGER REFERENCES clubs(id),
    PRIMARY KEY (article_id, club_id)
);

CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS article_locations (
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    location_id INTEGER REFERENCES locations(id),
    PRIMARY KEY (article_id, location_id)
);

CREATE TABLE IF NOT EXISTS similar_articles (
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    similar_article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    similarity_score REAL,
    shared_keywords TEXT,
    PRIMARY KEY (article_id, similar_article_id)
);

CREATE TABLE IF NOT EXISTS processing_logs (
    id SERIAL PRIMARY KEY,
    issue_id INTEGER REFERENCES issues(id),
    action TEXT,
    status TEXT,
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDIZES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_articles_gemeinde ON articles(gemeinde);
CREATE INDEX IF NOT EXISTS idx_articles_jahr ON articles(jahr);
CREATE INDEX IF NOT EXISTS idx_articles_saison ON articles(saison);
CREATE INDEX IF NOT EXISTS idx_articles_article_type ON articles(article_type);
CREATE INDEX IF NOT EXISTS idx_articles_content_type ON articles(content_type);
CREATE INDEX IF NOT EXISTS idx_articles_issue_id ON articles(issue_id);
CREATE INDEX IF NOT EXISTS idx_issues_gemeinde ON issues(gemeinde);
CREATE INDEX IF NOT EXISTS idx_issues_jahr ON issues(jahr);

-- Volltext-Suche über title + summary + full_text
CREATE INDEX IF NOT EXISTS idx_articles_fts ON articles
    USING GIN (to_tsvector('german', coalesce(title,'') || ' ' || coalesce(summary,'') || ' ' || coalesce(full_text,'')));

-- ============================================================
-- VIEWS (für einfachere Abfragen im Frontend)
-- ============================================================

CREATE OR REPLACE VIEW articles_with_categories AS
SELECT
    a.*,
    array_agg(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL) AS category_names
FROM articles a
LEFT JOIN article_categories ac ON a.id = ac.article_id
LEFT JOIN categories c ON ac.category_id = c.id
GROUP BY a.id;

CREATE OR REPLACE VIEW articles_with_keywords AS
SELECT
    a.id,
    array_agg(DISTINCT k.word) FILTER (WHERE k.word IS NOT NULL) AS keyword_list
FROM articles a
LEFT JOIN article_keywords ak ON a.id = ak.article_id
LEFT JOIN keywords k ON ak.keyword_id = k.id
GROUP BY a.id;

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================

ALTER TABLE issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE keywords ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_keywords ENABLE ROW LEVEL SECURITY;
ALTER TABLE people ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_people ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE clubs ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_clubs ENABLE ROW LEVEL SECURITY;
ALTER TABLE locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE similar_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_logs ENABLE ROW LEVEL SECURITY;

-- Nur Lesen für anonyme Nutzer (anon key)
CREATE POLICY "Public read" ON issues FOR SELECT USING (true);
CREATE POLICY "Public read" ON articles FOR SELECT USING (true);
CREATE POLICY "Public read" ON categories FOR SELECT USING (true);
CREATE POLICY "Public read" ON article_categories FOR SELECT USING (true);
CREATE POLICY "Public read" ON keywords FOR SELECT USING (true);
CREATE POLICY "Public read" ON article_keywords FOR SELECT USING (true);
CREATE POLICY "Public read" ON people FOR SELECT USING (true);
CREATE POLICY "Public read" ON article_people FOR SELECT USING (true);
CREATE POLICY "Public read" ON companies FOR SELECT USING (true);
CREATE POLICY "Public read" ON article_companies FOR SELECT USING (true);
CREATE POLICY "Public read" ON clubs FOR SELECT USING (true);
CREATE POLICY "Public read" ON article_clubs FOR SELECT USING (true);
CREATE POLICY "Public read" ON locations FOR SELECT USING (true);
CREATE POLICY "Public read" ON article_locations FOR SELECT USING (true);
CREATE POLICY "Public read" ON similar_articles FOR SELECT USING (true);

-- Schreiben nur mit Service-Key (kein anon-Zugriff)
-- processing_logs: kein öffentlicher Zugriff
CREATE POLICY "No public access" ON processing_logs FOR SELECT USING (false);

-- ============================================================
-- STANDARD-KATEGORIEN
-- ============================================================

INSERT INTO categories (name, parent_id, sort_order) VALUES
('Menschen & Porträts', NULL, 0),
('Vereine & Ehrenamt', NULL, 1),
('Veranstaltungen', NULL, 2),
('Region & Heimat', NULL, 3),
('Wirtschaft & Unternehmen', NULL, 4),
('Schule, Bildung & Jugend', NULL, 5),
('Senioren & Soziales', NULL, 6),
('Freizeit, Ausflug & Genuss', NULL, 7),
('Bauen, Wohnen & Garten', NULL, 8),
('Sonderthemen', NULL, 9),
('Leseraktionen', NULL, 10),
('Anzeigen / Advertorials', NULL, 11)
ON CONFLICT DO NOTHING;
