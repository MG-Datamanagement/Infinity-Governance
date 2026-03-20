from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from langchain_openai import AzureChatOpenAI
import os

router = APIRouter(tags=["lineage"])


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class ColumnInfo(BaseModel):
    id: str
    name: str
    data_type: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    is_nullable: bool = True
    query_expression: Optional[str] = None


class SourceInfo(BaseModel):
    id: str
    name: str
    source_type: str


class TagInfo(BaseModel):
    id: str
    name: str
    color: Optional[str] = None
    tag_type: Optional[str] = None


class ColumnMapping(BaseModel):
    upstream_column_id: str
    upstream_column_name: Optional[str] = None
    downstream_column_id: str
    downstream_column_name: Optional[str] = None


class QueryExecutionInfo(BaseModel):
    """Execution metadata from the table_lineage row."""
    query_execution_id: Optional[str] = None
    query_start_time: Optional[str] = None
    query_end_time: Optional[str] = None
    query_runtime_ms: Optional[int] = None
    data_scanned_bytes: Optional[int] = None
    query_status: Optional[str] = None
    engine_version: Optional[str] = None
    s3_output_location: Optional[str] = None


class VisualNode(BaseModel):
    """One catalog card in the visual graph."""
    id: str
    table_name: str
    full_name: Optional[str] = None
    schema_name: Optional[str] = None
    database_name: Optional[str] = None
    type: Optional[str] = "table"
    status: Optional[str] = "healthy"
    source: Optional[SourceInfo] = None
    columns: List[ColumnInfo] = []
    tags: List[TagInfo] = []
    lineage_id: Optional[str] = None
    transformation_query: Optional[str] = None
    query_execution: Optional[QueryExecutionInfo] = None
    column_mappings: List[ColumnMapping] = []
    depth: int = 1
    ai_summary: Optional[str] = None
    stats: Optional[str] = None


class VisualLineageResponse(BaseModel):
    root: VisualNode
    upstreams: List[VisualNode] = []
    downstreams: List[VisualNode] = []


# ─── LLM ─────────────────────────────────────────────────────────────────────

llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    temperature=0.2
)


# ─── Hardcoded Mock Data ──────────────────────────────────────────────────────

# Table names (lowercased) whose upstream list always includes the mock
# transaction node — matched against root_data["table_name"] at runtime.
MOCK_TRIGGER_TABLE_NAMES = {"all_booking", "booking_agent"}

# Sentinel ID prevents the mock node from being duplicated in visited sets.
MOCK_TRANSACTION_ID = "b12f9e3a-7c44-4c91-9f12-3c8c9c2a1111"

# The full mock transaction upstream node (sourced from error.json)
MOCK_TRANSACTION_NODE = VisualNode(
    id=MOCK_TRANSACTION_ID,
    table_name="transaction",
    full_name="operational-data-store.transaction",
    schema_name="operational-data-store",
    database_name=None,
    type="table",
    status="unhealthy",
    source=SourceInfo(
        id="36ddfa2f-c9bf-4e9f-bdfb-69189f786606",
        name="run-test-athena",
        source_type="athena",
    ),
    columns=[
        ColumnInfo(id="col-001", name="transactionid",     data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})",  is_primary_key=True,  is_foreign_key=False, is_nullable=False, query_expression=None),
        ColumnInfo(id="col-002", name="bookingid",         data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})",  is_primary_key=False, is_foreign_key=True,  is_nullable=True,  query_expression=None),
        ColumnInfo(id="col-003", name="agentid",           data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})",  is_primary_key=False, is_foreign_key=True,  is_nullable=True,  query_expression=None),
        ColumnInfo(id="col-004", name="transactionamount", data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True,  query_expression=None),
        ColumnInfo(id="col-005", name="address",           data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True,  query_expression=None),
        ColumnInfo(id="col-006", name="transactiontype",   data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True,  query_expression=None),
        ColumnInfo(id="col-007", name="transactionstatus", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True,  query_expression=None),
        ColumnInfo(id="col-008", name="paymentmethod",     data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True,  query_expression=None),
        ColumnInfo(id="col-009", name="transactiondate",   data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True,  query_expression=None),
        ColumnInfo(id="col-010", name="journaltime",       data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True,  query_expression=None),
        ColumnInfo(id="col-011", name="operationtype",     data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True,  query_expression=None),
        ColumnInfo(id="col-012", name="load_type",         data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True,  query_expression=None),
        ColumnInfo(id="col-013", name="filename",          data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True,  query_expression=None),
        ColumnInfo(id="col-014", name="ingestionsequence", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True,  query_expression=None),
        ColumnInfo(id="col-015", name="createdutc",        data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True,  query_expression=None),
        ColumnInfo(id="col-016", name="modifiedutc",       data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True,  query_expression=None),
    ],
    tags=[
        TagInfo(id="tag-001", name="Financial", color="#FF9800", tag_type="classification"),
    ],
    lineage_id="r9b7tb7e-bn86-4388-bd89-3324caa06866",
    transformation_query=(
        "CREATE TABLE booking_transaction\n"
        "COMMENT 'Derived from: booking, transaction tables'\n"
        "WITH (\n"
        "  format = 'PARQUET',\n"
        "  external_location = 's3://infinity-gov-test/data/data-lineage/booking_transaction/'\n"
        ") AS\n"
        "SELECT\n"
        "    b.bookingid,\n"
        "    b.bookingtype,\n"
        "    b.bookingutc,\n"
        "    b.currencycode,\n\n"
        "    t.transactionid,\n"
        "    t.transactionamount,\n"
        "    t.transactiontype,\n"
        "    t.transactionstatus,\n"
        "    t.paymentmethod,\n"
        "    t.transactiondate\n\n"
        "FROM booking b\n"
        "LEFT JOIN transaction t\n"
        "    ON b.bookingid = t.bookingid"
    ),
    query_execution=QueryExecutionInfo(
        query_execution_id="g3b7tb7s-bn90-5378-bd89-3324caa89071",
        query_start_time="2026-03-19T05:00:00.000000+00:00",
        query_end_time="2026-03-19T05:00:01.200000+00:00",
        query_runtime_ms=1200,
        data_scanned_bytes=45200,
        query_status="FAILURE",
        engine_version="Athena engine version 3",
        s3_output_location="s3://athena-query-results-tmp-123/transaction/",
    ),
    column_mappings=[],
    depth=1,
    ai_summary=(
        "The operational-data-store.transaction dataset captures financial transaction "
        "details associated with bookings and agents, enabling analysis of payment flows, "
        "transaction status, and revenue tracking within the operational data pipeline."
    ),
    stats="Columns: 16 | Rows: 0",
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _fetch_catalog_node(db, catalog_id: str) -> Optional[Dict]:
    """Return full catalog row joined with data_sources."""
    row = await db.fetch_one(
        """
        SELECT
            c.id, c.table_name, c.full_name, c.schema_name, c.database_name,
            c.type, c.status, c.row_count,
            ds.id   AS source_id,
            ds.name AS source_name,
            ds.source_type
        FROM catalogs c
        LEFT JOIN data_sources ds ON ds.id = c.source_id
        WHERE c.id = $1
        """,
        catalog_id,
    )
    return dict(row) if row else None


async def _fetch_columns(db, catalog_id: str) -> List[ColumnInfo]:
    rows = await db.fetch_all(
        """
        SELECT
            col.id,
            col.name,
            col.data_type,
            col.is_primary_key,
            col.is_foreign_key,
            col.is_nullable,
            cq.query_expression
        FROM columns col
        LEFT JOIN column_queries cq
            ON  (
                    cq.column_id  = col.id
                OR  (
                        cq.column_id IS NULL
                    AND LOWER(cq.column_name) = LOWER(col.name)
                    AND LOWER(cq.table_name)  = LOWER(
                            (SELECT table_name FROM catalogs WHERE id = col.catalog_id)
                        )
                )
            )
        WHERE col.catalog_id = $1
        ORDER BY col.ordinal_position NULLS LAST, col.name
        """,
        catalog_id,
    )
    return [
        ColumnInfo(
            id=str(r["id"]),
            name=r["name"],
            data_type=r.get("data_type"),
            is_primary_key=bool(r.get("is_primary_key")),
            is_foreign_key=bool(r.get("is_foreign_key")),
            is_nullable=bool(r.get("is_nullable", True)),
            query_expression=r.get("query_expression"),
        )
        for r in rows
    ]


async def _fetch_tags(db, catalog_id: str) -> List[TagInfo]:
    rows = await db.fetch_all(
        """
        SELECT t.id, t.name, t.color, t.tag_type
        FROM   tags t
        JOIN   tag_catalog_assignments tca ON tca.tag_id = t.id
        WHERE  tca.catalog_id = $1
        """,
        catalog_id,
    )
    return [
        TagInfo(
            id=str(r["id"]),
            name=r["name"],
            color=r.get("color"),
            tag_type=r.get("tag_type"),
        )
        for r in rows
    ]


async def _fetch_col_mappings(db, lineage_id: str) -> List[ColumnMapping]:
    rows = await db.fetch_all(
        """
        SELECT
            lcm.upstream_column_id,   uc.name AS upstream_column_name,
            lcm.downstream_column_id, dc.name AS downstream_column_name
        FROM   lineage_column_mappings lcm
        LEFT JOIN columns uc ON uc.id = lcm.upstream_column_id
        LEFT JOIN columns dc ON dc.id = lcm.downstream_column_id
        WHERE  lcm.lineage_id = $1
        """,
        lineage_id,
    )
    return [
        ColumnMapping(
            upstream_column_id=str(r["upstream_column_id"]),
            upstream_column_name=r.get("upstream_column_name"),
            downstream_column_id=str(r["downstream_column_id"]),
            downstream_column_name=r.get("downstream_column_name"),
        )
        for r in rows
    ]


def _build_query_execution_info(row: Dict) -> Optional[QueryExecutionInfo]:
    fields = {
        "query_execution_id": row.get("query_execution_id"),
        "query_start_time": (
            row["query_start_time"].isoformat()
            if row.get("query_start_time") else None
        ),
        "query_end_time": (
            row["query_end_time"].isoformat()
            if row.get("query_end_time") else None
        ),
        "query_runtime_ms": row.get("query_runtime_ms"),
        "data_scanned_bytes": row.get("data_scanned_bytes"),
        "query_status": row.get("query_status"),
        "engine_version": row.get("engine_version"),
        "s3_output_location": row.get("s3_output_location"),
    }
    if all(v is None for v in fields.values()):
        return None
    return QueryExecutionInfo(**fields)


async def _generate_ai_summary(
    llm, node: Dict, upstream: List[str], downstream: List[str]
) -> str:
    columns = ", ".join([c["name"] for c in node.get("columns", [])[:10]])
    upstream_str   = ", ".join(upstream)   if upstream   else "None"
    downstream_str = ", ".join(downstream) if downstream else "None"

    prompt = f"""
You are a senior data platform architect.

Describe the role of this dataset in the data pipeline.

Dataset:
{node.get("full_name")}

Key Columns:
{columns}

Upstream Tables:
{upstream_str}

Downstream Tables:
{downstream_str}

Explain:
- what the dataset represents
- where its data originates
- how downstream datasets use it
- its role in the pipeline

Respond in only one concise sentence.
Note:
-- Provide a Short Summary do not exceed 50 words. Be concise and professional.
-- The response should be in a short paragraph format, suitable for display in a data catalog entry.
   Avoid technical jargon and focus on key insights about the dataset's content and relevance.
"""
    result = await llm.ainvoke(prompt)
    return result.content


async def _build_visual_node(
    db,
    llm,
    catalog_id: str,
    lineage_row: Optional[Dict],
    depth: int,
) -> Optional["VisualNode"]:
    data = await _fetch_catalog_node(db, catalog_id)
    if not data:
        return None

    lineage_id           = str(lineage_row["id"])             if lineage_row else None
    transformation_query = lineage_row.get("transformation_query") if lineage_row else None
    query_execution      = _build_query_execution_info(lineage_row) if lineage_row else None

    columns      = await _fetch_columns(db, catalog_id)
    tags         = await _fetch_tags(db, catalog_id)
    col_mappings = await _fetch_col_mappings(db, lineage_id) if lineage_id else []
    column_count = len(columns)
    row_count    = data.get("row_count")
    row_count_str = f"{row_count:,}" if row_count is not None else "N/A"
    status_text  = f"Columns: {column_count} | Rows: {row_count_str}"

    upstream_tables   = []
    downstream_tables = []
    if lineage_id and transformation_query:
        upstream_tables.append("upstream dependency")
        downstream_tables.append("downstream dependency")

    ai_summary = await _generate_ai_summary(
        llm,
        {
            "full_name": data.get("full_name"),
            "columns": [c.dict() for c in columns],
        },
        upstream=upstream_tables,
        downstream=downstream_tables,
    )

    source = None
    if data.get("source_id"):
        source = SourceInfo(
            id=str(data["source_id"]),
            name=data["source_name"] or "",
            source_type=data["source_type"] or "",
        )

    return VisualNode(
        id=str(data["id"]),
        table_name=data["table_name"],
        full_name=data.get("full_name"),
        schema_name=data.get("schema_name"),
        database_name=data.get("database_name"),
        type=data.get("type", "table"),
        status=data.get("status", "healthy"),
        source=source,
        columns=columns,
        tags=tags,
        lineage_id=lineage_id,
        transformation_query=transformation_query,
        query_execution=query_execution,
        column_mappings=col_mappings,
        depth=depth,
        ai_summary=ai_summary,
        stats=status_text,
    )


async def _traverse(
    db,
    catalog_id: str,
    direction: str,
    max_depth: int,
    current_depth: int,
    visited: set,
    root_table_name: str = "",
) -> List[VisualNode]:
    """
    BFS/DFS returning a flat, depth-ordered list of VisualNode objects.

    Mock injection rule:
      When direction == 'upstream', current_depth == 1, and root_table_name
      (lowercased) is in MOCK_TRIGGER_TABLE_NAMES, the mock transaction node
      is prepended to the upstream list before any DB-sourced nodes.
      The sentinel MOCK_TRANSACTION_ID is added to `visited` immediately so
      it is never injected a second time within the same traversal.
    """
    if current_depth > max_depth:
        return []

    results: List[VisualNode] = []

    # ── Inject mock transaction node at depth-1 for trigger tables ───────────
    if (
        direction == "upstream"
        and current_depth == 1
        and root_table_name.lower() in MOCK_TRIGGER_TABLE_NAMES
        and MOCK_TRANSACTION_ID not in visited
    ):
        visited.add(MOCK_TRANSACTION_ID)
        mock = MOCK_TRANSACTION_NODE.copy(deep=True)
        mock.depth = current_depth
        results.append(mock)
        # The mock node has no real DB children — no deeper traversal for it.

    # ── Normal DB traversal ──────────────────────────────────────────────────
    if direction == "downstream":
        rows = await db.fetch_all(
            """
            SELECT
                id,
                downstream_catalog_id      AS next_id,
                transformation_query,
                query_execution_id,
                query_start_time,
                query_end_time,
                query_runtime_ms,
                data_scanned_bytes,
                query_status,
                engine_version,
                s3_output_location
            FROM   table_lineage
            WHERE  upstream_catalog_id = $1 AND is_active = TRUE
            """,
            catalog_id,
        )
    else:
        rows = await db.fetch_all(
            """
            SELECT
                id,
                upstream_catalog_id        AS next_id,
                transformation_query,
                query_execution_id,
                query_start_time,
                query_end_time,
                query_runtime_ms,
                data_scanned_bytes,
                query_status,
                engine_version,
                s3_output_location
            FROM   table_lineage
            WHERE  downstream_catalog_id = $1 AND is_active = TRUE
            """,
            catalog_id,
        )

    for row in rows:
        row_dict = dict(row)
        next_id  = str(row_dict["next_id"])
        if next_id in visited:
            continue
        visited.add(next_id)

        node = await _build_visual_node(
            db,
            llm,
            catalog_id=next_id,
            lineage_row=row_dict,
            depth=current_depth,
        )
        if node:
            results.append(node)
            deeper = await _traverse(
                db,
                next_id,
                direction,
                max_depth,
                current_depth + 1,
                visited,
                root_table_name=root_table_name,
            )
            results.extend(deeper)

    return results


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.get(
    "/api/v1/lineage-visual/{catalog_id}",
    response_model=VisualLineageResponse,
    summary="Visual lineage graph for a table",
    description=(
        "Returns the root table with its columns (including any derived "
        "query_expression from column_queries), source info, and tags, "
        "plus flat lists of upstream and downstream nodes. "
        "Each non-root node includes a `query_execution` block sourced from "
        "the table_lineage edge. "
        "Use `depth` (1–6, default 2) to control traversal depth and "
        "`direction` (upstream | downstream | both) to limit the graph."
    ),
)
async def get_visual_lineage(
    catalog_id: str,
    depth:     int = Query(2, ge=1, le=6, description="Traversal depth (1-6), default 2"),
    direction: str = Query("both", enum=["upstream", "downstream", "both"]),
):
    from app import db, logger
    try:
        # ── validate root exists ──────────────────────────────────────────────
        root_data = await _fetch_catalog_node(db, catalog_id)
        if not root_data:
            raise HTTPException(404, f"Catalog '{catalog_id}' not found")

        root_table_name = root_data.get("table_name", "")

        # ── build root node ───────────────────────────────────────────────────
        root_columns  = await _fetch_columns(db, catalog_id)
        root_tags     = await _fetch_tags(db, catalog_id)
        column_count  = len(root_columns)
        row_count     = root_data.get("row_count")
        row_count_str = f"{row_count:,}" if row_count is not None else "N/A"
        status_text   = f"Columns: {column_count} | Rows: {row_count_str}"

        root_source = None
        if root_data.get("source_id"):
            root_source = SourceInfo(
                id=str(root_data["source_id"]),
                name=root_data["source_name"] or "",
                source_type=root_data["source_type"] or "",
            )

        root_summary = await _generate_ai_summary(
            llm,
            {
                "full_name": root_data.get("full_name"),
                "columns": [c.dict() for c in root_columns],
            },
            upstream=[],
            downstream=[],
        )

        root_node = VisualNode(
            id=str(root_data["id"]),
            table_name=root_table_name,
            full_name=root_data.get("full_name"),
            schema_name=root_data.get("schema_name"),
            database_name=root_data.get("database_name"),
            type=root_data.get("type", "table"),
            status=root_data.get("status", "healthy"),
            source=root_source,
            columns=root_columns,
            tags=root_tags,
            depth=0,
            ai_summary=root_summary,
            stats=status_text,
        )

        # ── traverse upstreams ────────────────────────────────────────────────
        upstreams: List[VisualNode] = []
        if direction in ("upstream", "both"):
            visited_up = {catalog_id}
            upstreams = await _traverse(
                db, catalog_id, "upstream", depth, 1, visited_up,
                root_table_name=root_table_name,
            )

        # ── traverse downstreams ──────────────────────────────────────────────
        downstreams: List[VisualNode] = []
        if direction in ("downstream", "both"):
            visited_down = {catalog_id}
            downstreams = await _traverse(
                db, catalog_id, "downstream", depth, 1, visited_down,
                root_table_name=root_table_name,
            )

        return VisualLineageResponse(
            root=root_node,
            upstreams=upstreams,
            downstreams=downstreams,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_visual_lineage error: %s", e)
        raise HTTPException(500, str(e))