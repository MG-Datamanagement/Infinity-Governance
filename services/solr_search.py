"""
routers/search.py
Global search endpoint backed by Apache Solr.


Environment variables:
    SOLR_URL  – defaults to http://localhost:8983/solr/app_search_core
"""

import os
from typing import Any, Optional

import pysolr
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from index_to_solr import reindex

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Solr client (shared, thread-safe)
# ─────────────────────────────────────────────────────────────────────────────

SOLR_URL = os.getenv("SOLR_URL", "http://localhost:8983/solr/app_search_core")
_solr = pysolr.Solr(SOLR_URL, always_commit=False, timeout=10)

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic response models
# ─────────────────────────────────────────────────────────────────────────────

class SearchHit(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    name: str
    display_name: str
    description: Optional[str] = None
    # CATALOG extras
    full_name: Optional[str] = None
    table_name: Optional[str] = None
    schema_name: Optional[str] = None
    database_name: Optional[str] = None
    catalog_type: Optional[str] = None
    catalog_status: Optional[str] = None
    row_count: Optional[int] = None
    source_name: Optional[str] = None
    tag_names: list[str] = []
    domain_names: list[str] = []
    # COLUMN extras
    data_type: Optional[str] = None
    is_primary_key: Optional[bool] = None
    is_foreign_key: Optional[bool] = None
    catalog_name: Optional[str] = None
    # DOMAIN extras
    domain_color: Optional[str] = None
    # TAG extras
    tag_color: Optional[str] = None
    # GLOSSARY TERM extras
    group_name: Optional[str] = None
    # SOURCE extras
    source_type: Optional[str] = None
    source_status: Optional[str] = None
    # OWNER extras
    owner_role: Optional[str] = None
    owner_email: Optional[str] = None
    # Common
    owner_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    # Highlighting
    highlight: Optional[str] = None


class FacetCount(BaseModel):
    value: str
    count: int


class SearchResponse(BaseModel):
    query: str
    total: int
    page: int
    page_size: int
    results: list[SearchHit]
    facets: dict[str, list[FacetCount]] = {}


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────

router = APIRouter()

# Entity types accepted as filter values
VALID_ENTITY_TYPES = {
    "CATALOG", "COLUMN", "DOMAIN", "TAG",
    "GLOSSARY_TERM", "SOURCE", "OWNER",
}


def _first(val: Any) -> Any:
    """Solr returns multi-value fields as lists even when single-valued."""
    if isinstance(val, list):
        return val[0] if val else None
    return val


def _list(val: Any) -> list:
    if val is None:
        return []
    return val if isinstance(val, list) else [val]


@router.get("/search", response_model=SearchResponse, summary="Global search across all entities")
async def global_search(
    q: str = Query(..., min_length=1, description="Search query string"),
    entity_types: Optional[list[str]] = Query(
        None,
        alias="entity_type",
        description="Filter by entity type(s): CATALOG, COLUMN, DOMAIN, TAG, GLOSSARY_TERM, SOURCE, OWNER",
    ),
    source_type: Optional[str] = Query(None, description="Filter by data source type (e.g. postgres)"),
    catalog_status: Optional[str] = Query(None, description="Filter catalog status: healthy | warning | risk"),
    catalog_type: Optional[str] = Query(None, description="Filter catalog type: table | view"),
    data_type: Optional[str] = Query(None, description="Filter column data type"),
    owner_id: Optional[str] = Query(None, description="Filter by owner UUID"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    sort: str = Query("score desc", description="Sort order, e.g. 'score desc' or 'name asc'"),
):
    """
    Search across **all** indexed entities in one call.

    Supports:
    - Full-text search on name, description, tags, domains, data types, etc.
    - Wildcard suffix (user typed partial query → appended `*`)
    - Faceted counts by `entity_type`, `source_type`, `catalog_status`
    - Highlighted matching snippets
    - Pagination
    - Multiple optional filters
    """

    # ── Build Solr query ──────────────────────────────────────────────────────
    # Escape special chars, then support wildcard if query doesn't already have one
    safe_q = q.replace('"', '\\"')

    terms = safe_q.split()
    wildcard_clause = " AND ".join(f"{t}*" for t in terms)
    phrase_clause = f'"{safe_q}"~2^5'            # proximity phrase, boosted
    solr_q = f"search_text:({wildcard_clause}) OR search_text:({phrase_clause})"

    # ── Filters ───────────────────────────────────────────────────────────────
    fq: list[str] = []

    if entity_types:
        invalid = set(entity_types) - VALID_ENTITY_TYPES
        if invalid:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid entity_type(s): {sorted(invalid)}. "
                       f"Valid values: {sorted(VALID_ENTITY_TYPES)}",
            )
        type_filter = " OR ".join(f'entity_type:"{et}"' for et in entity_types)
        fq.append(f"({type_filter})")

    if source_type:
        fq.append(f'source_type:"{source_type}"')
    if catalog_status:
        fq.append(f'catalog_status:"{catalog_status}"')
    if catalog_type:
        fq.append(f'catalog_type:"{catalog_type}"')
    if data_type:
        fq.append(f'data_type:"{data_type}"')
    if owner_id:
        fq.append(f'owner_id:"{owner_id}"')

    # ── Pagination ────────────────────────────────────────────────────────────
    start = (page - 1) * page_size

    # ── Solr params ───────────────────────────────────────────────────────────
    solr_params: dict[str, Any] = {
        "fl": "*,score",
        "rows": page_size,
        "start": start,
        "sort": sort,
        # Highlighting
        "hl": "true",
        "hl.fl": "name description full_name",
        "hl.snippets": 1,
        "hl.fragsize": 120,
        "hl.simple.pre": "<em>",
        "hl.simple.post": "</em>",
        # Facets
        "facet": "true",
        "facet.field": ["entity_type", "source_type", "catalog_status", "catalog_type", "data_type"],
        "facet.mincount": 1,
        "facet.limit": 20,
    }
    if fq:
        solr_params["fq"] = fq

    # ── Execute ───────────────────────────────────────────────────────────────
    try:
        results = _solr.search(solr_q, **solr_params)
    except pysolr.SolrError as exc:
        raise HTTPException(status_code=502, detail=f"Solr error: {exc}") from exc

    # ── Parse highlighting ────────────────────────────────────────────────────
    highlighting: dict[str, str] = {}
    raw_hl = getattr(results, "highlighting", {}) or {}
    for doc_id, snippets in raw_hl.items():
        for field_snippets in snippets.values():
            if field_snippets:
                highlighting[doc_id] = field_snippets[0]
                break

    # ── Build hits ────────────────────────────────────────────────────────────
    hits: list[SearchHit] = []
    for doc in results.docs:
        doc_id = _first(doc.get("id", ""))
        hits.append(
            SearchHit(
                id=doc_id,
                entity_type=_first(doc.get("entity_type", "")),
                entity_id=_first(doc.get("entity_id", "")),
                name=_first(doc.get("name", "")),
                display_name=_first(doc.get("display_name", "")),
                description=_first(doc.get("description")),
                full_name=_first(doc.get("full_name")),
                table_name=_first(doc.get("table_name")),
                schema_name=_first(doc.get("schema_name")),
                database_name=_first(doc.get("database_name")),
                catalog_type=_first(doc.get("catalog_type")),
                catalog_status=_first(doc.get("catalog_status")),
                row_count=_first(doc.get("row_count")),
                source_name=_first(doc.get("source_name")),
                tag_names=_list(doc.get("tag_names")),
                domain_names=_list(doc.get("domain_names")),
                data_type=_first(doc.get("data_type")),
                is_primary_key=_first(doc.get("is_primary_key")),
                is_foreign_key=_first(doc.get("is_foreign_key")),
                catalog_name=_first(doc.get("catalog_name")),
                domain_color=_first(doc.get("domain_color")),
                tag_color=_first(doc.get("tag_color")),
                group_name=_first(doc.get("group_name")),
                source_type=_first(doc.get("source_type")),
                source_status=_first(doc.get("source_status")),
                owner_role=_first(doc.get("owner_role")),
                owner_email=_first(doc.get("owner_email")),
                owner_name=_first(doc.get("owner_name")),
                created_at=_first(doc.get("created_at")),
                updated_at=_first(doc.get("updated_at")),
                highlight=highlighting.get(doc_id),
            )
        )

    # ── Parse facets ─────────────────────────────────────────────────────────
    facets: dict[str, list[FacetCount]] = {}
    raw_facets = getattr(results, "facets", {}) or {}
    facet_fields = raw_facets.get("facet_fields", {})
    for field, counts in facet_fields.items():
        # Solr returns [value, count, value, count, …]
        parsed: list[FacetCount] = []
        for i in range(0, len(counts) - 1, 2):
            val, cnt = counts[i], counts[i + 1]
            if val and cnt:
                parsed.append(FacetCount(value=val, count=cnt))
        if parsed:
            facets[field] = parsed

    return SearchResponse(
        query=q,
        total=results.hits,
        page=page,
        page_size=page_size,
        results=hits,
        facets=facets,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Reindex trigger endpoint (call after ingestion jobs complete)
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/search/reindex",
    summary="Trigger a full Solr reindex",
    description="Re-reads all Postgres tables and pushes them to Solr. "
                "Safe to call after any ingestion job.",
)
async def trigger_reindex():
    """
    Runs the indexer in-process (fine for moderate data volumes).
    For large datasets, offload to a background task or Celery worker.
    """
    try:
        # Import here to avoid circular deps if indexer lives elsewhere
        from index_to_solr import reindex  # adjust import path as needed
        reindex()
        return {"status": "ok", "message": "Reindex complete."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ─────────────────────────────────────────────────────────────────────────────
# Suggestions / autocomplete endpoint
# ─────────────────────────────────────────────────────────────────────────────

class SuggestionItem(BaseModel):
    entity_id: str
    entity_type: str    # CATALOG | DOMAIN | TAG | GLOSSARY_TERM | SOURCE | OWNER
    name: str


# Entity types shown in suggestions (COLUMN excluded — too noisy for autocomplete)
SUGGEST_ENTITY_TYPES = {"CATALOG", "DOMAIN", "TAG", "GLOSSARY_TERM", "SOURCE", "OWNER"}


@router.get(
    "/search/suggest",
    response_model=list[SuggestionItem],
    summary="Autocomplete suggestions — catalogs, domains, tags, glossary terms, sources, owners",
    tags=["Search"],
)
async def search_suggest(
    q: str = Query(..., min_length=1, description="query string"),
    entity_types: Optional[list[str]] = Query(
        None,
        alias="entity_type",
        description="Restrict to specific types. Defaults to: CATALOG, DOMAIN, TAG, GLOSSARY_TERM, SOURCE, OWNER",
    ),
    limit: int = Query(10, ge=1, le=50, description="Max results to return"),
):
    """
    Prefix search for autocomplete / search-as-you-type.



    Returns:
    ```json
    [
      { "entity_id": "uuid", "entity_type": "CATALOG",       "name": "sales_customer" },
      { "entity_id": "uuid", "entity_type": "TAG",           "name": "customer_pii" },
      { "entity_id": "uuid", "entity_type": "GLOSSARY_TERM", "name": "customer_lifetime_value" }
    ]
    ```
    """
    safe_q = q.strip().replace('"', '\\"')
    terms = safe_q.split()


    name_clauses = " AND ".join(f"name:{t}* OR display_name:{t}*" for t in terms)
    solr_q = f"({name_clauses})"

    # ── Entity type filter ────────────────────────────────────────────────────
    # Use caller-supplied types if provided, otherwise default to SUGGEST_ENTITY_TYPES
    if entity_types:
        invalid = set(entity_types) - VALID_ENTITY_TYPES
        if invalid:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid entity_type(s): {sorted(invalid)}. "
                       f"Valid: {sorted(VALID_ENTITY_TYPES)}",
            )
        active_types = set(entity_types)
    else:
        active_types = SUGGEST_ENTITY_TYPES   # COLUMN always excluded unless explicitly asked

    type_filter = " OR ".join(f'entity_type:"{et}"' for et in sorted(active_types))
    fq = [f"({type_filter})"]

    params: dict[str, Any] = {
        "fl": "entity_id,entity_type,display_name",
        "rows": limit,
        "sort": "score desc",
        "fq": fq,
    }

    try:
        results = _solr.search(solr_q, **params)
    except pysolr.SolrError as exc:
        raise HTTPException(status_code=502, detail=f"Solr error: {exc}") from exc

    return [
        SuggestionItem(
            entity_id=_first(doc.get("entity_id", "")),
            entity_type=_first(doc.get("entity_type", "")),
            name=_first(doc.get("display_name", "")),
        )
        for doc in results.docs
    ]






class SourceSearchHit(BaseModel):
    source_id: str
    name: str
    source_type: Optional[str] = None    # postgres | mysql | mongodb | …
    source_status: Optional[str] = None  # running | failed | success
    owner_name: Optional[str] = None
    description: Optional[str] = None


class SourceSearchResponse(BaseModel):
    query: str
    total: int
    results: list[SourceSearchHit]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _first(val: Any) -> Any:
    if isinstance(val, list):
        return val[0] if val else None
    return val


@router.get(
    "/sources-list/search",
    response_model=SourceSearchResponse,
    summary="Search across data sources by name, type, or description",
    tags=["Search"],
)
async def search_sources(
    q: str = Query(..., min_length=1, description="Search query — e.g. 'mongo', 'prod', 'sales'"),
    source_type: Optional[str] = Query(
        None,
        description="Filter by connector type: postgres | mysql | mongodb | bigquery | snowflake …"
    ),
    status: Optional[str] = Query(
        None,
        description="Filter by ingestion status: running | failed | success"
    ),
    limit: int = Query(20, ge=1, le=100, description="Max number of results"),
):
    """
    Live search across your data sources list.

    Matches against **name** and **description** fields only — no noise from
    unrelated entities.

    Always scoped to `entity_type = SOURCE`, so catalogs, columns, tags, etc.
    are never returned.

    **Examples:**
    - `?q=mongo` → sources whose name contains "mongo"
    - `?q=prod&source_type=postgres` → postgres sources with "prod" in the name
    - `?q=ig&status=failed` → failed sources matching "ig"
    """
    safe_q = q.strip().replace('"', '\\"')
    terms = safe_q.split()

    # Match name/display_name/description with wildcard per term
    clauses = " OR ".join(
        f"name:{t}* OR display_name:{t}* OR description:{t}*"
        for t in terms
    )
    solr_q = f"({clauses})"

    # Always locked to SOURCE only
    fq = ['entity_type:"SOURCE"']

    if source_type:
        fq.append(f'source_type:"{source_type}"')
    if status:
        fq.append(f'source_status:"{status}"')

    params: dict[str, Any] = {
        "fl": "entity_id,display_name,source_type,source_status,owner_name,description",
        "rows": limit,
        "sort": "score desc",
        "fq": fq,
    }

    try:
        results = _solr.search(solr_q, **params)
    except pysolr.SolrError as exc:
        raise HTTPException(status_code=502, detail=f"Solr error: {exc}") from exc

    hits = [
        SourceSearchHit(
            source_id=_first(doc.get("entity_id", "")),
            name=_first(doc.get("display_name", "")),
            source_type=_first(doc.get("source_type")),
            source_status=_first(doc.get("source_status")),
            owner_name=_first(doc.get("owner_name")),
            description=_first(doc.get("description")),
        )
        for doc in results.docs
    ]

    return SourceSearchResponse(query=q, total=results.hits, results=hits)




class CatalogSearchHit(BaseModel):
    catalog_id: str
    full_name: Optional[str] = None
    table_name: str
    type: Optional[str] = None          # table | view
    status: Optional[str] = None        # healthy | warning | risk
    row_count: Optional[int] = None
    schema_name: Optional[str] = None
    database_name: Optional[str] = None
    tag_names: list[str] = []
    domain_names: list[str] = []


class CatalogSearchResponse(BaseModel):
    query: str
    source_id: str
    total: int
    filters: dict
    results: list[CatalogSearchHit]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _first(val: Any) -> Any:
    if isinstance(val, list):
        return val[0] if val else None
    return val

def _list(val: Any) -> list:
    if val is None:
        return []
    return val if isinstance(val, list) else [val]


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/sources/{source_id}/stats/search",
    response_model=CatalogSearchResponse,
    summary="Search tables/views within a specific data source",
    tags=["Search"],
)
async def search_source_catalogs(
    source_id: str,
    q: str = Query(..., min_length=1, description="Search query — e.g. 'sales', 'customer', 'order'"),
    type: Optional[str] = Query(
        None,
        description="Filter by type: table | view"
    ),
    status: Optional[str] = Query(
        None,
        description="Filter by status: healthy | warning | risk"
    ),
    limit: int = Query(20, ge=1, le=100, description="Max number of results"),
):
    """
    Search tables and views ingested from a specific data source.

    Scoped entirely to the given `source_id` — never returns catalogs
    from other sources.

    Matches against **table name**, **full name** (db.schema.table),
    and **description**.

    **Examples:**
    - `?q=sales` → all tables with "sales" in the name
    - `?q=customer&type=table` → tables only, matching "customer"
    - `?q=order&status=healthy` → healthy tables matching "order"
    - `?q=sale&type=view&status=warning` → combine all filters
    """
    safe_q = q.strip().replace('"', '\\"')
    terms = safe_q.split()

    # Match on table name, full name, description
    clauses = " OR ".join(
        f"table_name:{t}* OR full_name:{t}* OR name:{t}* OR description:{t}*"
        for t in terms
    )
    solr_q = f"({clauses})"

    # Always locked to CATALOG + this specific source
    fq = [
        'entity_type:"CATALOG"',
        f'source_id:"{source_id}"',
    ]

    if type and type.lower() != "all":
        fq.append(f'catalog_type:"{type.lower()}"')

    if status:
        fq.append(f'catalog_status:"{status.lower()}"')

    params: dict[str, Any] = {
        "fl": (
            "entity_id,table_name,full_name,schema_name,database_name,"
            "catalog_type,catalog_status,row_count,tag_names,domain_names"
        ),
        "rows": limit,
        "sort": "score desc",
        "fq": fq,
    }

    try:
        results = _solr.search(solr_q, **params)
    except pysolr.SolrError as exc:
        raise HTTPException(status_code=502, detail=f"Solr error: {exc}") from exc

    hits = [
        CatalogSearchHit(
            catalog_id=_first(doc.get("entity_id", "")),
            full_name=_first(doc.get("full_name")),
            table_name=_first(doc.get("table_name", "")),
            type=_first(doc.get("catalog_type")),
            status=_first(doc.get("catalog_status")),
            row_count=_first(doc.get("row_count")),
            schema_name=_first(doc.get("schema_name")),
            database_name=_first(doc.get("database_name")),
            tag_names=_list(doc.get("tag_names")),
            domain_names=_list(doc.get("domain_names")),
        )
        for doc in results.docs
    ]

    return CatalogSearchResponse(
        query=q,
        source_id=source_id,
        total=results.hits,
        filters={"type": type, "status": status},
        results=hits,
    )
