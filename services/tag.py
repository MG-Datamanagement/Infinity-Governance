from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict

from models import (
    TagCreate,
    TagUpdate,
    TagResponse,
    TagAssignRequest,
)

router = APIRouter(tags=["Tags"])


@router.post("/api/v1/tag-create", response_model=TagResponse, status_code=201)
async def create_tag(payload: TagCreate):
    """Create a new tag. Optionally link an owner."""
    from app import db, log_api_action, logger

    try:
        result = await db.fetch_one("""
            INSERT INTO tags (name, description, color, owner_id)
            VALUES ($1, $2, $3, $4)
            RETURNING id, name, description, color, owner_id, created_at, updated_at
        """, payload.name, payload.description, payload.color, payload.owner_id)
        data = dict(result)
        data["id"] = str(data["id"])
        data["owner_id"] = str(data["owner_id"]) if data.get("owner_id") else None
        await log_api_action(
            endpoint="/tags", method="POST",
            action_summary=f"New tag created: {payload.name}",
            entity_type="tag", entity_id=data["id"], entity_name=payload.name,
            owner_id=payload.owner_id
        )
        return data
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Tag '{payload.name}' already exists")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/taglist", response_model=List[TagResponse])
async def list_tags(limit: int = Query(100, ge=1, le=1000)):
    """List all tags"""
    from app import db

    try:
        rows = await db.fetch_all("""
            SELECT id, name, description, color, owner_id, created_at, updated_at
            FROM tags ORDER BY name LIMIT $1
        """, limit)
        return [dict(r, id=str(r['id']), owner_id=str(r['owner_id']) if r.get('owner_id') else None) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/tags/{tag_id}", response_model=TagResponse)
async def get_tag(tag_id: str):
    """Get tag by ID"""
    from app import db

    try:
        row = await db.fetch_one("SELECT id, name, description, color, owner_id, created_at, updated_at FROM tags WHERE id = $1", tag_id)
        if not row:
            raise HTTPException(status_code=404, detail="Tag not found")
        return dict(row, id=str(row['id']), owner_id=str(row['owner_id']) if row.get('owner_id') else None)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/v1/tag-update/{tag_id}", response_model=TagResponse)
async def update_tag(tag_id: str, payload: TagUpdate):
    """Update a tag"""
    from app import db

    try:
        existing = await db.fetch_one("SELECT id FROM tags WHERE id = $1", tag_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Tag not found")
        set_clauses, params = [], []
        if payload.name is not None:
            params.append(payload.name); set_clauses.append(f"name = ${{len(params)}}")
        if payload.description is not None:
            params.append(payload.description); set_clauses.append(f"description = ${{len(params)}}")
        if payload.color is not None:
            params.append(payload.color); set_clauses.append(f"color = ${{len(params)}}")
        if payload.owner_id is not None:
            params.append(payload.owner_id); set_clauses.append(f"owner_id = ${{len(params)}}")
        if not set_clauses:
            raise HTTPException(status_code=400, detail="No fields to update")
        params.append(tag_id)
        await db.execute(
            f"UPDATE tags SET {', '.join(set_clauses)}, updated_at = NOW() WHERE id = ${{len(params)}}", *params
        )
        return await get_tag(tag_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/v1/tag-delete/{tag_id}", status_code=204)
async def delete_tag(tag_id: str):
    """Delete a tag"""
    from app import db

    try:
        existing = await db.fetch_one("SELECT id FROM tags WHERE id = $1", tag_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Tag not found")
        await db.execute("DELETE FROM tags WHERE id = $1", tag_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/tags/{tag_id}/assign-to-catalogs", response_model=Dict)
async def assign_catalogs_to_tag(tag_id: str, payload: TagAssignRequest):
    """Assign one or more catalogs to a tag"""
    from app import db

    try:
        tag = await db.fetch_one("SELECT id, name FROM tags WHERE id = $1", tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        assigned, skipped, not_found = [], [], []
        for catalog_id in payload.catalog_ids:
            cat = await db.fetch_one("SELECT id FROM catalogs WHERE id = $1", catalog_id)
            if not cat:
                not_found.append(catalog_id); continue
            try:
                await db.execute("""
                    INSERT INTO tag_catalog_assignments (tag_id, catalog_id, assigned_by)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (tag_id, catalog_id) DO NOTHING
                """, tag_id, catalog_id, payload.assigned_by)
                assigned.append(catalog_id)
            except Exception:
                skipped.append(catalog_id)
        return {"tag_id": tag_id, "tag_name": tag['name'], "assigned": assigned,
                "already_assigned": skipped, "not_found": not_found}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/catalogs/{catalog_id}/tags")
async def get_catalog_tags(catalog_id: str):
    """Get all tags assigned to a catalog"""
    from app import db

    try:
        cat = await db.fetch_one("SELECT id FROM catalogs WHERE id = $1", catalog_id)
        if not cat:
            raise HTTPException(status_code=404, detail="Catalog not found")
        rows = await db.fetch_all("""
            SELECT t.id, t.name, t.description, t.color, tca.assigned_at, tca.assigned_by
            FROM tag_catalog_assignments tca
            JOIN tags t ON tca.tag_id = t.id
            WHERE tca.catalog_id = $1 ORDER BY t.name
        """, catalog_id)
        return [dict(r, id=str(r['id'])) for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
