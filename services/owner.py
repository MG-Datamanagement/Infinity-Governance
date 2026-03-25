from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from models import OwnerCreate, OwnerResponse, OwnerUpdate, OwnerRole

router = APIRouter(tags=["Owners"])


@router.post("/api/v1/owners-create", response_model=OwnerResponse, status_code=201)
async def create_owner(payload: OwnerCreate):
    """Create a new owner. Roles: data_steward, admin, technical_owner, business_owner"""
    # delayed imports to avoid circular dependencies with app
    from app import db, log_api_action, logger

    try:
        result = await db.fetch_one(
            """
            INSERT INTO owners (name, role, email)
            VALUES ($1, $2, $3)
            RETURNING id, name, role, email, created_at, updated_at
        """, payload.name, payload.role.value, payload.email)
        data = dict(result)
        data["id"] = str(data["id"])
        await log_api_action(
            endpoint="/owners",
            method="POST",
            action_summary=f"New owner created: {payload.name} ({payload.role.value})",
            entity_type="owner",
            entity_id=data["id"],
            entity_name=payload.name,
        )
        return data
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Owner already exists")
        logger.error(f"Error creating owner: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/owners-list", response_model=List[OwnerResponse])
async def list_owners(
    role: Optional[OwnerRole] = None, limit: int = Query(100, ge=1, le=1000)
):
    """List all owners, optionally filtered by role"""
    from app import db

    try:
        query = "SELECT id, name, role, email, created_at, updated_at FROM owners WHERE 1=1"
        params = []
        if role:
            query += f" AND role = ${len(params)+1}"
            params.append(role.value)
        query += f" ORDER BY name LIMIT ${len(params)+1}"
        params.append(limit)
        rows = await db.fetch_all(query, *params)
        return [dict(r, id=str(r["id"])) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/owners/{owner_id}", response_model=OwnerResponse)
async def get_owner(owner_id: str):
    """Get owner by ID"""
    from app import db

    try:
        row = await db.fetch_one(
            "SELECT id, name, role, email, created_at, updated_at FROM owners WHERE id = $1",
            owner_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Owner not found")
        return dict(row, id=str(row["id"]))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/v1/owner-update/{owner_id}", response_model=OwnerResponse)
async def update_owner(owner_id: str, payload: OwnerUpdate):
    """Update owner name, role, or email"""
    from app import db

    try:
        existing = await db.fetch_one("SELECT id FROM owners WHERE id = $1", owner_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Owner not found")
        set_clauses, params = [], []
        if payload.name is not None:
            params.append(payload.name)
            set_clauses.append(f"name = ${len(params)}")
        if payload.role is not None:
            params.append(payload.role.value)
            set_clauses.append(f"role = ${len(params)}")
        if payload.email is not None:
            params.append(payload.email)
            set_clauses.append(f"email = ${len(params)}")
        if not set_clauses:
            raise HTTPException(status_code=400, detail="No fields to update")
        params.append(owner_id)
        await db.execute(
            f"UPDATE owners SET {', '.join(set_clauses)}, updated_at = NOW() WHERE id = ${len(params)}",
            *params,
        )
        # reuse the local get_owner function
        return await get_owner(owner_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/v1/owner-delete/{owner_id}", status_code=204)
async def delete_owner(owner_id: str):
    """Delete an owner"""
    from app import db

    try:
        existing = await db.fetch_one("SELECT id FROM owners WHERE id = $1", owner_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Owner not found")
        await db.execute("DELETE FROM owners WHERE id = $1", owner_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
