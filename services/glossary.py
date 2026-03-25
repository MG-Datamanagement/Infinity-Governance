from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict

from models import (
    GlossaryGroupCreate,
    GlossaryGroupUpdate,
    GlossaryGroupResponse,
    GlossaryGroupNode,
    GlossaryTermCreate,
    GlossaryTermUpdate,
    GlossaryTermResponse,
    GlossaryTermAssignRequest,
)

router = APIRouter(tags=["glossary-groups"])


# ── GROUPS ───────────────────────────────────────────────────────────────────
@router.post("/api/v1/glossary/groups-create", response_model=GlossaryGroupResponse, status_code=201)
async def create_glossary_group(payload: GlossaryGroupCreate):
    from app import db, logger
    try:
        if payload.owner_id:
            if not await db.fetch_one("SELECT id FROM owners WHERE id = $1", payload.owner_id):
                raise HTTPException(400, f"Owner '{payload.owner_id}' not found")
        if payload.parent_group_id:
            if not await db.fetch_one("SELECT id FROM glossary_groups WHERE id = $1", payload.parent_group_id):
                raise HTTPException(400, f"Parent group '{payload.parent_group_id}' not found")
        row = await db.fetch_one(
            """
            INSERT INTO glossary_groups (name, description, owner_id, parent_group_id)
            VALUES ($1, $2, $3, $4) RETURNING id
            """, payload.name, payload.description, payload.owner_id, payload.parent_group_id)
        return await _get_glossary_group(str(row["id"]))
    except HTTPException:
        raise
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(409, "A group with this name already exists at this level")
        raise HTTPException(500, str(e))


@router.get("/api/v1/glossary/groups-list", response_model=List[GlossaryGroupResponse])
async def list_glossary_groups(
    parent_group_id: Optional[str] = Query(None, description="Filter by parent. Omit for top-level only."),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    from app import db, logger
    try:
        conditions = ["1=1"]
        params: list = []
        idx = 1
        if parent_group_id:
            conditions.append(f"g.parent_group_id = ${idx}")
            params.append(parent_group_id); idx += 1
        elif search is None:
            conditions.append("g.parent_group_id IS NULL")
        if search:
            conditions.append(f"g.name ILIKE ${idx}")
            params.append(f"%{search}%"); idx += 1
        params += [limit, skip]
        rows = await db.fetch_all(f"""
            SELECT g.id, g.name, g.description, g.owner_id, g.parent_group_id,
                   g.created_at, g.updated_at,
                   o.name  AS owner_name,
                   pg.name AS parent_group_name,
                   (SELECT COUNT(*) FROM glossary_groups c WHERE c.parent_group_id = g.id) AS child_group_count,
                   (SELECT COUNT(*) FROM glossary_terms  t WHERE t.parent_group_id  = g.id) AS child_term_count
            FROM glossary_groups g
            LEFT JOIN owners          o  ON g.owner_id        = o.id
            LEFT JOIN glossary_groups pg ON g.parent_group_id = pg.id
            WHERE {' AND '.join(conditions)}
            ORDER BY g.name
            LIMIT ${idx} OFFSET ${idx + 1}
        """, *params)
        return [_map_group(r) for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/api/v1/glossary/groups/listall", response_model=List[GlossaryGroupNode])
async def list_glossary_groups_tree():
    from app import db, logger
    try:
        all_groups = await db.fetch_all("""
            SELECT g.id, g.name, g.description, g.owner_id, g.parent_group_id,
                   o.name AS owner_name
            FROM glossary_groups g
            LEFT JOIN owners o ON g.owner_id = o.id
            ORDER BY g.name
        """)
        all_terms = await db.fetch_all("""
            SELECT t.id, t.name, t.description, t.owner_id, t.parent_group_id,
                   t.created_at, t.updated_at,
                   o.name AS owner_name, g.name AS parent_group_name
            FROM glossary_terms t
            LEFT JOIN owners          o ON t.owner_id        = o.id
            LEFT JOIN glossary_groups g ON t.parent_group_id = g.id
            ORDER BY t.name
        """)
        group_map = {str(r["id"]): {**dict(r), "child_groups": [], "terms": []} for r in all_groups}
        for term in all_terms:
            gid = str(term["parent_group_id"]) if term.get("parent_group_id") else None
            if gid and gid in group_map:
                group_map[gid]["terms"].append(_map_term(term))
        node_objects: dict = {}
        for gid, gdata in group_map.items():
            node_objects[gid] = GlossaryGroupNode(
                id=gid, name=gdata["name"], description=gdata.get("description"),
                owner_id=str(gdata["owner_id"]) if gdata.get("owner_id") else None,
                owner_name=gdata.get("owner_name"), terms=gdata["terms"],
            )
        roots = []
        for gid, gdata in group_map.items():
            parent = str(gdata["parent_group_id"]) if gdata.get("parent_group_id") else None
            if parent and parent in node_objects:
                node_objects[parent].child_groups.append(node_objects[gid])
            else:
                roots.append(node_objects[gid])
        return roots
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/api/v1/glossary/groups/{group_id}", response_model=GlossaryGroupResponse)
async def get_glossary_group_endpoint(group_id: str):
    from app import db, logger
    return await _get_glossary_group(group_id)


@router.put("/api/v1/glossary/group-update/{group_id}", response_model=GlossaryGroupResponse)
async def update_glossary_group(group_id: str, payload: GlossaryGroupUpdate):
    from app import db, logger
    try:
        if not await db.fetch_one("SELECT id FROM glossary_groups WHERE id = $1", group_id):
            raise HTTPException(404, "Glossary group not found")
        if payload.owner_id:
            if not await db.fetch_one("SELECT id FROM owners WHERE id = $1", payload.owner_id):
                raise HTTPException(400, f"Owner '{payload.owner_id}' not found")
        if payload.parent_group_id:
            if payload.parent_group_id == group_id:
                raise HTTPException(400, "A group cannot be its own parent")
            if not await db.fetch_one("SELECT id FROM glossary_groups WHERE id = $1", payload.parent_group_id):
                raise HTTPException(400, f"Parent group '{payload.parent_group_id}' not found")
        field_map = {"name": payload.name, "description": payload.description,
                     "owner_id": payload.owner_id, "parent_group_id": payload.parent_group_id}
        set_clauses, params = [], []
        for col, val in field_map.items():
            if val is not None:
                params.append(val); set_clauses.append(f"{col} = ${len(params)}")
        if set_clauses:
            params.append(group_id)
            await db.execute(
                f"UPDATE glossary_groups SET {', '.join(set_clauses)}, updated_at = NOW() WHERE id = ${len(params)}",
                *params)
        return await _get_glossary_group(group_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/api/v1/glossary/group-delete/{group_id}", status_code=204)
async def delete_glossary_group(group_id: str):
    from app import db, logger
    try:
        if not await db.fetch_one("SELECT 1 FROM glossary_groups WHERE id = $1", group_id):
            raise HTTPException(404, "Glossary group not found")
        await db.execute("DELETE FROM glossary_groups WHERE id = $1", group_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ── TERMS ─────────────────────────────────────────────────────────────────────

@router.post("/api/v1/glossary/terms-create", response_model=GlossaryTermResponse, status_code=201)
async def create_glossary_term(payload: GlossaryTermCreate):
    from app import db, logger
    try:
        if payload.owner_id:
            if not await db.fetch_one("SELECT id FROM owners WHERE id = $1", payload.owner_id):
                raise HTTPException(400, f"Owner '{payload.owner_id}' not found")
        if payload.parent_group_id:
            if not await db.fetch_one("SELECT id FROM glossary_groups WHERE id = $1", payload.parent_group_id):
                raise HTTPException(400, f"Glossary group '{payload.parent_group_id}' not found")
        row = await db.fetch_one("""
            INSERT INTO glossary_terms (name, description, owner_id, parent_group_id)
            VALUES ($1, $2, $3, $4) RETURNING id
        """, payload.name, payload.description, payload.owner_id, payload.parent_group_id)
        return await _get_glossary_term(str(row["id"]))
    except HTTPException:
        raise
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(409, "A term with this name already exists in this group")
        raise HTTPException(500, str(e))


@router.get("/api/v1/glossary/terms-list", response_model=List[GlossaryTermResponse])
async def list_glossary_terms(
    parent_group_id: Optional[str] = Query(None, description="Filter by glossary group ID"),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    from app import db, logger
    try:
        conditions = ["1=1"]
        params: list = []
        idx = 1
        if parent_group_id:
            conditions.append(f"t.parent_group_id = ${idx}")
            params.append(parent_group_id); idx += 1
        if search:
            conditions.append(f"t.name ILIKE ${idx}")
            params.append(f"%{search}%"); idx += 1
        params += [limit, skip]
        rows = await db.fetch_all(f"""
            SELECT t.id, t.name, t.description, t.owner_id, t.parent_group_id,
                   t.created_at, t.updated_at,
                   o.name AS owner_name, g.name AS parent_group_name
            FROM glossary_terms t
            LEFT JOIN owners          o ON t.owner_id        = o.id
            LEFT JOIN glossary_groups g ON t.parent_group_id = g.id
            WHERE {' AND '.join(conditions)}
            ORDER BY t.name
            LIMIT ${idx} OFFSET ${idx + 1}
        """, *params)
        return [_map_term(r) for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/api/v1/glossary/terms/{term_id}", response_model=GlossaryTermResponse)
async def get_glossary_term_endpoint(term_id: str):
    from app import db, logger
    return await _get_glossary_term(term_id)


@router.put("/api/v1/glossary/terms-update/{term_id}", response_model=GlossaryTermResponse)
async def update_glossary_term(term_id: str, payload: GlossaryTermUpdate):
    from app import db, logger
    try:
        if not await db.fetch_one("SELECT id FROM glossary_terms WHERE id = $1", term_id):
            raise HTTPException(404, "Glossary term not found")
        if payload.owner_id:
            if not await db.fetch_one("SELECT id FROM owners WHERE id = $1", payload.owner_id):
                raise HTTPException(400, f"Owner '{payload.owner_id}' not found")
        if payload.parent_group_id:
            if not await db.fetch_one("SELECT id FROM glossary_groups WHERE id = $1", payload.parent_group_id):
                raise HTTPException(400, f"Glossary group '{payload.parent_group_id}' not found")
        field_map = {"name": payload.name, "description": payload.description,
                     "owner_id": payload.owner_id, "parent_group_id": payload.parent_group_id}
        set_clauses, params = [], []
        for col, val in field_map.items():
            if val is not None:
                params.append(val); set_clauses.append(f"{col} = ${len(params)}")
        if set_clauses:
            params.append(term_id)
            await db.execute(
                f"UPDATE glossary_terms SET {', '.join(set_clauses)}, updated_at = NOW() WHERE id = ${len(params)}",
                *params)
        return await _get_glossary_term(term_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/api/v1/glossary/terms-delete/{term_id}", status_code=204)
async def delete_glossary_term(term_id: str):
    from app import db, logger
    try:
        if not await db.fetch_one("SELECT 1 FROM glossary_terms WHERE id = $1", term_id):
            raise HTTPException(404, "Glossary term not found")
        await db.execute("DELETE FROM glossary_terms WHERE id = $1", term_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ── ASSIGNMENTS ───────────────────────────────────────────────────────────────

@router.post("/glossary/terms/{term_id}/assign-catalogs")
async def assign_term_to_catalogs(term_id: str, payload: GlossaryTermAssignRequest):
    from app import db, logger
    try:
        term = await db.fetch_one("SELECT id, name FROM glossary_terms WHERE id = $1", term_id)
        if not term:
            raise HTTPException(404, "Glossary term not found")
        results = []
        for catalog_id in (payload.catalog_ids or []):
            if not await db.fetch_one("SELECT id FROM catalogs WHERE id = $1", catalog_id):
                results.append({"catalog_id": catalog_id, "status": "not_found"}); continue
            await db.execute("""
                INSERT INTO glossary_term_catalog_assignments (term_id, catalog_id, assigned_by)
                VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
            """, term_id, catalog_id, payload.assigned_by)
            results.append({"catalog_id": catalog_id, "status": "assigned"})
        return {"term_id": term_id, "term_name": term["name"], "assignments": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/api/v1/glossary/terms/{term_id}/assign-columns")
async def assign_term_to_columns(term_id: str, payload: GlossaryTermAssignRequest):
    from app import db, logger
    try:
        term = await db.fetch_one("SELECT id, name FROM glossary_terms WHERE id = $1", term_id)
        if not term:
            raise HTTPException(404, "Glossary term not found")
        results = []
        for column_id in (payload.column_ids or []):
            if not await db.fetch_one("SELECT id FROM columns WHERE id = $1", column_id):
                results.append({"column_id": column_id, "status": "not_found"}); continue
            await db.execute("""
                INSERT INTO glossary_term_column_assignments (term_id, column_id, assigned_by)
                VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
            """, term_id, column_id, payload.assigned_by)
            results.append({"column_id": column_id, "status": "assigned"})
        return {"term_id": term_id, "term_name": term["name"], "assignments": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/api/v1/glossary/terms/{term_id}/assign-catalog/{catalog_id}", status_code=204)
async def unassign_term_from_catalog(term_id: str, catalog_id: str):
    from app import db, logger
    try:
        await db.execute("""
            DELETE FROM glossary_term_catalog_assignments WHERE term_id = $1 AND catalog_id = $2
        """, term_id, catalog_id)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/api/v1/glossary/terms/{term_id}/assign-column/{column_id}", status_code=204)
async def unassign_term_from_column(term_id: str, column_id: str):
    from app import db, logger
    try:
        await db.execute("""
            DELETE FROM glossary_term_column_assignments WHERE term_id = $1 AND column_id = $2
        """, term_id, column_id)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/api/v1/catalogs/{catalog_id}/glossary-terms", response_model=List[GlossaryTermResponse])
async def get_catalog_glossary_terms(catalog_id: str):
    from app import db, logger
    try:
        rows = await db.fetch_all("""
            SELECT t.id, t.name, t.description, t.owner_id, t.parent_group_id,
                   t.created_at, t.updated_at,
                   o.name AS owner_name, g.name AS parent_group_name
            FROM glossary_term_catalog_assignments gtca
            JOIN glossary_terms t ON gtca.term_id = t.id
            LEFT JOIN owners o ON t.owner_id = o.id
            LEFT JOIN glossary_groups g on t.parent_group_id = g.id
            WHERE gtca.catalog_id = $1
            ORDER BY t.name
        """, catalog_id)
        return [_map_term(r) for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/api/v1/columns/{column_id}/glossary-terms", response_model=List[GlossaryTermResponse])
async def get_column_glossary_terms(column_id: str):
    from app import db, logger
    try:
        rows = await db.fetch_all("""
            SELECT t.id, t.name, t.description, t.owner_id, t.parent_group_id,
                   t.created_at, t.updated_at,
                   o.name AS owner_name, g.name AS parent_group_name
            FROM glossary_term_column_assignments gtca
            JOIN glossary_terms t ON gtca.term_id = t.id
            LEFT JOIN owners o ON t.owner_id = o.id
            LEFT JOIN glossary_groups g ON t.parent_group_id = g.id
            WHERE gtca.column_id = $1
            ORDER BY t.name
        """, column_id)
        return [_map_term(r) for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ── HELPERS ───────────────────────────────────────────────────────────────────
async def _get_glossary_group(group_id: str) -> GlossaryGroupResponse:
    from app import db
    row = await db.fetch_one("""
        SELECT g.id, g.name, g.description, g.owner_id, g.parent_group_id,
               g.created_at, g.updated_at,
               o.name  AS owner_name,
               pg.name AS parent_group_name,
               (SELECT COUNT(*) FROM glossary_groups c WHERE c.parent_group_id = g.id) AS child_group_count,
               (SELECT COUNT(*) FROM glossary_terms  t WHERE t.parent_group_id  = g.id) AS child_term_count
        FROM glossary_groups g
        LEFT JOIN owners          o  ON g.owner_id        = o.id
        LEFT JOIN glossary_groups pg ON g.parent_group_id = pg.id
        WHERE g.id = $1
    """, group_id)
    if not row:
        raise HTTPException(404, "Glossary group not found")
    return _map_group(row)


def _map_group(row) -> GlossaryGroupResponse:
    return GlossaryGroupResponse(
        id=str(row["id"]), name=row["name"], description=row.get("description"),
        owner_id=str(row["owner_id"]) if row.get("owner_id") else None,
        owner_name=row.get("owner_name"),
        parent_group_id=str(row["parent_group_id"]) if row.get("parent_group_id") else None,
        parent_group_name=row.get("parent_group_name"),
        child_group_count=row.get("child_group_count", 0),
        child_term_count=row.get("child_term_count", 0),
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


async def _get_glossary_term(term_id: str) -> GlossaryTermResponse:
    from app import db
    row = await db.fetch_one("""
        SELECT t.id, t.name, t.description, t.owner_id, t.parent_group_id,
               t.created_at, t.updated_at,
               o.name AS owner_name, g.name AS parent_group_name
        FROM glossary_terms t
        LEFT JOIN owners          o ON t.owner_id        = o.id
        LEFT JOIN glossary_groups g ON t.parent_group_id = g.id
        WHERE t.id = $1
    """, term_id)
    if not row:
        raise HTTPException(404, "Glossary term not found")
    return _map_term(row)


def _map_term(row) -> GlossaryTermResponse:
    return GlossaryTermResponse(
        id=str(row["id"]), name=row["name"], description=row.get("description"),
        owner_id=str(row["owner_id"]) if row.get("owner_id") else None,
        owner_name=row.get("owner_name"),
        parent_group_id=str(row["parent_group_id"]) if row.get("parent_group_id") else None,
        parent_group_name=row.get("parent_group_name"),
        created_at=row["created_at"], updated_at=row["updated_at"],
    )
