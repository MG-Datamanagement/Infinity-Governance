from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from langchain_openai import AzureChatOpenAI
import os
router = APIRouter(tags=["lineage"])



class ColumnInfo(BaseModel):
    id: str
    name: str
    data_type: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    is_nullable: bool = True
 
 
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
 
 
class VisualNode(BaseModel):
    """One catalog card in the visual graph."""
    id: str
    table_name: str
    full_name: Optional[str] = None
    schema_name: Optional[str] = None
    database_name: Optional[str] = None
    type: Optional[str] = "table"          # table | view
    status: Optional[str] = "healthy"
    source: Optional[SourceInfo] = None
    columns: List[ColumnInfo] = []
    tags: List[TagInfo] = []
    # edge back to the root (or next hop)
    lineage_id: Optional[str] = None
    transformation_query: Optional[str] = None
    column_mappings: List[ColumnMapping] = []
    depth: int = 1
    ai_summary: Optional[str] = None
    stats: Optional[str] = None
 
class VisualLineageResponse(BaseModel):
    root: VisualNode
    upstreams: List[VisualNode] = []      # flattened, depth-ordered
    downstreams: List[VisualNode] = []
 

#---------------llm-------------
llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    temperature=0.2
)

# ─── Helpers ─────────────────────────────────────────────────────────────────
 
async def _fetch_catalog_node(db, catalog_id: str) -> Optional[Dict]:
    """Return full catalog row joined with data_sources."""
    row = await db.fetch_one(
        """
        SELECT
            c.id, c.table_name, c.full_name, c.schema_name, c.database_name,
            c.type, c.status,
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
        SELECT id, name, data_type, is_primary_key, is_foreign_key, is_nullable
        FROM   columns
        WHERE  catalog_id = $1
        ORDER  BY ordinal_position NULLS LAST, name
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
        TagInfo(id=str(r["id"]), name=r["name"], color=r.get("color"), tag_type=r.get("tag_type"))
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
 
async def _generate_ai_summary(llm, node: Dict, upstream: List[str], downstream: List[str]) -> str:

    columns = ", ".join([c["name"] for c in node.get("columns", [])[:10]])

    upstream_str = ", ".join(upstream) if upstream else "None"
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

    Respond in only one concise sentences.
    Note:
    -- Provide a Short Summary do not exceed 50 words. Be concise and professional.
    -- The response should be in a short paragraph format, suitable for display in a data catalog entry. Avoid technical jargon and focus on key insights about the dataset's content and relevance.
    """
    result = await llm.ainvoke(prompt)

    return result.content

async def _build_visual_node(
    db,
    llm,
    catalog_id: str,
    lineage_id: Optional[str],
    transformation_query: Optional[str],
    depth: int,
) -> Optional[VisualNode]:
    data = await _fetch_catalog_node(db, catalog_id)
    if not data:
        return None
 
    columns      = await _fetch_columns(db, catalog_id)
    tags         = await _fetch_tags(db, catalog_id)
    col_mappings = await _fetch_col_mappings(db, lineage_id) if lineage_id else []
    column_count = len(columns)
    status_text = f"Column {column_count}"
    # determine lineage direction context

    upstream_tables = []
    downstream_tables = []

    if lineage_id and transformation_query:
        upstream_tables.append("upstream dependency")
        downstream_tables.append("downstream dependency")

    ai_summary = await _generate_ai_summary(
        llm,
        {
            "full_name": data.get("full_name"),
            "columns": [c.dict() for c in columns]
        },
        upstream=upstream_tables,
        downstream=downstream_tables
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
        lineage_id=str(lineage_id) if lineage_id else None,
        transformation_query=transformation_query,
        column_mappings=col_mappings,
        depth=depth,
        ai_summary=ai_summary,
        stats=status_text,
    )
 
 
async def _traverse(
    db,
    catalog_id: str,
    direction: str,        # "upstream" | "downstream"
    max_depth: int,
    current_depth: int,
    visited: set,
) -> List[VisualNode]:
    """
    BFS/DFS that returns a flat list of VisualNode objects, depth-ordered.
    direction="downstream": follow edges where upstream_catalog_id = catalog_id
    direction="upstream":   follow edges where downstream_catalog_id = catalog_id
    """
    if current_depth > max_depth:
        return []
 
    results: List[VisualNode] = []
 
    if direction == "downstream":
        rows = await db.fetch_all(
            """
            SELECT id, downstream_catalog_id AS next_id, transformation_query
            FROM   table_lineage
            WHERE  upstream_catalog_id = $1 AND is_active = TRUE
            """,
            catalog_id,
        )
    else:
        rows = await db.fetch_all(
            """
            SELECT id, upstream_catalog_id AS next_id, transformation_query
            FROM   table_lineage
            WHERE  downstream_catalog_id = $1 AND is_active = TRUE
            """,
            catalog_id,
        )
 
    for row in rows:
        next_id = str(row["next_id"])
        if next_id in visited:
            continue
        visited.add(next_id)
 
        node = await _build_visual_node(
            db,
            llm,
            catalog_id=next_id,
            lineage_id=str(row["id"]),
            transformation_query=row.get("transformation_query"),
            depth=current_depth,
        )
        if node:
            results.append(node)
            # recurse
            deeper = await _traverse(db, next_id, direction, max_depth, current_depth + 1, visited)
            results.extend(deeper)
 
    return results
 
 
# ─── Endpoint ────────────────────────────────────────────────────────────────
 
@router.get(
    "/api/v1/lineage-visual/{catalog_id}",
    response_model=VisualLineageResponse,
    summary="Visual lineage graph for a table",
    description=(
        "Returns the root table with its columns, source info, and tags, "
        "plus flat lists of upstream and downstream nodes (each with column "
        "mappings, source info, and tags). "
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
 
        # ── build root node (no lineage_id – it is the root) ─────────────────
        root_columns = await _fetch_columns(db, catalog_id)
        root_tags    = await _fetch_tags(db, catalog_id)
        column_count = len(root_columns)
        status_text = f"Column {column_count}"
        root_source = None
        if root_data.get("source_id"):
            root_source = SourceInfo(
                id=str(root_data["source_id"]),
                name=root_data["source_name"] or "",
                source_type=root_data["source_type"] or "",
            )
 
        # Generate AI summary for root

        root_summary = await _generate_ai_summary(
            llm,
            {
                "full_name": root_data.get("full_name"),
                "columns": [c.dict() for c in root_columns]
            },
            upstream=[],
            downstream=[]
        )

        root_node = VisualNode(
            id=str(root_data["id"]),
            table_name=root_data["table_name"],
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
            stats=status_text
        )
 
        # ── traverse upstreams ────────────────────────────────────────────────
        upstreams: List[VisualNode] = []
        if direction in ("upstream", "both"):
            visited_up = {catalog_id}
            upstreams = await _traverse(db, catalog_id, "upstream", depth, 1, visited_up)
 
        # ── traverse downstreams ──────────────────────────────────────────────
        downstreams: List[VisualNode] = []
        if direction in ("downstream", "both"):
            visited_down = {catalog_id}
            downstreams = await _traverse(db, catalog_id, "downstream", depth, 1, visited_down)
 
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