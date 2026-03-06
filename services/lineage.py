from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any, Set

from models import (
    LineageCreate,
    LineageUpdate,
    LineageEdgeOut,
    LineageGraphResponse,
    LineageNode,
    LineageEdge,
    ColumnMappingOut,
    TableRef,
)

router = APIRouter(tags=["lineage"])


async def _lineage_get_table_ref(db, catalog_id: str) -> Optional[Dict]:
    row = await db.fetch_one(
        "SELECT id, table_name, full_name, schema_name, database_name FROM catalogs WHERE id = $1",
        catalog_id,
    )
    if not row:
        return None
    return {
        "id":            str(row["id"]),
        "table_name":    row["table_name"],
        "full_name":     row.get("full_name"),
        "schema_name":   row.get("schema_name"),
        "database_name": row.get("database_name"),
    }


async def _lineage_get_col_maps(db, lineage_id: str) -> List[ColumnMappingOut]:
    rows = await db.fetch_all(
        """
        SELECT lcm.id, lcm.lineage_id,
               lcm.upstream_column_id,    uc.name AS upstream_column_name,
               lcm.downstream_column_id,  dc.name AS downstream_column_name,
               lcm.created_at
        FROM   lineage_column_mappings lcm
        LEFT JOIN columns uc ON uc.id = lcm.upstream_column_id
        LEFT JOIN columns dc ON dc.id = lcm.downstream_column_id
        WHERE  lcm.lineage_id = $1
        """,
        lineage_id,
    )
    return [
        ColumnMappingOut(
            id=str(r["id"]),
            lineage_id=str(r["lineage_id"]),
            upstream_column_id=str(r["upstream_column_id"]),
            upstream_column_name=r.get("upstream_column_name"),
            downstream_column_id=str(r["downstream_column_id"]),
            downstream_column_name=r.get("downstream_column_name"),
            created_at=r["created_at"],
        )
        for r in rows
    ]


async def _lineage_build_edge(db, row) -> LineageEdgeOut:
    upstream   = await _lineage_get_table_ref(db, str(row["upstream_catalog_id"]))
    downstream = await _lineage_get_table_ref(db, str(row["downstream_catalog_id"]))
    col_maps   = await _lineage_get_col_maps(db, str(row["id"]))

    owner_name = None
    if row.get("owner_id"):
        o = await db.fetch_one("SELECT name FROM owners WHERE id = $1", row["owner_id"])
        owner_name = o["name"] if o else None

    return LineageEdgeOut(
        id=str(row["id"]),
        upstream=TableRef(**upstream),
        downstream=TableRef(**downstream),
        transformation_query=row.get("transformation_query"),
        column_mappings=col_maps,
        owner_id=str(row["owner_id"]) if row.get("owner_id") else None,
        owner_name=owner_name,
        is_active=row["is_active"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def _lineage_traverse(
    db,
    catalog_id: str,
    direction: str,
    max_depth: int,
    depth: int,
    visited: set,
) -> Optional[LineageNode]:
    """
    Recursive DFS traversal.
      direction='downstream' → follow edges where upstream_catalog_id = catalog_id
      direction='upstream'   → follow edges where downstream_catalog_id = catalog_id
    """
    if depth > max_depth or catalog_id in visited:
        return None
    visited.add(catalog_id)

    table_ref = await _lineage_get_table_ref(db, catalog_id)
    if not table_ref:
        return None

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

    edges: List[LineageEdge] = []
    for row in rows:
        next_id = str(row["next_id"])
        child   = await _lineage_traverse(db, next_id, direction, max_depth, depth + 1, visited)

        # If already visited (cycle) or at max depth, show terminal node without further edges
        if child is None:
            ref = await _lineage_get_table_ref(db, next_id)
            if ref:
                child = LineageNode(depth=depth + 1, table=TableRef(**ref), edges=[])

        col_maps = await _lineage_get_col_maps(db, str(row["id"]))

        if child:
            edges.append(LineageEdge(
                lineage_id=str(row["id"]),
                transformation_query=row.get("transformation_query"),
                column_mappings=col_maps,
                connected_node=child,
            ))

    return LineageNode(depth=depth, table=TableRef(**table_ref), edges=edges)


async def _lineage_validate_col_belongs(db, column_id: str, catalog_id: str, label: str):
    """Raise 400/404 if a column doesn't belong to the expected catalog."""
    col = await db.fetch_one("SELECT catalog_id FROM columns WHERE id = $1", column_id)
    if not col:
        raise HTTPException(404, f"{label} column '{column_id}' not found")
    if str(col["catalog_id"]) != catalog_id:
        raise HTTPException(400, f"{label} column '{column_id}' does not belong to the specified table")


# ─────────────────────────────────────────────────────────────────────────────
# 1.  CREATE LINEAGE
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/api/v1/lineage-create",
    response_model=LineageEdgeOut,
    summary="Create a lineage relationship between two tables",
    description=(
        "Provide the upstream (source) catalog ID, downstream (target) catalog ID, "
        "column-level mappings, the transformation SQL/logic, and an optional owner_id."
    ),
)
async def add_lineage(payload: LineageCreate):
    from app import db, logger
    try:
        # ── validate both tables ──────────────────────────────────────────────
        if not await db.fetch_one("SELECT 1 FROM catalogs WHERE id = $1", payload.upstream_catalog_id):
            raise HTTPException(404, f"Upstream catalog '{payload.upstream_catalog_id}' not found")
        if not await db.fetch_one("SELECT 1 FROM catalogs WHERE id = $1", payload.downstream_catalog_id):
            raise HTTPException(404, f"Downstream catalog '{payload.downstream_catalog_id}' not found")
        if payload.upstream_catalog_id == payload.downstream_catalog_id:
            raise HTTPException(400, "upstream_catalog_id and downstream_catalog_id must be different tables")
        if payload.owner_id and not await db.fetch_one("SELECT 1 FROM owners WHERE id = $1", payload.owner_id):
            raise HTTPException(404, f"Owner '{payload.owner_id}' not found")

        # ── upsert lineage edge ───────────────────────────────────────────────
        row = await db.fetch_one(
            """
            INSERT INTO table_lineage
                (upstream_catalog_id, downstream_catalog_id, transformation_query, owner_id)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (upstream_catalog_id, downstream_catalog_id)
                DO UPDATE SET
                    transformation_query = EXCLUDED.transformation_query,
                    owner_id             = EXCLUDED.owner_id,
                    is_active            = TRUE,
                    updated_at           = NOW()
            RETURNING *
            """,
            payload.upstream_catalog_id,
            payload.downstream_catalog_id,
            payload.transformation_query,
            payload.owner_id,
        )
        lineage_id = str(row["id"])

        # ── validate & insert column mappings ─────────────────────────────────
        for cm in payload.column_mappings:
            await _lineage_validate_col_belongs(db, cm.upstream_column_id,   payload.upstream_catalog_id,   "Upstream")
            await _lineage_validate_col_belongs(db, cm.downstream_column_id, payload.downstream_catalog_id, "Downstream")
            await db.execute(
                """
                INSERT INTO lineage_column_mappings
                    (lineage_id, upstream_column_id, downstream_column_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (lineage_id, upstream_column_id, downstream_column_id) DO NOTHING
                """,
                lineage_id,
                cm.upstream_column_id,
                cm.downstream_column_id,
            )

        return await _lineage_build_edge(db, row)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("add_lineage error: %s", e)
        raise HTTPException(500, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 2.  GET LINEAGE GRAPH
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/api/v1/lineage/{catalog_id}",
    response_model=LineageGraphResponse,
    summary="Get lineage graph for a table (up to depth 6)",
    description=(
        "Returns a recursive lineage graph rooted at the given catalog. "
        "direction: 'upstream' (what feeds this table), 'downstream' (what this table feeds), "
        "or 'both'. max_depth capped at 6. Pass owner_id to annotate ownership in the response."
    ),
)
async def get_lineage(
    catalog_id: str,
    direction:  str = Query("both", enum=["upstream", "downstream", "both"]),
    max_depth:  int = Query(6, ge=1, le=6, description="Traversal depth limit (1-6)"),
    owner_id:   Optional[str] = Query(None, description="Owner ID to attach to the response"),
):
    from app import db, logger
    try:
        if not await db.fetch_one("SELECT 1 FROM catalogs WHERE id = $1", catalog_id):
            raise HTTPException(404, f"Catalog '{catalog_id}' not found")

        table_ref  = await _lineage_get_table_ref(db, catalog_id)
        owner_name = None
        if owner_id:
            o = await db.fetch_one("SELECT name FROM owners WHERE id = $1", owner_id)
            if not o:
                raise HTTPException(404, f"Owner '{owner_id}' not found")
            owner_name = o["name"]

        nodes: List[LineageNode] = []

        if direction in ("downstream", "both"):
            node = await _lineage_traverse(db, catalog_id, "downstream", max_depth, 0, set())
            if node:
                nodes.append(node)

        if direction in ("upstream", "both"):
            node = await _lineage_traverse(db, catalog_id, "upstream", max_depth, 0, set())
            if node:
                nodes.append(node)

        return LineageGraphResponse(
            root_table=TableRef(**table_ref),
            direction=direction,
            max_depth=max_depth,
            owner_id=owner_id,
            owner_name=owner_name,
            nodes=nodes,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_lineage error: %s", e)
        raise HTTPException(500, str(e))


@router.get(
    "/api/v1/lineage-list/{catalog_id}/edges",
    response_model=List[LineageEdgeOut],
    summary="List direct (1-hop) lineage edges for a table",
    description=(
        "Returns only the immediate upstream or downstream neighbours. "
        "Use this to populate the 'which tables to connect' UI picker."
    ),
)
async def list_lineage_edges(
    catalog_id: str,
    direction:  str = Query("both", enum=["upstream", "downstream", "both"]),
    owner_id:   Optional[str] = Query(None),
):
    from app import db
    try:
        if not await db.fetch_one("SELECT 1 FROM catalogs WHERE id = $1", catalog_id):
            raise HTTPException(404, f"Catalog '{catalog_id}' not found")

        params: list = [catalog_id]
        if direction == "downstream":
            where = "tl.upstream_catalog_id = $1"
        elif direction == "upstream":
            where = "tl.downstream_catalog_id = $1"
        else:
            where = "(tl.upstream_catalog_id = $1 OR tl.downstream_catalog_id = $1)"

        if owner_id:
            params.append(owner_id)
            where += f" AND tl.owner_id = ${len(params)}"

        rows = await db.fetch_all(
            f"SELECT * FROM table_lineage tl WHERE {where} AND tl.is_active = TRUE ORDER BY tl.created_at DESC",
            *params,
        )
        return [await _lineage_build_edge(db, r) for r in rows]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 3.  UPDATE LINEAGE
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/api/v1/lineage-update/{lineage_id}",
    response_model=LineageEdgeOut,
    summary="Update a lineage relationship",
    description=(
        "Update transformation_query, owner, active status, or column mappings. "
        "Providing column_mappings REPLACES all existing mappings for this edge."
    ),
)
async def update_lineage(lineage_id: str, payload: LineageUpdate):
    from app import db, logger
    try:
        row = await db.fetch_one("SELECT * FROM table_lineage WHERE id = $1", lineage_id)
        if not row:
            raise HTTPException(404, "Lineage edge not found")

        # ── build SET clauses dynamically ─────────────────────────────────────
        updates: Dict[str, Any] = {}
        if payload.transformation_query is not None:
            updates["transformation_query"] = payload.transformation_query
        if payload.is_active is not None:
            updates["is_active"] = payload.is_active
        if payload.owner_id is not None:
            if not await db.fetch_one("SELECT 1 FROM owners WHERE id = $1", payload.owner_id):
                raise HTTPException(404, f"Owner '{payload.owner_id}' not found")
            updates["owner_id"] = payload.owner_id

        if updates:
            set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates.keys())]
            await db.execute(
                f"UPDATE table_lineage SET {', '.join(set_parts)}, updated_at = NOW() WHERE id = $1",
                lineage_id, *list(updates.values()),
            )

        # ── replace column mappings if provided ───────────────────────────────
        if payload.column_mappings is not None:
            await db.execute("DELETE FROM lineage_column_mappings WHERE lineage_id = $1", lineage_id)
            up_id   = str(row["upstream_catalog_id"])
            down_id = str(row["downstream_catalog_id"])
            for cm in payload.column_mappings:
                await _lineage_validate_col_belongs(db, cm.upstream_column_id,   up_id,   "Upstream")
                await _lineage_validate_col_belongs(db, cm.downstream_column_id, down_id, "Downstream")
                await db.execute(
                    """
                    INSERT INTO lineage_column_mappings
                        (lineage_id, upstream_column_id, downstream_column_id)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (lineage_id, upstream_column_id, downstream_column_id) DO NOTHING
                    """,
                    lineage_id,
                    cm.upstream_column_id,
                    cm.downstream_column_id,
                )

        updated = await db.fetch_one("SELECT * FROM table_lineage WHERE id = $1", lineage_id)
        return await _lineage_build_edge(db, updated)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_lineage error: %s", e)
        raise HTTPException(500, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 4.  REMOVE LINEAGE
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/api/v1/lineage-delete/{lineage_id}",
    status_code=204,
    summary="Delete a lineage relationship",
    description=(
        "Hard-deletes the edge and all column mappings (cascade) by default. "
        "Pass ?soft=true to set is_active=false and preserve audit history."
    ),
)
async def remove_lineage(
    lineage_id: str,
    soft: bool = Query(False, description="Soft-delete: set is_active=false instead of hard delete"),
):
    from app import db, logger
    try:
        if not await db.fetch_one("SELECT 1 FROM table_lineage WHERE id = $1", lineage_id):
            raise HTTPException(404, "Lineage edge not found")

        if soft:
            await db.execute(
                "UPDATE table_lineage SET is_active = FALSE, updated_at = NOW() WHERE id = $1",
                lineage_id,
            )
        else:
            # lineage_column_mappings cascade-deletes via FK
            await db.execute("DELETE FROM table_lineage WHERE id = $1", lineage_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("remove_lineage error: %s", e)
        raise HTTPException(500, str(e))
