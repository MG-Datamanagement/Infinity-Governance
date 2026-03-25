"""
Tag management API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
import asyncpg

from app.models import (
    CreateTagInput,
    TagResponse,
    UpdateTagInput,
)
from app.utils import get_db_pool, execute_graphql_query

router = APIRouter(prefix="/tags", tags=["tags"])


@router.post("/create", response_model=TagResponse)
async def create_tag(tag_input: CreateTagInput, pool: asyncpg.Pool = Depends(get_db_pool)):
    """Create Tag via GraphQL + save owner details to PostgreSQL"""
    
    if not tag_input.owners:
        raise HTTPException(status_code=400, detail="At least one owner required")
    
    # graphql mutation for creating tag
    mutation = """
    mutation createTag($input: CreateTagInput!) {
      createTag(input: $input)
    }
    """
    
    graphql_input = {
        "id": tag_input.id,
        "name": tag_input.name,
        "description": tag_input.description
    }
    
    try:
        # Execute GraphQL - returns URN string directly
        data = await execute_graphql_query(mutation, {"input": graphql_input})
        tag_urn = data.get("createTag")  # Direct string, not object
        
        if not tag_urn:
            raise HTTPException(status_code=400, detail="Failed to create tag through GraphQL")
        
        # Save to PostgreSQL (same as before)
        first_owner = tag_input.owners[0]
        await pool.execute("""
        CREATE TABLE IF NOT EXISTS ig_tag (
            urn VARCHAR PRIMARY KEY, id VARCHAR NOT NULL, name VARCHAR NOT NULL,
            description TEXT, ownerUrn VARCHAR NOT NULL, ownershipTypeUrn VARCHAR NOT NULL,
            ownerEntityType VARCHAR NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        await pool.execute("""
        INSERT INTO ig_tag (urn, id, name, description, ownerUrn, ownershipTypeUrn, ownerEntityType)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (urn) DO UPDATE SET id = EXCLUDED.id, name = EXCLUDED.name,
            description = EXCLUDED.description, ownerUrn = EXCLUDED.ownerUrn,
            ownershipTypeUrn = EXCLUDED.ownershipTypeUrn, ownerEntityType = EXCLUDED.ownerEntityType
        """, tag_urn, tag_input.id, tag_input.name, tag_input.description,
           first_owner.ownerUrn, first_owner.ownershipTypeUrn, first_owner.ownerEntityType.value)
        
        return TagResponse(
            urn=tag_urn, id=tag_input.id, name=tag_input.name,
            description=tag_input.description, ownerUrn=first_owner.ownerUrn,
            ownershipTypeUrn=first_owner.ownershipTypeUrn, ownerEntityType=first_owner.ownerEntityType.value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tag creation failed: {str(e)}")


@router.put("/{urn}", response_model=TagResponse)
async def update_tag(
    urn: str,
    tag_update: UpdateTagInput, 
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Update tag in PostgreSQL ONLY (name, description, owners).
    """
    # Validate URN
    if urn != tag_update.urn:
        raise HTTPException(status_code=400, detail="Path urn must match input urn")
    
    # Check existence
    existing = await pool.fetchrow("SELECT urn FROM ig_tag WHERE urn = $1", urn)
    if not existing:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    # Build dynamic UPDATE (same as domain)
    update_fields = []
    params = [urn]
    param_index = 1
    
    if tag_update.name is not None:
        update_fields.append("name = $" + str(param_index + 1))
        params.append(tag_update.name)
        param_index += 1
    
    if tag_update.description is not None:
        update_fields.append("description = $" + str(param_index + 1))
        params.append(tag_update.description)
        param_index += 1
    
    if tag_update.ownerUrn is not None:
        update_fields.append("ownerUrn = $" + str(param_index + 1))
        params.append(tag_update.ownerUrn)
        param_index += 1
    
    if tag_update.ownershipTypeUrn is not None:
        update_fields.append("ownershipTypeUrn = $" + str(param_index + 1))
        params.append(tag_update.ownershipTypeUrn)
        param_index += 1
    
    if tag_update.ownerEntityType is not None:
        update_fields.append("ownerEntityType = $" + str(param_index + 1))
        params.append(tag_update.ownerEntityType.value)
        param_index += 1
    
    # Always update timestamp
    update_fields.append("updated_at = CURRENT_TIMESTAMP")
    
    if not update_fields[:-1]:  # No actual fields except timestamp
        raise HTTPException(status_code=400, detail="No fields provided to update")
    
    update_query = f"""
        UPDATE ig_tag 
        SET {', '.join(update_fields)}
        WHERE urn = $1
        RETURNING urn, id, name, description, ownerUrn, ownershipTypeUrn, ownerEntityType
    """
    
    result = await pool.fetchrow(update_query, *params)
    
    return TagResponse(
        urn=result['urn'],
        id=result['id'],
        name=result['name'],
        description=result['description'],
        ownerUrn=result['ownerurn'],
        ownershipTypeUrn=result['ownershiptypeurn'],
        ownerEntityType=result['ownerentitytype']
    )


@router.delete("/{urn}", status_code=204)
async def delete_tag(urn: str, pool: asyncpg.Pool = Depends(get_db_pool)):
    """
    Delete tag by URN from both PostgreSQL and GraphQL.
    Returns 204 No Content on success.
    """
    try:
        # 1. FIRST: Delete from GraphQL
        delete_mutation = """
        mutation deleteTag($urn: String!) {
          deleteTag(urn: $urn)
        }
        """
        
        variables = {"urn": urn}
        data = await execute_graphql_query(delete_mutation, variables)
        
        # Verify GraphQL deletion succeeded (returns Boolean true)
        if not data.get("deleteTag"):
            raise HTTPException(status_code=400, detail="Failed to delete tag in GraphQL")
        
        # 2. THEN: Delete from PostgreSQL
        result = await pool.execute(
            "DELETE FROM ig_tag WHERE urn = $1 RETURNING urn", 
            urn
        )
        
        # Tag might not exist in Postgres but deleted from GraphQL = still success
        if not result:
            pass
        
        # 204 No Content - success, no body
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tag deletion failed: {str(e)}")


@router.get("/list")
async def list_tags(pool: asyncpg.Pool = Depends(get_db_pool)):
    """
    List all tags from PostgreSQL with full details.
    """
    try:
        rows = await pool.fetch("""
            SELECT urn, id, name, description, ownerUrn, ownershipTypeUrn, 
                   ownerEntityType, created_at, updated_at
            FROM ig_tag 
            ORDER BY created_at DESC
        """)
        
        tags = []
        for row in rows:
            tags.append({
                "urn": row["urn"],
                "id": row["id"],
                "name": row["name"],
                "description": row["description"] or "",
                "ownerUrn": row["ownerurn"],
                "ownershipTypeUrn": row["ownershiptypeurn"],
                "ownerEntityType": row["ownerentitytype"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
            })
        
        return {
            "status": "success", 
            "tags": tags, 
            "total": len(tags)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tags: {str(e)}")
