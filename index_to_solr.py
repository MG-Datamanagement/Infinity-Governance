"""
index_to_solr.py
Reads all searchable entities from Postgres and indexes them into Solr.

Run manually or hook into your ingestion pipeline:
    python index_to_solr.py

Reads from .env (via python-dotenv) or environment:
    PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASS
    SOLR_URL
"""

import logging
import os
from contextlib import closing

import psycopg2
import pysolr
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

PG_DSN = (
    f"host={os.getenv('PG_HOST', 'localhost')} "
    f"port={os.getenv('PG_PORT', '5432')} "
    f"dbname={os.getenv('PG_DB', 'ig_database')} "
    f"user={os.getenv('PG_USER', 'ig_user')} "
    f"password={os.getenv('PG_PASS', 'ig_pass')}"
)
SOLR_URL = os.getenv("SOLR_URL", "http://localhost:8983/solr/app_search_core")

solr = pysolr.Solr(SOLR_URL, always_commit=True, timeout=10)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def fetchall_dict(cur) -> list[dict]:
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _ts(val) -> str | None:
    """Convert datetime → ISO-8601 string for Solr pdate field."""
    return val.strftime("%Y-%m-%dT%H:%M:%SZ") if val else None


# ─────────────────────────────────────────────────────────────────────────────
# Per-entity builders
# ─────────────────────────────────────────────────────────────────────────────

def build_catalog_docs(cur) -> list[dict]:
    cur.execute("""
        SELECT
            c.id, c.table_name, c.full_name, c.database_name, c.schema_name,
            c.description, c.row_count, c.type, c.status,
            c.source_id, c.owner_id, c.created_at, c.updated_at,
            ds.name  AS source_name,
            o.name   AS owner_name,
            -- aggregated tags
            ARRAY_REMOVE(ARRAY_AGG(DISTINCT t.id::text),   NULL) AS tag_ids,
            ARRAY_REMOVE(ARRAY_AGG(DISTINCT t.name),       NULL) AS tag_names,
            -- aggregated domains
            ARRAY_REMOVE(ARRAY_AGG(DISTINCT d.id::text),   NULL) AS domain_ids,
            ARRAY_REMOVE(ARRAY_AGG(DISTINCT d.name),       NULL) AS domain_names
        FROM catalogs c
        LEFT JOIN data_sources          ds  ON ds.id  = c.source_id
        LEFT JOIN owners                o   ON o.id   = c.owner_id
        LEFT JOIN tag_catalog_assignments tca ON tca.catalog_id = c.id
        LEFT JOIN tags                  t   ON t.id   = tca.tag_id
        LEFT JOIN domain_catalog_assignments dca ON dca.catalog_id = c.id
        LEFT JOIN domains               d   ON d.id   = dca.domain_id
        GROUP BY c.id, ds.name, o.name
    """)
    docs = []
    for r in fetchall_dict(cur):
        docs.append({
            "id":             f"catalog::{r['id']}",
            "entity_type":    "CATALOG",
            "entity_id":      str(r["id"]),
            "name":           r["table_name"],
            "display_name":   r["full_name"] or r["table_name"],
            "full_name":      r["full_name"],
            "table_name":     r["table_name"],
            "database_name":  r["database_name"],
            "schema_name":    r["schema_name"],
            "description":    r["description"],
            "row_count":      r["row_count"],
            "catalog_type":   r["type"],
            "catalog_status": r["status"],
            "source_id":      str(r["source_id"]) if r["source_id"] else None,
            "source_name":    r["source_name"],
            "owner_id":       str(r["owner_id"]) if r["owner_id"] else None,
            "owner_name":     r["owner_name"],
            "tag_ids":        r["tag_ids"] or [],
            "tag_names":      r["tag_names"] or [],
            "domain_ids":     r["domain_ids"] or [],
            "domain_names":   r["domain_names"] or [],
            "created_at":     _ts(r["created_at"]),
            "updated_at":     _ts(r["updated_at"]),
        })
    return docs


def build_column_docs(cur) -> list[dict]:
    cur.execute("""
        SELECT
            col.id, col.name, col.description, col.data_type,
            col.is_primary_key, col.is_foreign_key, col.is_nullable,
            col.catalog_id, col.created_at, col.updated_at,
            c.full_name   AS catalog_name,
            c.table_name  AS table_name,
            -- aggregated tags
            ARRAY_REMOVE(ARRAY_AGG(DISTINCT t.id::text), NULL) AS tag_ids,
            ARRAY_REMOVE(ARRAY_AGG(DISTINCT t.name),     NULL) AS tag_names
        FROM columns col
        LEFT JOIN catalogs c ON c.id = col.catalog_id
        LEFT JOIN tag_column_assignments tca ON tca.column_id = col.id
        LEFT JOIN tags t ON t.id = tca.tag_id
        GROUP BY col.id, c.full_name, c.table_name
    """)
    docs = []
    for r in fetchall_dict(cur):
        docs.append({
            "id":            f"column::{r['id']}",
            "entity_type":   "COLUMN",
            "entity_id":     str(r["id"]),
            "name":          r["name"],
            "display_name":  r["name"],
            "description":   r["description"],
            "data_type":     r["data_type"],
            "is_primary_key": r["is_primary_key"],
            "is_foreign_key": r["is_foreign_key"],
            "is_nullable":   r["is_nullable"],
            "catalog_id":    str(r["catalog_id"]) if r["catalog_id"] else None,
            "catalog_name":  r["catalog_name"] or r["table_name"],
            "tag_ids":       r["tag_ids"] or [],
            "tag_names":     r["tag_names"] or [],
            "created_at":    _ts(r["created_at"]),
            "updated_at":    _ts(r["updated_at"]),
        })
    return docs


def build_domain_docs(cur) -> list[dict]:
    cur.execute("""
        SELECT
            d.id, d.name, d.description, d.color,
            d.parent_domain_id, d.owner_id,
            d.created_at, d.updated_at,
            o.name AS owner_name,
            pd.name AS parent_name
        FROM domains d
        LEFT JOIN owners  o  ON o.id = d.owner_id
        LEFT JOIN domains pd ON pd.id = d.parent_domain_id
    """)
    docs = []
    for r in fetchall_dict(cur):
        docs.append({
            "id":           f"domain::{r['id']}",
            "entity_type":  "DOMAIN",
            "entity_id":    str(r["id"]),
            "name":         r["name"],
            "display_name": r["name"],
            "description":  r["description"],
            "domain_color": r["color"],
            "parent_id":    str(r["parent_domain_id"]) if r["parent_domain_id"] else None,
            "owner_id":     str(r["owner_id"]) if r["owner_id"] else None,
            "owner_name":   r["owner_name"],
            "created_at":   _ts(r["created_at"]),
            "updated_at":   _ts(r["updated_at"]),
        })
    return docs


def build_tag_docs(cur) -> list[dict]:
    cur.execute("""
        SELECT t.id, t.name, t.description, t.color,
               t.owner_id, t.created_at, t.updated_at,
               o.name AS owner_name
        FROM tags t
        LEFT JOIN owners o ON o.id = t.owner_id
    """)
    docs = []
    for r in fetchall_dict(cur):
        docs.append({
            "id":           f"tag::{r['id']}",
            "entity_type":  "TAG",
            "entity_id":    str(r["id"]),
            "name":         r["name"],
            "display_name": r["name"],
            "description":  r["description"],
            "tag_color":    r["color"],
            "owner_id":     str(r["owner_id"]) if r["owner_id"] else None,
            "owner_name":   r["owner_name"],
            "created_at":   _ts(r["created_at"]),
            "updated_at":   _ts(r["updated_at"]),
        })
    return docs


def build_glossary_term_docs(cur) -> list[dict]:
    cur.execute("""
        SELECT gt.id, gt.name, gt.description,
               gt.parent_group_id, gt.owner_id,
               gt.created_at, gt.updated_at,
               o.name  AS owner_name,
               gg.name AS group_name
        FROM glossary_terms gt
        LEFT JOIN owners         o  ON o.id  = gt.owner_id
        LEFT JOIN glossary_groups gg ON gg.id = gt.parent_group_id
    """)
    docs = []
    for r in fetchall_dict(cur):
        docs.append({
            "id":           f"glossary_term::{r['id']}",
            "entity_type":  "GLOSSARY_TERM",
            "entity_id":    str(r["id"]),
            "name":         r["name"],
            "display_name": r["name"],
            "description":  r["description"],
            "group_id":     str(r["parent_group_id"]) if r["parent_group_id"] else None,
            "group_name":   r["group_name"],
            "owner_id":     str(r["owner_id"]) if r["owner_id"] else None,
            "owner_name":   r["owner_name"],
            "created_at":   _ts(r["created_at"]),
            "updated_at":   _ts(r["updated_at"]),
        })
    return docs


def build_source_docs(cur) -> list[dict]:
    cur.execute("""
        SELECT ds.id, ds.name, ds.source_type, ds.description,
               ds.status, ds.owner_id, ds.created_at, ds.updated_at,
               o.name AS owner_name
        FROM data_sources ds
        LEFT JOIN owners o ON o.id = ds.owner_id
    """)
    docs = []
    for r in fetchall_dict(cur):
        docs.append({
            "id":            f"source::{r['id']}",
            "entity_type":   "SOURCE",
            "entity_id":     str(r["id"]),
            "name":          r["name"],
            "display_name":  r["name"],
            "description":   r["description"],
            "source_type":   r["source_type"],
            "source_status": r["status"],
            "owner_id":      str(r["owner_id"]) if r["owner_id"] else None,
            "owner_name":    r["owner_name"],
            "created_at":    _ts(r["created_at"]),
            "updated_at":    _ts(r["updated_at"]),
        })
    return docs


def build_owner_docs(cur) -> list[dict]:
    cur.execute("SELECT id, name, role, email, created_at, updated_at FROM owners")
    docs = []
    for r in fetchall_dict(cur):
        docs.append({
            "id":           f"owner::{r['id']}",
            "entity_type":  "OWNER",
            "entity_id":    str(r["id"]),
            "name":         r["name"],
            "display_name": r["name"],
            "owner_role":   r["role"],
            "owner_email":  r["email"],
            "created_at":   _ts(r["created_at"]),
            "updated_at":   _ts(r["updated_at"]),
        })
    return docs


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

BUILDERS = [
    ("CATALOG",       build_catalog_docs),
    ("COLUMN",        build_column_docs),
    ("DOMAIN",        build_domain_docs),
    ("TAG",           build_tag_docs),
    ("GLOSSARY_TERM", build_glossary_term_docs),
    ("SOURCE",        build_source_docs),
    ("OWNER",         build_owner_docs),
]


def reindex():
    log.info("Clearing existing Solr index …")
    solr.delete(q="*:*")

    all_docs: list[dict] = []

    with closing(psycopg2.connect(PG_DSN)) as conn:
        with conn.cursor() as cur:
            for label, builder in BUILDERS:
                docs = builder(cur)
                log.info("  %-14s → %d docs", label, len(docs))
                all_docs.extend(docs)

    if not all_docs:
        log.warning("No documents to index. Is the database populated?")
        return

    batch_size = 500
    log.info("Indexing %d total docs (batch=%d) …", len(all_docs), batch_size)
    for i in range(0, len(all_docs), batch_size):
        solr.add(all_docs[i : i + batch_size])

    log.info("✅ Indexing complete.")


if __name__ == "__main__":
    reindex()
    