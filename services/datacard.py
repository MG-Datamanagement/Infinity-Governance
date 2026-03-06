from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import json
import re
from datetime import datetime

from models import CatalogDataCardResponse

router = APIRouter(tags=["datacard"])


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

### 4. Data Quality Indicators
Highlight any nullable columns, presence/absence of primary keys, foreign-key relationships, 
and what this implies about data integrity.

### 5. Business Value & Use Cases
2-3 concrete use cases or analytical questions this dataset can answer.

### 6. Governance Notes
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


@router.post(
    "/api/v1/catalogs/{catalog_id}/datacard",
    response_model=CatalogDataCardResponse,
    summary="Generate an AI data card for a catalog entry",
)
async def generate_catalog_datacard(catalog_id: str, max_tokens: int = 2000):
    """
    Fetches ALL metadata for the given catalog_id (table, columns, owner, 
    domains, tags, properties) and asks Azure OpenAI to produce a structured
    Data Card.  The result is stored back into the catalogs.metadata JSONB 
    column under the key 'data_card' so future calls can return the cached copy.
    """
    from app import db, logger, get_azure_client, AZURE_CONFIG

    ai_client = get_azure_client()
    if not ai_client:
        raise HTTPException(
            status_code=503,
            detail="Azure OpenAI is not configured. Set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT."
        )

    # ── Step 1: Fetch full catalog detail ──────────────────────────────────
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
        raise HTTPException(status_code=404, detail=f"Catalog '{catalog_id}' not found")

    # ── Step 2: Columns ─────────────────────────────────────────────────────
    columns = await db.fetch_all("""
        SELECT name, data_type, ordinal_position, is_nullable,
               is_primary_key, is_foreign_key, description
        FROM columns
        WHERE catalog_id = $1
        ORDER BY ordinal_position ASC
    """, catalog_id)

    # ── Step 3: Domains ─────────────────────────────────────────────────────
    domains = await db.fetch_all("""
        SELECT d.id, d.name, d.description, d.color,
               dca.assigned_at, dca.assigned_by
        FROM domain_catalog_assignments dca
        JOIN domains d ON dca.domain_id = d.id
        WHERE dca.catalog_id = $1
        ORDER BY d.name
    """, catalog_id)

    # ── Step 4: Tags ────────────────────────────────────────────────────────
    tags = await db.fetch_all("""
        SELECT t.id, t.name, t.color, t.description,
               tca.assigned_at, tca.assigned_by
        FROM tag_catalog_assignments tca
        JOIN tags t ON tca.tag_id = t.id
        WHERE tca.catalog_id = $1
        ORDER BY t.name
    """, catalog_id)

    # ── Step 5: Check for cached datacard ───────────────────────────────────
    existing_meta = catalog["properties"] or {}
    if isinstance(existing_meta, str):
        try:
            existing_meta = json.loads(existing_meta)
        except Exception:
            existing_meta = {}

    if existing_meta.get("data_card"):
        logger.info(f"Returning cached datacard for catalog {catalog_id}")
        return CatalogDataCardResponse(
            catalog_id=catalog_id,
            table_name=catalog["table_name"],
            full_name=catalog["full_name"],
            data_card=existing_meta["data_card"],
            generated_at=catalog["updated_at"],
            status="cached",
        )

    # ── Step 6: Build the rich context dict ─────────────────────────────────
    def _parse_dtype(raw: str) -> str:
        if not raw:
            return "unknown"
        
        m = re.search(r"type': (\w+)\(", raw)
        if m:
            return {
                "StringTypeClass": "string", "BytesTypeClass": "bytes",
                "TimeTypeClass": "timestamp", "NumberTypeClass": "number",
                "IntTypeClass": "integer", "FloatTypeClass": "float",
                "BooleanTypeClass": "boolean", "ArrayTypeClass": "array",
                "MapTypeClass": "map", "NullTypeClass": "null",
                "RecordTypeClass": "record", "EnumTypeClass": "enum",
                "UnionTypeClass": "union", "DateTypeClass": "date",
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
        "domains": [
            {"name": d["name"], "description": d["description"]}
            for d in domains
        ],
        "tags": [
            {"name": t["name"], "description": t["description"]}
            for t in tags
        ],
        "columns": [
            {
                "name":           col["name"],
                "data_type":      _parse_dtype(col["data_type"]),
                "ordinal_position": col["ordinal_position"],
                "is_nullable":    col["is_nullable"],
                "is_primary_key": col["is_primary_key"],
                "is_foreign_key": col["is_foreign_key"],
                "description":    col["description"],
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
        logger.error(f"Azure OpenAI call failed for catalog {catalog_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"AI generation failed: {exc}")

    data_card_text = ai_response.choices[0].message.content.strip()

    # ── Step 8: Persist datacard into catalogs.metadata JSONB ────────────────
    updated_meta = {**existing_meta, "data_card": data_card_text}
    try:
        await db.execute(
            "UPDATE catalogs SET metadata = $1, updated_at = NOW() WHERE id = $2",
            json.dumps(updated_meta),
            catalog_id,
        )
        logger.info(f"Datacard saved for catalog {catalog_id}")
    except Exception as exc:
        logger.warning(f"Could not persist datacard: {exc}")

    return CatalogDataCardResponse(
        catalog_id=catalog_id,
        table_name=catalog["table_name"],
        full_name=catalog["full_name"],
        data_card=data_card_text,
        generated_at=datetime.utcnow(),
        status="generated",
    )
