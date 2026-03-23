from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import json
import re
from datetime import datetime
from pydantic import BaseModel


from models import CatalogDataCardResponse

router = APIRouter(tags=["datacard"])


class BulkDataCardResult(BaseModel):
    catalog_id: str
    table_name: str
    full_name: Optional[str]
    status: str                     # "generated" | "cached" | "failed"
    error: Optional[str] = None     # populated only when status == "failed"
    generated_at: Optional[datetime] = None


class BulkDataCardResponse(BaseModel):
    source_id: str
    total_catalogs: int
    generated: int
    cached: int
    failed: int
    results: List[BulkDataCardResult]

# ============================================================================
# Schemas – catalog properties + custom properties
# ============================================================================

class CustomPropertyItem(BaseModel):
    id:         str
    key:        str
    value:      str
    value_type: str


class CatalogPropertiesResponse(BaseModel):
    full_name:         Optional[str]
    database:          Optional[str]
    schema_name:       Optional[str]
    source:            Optional[str]
    source_type:       Optional[str]
    column_count:      int
    row_count:         Optional[int]
    tags:              str
    owner:             str
    last_updated:      Optional[str]
    custom_properties: List[CustomPropertyItem] = []


class CreateCustomPropertyRequest(BaseModel):
    key:        str
    value:      str
    value_type: Optional[str] = "string"


def _build_datacard_prompt(catalog_detail: dict) -> str:
    """
    Build a rich, structured prompt from the full catalog detail dict
    (same shape returned by GET /catalogs/detail/{catalog_id}).
    """
    col_lines = []
    for col in catalog_detail.get("columns", []):
        flags = []
        if col.get("is_primary_key"):  flags.append("PK")
        if col.get("is_foreign_key"):  flags.append("FK")
        if not col.get("is_nullable"): flags.append("NOT NULL")
        flag_str = f"  [{', '.join(flags)}]" if flags else ""
        desc = f"  – {col['description']}" if col.get("description") else ""
        col_lines.append(f"  • {col['name']} ({col['data_type']}){flag_str}{desc}")

    columns_section = "\n".join(col_lines) if col_lines else "  (no columns available)"

    domains = ", ".join(d["name"] for d in catalog_detail.get("domains", [])) or "None"
    tags    = ", ".join(t["name"] for t in catalog_detail.get("tags", []))    or "None"
    owner   = catalog_detail.get("owner")
    owner_str = (
        f"{owner['name']} ({owner['role']}) – {owner.get('email', 'no email')}"
        if owner else "Unassigned"
    )

    props = catalog_detail.get("properties") or {}
    props_lines = "\n".join(f"  {k}: {v}" for k, v in props.items()) if props else "  (none)"

    # ── Row count: show real number or "Unknown" ─────────────────────────────
    row_count_raw = catalog_detail.get("row_count")
    row_count_str = f"{row_count_raw:,}" if row_count_raw is not None else "Unknown"  # ← ADDED

    prompt = f"""You are a senior data governance analyst. Generate a professional **Data Card** 
for the dataset described below. The card must strictly follow this format:

---
## Data Card: {{table_name}}

### 1. Overview
A 2-3 sentence business-friendly summary of what this table/dataset represents, 
its primary purpose, and who typically uses it.

### 2. Key Metadata
| Attribute      | Value |
|----------------|-------|
| Full Name      | ...   |
| Database       | ...   |
| Schema         | ...   |
| Source         | ...   |
| Source Type    | ...   |
| Column Count   | ...   |
| Row Count      | ...   |
| Domain(s)      | ...   |
| Tags           | ...   |
| Owner          | ...   |
| Last Updated   | ...   |

### 3. Schema & Column Details
Brief explanation of what the schema represents, followed by notable columns and their business meaning.


### 4. Business Value & Use Cases
2-3 concrete use cases or analytical questions this dataset can answer.

### 5. Governance Notes
Domain classification, assigned tags, ownership, and any data sensitivity considerations 
inferred from column names or types.
---

=== DATASET INFORMATION ===
Table Name   : {catalog_detail.get('table_name')}
Full Name    : {catalog_detail.get('full_name') or 'N/A'}
Database     : {catalog_detail.get('database_name') or 'N/A'}
Schema       : {catalog_detail.get('schema_name') or 'N/A'}
Source Name  : {catalog_detail.get('source_name') or 'N/A'}
Source Type  : {catalog_detail.get('source_type') or 'N/A'}
Description  : {catalog_detail.get('description') or 'No description provided'}
Column Count : {catalog_detail.get('column_count', len(catalog_detail.get('columns', [])))}
Row Count    : {row_count_str}
Tags         : {tags}
Owner        : {owner_str}
Last Updated : {catalog_detail.get('updated_at') or 'Unknown'}

Custom Properties:
{props_lines}

Columns ({len(catalog_detail.get('columns', []))} total):
{columns_section}

Now write the Data Card following the format above exactly.
Replace all placeholder '...' values with real data from the dataset information.
"""
    return prompt


# ============================================================================
# HELPER – write a row to api_logs (mirrors app.log_api_action signature)
# ============================================================================

async def _log(
    db,
    logger,
    *,
    endpoint: str,
    method: str,
    action_summary: str,
    entity_type: str = "catalog",
    entity_id: str = None,
    entity_name: str = None,
    status_code: int = 200,
    request_body: dict = None,
    response_summary: str = None,
):
    """Non-blocking api_logs insert; errors are swallowed so they never break the caller."""
    try:
        await db.execute(
            """
            INSERT INTO api_logs
                (endpoint, method, action_summary, entity_type, entity_id, entity_name,
                 status_code, request_body, response_summary)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            endpoint,
            method,
            action_summary,
            entity_type,
            entity_id,
            entity_name,
            status_code,
            json.dumps(request_body) if request_body else None,
            response_summary,
        )
    except Exception as exc:
        logger.warning(f"[datacard] Failed to write api_log: {exc}")


# ============================================================================
# HELPER – upsert datacard into dedicated `datacards` table
# ============================================================================

async def _save_datacard(
    db,
    logger,
    *,
    catalog_id: str,
    table_name: str,
    full_name: str,
    data_card_text: str,
    status: str = "generated",
):
    """
    Insert or update the datacards table.
    Uses ON CONFLICT (catalog_id) DO UPDATE so re-generating always refreshes the row.
    """
    try:
        await db.execute(
            """
            INSERT INTO datacards (catalog_id, table_name, full_name, data_card, status, generated_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
            ON CONFLICT (catalog_id) DO UPDATE
                SET table_name   = EXCLUDED.table_name,
                    full_name    = EXCLUDED.full_name,
                    data_card    = EXCLUDED.data_card,
                    status       = EXCLUDED.status,
                    generated_at = NOW(),
                    updated_at   = NOW()
            """,
            catalog_id,
            table_name,
            full_name,
            data_card_text,
            status,
        )
        logger.info(f"[datacard] Saved to datacards table for catalog")
    except Exception as exc:
        logger.warning(f"[datacard] Could not persist to datacards table: {exc}")


# ============================================================================
# POST  /api/v1/catalogs/{catalog_id}/datacard
# ============================================================================

@router.post(
    "/api/v1/catalogs/{catalog_id}/datacard",
    response_model=CatalogDataCardResponse,
    summary="Generate an AI data card for a catalog entry",
)
async def generate_catalog_datacard(catalog_id: str, max_tokens: int = 2000):
    """
    Fetches ALL metadata for the given catalog_id (table, columns, owner,
    domains, tags, properties) and asks Azure OpenAI to produce a structured
    Data Card.

    Storage behaviour
    -----------------
    1. The generated text is saved to the **datacards** table (upsert on catalog_id).
    2. It is also persisted in **catalogs.metadata** JSONB under the key 'data_card'
       (backward-compatible cache).
    3. A record is written to **api_logs** for audit purposes.
    """
    from app import db, logger, get_azure_client, AZURE_CONFIG

    endpoint = f"/api/v1/catalogs/{catalog_id}/datacard"

    ai_client = get_azure_client()
    if not ai_client:
        await _log(
            db, logger,
            endpoint=endpoint, method="POST",
            action_summary="Datacard generation failed – Azure OpenAI not configured",
            entity_id=catalog_id, status_code=503,
        )
        raise HTTPException(
            status_code=503,
            detail="Azure OpenAI is not configured. Set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT.",
        )

    # ── Step 1: Fetch full catalog detail ──────────────────────────────────
    catalog = await db.fetch_one(
        """
        SELECT
            c.id,
            c.table_name,
            c.full_name,
            c.database_name,
            c.schema_name,
            c.description,
            c.metadata        AS properties,
            c.row_count,                          -- ← ADDED
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
        """,
        catalog_id,
    )

    if not catalog:
        await _log(
            db, logger,
            endpoint=endpoint, method="POST",
            action_summary=f"Datacard generation failed – catalog not found",
            entity_id=catalog_id, status_code=404,
        )
        raise HTTPException(status_code=404, detail=f"Catalog not found")

    # ── Step 2: Columns ─────────────────────────────────────────────────────
    columns = await db.fetch_all(
        """
        SELECT name, data_type, ordinal_position, is_nullable,
               is_primary_key, is_foreign_key, description
        FROM columns
        WHERE catalog_id = $1
        ORDER BY ordinal_position ASC
        """,
        catalog_id,
    )

    # ── Step 3: Domains ─────────────────────────────────────────────────────
    domains = await db.fetch_all(
        """
        SELECT d.id, d.name, d.description, d.color,
               dca.assigned_at, dca.assigned_by
        FROM domain_catalog_assignments dca
        JOIN domains d ON dca.domain_id = d.id
        WHERE dca.catalog_id = $1
        ORDER BY d.name
        """,
        catalog_id,
    )

    # ── Step 4: Tags ────────────────────────────────────────────────────────
    tags = await db.fetch_all(
        """
        SELECT t.id, t.name, t.color, t.description,
               tca.assigned_at, tca.assigned_by
        FROM tag_catalog_assignments tca
        JOIN tags t ON tca.tag_id = t.id
        WHERE tca.catalog_id = $1
        ORDER BY t.name
        """,
        catalog_id,
    )

    # ── Step 5: Check for cached datacard in datacards table ────────────────
    existing_meta = catalog["properties"] or {}
    if isinstance(existing_meta, str):
        try:
            existing_meta = json.loads(existing_meta)
        except Exception:
            existing_meta = {}

    cached_row = await db.fetch_one(
        "SELECT data_card, generated_at FROM datacards WHERE catalog_id = $1",
        catalog_id,
    )

    if cached_row and cached_row["data_card"]:
        logger.info(f"[datacard] Returning cached datacard for catalog {catalog_id}")

        await _log(
            db, logger,
            endpoint=endpoint, method="POST",
            action_summary=f"Datacard returned from cache for catalog",
            entity_id=catalog_id,
            entity_name=catalog["table_name"],
            status_code=200,
            response_summary="status=cached",
        )

        return CatalogDataCardResponse(
            catalog_id=catalog_id,
            table_name=catalog["table_name"],
            full_name=catalog["full_name"],
            data_card=cached_row["data_card"],
            generated_at=cached_row["generated_at"],
            status="cached",
        )

    # ── Step 6: Build the rich context dict ─────────────────────────────────
    def _parse_dtype(raw: str) -> str:
        if not raw:
            return "unknown"
        m = re.search(r"type': (\w+)\(", raw)
        if m:
            return {
                "StringTypeClass":  "string",   "BytesTypeClass":   "bytes",
                "TimeTypeClass":    "timestamp", "NumberTypeClass":  "number",
                "IntTypeClass":     "integer",   "FloatTypeClass":   "float",
                "BooleanTypeClass": "boolean",   "ArrayTypeClass":   "array",
                "MapTypeClass":     "map",       "NullTypeClass":    "null",
                "RecordTypeClass":  "record",    "EnumTypeClass":    "enum",
                "UnionTypeClass":   "union",     "DateTypeClass":    "date",
            }.get(m.group(1), m.group(1).lower())
        return raw

    catalog_detail = {
        "id":            str(catalog["id"]),
        "table_name":    catalog["table_name"],
        "full_name":     catalog["full_name"],
        "database_name": catalog["database_name"],
        "schema_name":   catalog["schema_name"],
        "description":   catalog["description"],
        "source_name":   catalog["source_name"],
        "source_type":   catalog["source_type"],
        "column_count":  len(columns),
        "row_count":     catalog["row_count"],        # ← ADDED
        "properties":    existing_meta,
        "updated_at":    catalog["updated_at"].isoformat() if catalog["updated_at"] else None,
        "owner": {
            "id":    str(catalog["owner_id"]),
            "name":  catalog["owner_name"],
            "email": catalog["owner_email"],
            "role":  catalog["owner_role"],
        } if catalog["owner_id"] else None,
        "domains": [{"name": d["name"], "description": d["description"]} for d in domains],
        "tags":    [{"name": t["name"], "description": t["description"]} for t in tags],
        "columns": [
            {
                "name":             col["name"],
                "data_type":        _parse_dtype(col["data_type"]),
                "ordinal_position": col["ordinal_position"],
                "is_nullable":      col["is_nullable"],
                "is_primary_key":   col["is_primary_key"],
                "is_foreign_key":   col["is_foreign_key"],
                "description":      col["description"],
            }
            for col in columns
        ],
    }

    # ── Step 7: Call Azure OpenAI ────────────────────────────────────────────
    prompt = _build_datacard_prompt(catalog_detail)

    try:
        ai_response = await ai_client.chat.completions.create(
            model=AZURE_CONFIG["azure_deployment"],
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior data governance analyst who writes clear, "
                        "accurate, and professional data cards for enterprise data catalogs."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        logger.error(f"[datacard] Azure OpenAI call failed for catalog {catalog_id}: {exc}", exc_info=True)
        await _log(
            db, logger,
            endpoint=endpoint, method="POST",
            action_summary=f"Datacard AI generation failed for catalog '{catalog_id}'",
            entity_id=catalog_id,
            entity_name=catalog["table_name"],
            status_code=502,
            response_summary=str(exc),
        )
        raise HTTPException(status_code=502, detail=f"AI generation failed: {exc}")

    data_card_text = ai_response.choices[0].message.content.strip()
    generated_at   = datetime.utcnow()

    # ── Step 8a: Save to dedicated datacards table ───────────────────────────
    await _save_datacard(
        db, logger,
        catalog_id=catalog_id,
        table_name=catalog["table_name"],
        full_name=catalog["full_name"],
        data_card_text=data_card_text,
        status="generated",
    )

    # ── Step 8b: Also persist into catalogs.metadata JSONB (backward compat) ─
    updated_meta = {**existing_meta, "data_card": data_card_text}
    try:
        await db.execute(
            "UPDATE catalogs SET metadata = $1, updated_at = NOW() WHERE id = $2",
            json.dumps(updated_meta),
            catalog_id,
        )
        logger.info(f"[datacard] Also saved to catalogs.metadata for catalog")
    except Exception as exc:
        logger.warning(f"[datacard] Could not persist to catalogs.metadata: {exc}")

    # ── Step 9: Log to api_logs ──────────────────────────────────────────────
    await _log(
        db, logger,
        endpoint=endpoint,
        method="POST",
        action_summary=f"Datacard generated for catalog '{catalog['table_name']}'",
        entity_type="catalog",
        entity_id=catalog_id,
        entity_name=catalog["table_name"],
        status_code=200,
        request_body={"catalog_id": catalog_id, "max_tokens": max_tokens},
        response_summary=(
            f"status=generated | "
            f"columns={len(columns)} | "
            f"rows={catalog['row_count']} | "       # ← ADDED
            f"domains={len(domains)} | "
            f"tags={len(tags)} | "
            f"datacard_chars={len(data_card_text)}"
        ),
    )

    return CatalogDataCardResponse(
        catalog_id=catalog_id,
        table_name=catalog["table_name"],
        full_name=catalog["full_name"],
        data_card=data_card_text,
        generated_at=generated_at,
        status="generated",
    )


# ============================================================================
# GET  /api/v1/catalogs/{catalog_id}/datacard
# ============================================================================

@router.get(
    "/api/v1/catalogs/{catalog_id}/datacard",
    response_model=CatalogDataCardResponse,
    summary="Retrieve the stored data card for a catalog entry",
)
async def get_catalog_datacard(catalog_id: str):
    """
    Returns the most recently generated Data Card for the given catalog_id
    directly from the **datacards** table.  Returns 404 if no card has been
    generated yet (call POST first).
    """
    from app import db, logger

    endpoint = f"/api/v1/catalogs/{catalog_id}/datacard"

    # ── Fetch from datacards table ───────────────────────────────────────────
    row = await db.fetch_one(
        """
        SELECT dc.catalog_id,
               dc.table_name,
               dc.full_name,
               dc.data_card,
               dc.generated_at,
               dc.status
        FROM datacards dc
        WHERE dc.catalog_id = $1
        """,
        catalog_id,
    )

    if not row:
        await _log(
            db, logger,
            endpoint=endpoint, method="GET",
            action_summary=f"Datacard GET failed – no datacard found for catalog '{catalog_id}'",
            entity_id=catalog_id, status_code=404,
        )
        raise HTTPException(
            status_code=404,
            detail=(
                f"No data card found for catalog '{catalog_id}'. "
                "Call POST /api/v1/catalogs/{catalog_id}/datacard to generate one."
            ),
        )

    # ── Log successful retrieval ─────────────────────────────────────────────
    await _log(
        db, logger,
        endpoint=endpoint, method="GET",
        action_summary=f"Datacard retrieved for catalog '{row['table_name']}'",
        entity_type="catalog",
        entity_id=catalog_id,
        entity_name=row["table_name"],
        status_code=200,
        response_summary=f"status={row['status']} | generated_at={row['generated_at']}",
    )

    return CatalogDataCardResponse(
        catalog_id=row["catalog_id"],
        table_name=row["table_name"],
        full_name=row["full_name"],
        data_card=row["data_card"],
        generated_at=row["generated_at"],
        status=row["status"],
    )


@router.post(
    "/api/v1/sources/{source_id}/datacards/bulk-generate",
    response_model=BulkDataCardResponse,
    summary="Generate AI data cards for ALL catalogs under a data source",
)
async def bulk_generate_datacards(
    source_id: str,
    max_tokens: int = 2000,
    skip_cached: bool = True,
):
    """
    Iterates over every catalog that belongs to the given **source_id** and
    generates (or returns the cached) Data Card for each one, storing results
    in the `datacards` table.

    Query parameters
    ----------------
    - **max_tokens** (default 2000): token budget passed to Azure OpenAI per card.
    - **skip_cached** (default true): when *true*, catalogs that already have a
      stored datacard are skipped (returned with status="cached").  Set to
      *false* to force-regenerate every card even if one already exists.

    Response
    --------
    Returns a summary with per-catalog results including status
    ("generated" | "cached" | "failed") and any error messages for failed ones.
    """
    from app import db, logger, get_azure_client, AZURE_CONFIG

    endpoint = f"/api/v1/sources/{source_id}/datacards/bulk-generate"

    # ── Guard: Azure OpenAI must be configured ───────────────────────────────
    ai_client = get_azure_client()
    if not ai_client:
        await _log(
            db, logger,
            endpoint=endpoint, method="POST",
            action_summary="Bulk datacard generation failed – Azure OpenAI not configured",
            entity_type="source",
            entity_id=source_id,
            status_code=503,
        )
        raise HTTPException(
            status_code=503,
            detail="Azure OpenAI is not configured. Set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT.",
        )

    # ── Step 1: Verify the source exists ────────────────────────────────────
    source = await db.fetch_one(
        "SELECT id, name, source_type FROM data_sources WHERE id = $1",
        source_id,
    )
    if not source:
        await _log(
            db, logger,
            endpoint=endpoint, method="POST",
            action_summary=f"Bulk datacard failed – source '{source_id}' not found",
            entity_type="source",
            entity_id=source_id,
            status_code=404,
        )
        raise HTTPException(status_code=404, detail=f"Data source not found")

    # ── Step 2: Fetch all catalogs for this source ───────────────────────────
    catalogs = await db.fetch_all(
        """
        SELECT
            c.id,
            c.table_name,
            c.full_name,
            c.database_name,
            c.schema_name,
            c.description,
            c.metadata        AS properties,
            c.row_count,                          -- ← ADDED
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
        WHERE c.source_id = $1
        ORDER BY c.table_name ASC
        """,
        source_id,
    )

    if not catalogs:
        raise HTTPException(
            status_code=404,
            detail=f"No catalogs found for source '{source_id}'",
        )

    # ── Step 3: Process each catalog ────────────────────────────────────────
    results: List[BulkDataCardResult] = []
    generated_count = 0
    cached_count    = 0
    failed_count    = 0

    def _parse_dtype(raw: str) -> str:
        if not raw:
            return "unknown"
        m = re.search(r"type': (\w+)\(", raw)
        if m:
            return {
                "StringTypeClass":  "string",   "BytesTypeClass":   "bytes",
                "TimeTypeClass":    "timestamp", "NumberTypeClass":  "number",
                "IntTypeClass":     "integer",   "FloatTypeClass":   "float",
                "BooleanTypeClass": "boolean",   "ArrayTypeClass":   "array",
                "MapTypeClass":     "map",       "NullTypeClass":    "null",
                "RecordTypeClass":  "record",    "EnumTypeClass":    "enum",
                "UnionTypeClass":   "union",     "DateTypeClass":    "date",
            }.get(m.group(1), m.group(1).lower())
        return raw

    for catalog in catalogs:
        catalog_id  = str(catalog["id"])
        table_name  = catalog["table_name"]
        full_name   = catalog["full_name"]

        try:
            # ── 3a: Check cache ──────────────────────────────────────────────
            cached_row = await db.fetch_one(
                "SELECT data_card, generated_at FROM datacards WHERE catalog_id = $1",
                catalog_id,
            )

            if skip_cached and cached_row and cached_row["data_card"]:
                logger.info(f"[bulk-datacard] Skipping cached catalog {catalog_id}")
                cached_count += 1
                results.append(BulkDataCardResult(
                    catalog_id=catalog_id,
                    table_name=table_name,
                    full_name=full_name,
                    status="cached",
                    generated_at=cached_row["generated_at"],
                ))
                continue

            # ── 3b: Fetch columns ────────────────────────────────────────────
            columns = await db.fetch_all(
                """
                SELECT name, data_type, ordinal_position, is_nullable,
                       is_primary_key, is_foreign_key, description
                FROM columns
                WHERE catalog_id = $1
                ORDER BY ordinal_position ASC
                """,
                catalog_id,
            )

            # ── 3c: Fetch domains ────────────────────────────────────────────
            domains = await db.fetch_all(
                """
                SELECT d.name, d.description
                FROM domain_catalog_assignments dca
                JOIN domains d ON dca.domain_id = d.id
                WHERE dca.catalog_id = $1
                ORDER BY d.name
                """,
                catalog_id,
            )

            # ── 3d: Fetch tags ───────────────────────────────────────────────
            tags = await db.fetch_all(
                """
                SELECT t.name, t.description
                FROM tag_catalog_assignments tca
                JOIN tags t ON tca.tag_id = t.id
                WHERE tca.catalog_id = $1
                ORDER BY t.name
                """,
                catalog_id,
            )

            # ── 3e: Build catalog_detail dict ────────────────────────────────
            existing_meta = catalog["properties"] or {}
            if isinstance(existing_meta, str):
                try:
                    existing_meta = json.loads(existing_meta)
                except Exception:
                    existing_meta = {}

            catalog_detail = {
                "id":            catalog_id,
                "table_name":    table_name,
                "full_name":     full_name,
                "database_name": catalog["database_name"],
                "schema_name":   catalog["schema_name"],
                "description":   catalog["description"],
                "source_name":   catalog["source_name"],
                "source_type":   catalog["source_type"],
                "column_count":  len(columns),
                "row_count":     catalog["row_count"],    # ← ADDED
                "properties":    existing_meta,
                "updated_at":    catalog["updated_at"].isoformat() if catalog["updated_at"] else None,
                "owner": {
                    "id":    str(catalog["owner_id"]),
                    "name":  catalog["owner_name"],
                    "email": catalog["owner_email"],
                    "role":  catalog["owner_role"],
                } if catalog["owner_id"] else None,
                "domains": [{"name": d["name"], "description": d["description"]} for d in domains],
                "tags":    [{"name": t["name"], "description": t["description"]} for t in tags],
                "columns": [
                    {
                        "name":             col["name"],
                        "data_type":        _parse_dtype(col["data_type"]),
                        "ordinal_position": col["ordinal_position"],
                        "is_nullable":      col["is_nullable"],
                        "is_primary_key":   col["is_primary_key"],
                        "is_foreign_key":   col["is_foreign_key"],
                        "description":      col["description"],
                    }
                    for col in columns
                ],
            }

            # ── 3f: Build prompt & call Azure OpenAI ─────────────────────────
            prompt = _build_datacard_prompt(catalog_detail)

            ai_response = await ai_client.chat.completions.create(
                model=AZURE_CONFIG["azure_deployment"],
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a senior data governance analyst who writes clear, "
                            "accurate, and professional data cards for enterprise data catalogs."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=max_tokens,
            )

            data_card_text = ai_response.choices[0].message.content.strip()
            generated_at   = datetime.utcnow()

            # ── 3g: Persist to datacards table ───────────────────────────────
            await _save_datacard(
                db, logger,
                catalog_id=catalog_id,
                table_name=table_name,
                full_name=full_name,
                data_card_text=data_card_text,
                status="generated",
            )

            # ── 3h: Also update catalogs.metadata JSONB (backward compat) ────
            updated_meta = {**existing_meta, "data_card": data_card_text}
            try:
                await db.execute(
                    "UPDATE catalogs SET metadata = $1, updated_at = NOW() WHERE id = $2",
                    json.dumps(updated_meta),
                    catalog_id,
                )
            except Exception as exc:
                logger.warning(f"[bulk-datacard] Could not update catalogs.metadata for {catalog_id}: {exc}")

            generated_count += 1
            results.append(BulkDataCardResult(
                catalog_id=catalog_id,
                table_name=table_name,
                full_name=full_name,
                status="generated",
                generated_at=generated_at,
            ))
            logger.info(f"[bulk-datacard] Generated datacard for catalog ({table_name})")

        except Exception as exc:
            # Individual catalog failure must not abort the whole batch
            failed_count += 1
            logger.error(
                f"[bulk-datacard] Failed for catalog  ({table_name}): {exc}",
                exc_info=True,
            )
            results.append(BulkDataCardResult(
                catalog_id=catalog_id,
                table_name=table_name,
                full_name=full_name,
                status="failed",
                error=str(exc),
            ))

    # ── Step 4: Audit log ────────────────────────────────────────────────────
    await _log(
        db, logger,
        endpoint=endpoint,
        method="POST",
        action_summary=(
            f"Bulk datacard generation completed for source '{source['name']}': "
            f"{generated_count} generated, {cached_count} cached, {failed_count} failed"
        ),
        entity_type="source",
        entity_id=source_id,
        entity_name=source["name"],
        status_code=200,
        request_body={"source_id": source_id, "max_tokens": max_tokens, "skip_cached": skip_cached},
        response_summary=(
            f"total={len(catalogs)} | "
            f"generated={generated_count} | "
            f"cached={cached_count} | "
            f"failed={failed_count}"
        ),
    )

    return BulkDataCardResponse(
        source_id=source_id,
        total_catalogs=len(catalogs),
        generated=generated_count,
        cached=cached_count,
        failed=failed_count,
        results=results,
    )


# ============================================================================
# GET  /api/v1/catalogs/{catalog_id}/properties
# ============================================================================

@router.get(
    "/api/v1/catalogs/{catalog_id}/properties",
    response_model=CatalogPropertiesResponse,
    summary="Get key metadata properties for a catalog entry",
    description=(
        "Returns core metadata (source, schema, owner, tags, row/column count) plus all "
        "custom properties stored for this catalog. Properties with null/empty values "
        "are excluded from the response."
    ),
)
async def get_catalog_properties(catalog_id: str):
    from app import db, logger
    try:
        catalog = await db.fetch_one(
            """
            SELECT
                c.full_name,
                c.database_name,
                c.schema_name,
                c.updated_at,
                c.row_count,
                ds.name        AS source_name,
                ds.source_type AS source_type,
                o.name         AS owner_name,
                o.role         AS owner_role,
                o.email        AS owner_email
            FROM catalogs c
            LEFT JOIN data_sources ds ON c.source_id = ds.id
            LEFT JOIN owners o        ON c.owner_id  = o.id
            WHERE c.id = $1
            """,
            catalog_id,
        )

        if not catalog:
            raise HTTPException(status_code=404, detail=f"Catalog '{catalog_id}' not found")

        # ── Column count ──────────────────────────────────────────────────────
        col_count_row = await db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM columns WHERE catalog_id = $1", catalog_id,
        )
        column_count = col_count_row["cnt"] if col_count_row else 0

        # ── Row count (from catalogs table, may be NULL) ──────────────────────
        row_count = catalog["row_count"]

        # ── Tags ──────────────────────────────────────────────────────────────
        tag_rows = await db.fetch_all(
            """
            SELECT t.name FROM tag_catalog_assignments tca
            JOIN tags t ON tca.tag_id = t.id
            WHERE tca.catalog_id = $1 ORDER BY t.name
            """,
            catalog_id,
        )
        tags_str = ", ".join(r["name"] for r in tag_rows) or "None"

        # ── Custom properties – exclude null/empty values at DB level ─────────
        cp_rows = await db.fetch_all(
            """
            SELECT id, key, value, value_type
            FROM   custom_properties
            WHERE  catalog_id = $1
              AND  value IS NOT NULL
              AND  TRIM(value) <> ''
            ORDER  BY key
            """,
            catalog_id,
        )
        custom_props = [
            CustomPropertyItem(
                id=str(r["id"]),
                key=r["key"],
                value=r["value"],
                value_type=r["value_type"] or "string",
            )
            for r in cp_rows
        ]

        # ── Owner ─────────────────────────────────────────────────────────────
        if catalog["owner_name"]:
            owner_str = f"{catalog['owner_name']} ({catalog['owner_role']}) – {catalog['owner_email'] or 'no email'}"
        else:
            owner_str = "Unassigned"

        # ── Last updated ──────────────────────────────────────────────────────
        last_updated = (
            catalog["updated_at"].strftime("%d/%m/%Y %H:%M:%S")
            if catalog["updated_at"] else None
        )

        # ── Strip None/empty scalar fields ────────────────────────────────────
        def _val(v):
            return v if v is not None and str(v).strip() != "" else None

        await _log(
            db, logger,
            endpoint=f"/api/v1/catalogs/{catalog_id}/properties",
            method="GET",
            action_summary=f"Properties retrieved for catalog '{catalog_id}'",
            entity_type="catalog",
            entity_id=catalog_id,
            status_code=200,
            response_summary=(
                f"columns={column_count} | "
                f"rows={row_count} | "
                f"tags={tags_str} | "
                f"custom_props={len(custom_props)}"
            ),
        )

        return CatalogPropertiesResponse(
            full_name=_val(catalog["full_name"]),
            database=_val(catalog["database_name"]),
            schema_name=_val(catalog["schema_name"]),
            source=_val(catalog["source_name"]),
            source_type=_val(catalog["source_type"]),
            column_count=column_count,
            row_count=row_count,
            tags=tags_str,
            owner=owner_str,
            last_updated=last_updated,
            custom_properties=custom_props,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_catalog_properties error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# POST  /api/v1/catalogs/{catalog_id}/properties
# Add a custom property to a catalog
# ============================================================================

@router.post(
    "/api/v1/catalogs/{catalog_id}/properties",
    response_model=CustomPropertyItem,
    status_code=201,
    summary="Add a custom property to a catalog",
    description=(
        "Inserts a new key/value pair into `custom_properties` for the given catalog. "
        "Returns 409 if the key already exists (use PATCH to update an existing key). "
        "Empty key or value is rejected with 400."
    ),
)
async def create_custom_property(catalog_id: str, body: CreateCustomPropertyRequest):
    from app import db, logger
    try:
        # ── Validate catalog exists ───────────────────────────────────────────
        cat = await db.fetch_one("SELECT id FROM catalogs WHERE id = $1", catalog_id)
        if not cat:
            raise HTTPException(status_code=404, detail=f"Catalog '{catalog_id}' not found")

        # ── Validate inputs ───────────────────────────────────────────────────
        if not body.key or not body.key.strip():
            raise HTTPException(status_code=400, detail="Property key must not be empty.")
        if not body.value or not body.value.strip():
            raise HTTPException(status_code=400, detail="Property value must not be empty.")

        # ── Duplicate key guard ───────────────────────────────────────────────
        existing = await db.fetch_one(
            "SELECT id FROM custom_properties WHERE catalog_id = $1 AND key = $2",
            catalog_id, body.key.strip(),
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Property key '{body.key}' already exists for this catalog. Use PATCH to update it.",
            )

        # ── Insert ────────────────────────────────────────────────────────────
        row = await db.fetch_one(
            """
            INSERT INTO custom_properties (catalog_id, key, value, value_type)
            VALUES ($1, $2, $3, $4)
            RETURNING id, key, value, value_type
            """,
            catalog_id,
            body.key.strip(),
            body.value.strip(),
            (body.value_type or "string").strip(),
        )

        await _log(db, logger,
                   endpoint=f"/api/v1/catalogs/{catalog_id}/properties",
                   method="POST",
                   action_summary=f"Custom property '{body.key}' added to catalog '{catalog_id}'",
                   entity_type="catalog", entity_id=catalog_id,
                   status_code=201,
                   request_body={"key": body.key, "value": body.value, "value_type": body.value_type},
                   response_summary=f"property_id={row['id']}")

        return CustomPropertyItem(
            id=str(row["id"]),
            key=row["key"],
            value=row["value"],
            value_type=row["value_type"] or "string",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_custom_property error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))