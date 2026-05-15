"""
BlickPUNKT Archiv – SQLite → Supabase Sync
Lädt lokale Daten nach Supabase hoch.

Nutzung:
    python sync_to_supabase.py              # Alles hochladen
    python sync_to_supabase.py --issues     # Nur Ausgaben
    python sync_to_supabase.py --articles   # Nur Artikel
    python sync_to_supabase.py --since 7    # Nur letzte 7 Tage
"""

import os
import sys
import json
import argparse
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ supabase-py nicht installiert. Führe aus: pip install supabase")
    sys.exit(1)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "archive.db"))

BATCH_SIZE = 100


def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("❌ SUPABASE_URL oder SUPABASE_SERVICE_KEY fehlt in .env")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_sqlite():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def upsert_batch(sb: Client, table: str, rows: list, conflict_col: str = "id"):
    if not rows:
        return 0
    try:
        sb.table(table).upsert(rows, on_conflict=conflict_col).execute()
        return len(rows)
    except Exception as e:
        print(f"  ⚠️ Fehler bei {table}: {e}")
        return 0


def sync_categories(sb: Client, conn: sqlite3.Connection):
    print("📂 Kategorien synchronisieren...")
    rows = [dict(r) for r in conn.execute(
        "SELECT id, name, parent_id, sort_order FROM categories ORDER BY parent_id NULLS FIRST, sort_order"
    ).fetchall()]
    # Erst Eltern, dann Kinder
    parents = [r for r in rows if r["parent_id"] is None]
    children = [r for r in rows if r["parent_id"] is not None]
    n = upsert_batch(sb, "categories", parents)
    n += upsert_batch(sb, "categories", children)
    print(f"  ✅ {n} Kategorien hochgeladen")


def sync_issues(sb: Client, conn: sqlite3.Connection, since_days: int = None):
    print("📰 Ausgaben synchronisieren...")
    q = "SELECT id, title, gemeinde, saison, jahr, ausgabe_nr, pdf_url, local_path, download_date, page_count, status, created_at, updated_at FROM issues"
    params = []
    if since_days:
        cutoff = (datetime.now() - timedelta(days=since_days)).isoformat()
        q += " WHERE created_at >= ?"
        params.append(cutoff)

    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    total = 0
    for i in range(0, len(rows), BATCH_SIZE):
        total += upsert_batch(sb, "issues", rows[i:i+BATCH_SIZE])
    print(f"  ✅ {total} Ausgaben hochgeladen")
    return {r["id"] for r in rows}


def sync_lookup_table(sb: Client, conn: sqlite3.Connection, table: str, field: str):
    rows = [dict(r) for r in conn.execute(f"SELECT id, {field} FROM {table}").fetchall()]
    total = 0
    for i in range(0, len(rows), BATCH_SIZE):
        total += upsert_batch(sb, table, rows[i:i+BATCH_SIZE])
    return total


def sync_articles(sb: Client, conn: sqlite3.Connection, since_days: int = None):
    print("📄 Artikel synchronisieren...")

    q = """
        SELECT id, issue_id, title, summary, full_text, gemeinde, saison, jahr,
               page_start, page_end, article_type, content_type, content_type_confidence,
               ad_score, editorial_score, detected_signals, status,
               pdf_source, original_url, created_at, updated_at
        FROM articles
    """
    params = []
    if since_days:
        cutoff = (datetime.now() - timedelta(days=since_days)).isoformat()
        q += " WHERE created_at >= ?"
        params.append(cutoff)

    rows = conn.execute(q, params).fetchall()
    article_ids = set()
    total = 0

    batch = []
    for r in rows:
        row = dict(r)
        article_ids.add(row["id"])
        # detected_signals: SQLite speichert als Text, Supabase erwartet JSONB
        signals = row.get("detected_signals", "[]")
        if isinstance(signals, str):
            try:
                row["detected_signals"] = json.loads(signals)
            except Exception:
                row["detected_signals"] = []
        batch.append(row)
        if len(batch) >= BATCH_SIZE:
            total += upsert_batch(sb, "articles", batch)
            batch = []
    if batch:
        total += upsert_batch(sb, "articles", batch)

    print(f"  ✅ {total} Artikel hochgeladen")

    # Lookup-Tabellen
    print("  🔑 Keywords, Personen, Unternehmen, Vereine, Orte...")
    for table, field in [("keywords", "word"), ("people", "name"),
                          ("companies", "name"), ("clubs", "name"), ("locations", "name")]:
        n = sync_lookup_table(sb, conn, table, field)
        print(f"     {table}: {n}")

    # Verknüpfungstabellen
    print("  🔗 Verknüpfungen synchronisieren...")
    for junction in [
        ("article_categories", "article_id", "category_id"),
        ("article_keywords",   "article_id", "keyword_id"),
        ("article_people",     "article_id", "person_id"),
        ("article_companies",  "article_id", "company_id"),
        ("article_clubs",      "article_id", "club_id"),
        ("article_locations",  "article_id", "location_id"),
    ]:
        table, col1, col2 = junction
        jrows = [dict(r) for r in conn.execute(
            f"SELECT {col1}, {col2} FROM {junction[0]}"
        ).fetchall()]
        if since_days:
            jrows = [r for r in jrows if r[col1] in article_ids]
        jn = 0
        for i in range(0, len(jrows), BATCH_SIZE):
            jn += upsert_batch(sb, table, jrows[i:i+BATCH_SIZE], conflict_col=f"{col1},{col2}")
        print(f"     {table}: {jn}")

    # Ähnliche Artikel
    print("  🔁 Ähnlichkeiten...")
    sim_rows = [dict(r) for r in conn.execute(
        "SELECT article_id, similar_article_id, similarity_score, shared_keywords FROM similar_articles"
    ).fetchall()]
    sn = 0
    for i in range(0, len(sim_rows), BATCH_SIZE):
        sn += upsert_batch(sb, "similar_articles", sim_rows[i:i+BATCH_SIZE],
                           conflict_col="article_id,similar_article_id")
    print(f"     similar_articles: {sn}")


def main():
    parser = argparse.ArgumentParser(description="BlickPUNKT SQLite → Supabase Sync")
    parser.add_argument("--issues", action="store_true", help="Nur Ausgaben")
    parser.add_argument("--articles", action="store_true", help="Nur Artikel")
    parser.add_argument("--categories", action="store_true", help="Nur Kategorien")
    parser.add_argument("--since", type=int, metavar="TAGE", help="Nur Einträge der letzten N Tage")
    args = parser.parse_args()

    all_mode = not (args.issues or args.articles or args.categories)

    print(f"🚀 Starte Sync: {DB_PATH} → {SUPABASE_URL}")
    sb = get_supabase()
    conn = get_sqlite()

    try:
        if all_mode or args.categories:
            sync_categories(sb, conn)
        if all_mode or args.issues:
            sync_issues(sb, conn, args.since)
        if all_mode or args.articles:
            sync_articles(sb, conn, args.since)
    finally:
        conn.close()

    print("✅ Sync abgeschlossen.")


if __name__ == "__main__":
    main()
