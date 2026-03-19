"""
Dashboard Service

Provides endpoints for:
- Root and health checks
- Catalog browsing and search
- Statistics and overview metrics
- API logs and activity tracking
"""

import json
import re
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from models.search_schemas import SearchRequest, StatisticsResponse
from models.catalog_schemas import CatalogInfo
import psycopg2
from datetime import datetime, timezone


import os
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("PG_HOST", "postgres_ig"),
    "port": int(os.getenv("PG_PORT", "5432")),
    "dbname": os.getenv("PG_NAME", "ig_database"),
    "user": os.getenv("PG_USER", "ig_user"),
    "password": os.getenv("PG_PASSWORD", "ig_pass"),
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def execute_query(query, params=None):
    conn = get_connection()

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params or {})
            return cur.fetchall()
    finally:
        conn.close()
        
router = APIRouter()


# ============================================================================
# ROOT & HEALTH
# ============================================================================

@router.get("/")
async def root():
    """Root endpoint"""
    from ingestion.core import SOURCE_TEMPLATES
    return {
        "service": "Unified Metadata Ingestion API",
        "version": "1.0.0",
        "status": "running",
        "supported_sources": list(SOURCE_TEMPLATES.keys()),
        "database": "configured"
    }


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    from app import db
    try:
        await db.fetch_val("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


# ============================================================================
# CATALOGS
# ============================================================================

@router.get("/api/v1/catalogs/list", response_model=List[CatalogInfo], tags=["Catalogs"])
async def list_catalogs(
    source_id: Optional[str] = None,
    database: Optional[str] = None,
    schema: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """List all catalogs/datasets"""
    from app import db, logger
    try:
        query = """
            SELECT 
                c.id, c.database_name, c.schema_name, c.table_name, 
                c.full_name, c.description, c.created_at, c.updated_at,
                c.row_count, c.owner_id,
                ds.name as source_name, ds.source_type,
                COUNT(DISTINCT col.id) as column_count
            FROM catalogs c
            JOIN data_sources ds ON c.source_id = ds.id
            LEFT JOIN columns col ON c.id = col.catalog_id
            WHERE 1=1
        """
        params = []
        
        if source_id:
            query += f" AND c.source_id = ${len(params) + 1}"
            params.append(source_id)
        
        if database:
            query += f" AND c.database_name = ${len(params) + 1}"
            params.append(database)
        
        if schema:
            query += f" AND c.schema_name = ${len(params) + 1}"
            params.append(schema)
        
        if search:
            query += f" AND (c.table_name ILIKE ${len(params) + 1} OR c.full_name ILIKE ${len(params) + 1})"
            params.append(f"%{search}%")
        
        query += " GROUP BY c.id, c.row_count, c.owner_id, ds.name, ds.source_type ORDER BY c.table_name"
        query += f" LIMIT ${len(params) + 1}"
        params.append(limit)
        
        results = await db.fetch_all(query, *params)
        
        catalogs = []
        for row in results:
            catalog = dict(row)
            # Convert UUID to string
            catalog['id'] = str(catalog['id']) if catalog['id'] else None
            catalog['owner_id'] = str(catalog['owner_id']) if catalog.get('owner_id') else None
            # Get columns for this catalog
            columns = await db.fetch_all("""
                SELECT name, data_type, ordinal_position, is_nullable, 
                       is_primary_key, is_foreign_key, description
                FROM columns
                WHERE catalog_id = $1
                ORDER BY ordinal_position
            """, catalog['id'])
            catalog['columns'] = [dict(col) for col in columns]
            catalogs.append(catalog)
        
        return catalogs
    
    except Exception as e:
        logger.error(f"Error listing catalogs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/catalog/detail/{catalog_id}", response_model=CatalogInfo, tags=["Catalogs"])
async def get_catalog(catalog_id: str):
    """Get catalog by ID with full details"""
    from app import db, logger
    try:
        # Get catalog
        catalog = await db.fetch_one("""
            SELECT 
                c.*, ds.name as source_name, ds.source_type
            FROM catalogs c
            JOIN data_sources ds ON c.source_id = ds.id
            WHERE c.id = $1
        """, catalog_id)
        
        if not catalog:
            raise HTTPException(status_code=404, detail="Catalog not found")
        
        # Get columns
        columns = await db.fetch_all("""
            SELECT name, data_type, ordinal_position, is_nullable,
                   is_primary_key, is_foreign_key, description
            FROM columns 
            WHERE catalog_id = $1 
            ORDER BY ordinal_position
        """, catalog_id)
        
        # Get custom properties
        properties = await db.fetch_all("""
            SELECT key, value FROM custom_properties 
            WHERE catalog_id = $1
        """, catalog_id)
        
        result = dict(catalog)
        result['id'] = str(result['id']) if result['id'] else None
        result['owner_id'] = str(result['owner_id']) if result.get('owner_id') else None
        result['columns'] = [dict(col) for col in columns]
        result['properties'] = {row['key']: row['value'] for row in properties}
        result['column_count'] = len(columns)
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting catalog: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _parse_data_type(raw: str) -> str:
    """Extract clean type name from SchemaFieldDataTypeClass string."""
    if not raw:
        return "unknown"
    
    match = re.search(r"type': (\w+)\(", raw)
    if match:
        type_name = match.group(1)
        type_map = {
            "StringTypeClass":  "string",
            "BytesTypeClass":   "bytes",
            "TimeTypeClass":    "timestamp",
            "NumberTypeClass":  "number",
            "IntTypeClass":     "integer",
            "FloatTypeClass":   "float",
            "BooleanTypeClass": "boolean",
            "ArrayTypeClass":   "array",
            "MapTypeClass":     "map",
            "NullTypeClass":    "null",
            "RecordTypeClass":  "record",
            "EnumTypeClass":    "enum",
            "UnionTypeClass":   "union",
            "DateTypeClass":    "date",
        }
        return type_map.get(type_name, type_name)
    return raw


@router.get("/api/v1/catalogs/minimal-detail/{catalog_id}", tags=["Catalogs"])
async def get_catalog_detail(catalog_id: str):
    """
    Get detailed information about a specific catalog/dataset including:
    - basic metadata
    - source
    - owner
    - assigned domains (multiple possible)
    - assigned tags
    - columns (with per-column tags and glossary terms)
    """
    from app import db, logger
    try:
        # Main catalog info
        catalog = await db.fetch_one("""
            SELECT
                c.id,
                c.table_name,
                c.full_name,
                c.database_name,
                c.schema_name,
                c.description,
                c.row_count,
                c.metadata        AS properties,
                c.created_at,
                c.updated_at,
                ds.name           AS source_name,
                ds.source_type    AS source_type,
                o.id              AS owner_id,
                o.name            AS owner_name,
                o.email           AS owner_email,
                o.role            AS owner_role
            FROM catalogs c
            LEFT JOIN data_sources ds ON c.source_id = ds.id
            LEFT JOIN owners o        ON c.owner_id  = o.id
            WHERE c.id = $1
        """, catalog_id)

        if not catalog:
            raise HTTPException(status_code=404, detail="Catalog not found")

        # Columns
        columns = await db.fetch_all("""
            SELECT 
                id,
                name, 
                data_type, 
                ordinal_position, 
                is_nullable,
                is_primary_key, 
                is_foreign_key, 
                description
            FROM columns
            WHERE catalog_id = $1
            ORDER BY ordinal_position ASC
        """, catalog_id)

        # Per-column tags (all columns for this catalog in one query)
        column_tags_rows = await db.fetch_all("""
            SELECT
                tca.column_id,
                t.id        AS tag_id,
                t.name      AS tag_name,
                t.color     AS tag_color
            FROM tag_column_assignments tca
            JOIN tags t ON tca.tag_id = t.id
            WHERE tca.catalog_id = $1
        """, catalog_id)

        # Per-column glossary terms (all columns for this catalog in one query)
        column_terms_rows = await db.fetch_all("""
            SELECT
                gtca.column_id,
                gt.id        AS term_id,
                gt.name      AS term_name,
                gt.description AS term_description
            FROM glossary_term_column_assignments gtca
            JOIN glossary_terms gt ON gtca.term_id = gt.id
            JOIN columns col ON gtca.column_id = col.id
            WHERE col.catalog_id = $1
        """, catalog_id)

        # Build lookup maps keyed by column_id
        tags_by_column = {}
        for row in column_tags_rows:
            col_id = str(row["column_id"])
            tags_by_column.setdefault(col_id, []).append({
                "id":    str(row["tag_id"]),
                "name":  row["tag_name"],
                "color": row["tag_color"],
            })

        terms_by_column = {}
        for row in column_terms_rows:
            col_id = str(row["column_id"])
            terms_by_column.setdefault(col_id, []).append({
                "id":          str(row["term_id"]),
                "name":        row["term_name"],
                "description": row["term_description"],
            })

        # Domains (multiple possible)
        domains = await db.fetch_all("""
            SELECT
                d.id,
                d.name,
                d.description,
                d.color,
                dca.assigned_at,
                dca.assigned_by
            FROM domain_catalog_assignments dca
            JOIN domains d ON dca.domain_id = d.id
            WHERE dca.catalog_id = $1
            ORDER BY d.name
        """, catalog_id)

        # Catalog-level tags
        tags = await db.fetch_all("""
            SELECT 
                t.id, 
                t.name, 
                t.color, 
                t.description,
                tca.assigned_at,
                tca.assigned_by
            FROM tag_catalog_assignments tca
            JOIN tags t ON tca.tag_id = t.id
            WHERE tca.catalog_id = $1
            ORDER BY t.name
        """, catalog_id)

        return {
            "id": str(catalog["id"]),
            "table_name": catalog["table_name"],
            "full_name": catalog["full_name"],
            "database_name": catalog["database_name"],
            "schema_name": catalog["schema_name"],
            "description": catalog["description"],
            "source_name": catalog["source_name"],
            "source_type": catalog["source_type"],
            "row_count": catalog["row_count"] or 0,
            "column_count": len(columns),
            "properties": catalog["properties"] or {},
            "created_at": catalog["created_at"].isoformat() if catalog["created_at"] else None,
            "updated_at": catalog["updated_at"].isoformat() if catalog["updated_at"] else None,

            "owner": {
                "id":    str(catalog["owner_id"]),
                "name":  catalog["owner_name"],
                "email": catalog["owner_email"],
                "role":  catalog["owner_role"],
            } if catalog["owner_id"] else None,

            "domains": [
                {
                    "id":          str(d["id"]),
                    "name":        d["name"],
                    "description": d["description"],
                    "color":       d["color"],
                    "assigned_at": d["assigned_at"].isoformat() if d["assigned_at"] else None,
                    "assigned_by": d["assigned_by"],
                }
                for d in domains
            ],

            "tags": [
                {
                    "id":          str(t["id"]),
                    "name":        t["name"],
                    "color":       t["color"],
                    "description": t["description"],
                    "assigned_at": t["assigned_at"].isoformat() if t["assigned_at"] else None,
                    "assigned_by": t["assigned_by"],
                }
                for t in tags
            ],

            "columns": [
                {
                    "name":             col["name"],
                    "type":             _parse_data_type(col["data_type"]),
                    "is_nullable":      col["is_nullable"],
                    "is_primary_key":   col["is_primary_key"],
                    "is_foreign_key":   col["is_foreign_key"],
                    "ordinal_position": col["ordinal_position"],
                    "description":      col["description"],
                    "tags":             tags_by_column.get(str(col["id"]), []),
                    "glossary_terms":   terms_by_column.get(str(col["id"]), []),
                }
                for col in columns
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching catalog detail {catalog_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
# ============================================================================
# SEARCH
# ============================================================================

@router.post("/api/v1/search", tags=["Search"])
async def search_metadata(request: SearchRequest):
    """Search across metadata"""
    from app import db, logger
    try:
        query = """
            SELECT DISTINCT 
                c.id,
                c.full_name,
                c.table_name,
                c.database_name,
                c.schema_name,
                c.description,
                ds.name as source_name,
                ds.source_type,
                COUNT(DISTINCT col.id) as column_count,
                ts_rank(
                    to_tsvector('english', 
                        COALESCE(c.table_name, '') || ' ' || 
                        COALESCE(c.description, '') || ' ' ||
                        COALESCE(c.full_name, '')
                    ), 
                    plainto_tsquery('english', $1)
                ) as rank
            FROM catalogs c
            JOIN data_sources ds ON c.source_id = ds.id
            LEFT JOIN columns col ON c.id = col.catalog_id
            WHERE to_tsvector('english', 
                COALESCE(c.table_name, '') || ' ' || 
                COALESCE(c.description, '') || ' ' ||
                COALESCE(c.full_name, '')
            ) @@ plainto_tsquery('english', $1)
        """
        params = [request.query]
        
        if request.source_type:
            query += f" AND ds.source_type = ${len(params) + 1}"
            params.append(request.source_type.value)
        
        query += " GROUP BY c.id, ds.name, ds.source_type ORDER BY rank DESC"
        query += f" LIMIT ${len(params) + 1}"
        params.append(request.limit)
        
        results = await db.fetch_all(query, *params)
        
        # Convert UUIDs to strings
        return [dict(row, id=str(row['id']) if row['id'] else None) for row in results]
    
    except Exception as e:
        logger.error(f"Error searching metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STATISTICS
# ============================================================================
@router.get("/api/v1/statistics", response_model=StatisticsResponse, tags=["Overview"])
async def get_statistics():
    """Get metadata statistics"""
    from app import db, logger
    from fastapi import HTTPException

    try:
        stats = await db.fetch_one("""
            SELECT
                (SELECT COUNT(*) FROM data_sources)                       as total_sources,
                (SELECT COUNT(*) FROM data_sources WHERE status = 'success') as success_sources,
                (SELECT COUNT(*) FROM catalogs)                           as total_datasets,
                (SELECT COUNT(*) FROM columns)                            as total_columns,
                (SELECT COUNT(*) FROM ingestion_jobs WHERE status = 'success') as successful_jobs,
                (SELECT COUNT(*) FROM ingestion_jobs WHERE status = 'failed')   as failed_jobs,
                (SELECT COUNT(DISTINCT source_type) FROM data_sources)    as source_types_count,
                (SELECT MAX(last_ingested_at) FROM data_sources)          as last_ingestion
        """)

        sources_by_type = await db.fetch_all("""
            SELECT source_type, COUNT(*) as count
            FROM data_sources
            GROUP BY source_type
        """)

        result = dict(stats)
        result['sources_by_type']   = {row['source_type']: row['count'] for row in sources_by_type}
        
        # Fix: add the required field
        result['active_sources']    = result['success_sources']   # ← most logical mapping

        return result

    except Exception as e:
        logger.error(f"Error getting statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# API LOGS
# ============================================================================

@router.get("/api/v1/logs", tags=["API Logs"])
async def list_api_logs(
    entity_type: Optional[str] = None,
    api_endpoint: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """
    List API activity logs.
    
    Shows all recorded operations with timestamps, descriptions, and associated owner.
    """
    from app import db, logger
    try:
        query = """
            SELECT
                l.id, l.endpoint, l.method, l.action_summary,
                l.entity_type, l.entity_id, l.entity_name,
                l.owner_id, o.name AS owner_name, o.role AS owner_role,
                l.status_code, l.request_body, l.created_at
            FROM api_logs l
            LEFT JOIN owners o ON l.owner_id = o.id
            WHERE 1=1
        """
        params = []
        if entity_type:
            query += f" AND l.entity_type = ${len(params)+1}"
            params.append(entity_type)
        if api_endpoint:
            query += f" AND l.endpoint = ${len(params)+1}"
            params.append(api_endpoint)
        query += f" ORDER BY l.created_at DESC LIMIT ${len(params)+1}"
        params.append(limit)

        rows = await db.fetch_all(query, *params)
        result = []
        for r in rows:
            d = dict(r)
            d['id'] = str(d['id'])
            d['owner_id'] = str(d['owner_id']) if d.get('owner_id') else None
            if d.get('request_body') and isinstance(d['request_body'], str):
                try:
                    d['request_body'] = json.loads(d['request_body'])
                except Exception:
                    pass
            result.append(d)
        return result
    except Exception as e:
        logger.error(f"Error listing api logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/recent-activity", tags=["Overview"])
async def get_recent_activity_minimal(
    limit: int = Query(12, ge=5, le=80)
):
    """Get recent API activity in minimal format"""
    from app import db
    rows = await db.fetch_all("""
        SELECT 
            created_at,
            action_summary
        FROM api_logs
        ORDER BY created_at DESC
        LIMIT $1
    """, limit)

    return [
        {
            "t": row["created_at"].isoformat() if row["created_at"] else None,
            "msg": row["action_summary"]
        }
        for row in rows
    ]



def format_time_ago(timestamp):
    now = datetime.now(timezone.utc)
    diff = now - timestamp

    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"

    minutes = seconds // 60
    if minutes < 60:
        return f"{int(minutes)} min ago"

    hours = minutes // 60
    if hours < 24:
        return f"{int(hours)} hr ago"

    days = hours // 24
    return f"{int(days)} days ago"
@router.get("/api/v1/recently-viewed" , tags=["Overview"])
def get_recently_viewed():
    try:

        rows = execute_query("""
            SELECT
                c.table_name,
                ds.name AS source_name,
                t.name AS tag,
                al.created_at
            FROM api_logs al
            JOIN catalogs c
                ON c.id::text = al.entity_id
            LEFT JOIN data_sources ds
                ON ds.id = c.source_id
            LEFT JOIN tag_catalog_assignments tca
                ON tca.catalog_id = c.id
            LEFT JOIN tags t
                ON t.id = tca.tag_id
            WHERE al.entity_type = 'catalog'
            ORDER BY al.created_at DESC
            LIMIT 5
        """)

        datasets = [
            {
                "dataset": row["table_name"],
                "source": row["source_name"],
                "tag": row["tag"],
                "time": format_time_ago(row["created_at"])
            }
            for row in rows
        ]

        return {"recently_viewed": datasets}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# ============================================================================
# RUN HISTORY
# ============================================================================
@router.get("/api/v1/run-history", tags=["Overview"])
async def get_run_history(
    status: Optional[str] = Query(None, description="Filter by job status (running, failed, success)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Get ingestion run history for all data sources.
    Retrieves data from ingestion_jobs table with source details.
    """
    from app import db, logger
    from fastapi import HTTPException

    try:
        filters = []
        params = []

        if status:
            params.append(status.lower())
            filters.append("ij.status = $1")

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        param_count = len(params)
        limit_idx = param_count + 1
        offset_idx = param_count + 2

        rows = await db.fetch_all(f"""
            SELECT
                ij.id                  AS job_id,
                ij.source_id,
                ds.name                AS source_name,
                ds.source_type,
                ds.schedule,
                o.name                 AS owner_name,
                ij.status,
                ij.created_at          AS started_at,
                ij.completed_at        AS completed_at,
                ij.records_ingested,
                ij.error_message,
                CASE 
                    WHEN ij.completed_at IS NOT NULL 
                    THEN EXTRACT(EPOCH FROM (ij.completed_at - ij.created_at))::INTEGER
                    ELSE NULL
                END                    AS duration_seconds
            FROM ingestion_jobs ij
            LEFT JOIN data_sources ds ON ij.source_id = ds.id
            LEFT JOIN owners o        ON ds.owner_id  = o.id
            {where_clause}
            ORDER BY ij.created_at DESC
            LIMIT ${limit_idx} OFFSET ${offset_idx}
        """, *params, limit, offset)

        count_params = params.copy()
        total_row = await db.fetch_one(f"""
            SELECT COUNT(*) AS total
            FROM ingestion_jobs ij
            {where_clause}
        """, *count_params)

        history = []
        for r in rows:
            history.append({
                "job_id":           str(r["job_id"]),
                "source_id":        str(r["source_id"]) if r["source_id"] else None,
                "source_name":      r["source_name"],
                "source_type":      r["source_type"],
                "schedule":         r["schedule"],
                "owner_name":       r["owner_name"],
                "status":           r["status"],
                "started_at":       r["started_at"].isoformat() if r["started_at"] else None,
                "completed_at":     r["completed_at"].isoformat() if r["completed_at"] else None,
                "duration_seconds": r["duration_seconds"] if r["duration_seconds"] is not None else None,
                "records_ingested": r["records_ingested"] or 0,
                "error_message":    r["error_message"],
            })

        return {
            "total":   int(total_row["total"]) if total_row else 0,
            "limit":   limit,
            "offset":  offset,
            "results": history
        }

    except Exception as e:
        logger.error(f"Error fetching run history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
# ============================================================================
# OVERVIEW STATISTICS
# ============================================================================

@router.get("/api/v1/overview/stats", tags=["Overview"])
async def get_overview_stats():
    """
    Returns total counts for datasets, tags, domains, overall assets,
    plus compliance metrics: pending_review, open_issues, governance_score,
    and at_risk_domains.
    """
    from app import db, logger
    try:
        # -- Core asset counts ------------------------------------------------
        row = await db.fetch_one("""
            SELECT
                (SELECT COUNT(*) FROM catalogs)         AS total_datasets,
                (SELECT COUNT(*) FROM tags)             AS total_tags,
                (SELECT COUNT(*) FROM domains)          AS total_domains,
                (
                    (SELECT COUNT(*) FROM catalogs) +
                    (SELECT COUNT(*) FROM tags) +
                    (SELECT COUNT(*) FROM domains)
                )                                       AS total_assets
        """)

        # -- Pending review: catalogs missing owner or description ------------
        pending_review = await db.fetch_val("""
            SELECT COUNT(*)
            FROM catalogs c
            WHERE NOT EXISTS (
            SELECT 1
            FROM tag_catalog_assignments tca
            WHERE tca.catalog_id = c.id
        );
        """)

        # -- Latest compliance snapshot ---------------------------------------
        snapshot_row = await db.fetch_one("""
            SELECT open_issues_count, overall_score
            FROM compliance_snapshots
            ORDER BY recorded_at DESC
            LIMIT 1
        """)

        open_issues      = None
        governance_score = None
        at_risk_domains  = 0

        if snapshot_row:
            open_issues      = snapshot_row["open_issues_count"]
            governance_score = snapshot_row["overall_score"]

            # -- At-risk domains: CRITICAL or HIGH severity issues ------------
            at_risk_row = await db.fetch_val("""
                SELECT COUNT(DISTINCT issue->>'dataset')
                FROM compliance_snapshots,
                     jsonb_array_elements(snapshot_json->'open_issues'->'items') AS issue
                WHERE issue->>'severity' IN ('CRITICAL', 'HIGH')
                  AND recorded_at = (SELECT MAX(recorded_at) FROM compliance_snapshots)
            """)
            at_risk_domains = at_risk_row or 0

        return {
            "total_datasets":   {
                "value" : row["total_datasets"],
                "info" : "Count of total catalogs that have been ingested into the data catalog"},
            "total_tags":       row["total_tags"],
            "total_domains":    row["total_domains"],
            "total_assets":     row["total_assets"],
            "pending_review":   pending_review or 0,
            "open_issues":      open_issues,
            "governance_score": governance_score,
            "at_risk_domains":  at_risk_domains,
        }

    except Exception as e:
        logger.error(f"Error fetching overview stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DATASETS BY PLATFORM
# ============================================================================

@router.get("/api/v1/overview/datasets-by-platform", tags=["Overview"])
async def get_datasets_by_platform():
    """
    Returns catalog count grouped by platform (source type).
    """
    from app import db, logger
    try:
        rows = await db.fetch_all("""
            SELECT
                ds.source_type  AS platform,
                COUNT(c.id)     AS catalog_count
            FROM data_sources ds
            LEFT JOIN catalogs c ON c.source_id = ds.id
            GROUP BY ds.source_type
            ORDER BY catalog_count DESC
        """)

        return {
            "platforms": [
                {
                    "platform":      r["platform"],
                    "catalog_count": r["catalog_count"]
                }
                for r in rows
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching datasets by platform: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/domains/dataset-count",tags=["Overview"])
async def domains_simple_with_count(
    limit: int = Query(30, ge=1, le=200)
):
    from app import db

    rows = await db.fetch_all(
        """
        SELECT 
            d.id,
            d.name,
            COUNT(dca.catalog_id) AS dataset_count
        FROM domains d
        LEFT JOIN domain_catalog_assignments dca ON d.id = dca.domain_id
        GROUP BY d.id, d.name
        ORDER BY dataset_count DESC, d.name ASC
        LIMIT $1
        """,
        limit,
    )

    return [
        {"id": str(row["id"]), "name": row["name"], "dataset_count": row["dataset_count"] or 0}
        for row in rows
    ]


@router.get("/compliance-overview", tags=["Overview"])
def get_compliance_overview():
    try:
        snapshot = execute_query("""
            SELECT snapshot_json
            FROM compliance_snapshots
            ORDER BY recorded_at DESC
            LIMIT 1
        """)[0]["snapshot_json"]

        insight_text = snapshot.get("ai_insights", {}).get("text", "")

        frameworks = snapshot.get("frameworks", [])

        framework_scores = [
            {"framework": fw["name"], "score": fw["score"]}
            for fw in frameworks
        ]

        return {
            "insight": insight_text,
            "framework_scores": framework_scores
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/tags/top", tags=["Overview"])
async def get_top_tags(
    limit: int = Query(30, ge=1, le=200)
):
    """
    Returns tags with total asset count (catalogs + columns) in descending order.
    """
    from app import db, logger
    try:
        rows = await db.fetch_all(
            """
            SELECT
                t.id,
                t.name,
                t.color,
                t.tag_type,
                COUNT(DISTINCT tca.catalog_id)  AS catalog_count,
                COUNT(DISTINCT tcola.column_id) AS column_count,
                COUNT(DISTINCT tca.catalog_id) + COUNT(DISTINCT tcola.column_id) AS total_assets
            FROM tags t
            LEFT JOIN tag_catalog_assignments tca   ON t.id = tca.tag_id
            LEFT JOIN tag_column_assignments  tcola ON t.id = tcola.tag_id
            GROUP BY t.id, t.name, t.color, t.tag_type
            ORDER BY total_assets DESC, t.name ASC
            LIMIT $1
            """,
            limit,
        )

        return [
            {
                "id":            str(row["id"]),
                "name":          row["name"],
                "color":         row["color"],
                "tag_type":      row["tag_type"],
                "catalog_count": row["catalog_count"] or 0,
                "column_count":  row["column_count"]  or 0,
                "total_assets":  row["total_assets"]  or 0,
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Error fetching top tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))