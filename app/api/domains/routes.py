"""
Domain management API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
import asyncpg

from app.models import (
    CreateDomainInput,
    DomainResponse,
    UpdateDomainInput,
    DomainState,
)
from app.utils import get_db_pool, execute_graphql_query

router = APIRouter(prefix="/domains", tags=["domains"])


@router.post("/create", response_model=DomainResponse)
async def create_domain(domain_input: CreateDomainInput, pool: asyncpg.Pool = Depends(get_db_pool)):
    """Create a new Domain and save to PostgreSQL"""
    
    # Validate input
    if not domain_input.owners:
        raise HTTPException(status_code=400, detail="At least one owner required")
    
    # Create domain mutation
    mutation = """
    mutation createDomain($input: CreateDomainInput!) {
      createDomain(input: $input)
    }
    """
    
    input_data = {
        "id": domain_input.id,
        "name": domain_input.name,
        "description": domain_input.description,
        "owners": [
            {
                "ownerUrn": owner.ownerUrn,
                "ownerEntityType": owner.ownerEntityType,
                "ownershipTypeUrn": owner.ownershipTypeUrn
            }
            for owner in domain_input.owners
        ]
    }
    
    try:
        # Execute domain creation
        data = await execute_graphql_query(mutation, {"input": input_data})
        domain_urn = data.get("createDomain")
        
        if not domain_urn:
            raise HTTPException(status_code=400, detail="Failed to create domain")
        
        # Save first owner details to PostgreSQL (assuming single primary owner)
        first_owner = domain_input.owners[0]
        
        # Create table if not exists
        await pool.execute("""
            CREATE TABLE IF NOT EXISTS ig_domain (
                urn VARCHAR PRIMARY KEY,
                id VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                description TEXT,
                ownerUrn VARCHAR NOT NULL,
                ownershipTypeUrn VARCHAR NOT NULL,
                ownerEntityType VARCHAR NOT NULL,
                state VARCHAR DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert domain record
        await pool.execute("""
            INSERT INTO ig_domain (urn, id, name, description, ownerUrn, ownershipTypeUrn, ownerEntityType, state)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (urn) DO UPDATE SET
                id = EXCLUDED.id,
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                ownerUrn = EXCLUDED.ownerUrn,
                ownershipTypeUrn = EXCLUDED.ownershipTypeUrn,
                ownerEntityType = EXCLUDED.ownerEntityType,
                state = EXCLUDED.state
        """, domain_urn, domain_input.id, domain_input.name, domain_input.description,
              first_owner.ownerUrn, first_owner.ownershipTypeUrn, first_owner.ownerEntityType.value, DomainState.ACTIVE)
        
        return DomainResponse(
            urn=domain_urn,
            id=domain_input.id,
            name=domain_input.name,
            description=domain_input.description,
            ownerUrn=first_owner.ownerUrn,
            ownershipTypeUrn=first_owner.ownershipTypeUrn,
            ownerEntityType=first_owner.ownerEntityType.value,
            state=DomainState.ACTIVE
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Domain creation failed: {str(e)}")


@router.get("/list")
async def list_domains(pool: asyncpg.Pool = Depends(get_db_pool)):
    """List all domains from PostgreSQL"""
    try:
        rows = await pool.fetch("""
            SELECT urn, id, name, description, ownerUrn, ownershipTypeUrn, ownerEntityType, state, created_at
            FROM ig_domain
            ORDER BY created_at DESC
        """)
        
        domains = []
        for row in rows:
            domains.append({
                "urn": row["urn"],
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "ownerUrn": row["ownerurn"],
                "ownershipTypeUrn": row["ownershiptypeurn"],
                "ownerEntityType": row["ownerentitytype"],
                "state": row["state"],
                "created_at": row["created_at"].isoformat()
            })
        
        return {"status": "success", "domains": domains, "total": len(domains)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch domains: {str(e)}")


@router.put("/{urn}", response_model=DomainResponse)
async def update_domain(
    urn: str,
    domain_update: UpdateDomainInput, 
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Update existing domain in PostgreSQL only.
    All fields optional except urn identifier.
    """
    # Validate urn matches input
    if urn != domain_update.urn:
        raise HTTPException(status_code=400, detail="Path urn must match input urn")
    
    # Check if domain exists first
    existing = await pool.fetchrow(
        "SELECT urn FROM ig_domain WHERE urn = $1", urn
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    # Build dynamic UPDATE query with only provided fields
    update_fields = []
    params = [urn]
    param_index = 1
    
    if domain_update.name is not None:
        update_fields.append("name = $" + str(param_index + 1))
        params.append(domain_update.name)
        param_index += 1
    
    if domain_update.description is not None:
        update_fields.append("description = $" + str(param_index + 1))
        params.append(domain_update.description)
        param_index += 1
    
    if domain_update.ownerUrn is not None:
        update_fields.append("ownerUrn = $" + str(param_index + 1))
        params.append(domain_update.ownerUrn)
        param_index += 1
    
    if domain_update.ownershipTypeUrn is not None:
        update_fields.append("ownershipTypeUrn = $" + str(param_index + 1))
        params.append(domain_update.ownershipTypeUrn)
        param_index += 1
    
    if domain_update.ownerEntityType is not None:
        update_fields.append("ownerEntityType = $" + str(param_index + 1))
        params.append(domain_update.ownerEntityType.value)
        param_index += 1
    
    if domain_update.state is not None:
        update_fields.append("state = $" + str(param_index + 1))
        params.append(domain_update.state.value)
        param_index += 1
    
    # Add updated_at timestamp
    update_fields.append("updated_at = CURRENT_TIMESTAMP")
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields provided to update")
    
    # Execute dynamic UPDATE
    update_query = f"""
        UPDATE ig_domain 
        SET {', '.join(update_fields)}
        WHERE urn = $1
        RETURNING urn, id, name, description, ownerUrn, ownershipTypeUrn, 
                  ownerEntityType, state, created_at
    """
    
    result = await pool.fetchrow(update_query, *params)
    
    if not result:
        raise HTTPException(status_code=404, detail="Domain update failed")
    
    return DomainResponse(
        urn=result['urn'],
        id=result['id'],
        name=result['name'],
        description=result['description'],
        ownerUrn=result['ownerurn'],
        ownershipTypeUrn=result['ownershiptypeurn'],
        ownerEntityType=result['ownerentitytype'],
        state=result['state']
    )


@router.delete("/{urn}", status_code=204)
async def delete_domain(urn: str, pool: asyncpg.Pool = Depends(get_db_pool)):
    """
    Delete domain by URN from both PostgreSQL and GraphQL.
    Returns 204 No Content on success.
    """
    try:
        # 1. FIRST: Delete from GraphQL
        delete_mutation = """
        mutation DeleteDomain($urn: String!) {
          deleteDomain(urn: $urn)
        }
        """
        
        variables = {"urn": urn}
        data = await execute_graphql_query(delete_mutation, variables)
        
        # Verify GraphQL deletion succeeded
        if not data.get("deleteDomain"):
            raise HTTPException(status_code=400, detail="Domain deletion failed in GraphQL")
        
        # 2. THEN: Delete from PostgreSQL
        result = await pool.execute(
            "DELETE FROM ig_domain WHERE urn = $1 RETURNING urn", 
            urn
        )
        
        if not result:
            # Domain wasn't in Postgres but deleted from GraphQL - still success
            pass
        
        # 204 No Content - success, no body returned
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Domain deletion failed: {str(e)}")
