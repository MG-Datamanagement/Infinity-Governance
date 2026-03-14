from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import json
import re
from datetime import datetime

from models import CatalogDataCardResponse

router = APIRouter(tags=["datacard"])


# ============================================================================
# SQL – run once at startup (or via your migration tool) to create the table
# ============================================================================
#
#   CREATE TABLE IF NOT EXISTS datacards (
#       id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
#       catalog_id    TEXT NOT NULL,
#       table_name    TEXT,
#       full_name     TEXT,
#       data_card     TEXT NOT NULL,
#       generated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
#       status        TEXT NOT NULL DEFAULT 'generated',   -- 'generated' | 'cached'
#       created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
#       updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
#       CONSTRAINT uq_datacards_catalog UNIQUE (catalog_id)
#   );
#
# ============================================================================


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
| Row Count      | ...   |
| Column Count   | ...   |
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
Row Count    : {catalog_detail.get('row_count', 'Unknown')}
Column Count : {catalog_detail.get('column_count', len(catalog_detail.get('columns', [])))}
Domain(s)    : {domains}
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
        logger.info(f"[datacard] Saved to datacards table for catalog {catalog_id}")
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
        """,
        catalog_id,
    )

    if not catalog:
        await _log(
            db, logger,
            endpoint=endpoint, method="POST",
            action_summary=f"Datacard generation failed – catalog '{catalog_id}' not found",
            entity_id=catalog_id, status_code=404,
        )
        raise HTTPException(status_code=404, detail=f"Catalog '{catalog_id}' not found")

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
            action_summary=f"Datacard returned from cache for catalog '{catalog_id}'",
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
        "row_count":     catalog["row_count"] or 0,
        "column_count":  len(columns),
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
        logger.info(f"[datacard] Also saved to catalogs.metadata for catalog {catalog_id}")
    except Exception as exc:
        logger.warning(f"[datacard] Could not persist to catalogs.metadata: {exc}")

    # ── Step 9: Log to api_logs ──────────────────────────────────────────────
    await _log(
        db, logger,
        endpoint=endpoint,
        method="POST",
        action_summary=f"Datacard generated for catalog '{catalog['table_name']}' (id={catalog_id})",
        entity_type="catalog",
        entity_id=catalog_id,
        entity_name=catalog["table_name"],
        status_code=200,
        request_body={"catalog_id": catalog_id, "max_tokens": max_tokens},
        response_summary=(
            f"status=generated | "
            f"columns={len(columns)} | "
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
        action_summary=f"Datacard retrieved for catalog '{row['table_name']}' (id={catalog_id})",
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