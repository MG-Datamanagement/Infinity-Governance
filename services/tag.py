from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict

from models.tags_schemas import TagCreate, TagResponse
from models.tag_schemas import (
    TagAssignRequest,
)

router = APIRouter(tags=["Tags"])



@router.post("/api/v1/tags-create", response_model=TagResponse, status_code=201)
async def create_tag(payload: TagCreate):

    from app import db, log_api_action

    try:

       
        if payload.owner_id:
            owner = await db.fetch_one(
                "SELECT id FROM owners WHERE id=$1",
                payload.owner_id
            )

            if not owner:
                raise HTTPException(
                    status_code=400,
                    detail=f"Owner {payload.owner_id} does not exist"
                )

        result = await db.fetch_one(
            """
            INSERT INTO tags
            (
                name,
                tag_type,
                description,
                security_policy,
                color,
                status,
                owner_id
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            RETURNING
                id,
                name,
                tag_type,
                description,
                security_policy,
                color,
                status,
                owner_id,
                created_at,
                updated_at
            """,
            payload.name,
            payload.tag_type,
            payload.description,
            payload.security_policy,
            payload.color,
            payload.status or "active",
            payload.owner_id
        )

        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to create tag"
            )

        data = dict(result)

        data["id"] = str(data["id"])
        data["owner_id"] = str(data["owner_id"]) if data.get("owner_id") else None

        await log_api_action(
            endpoint="/tags",
            method="POST",
            action_summary=f"New tag created: {payload.name}",
            entity_type="tag",
            entity_id=data["id"],
            entity_name=payload.name,
            owner_id=payload.owner_id
        )

        return data

    except Exception as e:

        # if "unique" in str(e).lower():
        #     raise HTTPException(
        #         status_code=409,
        #         detail=f"Tag '{payload.name}' already exists"
        #     )

        # raise HTTPException(
        #     status_code=500,
        #     detail=str(e)
        # )
        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__}: {str(e)!r} ── {repr(e)}"
        )
    
@router.get("/api/v1/tags-list", response_model=List[TagResponse])
async def get_tags(
    tag_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):

    from app import db

    query = """
        SELECT
            id,
            name,
            tag_type,
            description,
            security_policy,
            color,
            status,
            owner_id,
            created_at,
            updated_at
        FROM tags
        WHERE 1=1
    """

    params = []
    param_index = 1

    if tag_type and tag_type.lower() != "all":
        query += f" AND tag_type = ${param_index}"
        params.append(tag_type.lower())
        param_index += 1

    if status and status.lower() != "all":
        query += f" AND status = ${param_index}"
        params.append(status.lower())
        param_index += 1

    query += " ORDER BY created_at DESC"

    rows = await db.fetch_all(query, *params)

    result = []

    for r in rows:
        data = dict(r)
        data["id"] = str(data["id"])
        data["owner_id"] = str(data["owner_id"]) if data["owner_id"] else None
        result.append(data)

    return result




@router.get("/api/v1/tags-get/{tag_id}", response_model=TagResponse)
async def get_tag(tag_id: str):

    from app import db

    row = await db.fetch_one(
        """
        SELECT *
        FROM tags
        WHERE id=$1
        """,
        tag_id
    )

    if not row:
        raise HTTPException(status_code=404, detail="Tag not found")

    data = dict(row)
    data["id"] = str(data["id"])
    data["owner_id"] = str(data["owner_id"]) if data["owner_id"] else None

    return data



@router.put("/api/v1/tags-update/{tag_id}", response_model=TagResponse)
async def update_tag(tag_id: str, payload: TagCreate):

    from app import db, log_api_action

    try:

        if payload.owner_id:
            owner = await db.fetch_one(
                "SELECT id FROM owners WHERE id=$1",
                payload.owner_id
            )

            if not owner:
                raise HTTPException(
                    status_code=400,
                    detail="Owner does not exist"
                )

        result = await db.fetch_one(
            """
            UPDATE tags
            SET
                name=$1,
                tag_type=$2,
                description=$3,
                security_policy=$4,
                color=$5,
                status=$6,
                owner_id=$7,
                updated_at=NOW()
            WHERE id=$8
            RETURNING
                id,
                name,
                tag_type,
                description,
                security_policy,
                color,
                status,
                owner_id,
                created_at,
                updated_at
            """,
            payload.name,
            payload.tag_type,
            payload.description,
            payload.security_policy,
            payload.color,
            payload.status,
            payload.owner_id,
            tag_id
        )

        if not result:
            raise HTTPException(status_code=404, detail="Tag not found")

        data = dict(result)

        data["id"] = str(data["id"])
        data["owner_id"] = str(data["owner_id"]) if data["owner_id"] else None

        await log_api_action(
            endpoint="/tags",
            method="PUT",
            action_summary=f"Tag updated: {payload.name}",
            entity_type="tag",
            entity_id=data["id"],
            entity_name=payload.name,
            owner_id=payload.owner_id
        )

        return data

    except Exception as e:

        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail=f"Tag '{payload.name}' already exists"
            )

        raise HTTPException(status_code=500, detail=str(e))
    
@router.delete("/api/v1/tags-delete/{tag_id}")
async def delete_tag(tag_id: str):

    from app import db, log_api_action

    result = await db.fetch_one(
        """
        DELETE FROM tags
        WHERE id=$1
        RETURNING id, name, owner_id
        """,
        tag_id
    )

    if not result:
        raise HTTPException(status_code=404, detail="Tag not found")

    await log_api_action(
        endpoint="/tags",
        method="DELETE",
        action_summary=f"Tag deleted: {result['name']}",
        entity_type="tag",
        entity_id=str(result["id"]),
        entity_name=result["name"],
        owner_id=result["owner_id"]
    )

    return {"message": "Tag deleted successfully"}

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
