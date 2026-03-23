from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(tags=["catalog-properties"])


# ============================================================================
# SCHEMAS
# ============================================================================

class QueryItem(BaseModel):
    id: str
    catalog_id: str
    title: str
    description: Optional[str] = None
    query_text: str
    owner_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_lineage_query: bool = False


class QueryListResponse(BaseModel):
    catalog_id: str
    user_queries: List[QueryItem] = []


class CreateQueryRequest(BaseModel):
    title: str
    description: Optional[str] = None
    query_text: str
    owner_id: Optional[str] = None


class UpdateQueryRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    query_text: Optional[str] = None
    owner_id: Optional[str] = None


# ============================================================================
# HELPERS
# ============================================================================

async def _assert_catalog_exists(db, catalog_id: str):
    row = await db.fetch_one("SELECT id FROM catalogs WHERE id = $1", catalog_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Catalog '{catalog_id}' not found")


async def _assert_query_exists_and_not_lineage(db, query_id: str) -> dict:
    row = await db.fetch_one(
        """
        SELECT id, catalog_id, title, description, query_text, owner_id,
               created_at, updated_at
        FROM   catalog_queries
        WHERE  id = $1
        """,
        query_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"Query '{query_id}' not found")
    return dict(row)


# ============================================================================
# GET  /api/v1/catalogs/{catalog_id}/queries
# ============================================================================

@router.get(
    "/api/v1/catalogs/{catalog_id}/queries",
    response_model=QueryListResponse,
    summary="List all queries for a catalog",
)
async def list_catalog_queries(catalog_id: str):
    from app import db, logger
    try:
        await _assert_catalog_exists(db, catalog_id)

        rows = await db.fetch_all(
            """
            SELECT
                cq.id, cq.catalog_id, cq.title, cq.description,
                cq.query_text, cq.created_at, cq.updated_at,
                o.name AS owner_name
            FROM   catalog_queries cq
            LEFT JOIN owners o ON o.id = cq.owner_id
            WHERE  cq.catalog_id = $1
            ORDER  BY cq.created_at DESC
            """,
            catalog_id,
        )

        user_queries = [
            QueryItem(
                id=str(r["id"]),
                catalog_id=str(r["catalog_id"]),
                title=r["title"],
                description=r.get("description"),
                query_text=r["query_text"],
                owner_name=r.get("owner_name"),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                is_lineage_query=False,
            )
            for r in rows
        ]

        return QueryListResponse(
            catalog_id=catalog_id,
            user_queries=user_queries,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_catalog_queries error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# POST  /api/v1/catalogs/{catalog_id}/queries
# ============================================================================

@router.post(
    "/api/v1/catalogs/{catalog_id}/queries",
    response_model=QueryItem,
    status_code=201,
    summary="Create a query for a catalog",
)
async def create_catalog_query(catalog_id: str, body: CreateQueryRequest):
    from app import db, logger
    try:
        await _assert_catalog_exists(db, catalog_id)

        if body.owner_id:
            owner_row = await db.fetch_one(
                "SELECT id FROM owners WHERE id = $1", body.owner_id
            )
            if not owner_row:
                raise HTTPException(status_code=404, detail=f"Owner '{body.owner_id}' not found")

        row = await db.fetch_one(
            """
            INSERT INTO catalog_queries
                (catalog_id, title, description, query_text, owner_id)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, catalog_id, title, description, query_text,
                      owner_id, created_at, updated_at
            """,
            catalog_id,
            body.title,
            body.description,
            body.query_text,
            body.owner_id,
        )

        owner_name = None
        if row.get("owner_id"):
            owner_row = await db.fetch_one(
                "SELECT name FROM owners WHERE id = $1", str(row["owner_id"])
            )
            owner_name = owner_row["name"] if owner_row else None

        return QueryItem(
            id=str(row["id"]),
            catalog_id=str(row["catalog_id"]),
            title=row["title"],
            description=row.get("description"),
            query_text=row["query_text"],
            owner_name=owner_name,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            is_lineage_query=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_catalog_query error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PATCH  /api/v1/catalogs/{catalog_id}/queries/{query_id}
# ============================================================================

@router.patch(
    "/api/v1/catalogs/{catalog_id}/queries/{query_id}",
    response_model=QueryItem,
    summary="Update a catalog query",
)
async def update_catalog_query(catalog_id: str, query_id: str, body: UpdateQueryRequest):
    from app import db, logger
    try:
        await _assert_catalog_exists(db, catalog_id)
        existing = await _assert_query_exists_and_not_lineage(db, query_id)

        if str(existing["catalog_id"]) != catalog_id:
            raise HTTPException(
                status_code=400,
                detail="Query does not belong to the specified catalog.",
            )

        updates = {}
        if body.title is not None:
            updates["title"] = body.title
        if body.description is not None:
            updates["description"] = body.description
        if body.query_text is not None:
            updates["query_text"] = body.query_text
        if body.owner_id is not None:
            owner_row = await db.fetch_one(
                "SELECT id FROM owners WHERE id = $1", body.owner_id
            )
            if not owner_row:
                raise HTTPException(status_code=404, detail=f"Owner '{body.owner_id}' not found")
            updates["owner_id"] = body.owner_id

        if not updates:
            raise HTTPException(status_code=400, detail="No fields provided to update.")

        set_parts = [f"{col} = ${i + 2}" for i, col in enumerate(updates.keys())]
        values = list(updates.values())

        row = await db.fetch_one(
            f"""
            UPDATE catalog_queries
            SET    {", ".join(set_parts)}
            WHERE  id = $1
            RETURNING id, catalog_id, title, description, query_text,
                      owner_id, created_at, updated_at
            """,
            query_id,
            *values,
        )

        owner_name = None
        if row.get("owner_id"):
            owner_row = await db.fetch_one(
                "SELECT name FROM owners WHERE id = $1", str(row["owner_id"])
            )
            owner_name = owner_row["name"] if owner_row else None

        return QueryItem(
            id=str(row["id"]),
            catalog_id=str(row["catalog_id"]),
            title=row["title"],
            description=row.get("description"),
            query_text=row["query_text"],
            owner_name=owner_name,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            is_lineage_query=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_catalog_query error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DELETE  /api/v1/catalogs/{catalog_id}/queries/{query_id}
# ============================================================================

@router.delete(
    "/api/v1/catalogs/{catalog_id}/queries/{query_id}",
    status_code=204,
    summary="Delete a catalog query",
)
async def delete_catalog_query(catalog_id: str, query_id: str):
    from app import db, logger
    try:
        await _assert_catalog_exists(db, catalog_id)
        existing = await _assert_query_exists_and_not_lineage(db, query_id)

        if str(existing["catalog_id"]) != catalog_id:
            raise HTTPException(
                status_code=400,
                detail="Query does not belong to the specified catalog.",
            )

        await db.execute("DELETE FROM catalog_queries WHERE id = $1", query_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_catalog_query error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))