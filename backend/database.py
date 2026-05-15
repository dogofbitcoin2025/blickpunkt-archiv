"""
BlickPUNKT Archiv – Datenbank-Verwaltung
SQLite-Initialisierung, Kategorie-Setup, CRUD-Operationen
"""

import sqlite3
import json
import os
from datetime import datetime
from contextlib import contextmanager
from models import SCHEMA, DEFAULT_CATEGORIES

try:
    import thesaurus
    HAS_THESAURUS = True
except ImportError:
    HAS_THESAURUS = False

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "archive.db"))


def get_db_path():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return DB_PATH


@contextmanager
def get_db():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA)

        # Migration: neue Spalten hinzufügen falls DB bereits existiert
        try:
            conn.execute("SELECT content_type FROM articles LIMIT 1")
        except Exception:
            try:
                conn.execute("ALTER TABLE articles ADD COLUMN content_type TEXT DEFAULT 'unklar'")
                conn.execute("ALTER TABLE articles ADD COLUMN content_type_confidence INTEGER DEFAULT 0")
                conn.execute("ALTER TABLE articles ADD COLUMN ad_score INTEGER DEFAULT 0")
                conn.execute("ALTER TABLE articles ADD COLUMN editorial_score INTEGER DEFAULT 0")
                conn.execute("ALTER TABLE articles ADD COLUMN detected_signals TEXT DEFAULT '[]'")
                conn.commit()
                print("✅ Datenbank migriert: content_type Spalten hinzugefügt")
            except Exception as e:
                print(f"⚠️ Migration Fehler (ignoriert): {e}")

        # Kategorien nur einfügen, wenn leer
        count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        if count == 0:
            for name, _, subcats in DEFAULT_CATEGORIES:
                conn.execute(
                    "INSERT INTO categories (name, parent_id, sort_order) VALUES (?, NULL, ?)",
                    (name, DEFAULT_CATEGORIES.index((name, _, subcats)))
                )
                parent_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                for i, sub in enumerate(subcats):
                    conn.execute(
                        "INSERT INTO categories (name, parent_id, sort_order) VALUES (?, ?, ?)",
                        (sub, parent_id, i)
                    )
            conn.commit()
    print(f"✅ Datenbank initialisiert: {get_db_path()}")


# --- Issues ---

def upsert_issue(data: dict) -> int:
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM issues WHERE pdf_url = ?", (data.get("pdf_url"),)
        ).fetchone()
        if existing:
            conn.execute("""
                UPDATE issues SET title=?, gemeinde=?, saison=?, jahr=?,
                ausgabe_nr=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (data.get("title"), data.get("gemeinde"), data.get("saison"),
                  data.get("jahr"), data.get("ausgabe_nr"), existing["id"]))
            return existing["id"]
        else:
            conn.execute("""
                INSERT INTO issues (title, gemeinde, saison, jahr, ausgabe_nr,
                pdf_url, local_path, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (data.get("title"), data.get("gemeinde"), data.get("saison"),
                  data.get("jahr"), data.get("ausgabe_nr"), data.get("pdf_url"),
                  data.get("local_path"), data.get("status", "neu")))
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def update_issue_status(issue_id: int, status: str, local_path: str = None):
    with get_db() as conn:
        if local_path:
            conn.execute(
                "UPDATE issues SET status=?, local_path=?, download_date=CURRENT_TIMESTAMP WHERE id=?",
                (status, local_path, issue_id)
            )
        else:
            conn.execute("UPDATE issues SET status=? WHERE id=?", (status, issue_id))


def get_issues(status=None, gemeinde=None, jahr=None):
    with get_db() as conn:
        q = "SELECT * FROM issues WHERE 1=1"
        params = []
        if status:
            q += " AND status = ?"
            params.append(status)
        if gemeinde:
            q += " AND gemeinde = ?"
            params.append(gemeinde)
        if jahr:
            q += " AND jahr = ?"
            params.append(jahr)
        q += " ORDER BY jahr DESC, saison DESC"
        return [dict(r) for r in conn.execute(q, params).fetchall()]


# --- Articles ---

def insert_article(data: dict) -> int:
    with get_db() as conn:
        # detected_signals als JSON speichern
        signals = data.get("detected_signals", [])
        if isinstance(signals, list):
            import json as _json
            signals = _json.dumps(signals, ensure_ascii=False)

        conn.execute("""
            INSERT INTO articles (issue_id, title, summary, full_text, gemeinde,
            saison, jahr, page_start, page_end, article_type,
            content_type, content_type_confidence, ad_score, editorial_score,
            detected_signals, status, pdf_source, original_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("issue_id"), data.get("title"), data.get("summary"),
            data.get("full_text"), data.get("gemeinde"), data.get("saison"),
            data.get("jahr"), data.get("page_start"), data.get("page_end"),
            data.get("article_type", "redaktionell"),
            data.get("content_type", "unklar"),
            data.get("content_type_confidence", 0),
            data.get("ad_score", 0),
            data.get("editorial_score", 0),
            signals,
            data.get("status", "automatisch"),
            data.get("pdf_source"), data.get("original_url")
        ))
        article_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Keywords
        for kw in data.get("keywords", []):
            kw_id = _get_or_create(conn, "keywords", "word", kw)
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO article_keywords VALUES (?, ?)",
                    (article_id, kw_id)
                )
            except Exception:
                pass

        # Categories
        for cat_name in data.get("categories", []):
            cat = conn.execute(
                "SELECT id FROM categories WHERE name = ?", (cat_name,)
            ).fetchone()
            if cat:
                conn.execute(
                    "INSERT OR IGNORE INTO article_categories VALUES (?, ?)",
                    (article_id, cat["id"])
                )

        # Entities
        for person in data.get("people", []):
            pid = _get_or_create(conn, "people", "name", person)
            conn.execute("INSERT OR IGNORE INTO article_people VALUES (?, ?)", (article_id, pid))
        for company in data.get("companies", []):
            cid = _get_or_create(conn, "companies", "name", company)
            conn.execute("INSERT OR IGNORE INTO article_companies VALUES (?, ?)", (article_id, cid))
        for club in data.get("clubs", []):
            clid = _get_or_create(conn, "clubs", "name", club)
            conn.execute("INSERT OR IGNORE INTO article_clubs VALUES (?, ?)", (article_id, clid))
        for loc in data.get("locations", []):
            lid = _get_or_create(conn, "locations", "name", loc)
            conn.execute("INSERT OR IGNORE INTO article_locations VALUES (?, ?)", (article_id, lid))

        return article_id


def _get_or_create(conn, table, field, value):
    row = conn.execute(f"SELECT id FROM {table} WHERE {field} = ?", (value,)).fetchone()
    if row:
        return row["id"]
    conn.execute(f"INSERT INTO {table} ({field}) VALUES (?)", (value,))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def update_article(article_id: int, data: dict):
    with get_db() as conn:
        fields = []
        params = []
        for key in ["title", "summary", "full_text", "gemeinde", "saison",
                     "jahr", "page_start", "page_end", "article_type",
                     "content_type", "content_type_confidence",
                     "ad_score", "editorial_score", "status"]:
            if key in data:
                fields.append(f"{key} = ?")
                params.append(data[key])
        if fields:
            fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(article_id)
            conn.execute(
                f"UPDATE articles SET {', '.join(fields)} WHERE id = ?", params
            )
        # Update categories
        if "categories" in data:
            conn.execute("DELETE FROM article_categories WHERE article_id = ?", (article_id,))
            for cat_name in data["categories"]:
                cat = conn.execute("SELECT id FROM categories WHERE name = ?", (cat_name,)).fetchone()
                if cat:
                    conn.execute("INSERT OR IGNORE INTO article_categories VALUES (?, ?)",
                                 (article_id, cat["id"]))
        # Update keywords
        if "keywords" in data:
            conn.execute("DELETE FROM article_keywords WHERE article_id = ?", (article_id,))
            for kw in data["keywords"]:
                kw_id = _get_or_create(conn, "keywords", "word", kw)
                conn.execute("INSERT OR IGNORE INTO article_keywords VALUES (?, ?)", (article_id, kw_id))


def delete_article(article_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))


def search_articles(query=None, kategorie=None, gemeinde=None, jahr=None,
                    saison=None, article_type=None, content_type=None,
                    keyword=None, exclude_ads=False,
                    limit=50, offset=0):
    try:
        with get_db() as conn:
            params = []
            select_cols = """
                a.id, a.issue_id, a.title, a.summary, a.gemeinde,
                a.saison, a.jahr, a.page_start, a.page_end,
                a.article_type, a.content_type, a.content_type_confidence,
                a.ad_score, a.editorial_score, a.detected_signals,
                a.status, a.pdf_source, a.original_url,
                a.created_at, a.updated_at,
                GROUP_CONCAT(DISTINCT c.name) as category_names,
                GROUP_CONCAT(DISTINCT k.word) as keyword_list
            """
            if query:
                # FTS search - sanitize query
                safe_query = query.replace('"', '').replace("'", "").strip()
                if not safe_query:
                    return []

                # Synonyme erweitern
                search_terms = [safe_query]
                if HAS_THESAURUS:
                    expanded = thesaurus.expand_search_query(safe_query)
                    search_terms = list(set(search_terms + expanded))

                # OR-Suche über alle Synonyme
                like_conditions = []
                for term in search_terms:
                    like_q = f"%{term}%"
                    like_conditions.append("(a.title LIKE ? OR a.summary LIKE ? OR a.full_text LIKE ?)")
                    params.extend([like_q, like_q, like_q])

                where_clause = " OR ".join(like_conditions)
                base = f"""
                    SELECT {select_cols}
                    FROM articles a
                    LEFT JOIN article_categories ac ON a.id = ac.article_id
                    LEFT JOIN categories c ON ac.category_id = c.id
                    LEFT JOIN article_keywords ak ON a.id = ak.article_id
                    LEFT JOIN keywords k ON ak.keyword_id = k.id
                    WHERE ({where_clause})
                """
            else:
                base = f"""
                    SELECT {select_cols}
                    FROM articles a
                    LEFT JOIN article_categories ac ON a.id = ac.article_id
                    LEFT JOIN categories c ON ac.category_id = c.id
                    LEFT JOIN article_keywords ak ON a.id = ak.article_id
                    LEFT JOIN keywords k ON ak.keyword_id = k.id
                    WHERE 1=1
                """

            if kategorie:
                base += " AND c.name = ?"
                params.append(kategorie)
            if gemeinde:
                base += " AND a.gemeinde = ?"
                params.append(gemeinde)
            if jahr:
                base += " AND a.jahr = ?"
                params.append(int(jahr))
            if saison:
                base += " AND a.saison = ?"
                params.append(saison)
            if article_type:
                base += " AND a.article_type = ?"
                params.append(article_type)
            if content_type:
                base += " AND a.content_type = ?"
                params.append(content_type)
            if keyword:
                base += " AND k.word LIKE ?"
                params.append(f"%{keyword}%")
            if exclude_ads:
                base += " AND a.content_type != 'anzeige'"

            base += " GROUP BY a.id ORDER BY a.jahr DESC, a.id DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(base, params).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"⚠️ search_articles Fehler: {e}")
        return []


def get_article(article_id: int):
    try:
        with get_db() as conn:
            article = conn.execute("""
                SELECT a.id, a.issue_id, a.title, a.summary, a.full_text,
                       a.gemeinde, a.saison, a.jahr, a.page_start, a.page_end,
                       a.article_type, a.content_type, a.content_type_confidence,
                       a.ad_score, a.editorial_score, a.detected_signals,
                       a.status, a.pdf_source, a.original_url,
                       a.created_at, a.updated_at,
                       i.title as issue_title, i.pdf_url
                FROM articles a
                LEFT JOIN issues i ON a.issue_id = i.id
                WHERE a.id = ?
            """, (article_id,)).fetchone()
            if not article:
                return None
            result = dict(article)
            result["categories"] = [r["name"] for r in conn.execute("""
                SELECT c.name FROM categories c
                JOIN article_categories ac ON c.id = ac.category_id
                WHERE ac.article_id = ?
            """, (article_id,)).fetchall()]
            result["keywords"] = [r["word"] for r in conn.execute("""
                SELECT k.word FROM keywords k
                JOIN article_keywords ak ON k.id = ak.keyword_id
                WHERE ak.article_id = ?
            """, (article_id,)).fetchall()]
            result["people"] = [r["name"] for r in conn.execute("""
                SELECT p.name FROM people p
                JOIN article_people ap ON p.id = ap.person_id
                WHERE ap.article_id = ?
            """, (article_id,)).fetchall()]
            result["companies"] = [r["name"] for r in conn.execute("""
                SELECT c.name FROM companies c
                JOIN article_companies ac ON c.id = ac.company_id
                WHERE ac.article_id = ?
            """, (article_id,)).fetchall()]
            result["clubs"] = [r["name"] for r in conn.execute("""
                SELECT c.name FROM clubs c
                JOIN article_clubs ac ON c.id = ac.club_id
                WHERE ac.article_id = ?
            """, (article_id,)).fetchall()]
            result["similar"] = [dict(r) for r in conn.execute("""
                SELECT sa.similar_article_id, sa.similarity_score, sa.shared_keywords,
                       a.title, a.gemeinde, a.saison, a.jahr
                FROM similar_articles sa
                JOIN articles a ON sa.similar_article_id = a.id
                WHERE sa.article_id = ?
                ORDER BY sa.similarity_score DESC LIMIT 10
            """, (article_id,)).fetchall()]
            return result
    except Exception as e:
        print(f"⚠️ get_article Fehler: {e}")
        return None


# --- Dashboard Stats ---

def get_dashboard_stats():
    with get_db() as conn:
        stats = {}
        stats["total_issues"] = conn.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
        stats["total_articles"] = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        stats["unreviewed"] = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE status = 'automatisch'"
        ).fetchone()[0]

        stats["by_category"] = [dict(r) for r in conn.execute("""
            SELECT c.name, COUNT(ac.article_id) as count
            FROM categories c
            LEFT JOIN article_categories ac ON c.id = ac.category_id
            WHERE c.parent_id IS NULL
            GROUP BY c.id ORDER BY count DESC
        """).fetchall()]

        stats["by_gemeinde"] = [dict(r) for r in conn.execute("""
            SELECT gemeinde, COUNT(*) as count FROM articles
            WHERE gemeinde IS NOT NULL
            GROUP BY gemeinde ORDER BY count DESC
        """).fetchall()]

        stats["by_year"] = [dict(r) for r in conn.execute("""
            SELECT jahr, COUNT(*) as count FROM articles
            WHERE jahr IS NOT NULL
            GROUP BY jahr ORDER BY jahr DESC
        """).fetchall()]

        stats["top_keywords"] = [dict(r) for r in conn.execute("""
            SELECT k.word, COUNT(*) as count
            FROM keywords k JOIN article_keywords ak ON k.id = ak.keyword_id
            GROUP BY k.id ORDER BY count DESC LIMIT 20
        """).fetchall()]

        stats["top_clubs"] = [dict(r) for r in conn.execute("""
            SELECT c.name, COUNT(*) as count
            FROM clubs c JOIN article_clubs ac ON c.id = ac.club_id
            GROUP BY c.id ORDER BY count DESC LIMIT 10
        """).fetchall()]

        stats["top_companies"] = [dict(r) for r in conn.execute("""
            SELECT c.name, COUNT(*) as count
            FROM companies c JOIN article_companies ac ON c.id = ac.company_id
            GROUP BY c.id ORDER BY count DESC LIMIT 10
        """).fetchall()]

        stats["recent_issues"] = [dict(r) for r in conn.execute("""
            SELECT * FROM issues ORDER BY created_at DESC LIMIT 5
        """).fetchall()]

        stats["recent_articles"] = [dict(r) for r in conn.execute("""
            SELECT id, title, gemeinde, saison, jahr, status
            FROM articles ORDER BY created_at DESC LIMIT 10
        """).fetchall()]

        return stats


# --- Categories ---

def get_categories():
    with get_db() as conn:
        cats = conn.execute("""
            SELECT c.*, p.name as parent_name
            FROM categories c
            LEFT JOIN categories p ON c.parent_id = p.id
            ORDER BY c.parent_id NULLS FIRST, c.sort_order
        """).fetchall()
        return [dict(c) for c in cats]


# --- Export ---

def export_articles(format="json"):
    articles = search_articles(limit=100000)
    if format == "json":
        return json.dumps(articles, ensure_ascii=False, indent=2, default=str)
    return articles


# --- Similar articles storage ---

def store_similar(article_id: int, similar_id: int, score: float, shared_kw: str = ""):
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO similar_articles
            (article_id, similar_article_id, similarity_score, shared_keywords)
            VALUES (?, ?, ?, ?)
        """, (article_id, similar_id, score, shared_kw))


def log_processing(issue_id: int, action: str, status: str, message: str = ""):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO processing_logs (issue_id, action, status, message)
            VALUES (?, ?, ?, ?)
        """, (issue_id, action, status, message))


def update_article_embedding(article_id: int, embedding_bytes: bytes):
    with get_db() as conn:
        conn.execute("UPDATE articles SET embedding = ? WHERE id = ?",
                     (embedding_bytes, article_id))
