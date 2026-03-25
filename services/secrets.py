from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict

from models.secret_schemas import SecretCreateRequest, SecretUpdateRequest
from cryptography.fernet import Fernet


cipher = Fernet("LrGltIw7g1MDg0IBF098emoIsDDTlS2jbxAKzEyAbZM=")

router = APIRouter(tags=["Secrets"])



@router.post("/api/v1/add/secrets")
async def create_secret(secret: SecretCreateRequest):

    from app import db
    existing = await db.fetch_one(
        "SELECT id FROM secrets WHERE name = $1",
        secret.name
    )
    if existing:
        raise HTTPException(status_code=400, detail="Secret already exists")

    
    encrypted_value = cipher.encrypt(secret.value.encode()).decode()

    query = """
    INSERT INTO secrets (name, type, encrypted_value, description, created_at)
    VALUES ($1, $2, $3, $4, NOW())
    RETURNING id, name, type, created_at
    """

    result = await db.fetch_one(
        query,
        secret.name,
        secret.type,
        encrypted_value,
        secret.description
    )

    return dict(result)



@router.put("/api/v1/update/secrets/{secret_id}")
async def update_secret(secret_id: str, payload: SecretUpdateRequest):
    from app import db

    existing = await db.fetch_one(
        "SELECT id FROM secrets WHERE id = $1",
        secret_id
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Secret not found")

 
    encrypted_value = cipher.encrypt(payload.value.encode()).decode()

    query = """
    UPDATE secrets
    SET encrypted_value = $1,
        description = COALESCE($2, description),
        last_rotated = NOW(),
        updated_at = NOW()
    WHERE id = $3
    RETURNING id, name, type, last_rotated, updated_at
    """

    result = await db.fetch_one(
        query,
        encrypted_value,
        payload.description,
        secret_id
    )

    return dict(result)

@router.get("/api/v1/get/secrets")
async def get_secrets():
    from app import db

    query = """
    SELECT id, name, type, description, created_at, last_rotated, is_active
    FROM secrets
    ORDER BY created_at DESC
    """

    rows = await db.fetch_all(query)

    return [dict(row) for row in rows]


@router.get("/api/v1/get/secrets/{secret_id}")
async def get_secret(secret_id: str):
    from app import db

    query = """
    SELECT id, name, type, description, created_at, last_rotated, is_active
    FROM secrets
    WHERE id = $1
    """

    row = await db.fetch_one(query, secret_id)

    if not row:
        raise HTTPException(status_code=404, detail="Secret not found")

    return dict(row)


@router.delete("/api/v1/secrets/delete/{secret_id}")
async def delete_secret(secret_id: str):
    from app import db

  
    existing = await db.fetch_one(
        "SELECT id FROM secrets WHERE id = $1",
        secret_id
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Secret not found")

   
    query = """
    UPDATE secrets
    SET is_active = FALSE,
        updated_at = NOW()
    WHERE id = $1
    RETURNING id, name
    """

    result = await db.fetch_one(query, secret_id)

    return {
        "message": "Secret deactivated successfully",
        "id": result["id"],
        "name": result["name"]
    }


@router.delete("/api/v1/secrets/remove/{secret_id}")
async def delete_secret(secret_id: str):
    from app import db   

    existing = await db.fetch_one(
        "SELECT id, name FROM secrets WHERE id = $1",
        secret_id
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Secret not found")


    query = """
    DELETE FROM secrets
    WHERE id = $1
    RETURNING id, name
    """

    result = await db.fetch_one(query, secret_id)

    return {
        "message": "Secret deleted permanently",
        "id": result["id"],
        "name": result["name"]
    }


