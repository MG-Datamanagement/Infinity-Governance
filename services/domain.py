from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from models import (
    DomainCreate, DomainUpdate, DomainResponse,
    DomainAssignRequest, DomainCatalogResponse,
)

router = APIRouter(tags=["Domains"])


@router.post("/api/v1/domain-create", response_model=DomainResponse, status_code=201)
async def create_domain(payload: DomainCreate):
    """Create a new domain, with optional parent nesting."""
    from app import db, log_api_action, logger

    try:
        if payload.parent_domain_id:
            parent = await db.fetch_one(
                "SELECT id FROM domains WHERE id = $1",
                payload.parent_domain_id,
            )
            if not parent:
                raise HTTPException(status_code=404, detail=f"Parent domain '{payload.parent_domain_id}' not found")

        domain = await db.fetch_one(
            """
            INSERT INTO domains (name, description, color, parent_domain_id, owner_id)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, name, description, color, parent_domain_id, owner_id, created_at, updated_at
            """,
            payload.name,
            payload.description,
            payload.color,
            payload.parent_domain_id,
            payload.owner_id,
        )

        result = dict(domain)
        result["id"] = str(result["id"])
        result["parent_domain_id"] = str(result["parent_domain_id"]) if result.get("parent_domain_id") else None
        result["owner_id"] = str(result["owner_id"]) if result.get("owner_id") else None
        result["parent_domain_name"] = None
        result["dataset_count"] = 0

        logger.info(f"Created domain: {payload.name} (id={result['id']})")
        await log_api_action(
            endpoint="/domains",
            method="POST",
            action_summary=f"New domain created: {payload.name}",
            entity_type="domain",
            entity_id=result["id"],
            entity_name=payload.name,
            owner_id=payload.owner_id,
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Domain '{payload.name}' already exists")
        logger.error(f"Error creating domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# @router.get("/api/v1/domains/dataset-count")
# async def domains_simple_with_count(
#     limit: int = Query(30, ge=1, le=200)
# ):
#     from app import db

#     rows = await db.fetch_all(
#         """
#         SELECT 
#             d.id,
#             d.name,
#             COUNT(dca.catalog_id) AS dataset_count
#         FROM domains d
#         LEFT JOIN domain_catalog_assignments dca ON d.id = dca.domain_id
#         GROUP BY d.id, d.name
#         ORDER BY dataset_count DESC, d.name ASC
#         LIMIT $1
#         """,
#         limit,
#     )

#     return [
#         {"id": str(row["id"]), "name": row["name"], "dataset_count": row["dataset_count"] or 0}
#         for row in rows
#     ]


@router.get("/api/v1/domains0list", response_model=List[DomainResponse])
async def list_domains(
    search: Optional[str] = None,
    parent_domain_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
):
    from app import db, logger

    try:
        query = """
            SELECT
                d.id,
                d.name,
                d.description,
                d.color,
                d.parent_domain_id,
                d.owner_id,
                p.name AS parent_domain_name,
                d.created_at,
                d.updated_at,
                COUNT(DISTINCT dca.catalog_id) AS dataset_count
            FROM domains d
            LEFT JOIN domains p ON d.parent_domain_id = p.id
            LEFT JOIN domain_catalog_assignments dca ON d.id = dca.domain_id
            WHERE 1=1
        """
        params = []

        if search:
            query += f" AND (d.name ILIKE ${len(params)+1} OR d.description ILIKE ${len(params)+1})"
            params.append(f"%{search}%")

        if parent_domain_id:
            query += f" AND d.parent_domain_id = ${len(params)+1}"
            params.append(parent_domain_id)

        query += " GROUP BY d.id, d.name, d.description, d.color, d.parent_domain_id, d.owner_id, p.name"
        query += " ORDER BY d.name"
        query += f" LIMIT ${len(params)+1}"
        params.append(limit)

        rows = await db.fetch_all(query, *params)
        results = []
        for row in rows:
            r = dict(row)
            r["id"] = str(r["id"])
            r["parent_domain_id"] = str(r["parent_domain_id"]) if r.get("parent_domain_id") else None
            r["owner_id"] = str(r["owner_id"]) if r.get("owner_id") else None
            results.append(r)

        return results

    except Exception as e:
        logger.error(f"Error listing domains: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/domain-detail/{domain_id}", response_model=DomainResponse)
async def get_domain(domain_id: str):
    from app import db, logger

    try:
        row = await db.fetch_one(
            """
            SELECT
                d.id, d.name, d.description, d.color,
                d.parent_domain_id, d.owner_id, p.name AS parent_domain_name,
                d.created_at, d.updated_at,
                COUNT(DISTINCT dca.catalog_id) AS dataset_count
            FROM domains d
            LEFT JOIN domains p ON d.parent_domain_id = p.id
            LEFT JOIN domain_catalog_assignments dca ON d.id = dca.domain_id
            WHERE d.id = $1
            GROUP BY d.id, d.name, d.description, d.color, d.parent_domain_id, d.owner_id, p.name
            """,
            domain_id,
        )

        if not row:
            raise HTTPException(status_code=404, detail="Domain not found")

        result = dict(row)
        result["id"] = str(result["id"])
        result["parent_domain_id"] = str(result["parent_domain_id"]) if result.get("parent_domain_id") else None
        result["owner_id"] = str(result["owner_id"]) if result.get("owner_id") else None
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/v1/domain-update/{domain_id}", response_model=DomainResponse)
async def update_domain(domain_id: str, payload: DomainUpdate):
    from app import db, logger

    try:
        existing = await db.fetch_one("SELECT id FROM domains WHERE id = $1", domain_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Domain not found")

        set_clauses = []
        params = []

        if payload.name is not None:
            params.append(payload.name)
            set_clauses.append(f"name = ${len(params)}")
        if payload.description is not None:
            params.append(payload.description)
            set_clauses.append(f"description = ${len(params)}")
        if payload.color is not None:
            params.append(payload.color)
            set_clauses.append(f"color = ${len(params)}")
        if payload.parent_domain_id is not None:
            if payload.parent_domain_id == domain_id:
                raise HTTPException(status_code=400, detail="Domain cannot be its own parent")
            params.append(payload.parent_domain_id)
            set_clauses.append(f"parent_domain_id = ${len(params)}")
        if payload.owner_id is not None:
            params.append(payload.owner_id)
            set_clauses.append(f"owner_id = ${len(params)}")

        if not set_clauses:
            raise HTTPException(status_code=400, detail="No fields to update")

        params.append(domain_id)
        await db.execute(
            f"UPDATE domains SET {', '.join(set_clauses)}, updated_at = NOW() WHERE id = ${len(params)}",
            *params,
        )

        return await get_domain(domain_id)

    except HTTPException:
        raise
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Domain name already exists")
        logger.error(f"Error updating domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/v1/delete-domain/{domain_id}", status_code=204)
async def delete_domain(domain_id: str):
    from app import db, logger

    try:
        existing = await db.fetch_one("SELECT id FROM domains WHERE id = $1", domain_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Domain not found")

        await db.execute("DELETE FROM domains WHERE id = $1", domain_id)
        logger.info(f"Deleted domain id={domain_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/domains/{domain_id}/assign")
async def assign_catalogs_to_domain(domain_id: str, payload: DomainAssignRequest):
    from app import db, logger

    try:
        domain = await db.fetch_one("SELECT id, name FROM domains WHERE id = $1", domain_id)
        if not domain:
            raise HTTPException(status_code=404, detail="Domain not found")

        assigned, skipped, not_found = [], [], []

        for catalog_id in payload.catalog_ids:
            cat = await db.fetch_one("SELECT id, full_name FROM catalogs WHERE id = $1", catalog_id)
            if not cat:
                not_found.append(catalog_id)
                continue
            try:
                await db.execute(
                    """
                    INSERT INTO domain_catalog_assignments (domain_id, catalog_id, assigned_by)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (domain_id, catalog_id) DO NOTHING
                    """,
                    domain_id,
                    catalog_id,
                    payload.assigned_by,
                )
                assigned.append(catalog_id)
            except Exception:
                skipped.append(catalog_id)

        logger.info(f"Domain '{domain['name']}': assigned {len(assigned)} catalogs, {len(not_found)} not found")

        return {
            "domain_id": domain_id,
            "domain_name": domain['name'],
            "assigned": assigned,
            "already_assigned": skipped,
            "not_found": not_found,
            "total_assigned": len(assigned),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning catalogs to domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/v1/domains/{domain_id}/remove/{catalog_id}", status_code=204)
async def remove_catalog_from_domain(domain_id: str, catalog_id: str):
    from app import db, logger

    try:
        result = await db.execute(
            """
            DELETE FROM domain_catalog_assignments
            WHERE domain_id = $1 AND catalog_id = $2
            """,
            domain_id,
            catalog_id,
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Assignment not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing catalog from domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/domains/{domain_id}/datasets", response_model=List[DomainCatalogResponse])
async def list_domain_datasets(
    domain_id: str,
    limit: int = Query(200, ge=1, le=1000),
):
    from app import db, logger

    try:
        domain = await db.fetch_one("SELECT id FROM domains WHERE id = $1", domain_id)
        if not domain:
            raise HTTPException(status_code=404, detail="Domain not found")

        rows = await db.fetch_all(
            """
            SELECT
                c.id AS catalog_id,
                c.full_name,
                c.table_name,
                c.database_name,
                c.schema_name,
                ds.name AS source_name,
                ds.source_type,
                dca.assigned_at,
                dca.assigned_by
            FROM domain_catalog_assignments dca
            JOIN catalogs c ON dca.catalog_id = c.id
            JOIN data_sources ds ON c.source_id = ds.id
            WHERE dca.domain_id = $1
            ORDER BY c.full_name
            LIMIT $2
            """,
            domain_id,
            limit,
        )

        return [
            dict(row, catalog_id=str(row["catalog_id"]) if row["catalog_id"] else None)
            for row in rows
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing domain datasets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/catalogs/{catalog_id}/domains")
async def get_catalog_domains(catalog_id: str):
    from app import db, logger

    try:
        cat = await db.fetch_one("SELECT id FROM catalogs WHERE id = $1", catalog_id)
        if not cat:
            raise HTTPException(status_code=404, detail="Catalog not found")

        rows = await db.fetch_all(
            """
            SELECT
                d.id, d.name, d.description, d.color,
                dca.assigned_at, dca.assigned_by
            FROM domain_catalog_assignments dca
            JOIN domains d ON dca.domain_id = d.id
            WHERE dca.catalog_id = $1
            ORDER BY d.name
            """,
            catalog_id,
        )

        return [dict(row, id=str(row["id"]) if row["id"] else None) for row in rows]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting catalog domains: {e}")
        raise HTTPException(status_code=500, detail=str(e))