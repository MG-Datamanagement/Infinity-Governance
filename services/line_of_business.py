from fastapi import APIRouter, HTTPException
from uuid import uuid4

from models.line_of_business_schemas import DomainCreateRequest

router = APIRouter(tags=["Line of Business"])

@router.post("/api/v1/line-of-business")
async def create_line_of_business(request: DomainCreateRequest):
    from app import db


    owner = await db.fetch_one(
        "SELECT id, name FROM public.owners WHERE LOWER(name) = LOWER($1)",
        request.owner
    )

    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    owner_id = owner["id"]
    owner_name = owner["name"]

    lob_id = str(uuid4())

 
    parent_id = None
    if request.custom_domain_name:
        parent = await db.fetch_one(
            "SELECT id, parent_lob_id FROM line_of_business WHERE LOWER(name) = LOWER($1)",
            request.custom_domain_name
        )

        if not parent:
            raise HTTPException(status_code=404, detail="Parent LOB not found")

     
        if parent["parent_lob_id"] is not None:
            raise HTTPException(
                status_code=400,
                detail="Cannot assign child to a child domain."
            )

        parent_id = parent["id"]

 
    await db.execute("""
        INSERT INTO line_of_business (id, name, description, owner, color, parent_lob_id)
        VALUES ($1, $2, $3, $4, $5, $6)
    """, lob_id, request.name, request.description, owner_id, request.color, parent_id)

    
    if request.catalog_id:
        await db.execute("""
            INSERT INTO lob_catalog_map (lob_id, catalog_id)
            VALUES ($1, $2)
        """, lob_id, request.catalog_id)

    return {
        "message": "Line of Business created successfully",
        "lob_id": lob_id,
        "owner_name": owner_name
    }

@router.get("/api/v1/line-of-business")
async def get_line_of_business(owner: str = None):
    from app import db

    owner_id = None

    if owner and owner.lower() != "all":
        owner_row = await db.fetch_one(
            "SELECT id, name FROM public.owners WHERE LOWER(name) = LOWER($1)",
            owner
        )

        if not owner_row:
            return {"data": [], "message": "Owner not found"}

        owner_id = owner_row["id"]

    query = """
        SELECT lob.id, lob.name, lob.description, lob.owner, lob.color, lob.parent_lob_id,
               o.name AS owner_name
        FROM line_of_business lob
        LEFT JOIN owners o ON lob.owner = o.id
        WHERE 1=1
    """

    values = []

    if owner_id:
        query += f" AND lob.owner = ${len(values)+1}"
        values.append(owner_id)

    rows = await db.fetch_all(query, *values)

  
    lob_map = {}

    for row in rows:
        lob_map[row["id"]] = {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "owner": row["owner_name"] or "Unknown",
            "color": row["color"],
            "child_domain": []
        }

    root = []

    for row in rows:
        lob_id = row["id"]
        parent_id = row["parent_lob_id"]

        if parent_id and parent_id in lob_map:
            lob_map[parent_id]["child_domain"].append(lob_map[lob_id])
        else:
            root.append(lob_map[lob_id])

   
    def clean(node):
        if "child_domain" in node:
            if not node["child_domain"]:
                node.pop("child_domain")
            else:
                for child in node["child_domain"]:
                    clean(child)

    for item in root:
        clean(item)

    return {
        "count": len(root),  
        "data": root
    }




@router.delete("/api/v1/line-of-business/{lob_id}")
async def delete_line_of_business(lob_id: str):
    from app import db

 
    existing = await db.fetch_one(
        "SELECT id FROM line_of_business WHERE id = $1",
        lob_id
    )

    if not existing:
        raise HTTPException(status_code=404, detail="LOB not found")


    await db.execute("""
        WITH RECURSIVE lob_tree AS (
            SELECT id FROM line_of_business WHERE id = $1
            UNION ALL
            SELECT l.id
            FROM line_of_business l
            INNER JOIN lob_tree lt ON l.parent_lob_id = lt.id
        )
        DELETE FROM line_of_business
        WHERE id IN (SELECT id FROM lob_tree);
    """, lob_id)

    return {
        "message": "Line of Business and all child domains deleted successfully"
    }