import os
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field

load_dotenv()


# ---------------------------------------------------------------------------
# LLM initialisation (shared)
# ---------------------------------------------------------------------------

llm = AzureChatOpenAI(
    openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    model_name=os.getenv("AZURE_OPENAI_API_MODEL_NAME"),
    temperature=0.5,
)


# ===========================================================================
# TABLE CLASSIFICATION  (prefix: /tables)
# ===========================================================================

table_router = APIRouter(
    prefix="/tables",
    tags=["Table Classification"],
)


def create_table_classification_chain():
    """Creates a LangChain processing chain for table classification."""

    system_prompt = """
    You are an expert Data Architect specializing in enterprise data governance and data classification.

    Your task is to analyze a database table using its name and description, then assign exactly ONE
    appropriate data domain tag from the list of available tags provided to you.

    You must think step-by-step about:
    - what type of information the table contains
    - who or what the data represents
    - how the data is typically used in organizations

    Then choose the single best tag from the AVAILABLE TAGS list only.
    Do NOT invent a new tag name — you must pick one that exists in the list.

    Return ONLY valid JSON with:
    {{
        "tag": "<chosen_tag_name_exactly_as_in_available_tags>",
        "confidence_score": <0.0-1.0>,
        "reasoning": "<concise explanation>"
    }}

    ---

    Following are Few Examples for your reference:

    Example 1:
    Table Name: all_booking_agent
    Description: all_booking_agent dataset captures detailed information about booking agents and their associated bookings
    Available Tags: PII
 
    Output:
    {{
        "tag": "PII",
        "confidence_score": 0.65,
        "reasoning": "Includes details about agents and their associated bookings, which may contain identifiable information related to individuals."
    }}
 

    ---

    Example 2:
    Table Name: all_booking
    Description: all_booking dataset consolidates complete booking records
    Available Tags: PII
 
    Output:
    {{
        "tag": "PII",
        "confidence_score": 0.65,
        "reasoning": "Consolidates booking records which may include user-related details that can be linked to individuals, making it potentially identifiable."
    }}
 

    ---
    Example 3:
    Table Name: agent
    Description: agent dataset contains detailed information about agents associated with the operational-data-store with the agent record.
    Available Tags: PII
 
    Output:
    {{
        "tag": "PII",
        "confidence_score": 0.65,
        "reasoning": "Contains information about agents, which may include personal or identifiable details associated with individuals in the system."
    }}
 
    ---

    Now classify the provided table using ONLY the available tags listed.
    Remember:
    - choose exactly ONE tag from the available list
    - agent, all_booking, all_booking_agent, booking, bookingcontact, bookingpassenger, passengerjourneysegment are PII
    - base decision on semantics, not keywords alone
    - provide concise reasoning
    - output JSON only
    """

    user_prompt = (
        "Table Name: {table_name}\n"
        "Table Description: {table_description}\n"
        "Available Tags: {available_tags}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", user_prompt),
    ])

    return prompt | llm | JsonOutputParser()


# Initialise table agent once at module load
table_classification_agent = create_table_classification_chain()


# ---------------------------------------------------------------------------
# Pydantic Models — Table
# ---------------------------------------------------------------------------

class TableInfo(BaseModel):
    """Single-table classification request (manual / ad-hoc use)."""
    table_name: str
    table_description: str


class ClassificationResponse(BaseModel):
    table_name: str
    tag: str
    confidence_score: float
    reasoning: str


class BulkClassifyRequest(BaseModel):
    """
    Bulk-classify all catalogs that belong to a given source.

    Fields
    ------
    source_id              : UUID of the ingested data source
    Require_human_approval : when True the suggested tags are persisted to
                             tag_catalog_assignments; when False (default)
                             the response is preview-only
    assigned_by            : label stored in assigned_by column (default 'ai-auto')
    min_confidence         : only save assignments whose confidence_score is at or
                             above this threshold (default 0.0 → save everything)
    """
    source_id: str
    Require_human_approval: bool = False
    assigned_by: str = "ai-auto"
    min_confidence: float = 0.1


class CatalogClassificationResult(BaseModel):
    catalog_id: str
    table_name: str
    full_name: str
    suggested_tag: str
    tag_id: Optional[str] = None
    confidence_score: float
    reasoning: str
    saved: bool = True


class BulkClassifyResponse(BaseModel):
    source_id: str
    total_catalogs: int
    classified: int
    saved: int
    results: List[CatalogClassificationResult]


# ---------------------------------------------------------------------------
# Helpers — Table
# ---------------------------------------------------------------------------

async def _fetch_available_tags(db) -> List[dict]:
    """Return all tags from the tags table as {id, name, description}."""
    rows = await db.fetch_all("SELECT id, name, description FROM tags ORDER BY name")
    return [
        {"id": str(r["id"]), "name": r["name"], "description": r["description"]}
        for r in rows
    ]


async def _fetch_catalogs_for_source(db, source_id: str) -> List[dict]:
    """
    Return catalogs for source_id where column_count > 0, deduplicated by table_name.
    When the same table_name appears more than once, keeps the one with the most columns.
    """
    rows = await db.fetch_all(
        """
        SELECT
            c.id,
            c.table_name,
            c.full_name,
            c.description,
            COUNT(DISTINCT col.id) AS column_count
        FROM   catalogs c
        JOIN   columns  col ON col.catalog_id = c.id
        WHERE  c.source_id = $1
        GROUP  BY c.id, c.table_name, c.full_name, c.description
        HAVING COUNT(DISTINCT col.id) > 0
        ORDER  BY c.table_name
        """,
        source_id,
    )

    # Deduplicate by table_name — keep entry with highest column_count
    seen: dict = {}
    for r in rows:
        name = r["table_name"]
        if name not in seen or r["column_count"] > seen[name]["column_count"]:
            seen[name] = {
                "id": str(r["id"]),
                "table_name": r["table_name"],
                "full_name": r["full_name"],
                "description": r["description"] or "",
                "column_count": r["column_count"],
            }

    return list(seen.values())


async def _save_tag_assignment(db, tag_id: str, catalog_id: str, assigned_by: str) -> bool:
    """
    Upsert a row into tag_catalog_assignments.
    Returns True on success, False on failure.
    """
    try:
        await db.execute(
            """
            INSERT INTO tag_catalog_assignments (tag_id, catalog_id, assigned_by)
            VALUES ($1, $2, $3)
            ON CONFLICT (tag_id, catalog_id) DO UPDATE
                SET assigned_by  = EXCLUDED.assigned_by,
                    assigned_at  = NOW()
            """,
            tag_id,
            catalog_id,
            assigned_by,
        )
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Endpoints — Table
# ---------------------------------------------------------------------------

@table_router.post("/classify-table", response_model=ClassificationResponse)
async def classify_table(data: TableInfo):
    """
    Ad-hoc single-table classification.
    Uses whatever tags currently exist in the database as the allowed set.
    """
    from app import db, logger  # local import to match project pattern

    try:
        tags = await _fetch_available_tags(db)
        if not tags:
            raise HTTPException(
                status_code=422,
                detail="No tags found in the database. Please create tags first.",
            )

        available_tags_str = ", ".join(t["name"] for t in tags)

        result = table_classification_agent.invoke({
            "table_name": data.table_name,
            "table_description": data.table_description,
            "available_tags": available_tags_str,
        })

        return {
            "table_name": data.table_name,
            "tag": result.get("tag", "Unknown"),
            "confidence_score": result.get("confidence_score", 0.1),
            "reasoning": result.get("reasoning", "No reasoning provided"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent Execution Error: {str(e)}")


@table_router.post("/classify-table/source", response_model=BulkClassifyResponse)
async def classify_source_catalogs(request: BulkClassifyRequest):
    """
    Bulk-classify ALL catalogs ingested from a given source.

    Flow
    ----
    1. Validate the source exists.
    2. Fetch all catalogs for that source.
    3. Fetch all existing tags from the DB.
    4. For each catalog, call the LLM to suggest a tag (from the known tag list).
    5. If Require_human_approval=True AND confidence >= min_confidence, persist to
       tag_catalog_assignments.
    6. Return a preview/summary of every classification result.
    """
    from app import db, logger

    # -- 1. Validate source ------------------------------------------------
    source = await db.fetch_one(
        "SELECT id, name FROM data_sources WHERE id = $1", request.source_id
    )
    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{request.source_id}' not found.")

    # -- 2. Fetch catalogs --------------------------------------------------
    catalogs = await _fetch_catalogs_for_source(db, request.source_id)
    if not catalogs:
        raise HTTPException(
            status_code=404,
            detail=f"No catalogs found for source '{request.source_id}'. Run ingestion first.",
        )

    # -- 3. Fetch available tags -------------------------------------------
    tags = await _fetch_available_tags(db)
    if not tags:
        raise HTTPException(
            status_code=422,
            detail="No tags found in the database. Please create tags first.",
        )

    # Build a fast name→id lookup (case-insensitive)
    tag_name_to_id = {t["name"].lower(): t["id"] for t in tags}
    available_tags_str = ", ".join(t["name"] for t in tags)

    # -- 4. Classify each catalog ------------------------------------------
    results: List[CatalogClassificationResult] = []
    saved_count = 0

    for catalog in catalogs:
        try:
            llm_result = table_classification_agent.invoke({
                "table_name": catalog["table_name"],
                "table_description": catalog["description"] or catalog["table_name"],
                "available_tags": available_tags_str,
            })

            suggested_tag_name: str = llm_result.get("tag", "Unknown")
            confidence: float = float(llm_result.get("confidence_score", 0.1))
            reasoning: str = llm_result.get("reasoning", "No reasoning provided")

            # Resolve tag_id (case-insensitive match)
            tag_id: Optional[str] = tag_name_to_id.get(suggested_tag_name.lower())

            # -- 5. Optionally save to DB ----------------------------------
            saved = False
            if (
                request.Require_human_approval
                and tag_id is not None
                and confidence >= 0.1
            ):
                saved = await _save_tag_assignment(
                    db, tag_id, catalog["id"], request.assigned_by
                )
                if saved:
                    saved_count += 1

            results.append(CatalogClassificationResult(
                catalog_id=catalog["id"],
                table_name=catalog["table_name"],
                full_name=catalog["full_name"],
                suggested_tag=suggested_tag_name,
                tag_id=tag_id,
                confidence_score=confidence,
                reasoning=reasoning,
                saved=True,
            ))

        except Exception as e:
            logger.error(f"Classification failed for catalog {catalog['table_name']}: {e}")
            results.append(CatalogClassificationResult(
                catalog_id=catalog["id"],
                table_name=catalog["table_name"],
                full_name=catalog["full_name"],
                suggested_tag="Error",
                tag_id=None,
                confidence_score=0.1,
                reasoning=f"Classification error: {str(e)}",
                saved=True,
            ))

    # -- 6. Return summary -------------------------------------------------
    return BulkClassifyResponse(
        source_id=request.source_id,
        total_catalogs=len(catalogs),
        classified=sum(1 for r in results if r.suggested_tag != "Error"),
        saved=saved_count,
        results=results,
    )


# ===========================================================================
# COLUMN CLASSIFICATION  (prefix: /columns)
# ===========================================================================

column_router = APIRouter(
    prefix="/columns",
    tags=["Column Classification"],
)


def create_column_classification_chain():
    """Creates a LangChain chain for database column tag classification."""

    system_prompt = """
    You are a Data Privacy and Security Specialist with expertise in data classification,
    compliance, and schema governance.

    Your task is to analyze a database column using its name and description, then assign
    exactly ONE tag from the AVAILABLE TAGS list provided to you.

    You must reason step-by-step about:
    - what the column represents
    - whether it identifies a person or relates to financial activity
    - whether it falls under privacy regulations
    - typical database storage format

    Remainder:
    -bookingid, bookingtype, booking_lead_category, agentid, agencyname, agentrank, agentrlocation, agentsince, agent_tensure_years, agent_seniority_tier mark it has PII
    -bookingutc, bookingchannel, bookingclass, countrycode, status, booking_lead_days, booking_lead_category, used_promo, used_hold, agentbranch mark it has Non-PII


    Do NOT invent a new tag — you must pick one that exists in the AVAILABLE TAGS list.

    Return ONLY valid JSON:
    {{
        "tag": "<chosen_tag_name_exactly_as_in_available_tags>",
        "is_sensitive": <true|false>,
        "data_type": "<SQL_type>",
        "confidence_score": <0.0-1.0>,
        "reasoning": "<concise explanation>"
    }}

    ---

    Following are Few Examples for your reference:

    Example 1:
    Column Name: Booking_id
    Description: Unique identifier for each booking record in the system.
    Available Tags: PII

    Output:
    {{
        "tag": "PII",
        "is_sensitive": true,
        "confidence_score": 0.98,
        "reasoning": "Booking_id is a unique identifier linked to an individual booking record, which can be used to trace or associate activity with a specific person."
    }}

    ---

    Example 2:
    Column Name: bookingutc
    Description: UTC timestamp of the booking made by the agent.
    Available Tags: PII

    Output:
    {{
        "tag": "Non-PII",
        "is_sensitive": true,
        "confidence_score": 0.97,
        "reasoning": "Represents a timestamp of when a booking was made and does not directly identify an individual or contain personal information.."
    }}


    ---

    Now classify the provided column using ONLY the available tags listed.
    Rules:
    - Choose exactly ONE tag from the available list
    - bookingid, bookingtype, booking_lead_category, agentid, agencyname, agentrank, agentrlocation, agentsince, agent_tensure_years, agent_seniority_tier mark it has PII
    - bookingutc, bookingchannel, bookingclass, countrycode, status, booking_lead_days, booking_lead_category, used_promo, used_hold, agentbranch mark it has Non-PII
    - Prefer semantic meaning over keywords
    - Mark is_sensitive = true if data relates to an identifiable person or finances
    - Infer realistic SQL data type
    - Output JSON only



    
    """

    user_prompt = (
        "Column Name: {column_name}\n"
        "Description: {column_description}\n"
        "Available Tags: {available_tags}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", user_prompt),
    ])

    return prompt | llm | JsonOutputParser()


# Initialise column agent once at module load
column_classification_agent = create_column_classification_chain()


# ---------------------------------------------------------------------------
# Pydantic Models — Column
# ---------------------------------------------------------------------------

class ColumnInfo(BaseModel):
    """Single-column ad-hoc classification request."""
    column_name: str = Field(..., min_length=1)
    column_description: str = Field(..., min_length=1)


class ColumnClassificationResponse(BaseModel):
    column_name: str
    tag: str
    is_sensitive: bool
    confidence_score: float
    reasoning: str


class BulkColumnClassifyRequest(BaseModel):
    """
    Bulk-classify all columns that belong to a given source (across all its catalogs).

    Fields
    ------
    source_id       : UUID of the ingested data source
    catalog_id      : (optional) restrict classification to a single catalog/table
    save_to_db      : when True, persist suggested tags to tag_column_assignments;
                      when False (default) return a preview only
    assigned_by     : label stored in the assigned_by column  (default 'ai-auto')
    min_confidence  : only save assignments at or above this threshold (default 0.1)
    """
    source_id: str
    catalog_id: Optional[str] = None
    save_to_db: bool = False
    assigned_by: str = "ai-auto"
    min_confidence: float = 0.1


class ColumnClassificationResult(BaseModel):
    column_id: str
    column_name: str
    description: str
    is_nullable: Optional[bool]
    column_data_type: str
    catalog_id: str
    table_name: str
    suggested_tag: str
    tag_id: Optional[str] = None
    tag_name: Optional[str] = None
    is_sensitive: bool
    confidence_score: float
    reasoning: str
    saved: bool = False


class BulkColumnClassifyResponse(BaseModel):
    source_id: str
    catalog_id: Optional[str]
    total_columns: int
    classified: int
    saved: int
    results: List[ColumnClassificationResult]


# ---------------------------------------------------------------------------
# Helpers — Column
# ---------------------------------------------------------------------------

async def _fetch_columns_for_source(
    db,
    source_id: str,
    catalog_id: Optional[str] = None,
) -> List[dict]:
    """
    Return columns for the given source_id, restricted to catalogs that:
      - have at least one column (column_count > 0)
      - are the canonical catalog for their table_name (highest column_count
        wins when duplicates exist — same dedup rule as _fetch_catalogs_for_source)

    When catalog_id is given, that single catalog is used directly (no dedup needed).
    """
    if catalog_id:
        rows = await db.fetch_all(
            """
            SELECT col.id,
                   col.name         AS column_name,
                   col.description,
                   col.is_nullable,
                   col.data_type    AS column_data_type,
                   col.catalog_id,
                   cat.table_name
            FROM   columns  col
            JOIN   catalogs cat ON cat.id = col.catalog_id
            WHERE  cat.source_id = $1
              AND  col.catalog_id = $2
            ORDER  BY cat.table_name, col.ordinal_position
            """,
            source_id,
            catalog_id,
        )
    else:
        # Restrict to the canonical catalog per table_name:
        # the one catalog_id per table_name that has the most columns.
        rows = await db.fetch_all(
            """
            WITH ranked_catalogs AS (
                SELECT
                    c.id                        AS catalog_id,
                    c.table_name,
                    COUNT(DISTINCT col2.id)     AS column_count,
                    ROW_NUMBER() OVER (
                        PARTITION BY c.table_name
                        ORDER BY COUNT(DISTINCT col2.id) DESC
                    )                           AS rn
                FROM   catalogs c
                JOIN   columns  col2 ON col2.catalog_id = c.id
                WHERE  c.source_id = $1
                GROUP  BY c.id, c.table_name
                HAVING COUNT(DISTINCT col2.id) > 0
            )
            SELECT col.id,
                   col.name         AS column_name,
                   col.description,
                   col.is_nullable,
                   col.data_type    AS column_data_type,
                   col.catalog_id,
                   rc.table_name
            FROM   ranked_catalogs rc
            JOIN   columns col ON col.catalog_id = rc.catalog_id
            WHERE  rc.rn = 1
            ORDER  BY rc.table_name, col.ordinal_position
            """,
            source_id,
        )

    return [
        {
            "id": str(r["id"]),
            "column_name": r["column_name"],
            "description": r["description"] or "",
            "is_nullable": r["is_nullable"],
            "column_data_type": r["column_data_type"] or "UNKNOWN",
            "catalog_id": str(r["catalog_id"]),
            "table_name": r["table_name"],
        }
        for r in rows
    ]


async def _save_tag_column_assignment(
    db,
    tag_id: str,
    column_id: str,
    catalog_id: str,
    confidence_score: float,
    assigned_by: str,
) -> bool:
    """
    Upsert a row into tag_column_assignments.
    Returns True on success, False on failure.
    """
    try:
        await db.execute(
            """
            INSERT INTO tag_column_assignments
                        (tag_id, column_id, catalog_id, confidence_score, assigned_by)
            VALUES      ($1, $2, $3, $4, $5)
            ON CONFLICT (tag_id, column_id) DO UPDATE
                SET confidence_score = EXCLUDED.confidence_score,
                    assigned_by      = EXCLUDED.assigned_by,
                    assigned_at      = NOW()
            """,
            tag_id,
            column_id,
            catalog_id,
            confidence_score,
            assigned_by,
        )
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Endpoints — Column
# ---------------------------------------------------------------------------

@column_router.post(
    "/classify-column",
    response_model=ColumnClassificationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Column classified successfully"},
        422: {"description": "No tags in database / validation error"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
        503: {"description": "Classification service unavailable"},
    },
)
async def classify_column(data: ColumnInfo):
    """
    Ad-hoc single-column classification.
    Fetches the current tag list from the database and asks the LLM to
    pick the best match.
    """
    from app import db, logger  # local import — matches project pattern

    try:
        tags = await _fetch_available_tags(db)
        if not tags:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No tags found in the database. Please create tags first.",
            )

        available_tags_str = ", ".join(t["name"] for t in tags)

        result = column_classification_agent.invoke({
            "column_name": data.column_name,
            "column_description": data.column_description,
            "available_tags": available_tags_str,
        })

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Classification service unavailable",
            )

        return {
            "column_name": data.column_name,
            "tag": result.get("tag", "Unknown"),
            "is_sensitive": result.get("is_sensitive", False),
            "confidence_score": result.get("confidence_score", 0.1),
            "reasoning": result.get("reasoning", "No reasoning provided"),
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        if "rate" in str(e).lower() or "quota" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )
        raise
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Classification service timeout",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution error: {str(e)}",
        )


@column_router.post(
    "/classify-column/source",
    response_model=BulkColumnClassifyResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Bulk classification completed"},
        404: {"description": "Source / columns not found"},
        422: {"description": "No tags in database"},
        500: {"description": "Internal server error"},
    },
)
async def classify_source_columns(request: BulkColumnClassifyRequest):
    """
    Bulk-classify ALL columns ingested from a given source.

    Flow
    ----
    1. Validate the source_id exists in data_sources.
    2. Fetch all columns for that source (optionally filtered by catalog_id).
    3. Fetch all existing tags from the tags table.
    4. For each column, call the LLM to suggest the best tag from the known list.
    5. If save_to_db=True AND confidence >= min_confidence, upsert into
       tag_column_assignments (confidence_score is also stored).
    6. Return a full preview/summary — including which rows were saved.

    Set save_to_db=false (default) to preview suggestions before committing.
    """
    from app import db, logger

    # -- 1. Validate source ------------------------------------------------
    source = await db.fetch_one(
        "SELECT id, name FROM data_sources WHERE id = $1", request.source_id
    )
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source '{request.source_id}' not found.",
        )

    # -- 2. Fetch columns --------------------------------------------------
    columns = await _fetch_columns_for_source(db, request.source_id, request.catalog_id)
    if not columns:
        detail = (
            f"No columns found for catalog '{request.catalog_id}'."
            if request.catalog_id
            else f"No columns found for source '{request.source_id}'. Run ingestion first."
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    # -- 3. Fetch available tags -------------------------------------------
    tags = await _fetch_available_tags(db)
    if not tags:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No tags found in the database. Please create tags first.",
        )

    # Fast case-insensitive name → id lookup (and reverse)
    tag_name_to_id = {t["name"].lower(): t["id"] for t in tags}
    tag_id_to_name = {t["id"]: t["name"] for t in tags}
    available_tags_str = ", ".join(t["name"] for t in tags)

    # -- 4. Classify each column -------------------------------------------
    results: List[ColumnClassificationResult] = []
    saved_count = 0

    for col in columns:
        try:
            llm_result = column_classification_agent.invoke({
                "column_name": col["column_name"],
                # Fall back to column name if no description ingested
                "column_description": col["description"] or col["column_name"],
                "available_tags": available_tags_str,
            })

            suggested_tag: str  = llm_result.get("tag", "Unknown")
            confidence: float   = float(llm_result.get("confidence_score", 0.1))
            is_sensitive: bool  = bool(llm_result.get("is_sensitive", False))
            reasoning: str      = llm_result.get("reasoning", "No reasoning provided")

            # Resolve tag_id (case-insensitive)
            tag_id: Optional[str] = tag_name_to_id.get(suggested_tag.lower())

            # -- 5. Optionally save to DB ----------------------------------
            saved = False
            if (
                request.save_to_db
                and tag_id is not None
                and confidence >= 0.1
            ):
                saved = await _save_tag_column_assignment(
                    db,
                    tag_id,
                    col["id"],
                    col["catalog_id"],
                    confidence,
                    request.assigned_by,
                )
                if saved:
                    saved_count += 1

            results.append(ColumnClassificationResult(
                column_id=col["id"],
                column_name=col["column_name"],
                description=col["description"],
                is_nullable=col["is_nullable"],
                column_data_type=col["column_data_type"],
                catalog_id=col["catalog_id"],
                table_name=col["table_name"],
                suggested_tag=suggested_tag,
                tag_id=tag_id,
                tag_name=tag_id_to_name.get(tag_id) if tag_id else None,
                is_sensitive=is_sensitive,
                confidence_score=confidence,
                reasoning=reasoning,
                saved=True,
            ))

        except Exception as e:
            logger.error(
                f"Classification failed for column '{col['column_name']}' "
                f"(catalog {col['catalog_id']}): {e}"
            )
            results.append(ColumnClassificationResult(
                column_id=col["id"],
                column_name=col["column_name"],
                description=col["description"],
                is_nullable=col["is_nullable"],
                column_data_type=col["column_data_type"],
                catalog_id=col["catalog_id"],
                table_name=col["table_name"],
                suggested_tag="Error",
                tag_id=None,
                tag_name=None,
                is_sensitive=False,
                confidence_score=0.1,
                reasoning=f"Classification error: {str(e)}",
                saved=True,
            ))

    # -- 6. Return summary -------------------------------------------------
    return BulkColumnClassifyResponse(
        source_id=request.source_id,
        catalog_id=request.catalog_id,
        total_columns=len(columns),
        classified=sum(1 for r in results if r.suggested_tag != "Error"),
        saved=saved_count,
        results=results,
    )


class BulkColumnClassifyByCatalogRequest(BaseModel):
    """
    Bulk-classify all columns that belong to a given catalog (table).

    Fields
    ------
    catalog_id      : UUID of the catalog (table) to classify
    save_to_db      : when True, persist suggested tags to tag_column_assignments
    assigned_by     : label stored in the assigned_by column (default 'ai-auto')
    min_confidence  : only save assignments at or above this threshold (default 0.1)
    """
    catalog_id: str
    save_to_db: bool = True
    assigned_by: str = "ai-auto"
    min_confidence: float = 0.1


@column_router.post(
    "/classify-column/catalog",
    response_model=BulkColumnClassifyResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Bulk classification completed"},
        404: {"description": "Catalog / columns not found"},
        422: {"description": "No tags in database"},
        500: {"description": "Internal server error"},
    },
)
async def classify_catalog_columns(request: BulkColumnClassifyByCatalogRequest):
    """
    Bulk-classify ALL columns belonging to a specific catalog (table).

    Flow
    ----
    1. Validate the catalog_id exists and fetch its parent source_id.
    2. Fetch all columns for that catalog.
    3. Fetch all existing tags from the tags table.
    4. For each column, call the LLM to suggest the best tag from the known list.
    5. If save_to_db=True AND confidence >= min_confidence, upsert into
       tag_column_assignments (confidence_score is also stored).
    6. Return a full preview/summary — including which rows were saved.
    """
    from app import db, logger

    # -- 1. Validate catalog -----------------------------------------------
    catalog = await db.fetch_one(
        "SELECT id, source_id, table_name FROM catalogs WHERE id = $1",
        request.catalog_id,
    )
    if not catalog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Catalog '{request.catalog_id}' not found.",
        )

    source_id: str = str(catalog["source_id"])

    # -- 2. Fetch columns --------------------------------------------------
    columns = await _fetch_columns_for_source(db, source_id, catalog_id=request.catalog_id)
    if not columns:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No columns found for catalog '{request.catalog_id}'. Run ingestion first.",
        )

    # -- 3. Fetch available tags -------------------------------------------
    tags = await _fetch_available_tags(db)
    if not tags:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No tags found in the database. Please create tags first.",
        )

    tag_name_to_id = {t["name"].lower(): t["id"] for t in tags}
    tag_id_to_name = {t["id"]: t["name"] for t in tags}
    available_tags_str = ", ".join(t["name"] for t in tags)

    # -- 4. Classify each column -------------------------------------------
    results: List[ColumnClassificationResult] = []
    saved_count = 0

    for col in columns:
        try:
            llm_result = column_classification_agent.invoke({
                "column_name": col["column_name"],
                "column_description": col["description"] or col["column_name"],
                "available_tags": available_tags_str,
            })

            suggested_tag: str = llm_result.get("tag", "Unknown")
            confidence: float  = float(llm_result.get("confidence_score", 0.1))
            is_sensitive: bool = bool(llm_result.get("is_sensitive", False))
            reasoning: str     = llm_result.get("reasoning", "No reasoning provided")

            tag_id: Optional[str] = tag_name_to_id.get(suggested_tag.lower())

            # -- 5. Optionally save to DB ----------------------------------
            saved = False
            if (
                request.save_to_db
                and tag_id is not None
                and confidence >= 0.1
            ):
                saved = await _save_tag_column_assignment(
                    db,
                    tag_id,
                    col["id"],
                    col["catalog_id"],
                    confidence,
                    request.assigned_by,
                )
                if saved:
                    saved_count += 1

            results.append(ColumnClassificationResult(
                column_id=col["id"],
                column_name=col["column_name"],
                description=col["description"],
                is_nullable=col["is_nullable"],
                column_data_type=col["column_data_type"],
                catalog_id=col["catalog_id"],
                table_name=col["table_name"],
                suggested_tag=suggested_tag,
                tag_id=tag_id,
                tag_name=tag_id_to_name.get(tag_id) if tag_id else None,
                is_sensitive=is_sensitive,
                confidence_score=confidence,
                reasoning=reasoning,
                saved=True,
            ))

        except Exception as e:
            logger.error(
                f"Classification failed for column '{col['column_name']}' "
                f"(catalog {col['catalog_id']}): {e}"
            )
            results.append(ColumnClassificationResult(
                column_id=col["id"],
                column_name=col["column_name"],
                description=col["description"],
                is_nullable=col["is_nullable"],
                column_data_type=col["column_data_type"],
                catalog_id=col["catalog_id"],
                table_name=col["table_name"],
                suggested_tag="Error",
                tag_id=None,
                tag_name=None,
                is_sensitive=False,
                confidence_score=0.1,
                reasoning=f"Classification error: {str(e)}",
                saved=True,
            ))

    # -- 6. Return summary -------------------------------------------------
    return BulkColumnClassifyResponse(
        source_id=source_id,
        total_columns=len(columns),
        classified=sum(1 for r in results if r.suggested_tag != "Error"),
        saved=saved_count,
        results=results,
    )



# ===========================================================================
# FULL SCAN  (prefix: /scan)
# Accepts a source_id, runs table + column classification for the entire
# source, auto-saves all assignments, and returns a rich summary report.
# ===========================================================================

scan_router = APIRouter(
    prefix="/scan",
    tags=["Full Scan"],
)


# ---------------------------------------------------------------------------
# Pydantic Models — Full Scan
# ---------------------------------------------------------------------------

class FullScanRequest(BaseModel):
    """
    Run a full classification scan across all tables and columns of a source.

    Fields
    ------
    source_id      : UUID of the ingested data source
    save_to_db     : persist all assignments (default True)
    assigned_by    : label stored in assigned_by columns (default 'ai-auto')
    min_confidence : skip saving assignments below this threshold (default 0.1)
    """
    source_id: str
    save_to_db: bool = True
    assigned_by: str = "ai-auto"
    min_confidence: float = 0.1


class TableScanResult(BaseModel):
    """Per-table result in the full scan response."""
    catalog_id: str
    table_name: str
    full_name: str
    # Table-level tag
    table_tag: str
    table_tag_id: Optional[str] = None
    table_confidence: float
    table_reasoning: str
    table_tag_saved: bool
    is_tagged: bool                          # True when table_tag != "Error" / "Unknown"
    # Column-level summary for this table
    total_columns: int
    columns_classified: int
    columns_saved: int
    sensitive_columns: int                   # columns where is_sensitive=True
    # Per-tag column breakdown  {tag_name: count}
    column_tag_breakdown: dict


class TagSummary(BaseModel):
    """Aggregate count for a single tag across the whole source."""
    tag_name: str
    tables_tagged: int
    columns_tagged: int
    columns_saved: int


class FullScanResponse(BaseModel):
    source_id: str
    source_name: str
    # Top-level counters
    total_tables: int
    tables_tagged: int
    tables_saved: int
    total_columns: int
    columns_classified: int
    columns_saved: int
    total_sensitive_columns: int
    # Per-tag breakdown (sorted by total hits descending)
    tag_summary: List[TagSummary]
    # Per-table details
    tables: List[TableScanResult]


# ---------------------------------------------------------------------------
# Endpoint — Full Scan
# ---------------------------------------------------------------------------

@scan_router.post(
    "/source",
    response_model=FullScanResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Full scan completed"},
        404: {"description": "Source not found or no data ingested"},
        422: {"description": "No tags configured in the database"},
        500: {"description": "Internal server error"},
    },
)
async def full_scan_source(request: FullScanRequest):
    """
    Full classification scan for an entire source.

    Flow
    ----
    1. Validate source exists.
    2. Fetch all catalogs (tables) and all columns for the source.
    3. Fetch all available tags.
    4. For every table  → run table-level LLM classification.
    5. For every column → run column-level LLM classification.
    6. Optionally persist both table and column assignments to the DB.
    7. Return a summary with:
       - total tables scanned, how many got tagged, how many saved
       - total columns scanned, classified, saved, and sensitive count
       - per-tag breakdown (tables_tagged, columns_tagged, columns_saved)
       - per-table detail including is_tagged flag and column tag breakdown
    """
    from app import db, logger

    # -- 1. Validate source ------------------------------------------------
    source = await db.fetch_one(
        "SELECT id, name FROM data_sources WHERE id = $1", request.source_id
    )
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source '{request.source_id}' not found.",
        )
    source_name: str = source["name"]

    # -- 2. Fetch catalogs & columns ---------------------------------------
    catalogs = await _fetch_catalogs_for_source(db, request.source_id)
    if not catalogs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No catalogs found for source '{request.source_id}'. Run ingestion first.",
        )

    all_columns = await _fetch_columns_for_source(db, request.source_id)

    # Group columns by catalog_id for quick per-table lookup
    from collections import defaultdict
    columns_by_catalog: dict = defaultdict(list)
    for col in all_columns:
        columns_by_catalog[col["catalog_id"]].append(col)

    # -- 3. Fetch available tags -------------------------------------------
    tags = await _fetch_available_tags(db)
    if not tags:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No tags found in the database. Please create tags first.",
        )

    tag_name_to_id = {t["name"].lower(): t["id"] for t in tags}
    available_tags_str = ", ".join(t["name"] for t in tags)

    # Accumulators
    table_results: List[TableScanResult] = []
    # {tag_name: {tables_tagged, columns_tagged, columns_saved}}
    tag_agg: dict = defaultdict(lambda: {"tables_tagged": 0, "tables_saved": 0, "columns_tagged": 0, "columns_saved": 0})

    total_columns_classified = 0
    total_columns_saved = 0
    total_sensitive_columns = 0
    tables_saved_count = 0

    # -- 4 & 5. Classify each table + its columns --------------------------
    for catalog in catalogs:
        catalog_id = catalog["id"]

        # ---- 4. Table classification ------------------------------------
        table_tag = "Error"
        table_tag_id: Optional[str] = None
        table_confidence = 0.1
        table_reasoning = "Classification error"
        table_tag_saved = False

        try:
            tbl_result = table_classification_agent.invoke({
                "table_name": catalog["table_name"],
                "table_description": catalog["description"] or catalog["table_name"],
                "available_tags": available_tags_str,
            })
            table_tag       = tbl_result.get("tag", "Unknown")
            table_confidence = float(tbl_result.get("confidence_score", 0.1))
            table_reasoning  = tbl_result.get("reasoning", "No reasoning provided")
            table_tag_id     = tag_name_to_id.get(table_tag.lower())

            if (
                request.save_to_db
                and table_tag_id is not None
                and table_confidence >= 0.1
            ):
                table_tag_saved = await _save_tag_assignment(
                    db, table_tag_id, catalog_id, request.assigned_by
                )
                if table_tag_saved:
                    tables_saved_count += 1

            if table_tag not in ("Error", "Unknown"):
                tag_agg[table_tag]["tables_tagged"] += 1
                if table_tag_saved:
                    tag_agg[table_tag]["tables_saved"] += 1

        except Exception as e:
            logger.error(f"[FullScan] Table classification failed for '{catalog['table_name']}': {e}")

        is_tagged = table_tag not in ("Error", "Unknown")

        # ---- 5. Column classification for this table --------------------
        table_cols = columns_by_catalog.get(catalog_id, [])
        col_classified = 0
        col_saved = 0
        col_sensitive = 0
        col_tag_breakdown: dict = defaultdict(int)

        for col in table_cols:
            try:
                col_result = column_classification_agent.invoke({
                    "column_name": col["column_name"],
                    "column_description": col["description"] or col["column_name"],
                    "available_tags": available_tags_str,
                })

                suggested_tag: str = col_result.get("tag", "Unknown")
                confidence: float  = float(col_result.get("confidence_score", 0.1))
                is_sensitive: bool = bool(col_result.get("is_sensitive", False))
                col_tag_id: Optional[str] = tag_name_to_id.get(suggested_tag.lower())

                if suggested_tag not in ("Error", "Unknown"):
                    col_classified += 1
                    col_tag_breakdown[suggested_tag] += 1
                    tag_agg[suggested_tag]["columns_tagged"] += 1

                if is_sensitive:
                    col_sensitive += 1

                if (
                    request.save_to_db
                    and col_tag_id is not None
                    and confidence >= 0.1
                ):
                    saved = await _save_tag_column_assignment(
                        db,
                        col_tag_id,
                        col["id"],
                        catalog_id,
                        confidence,
                        request.assigned_by,
                    )
                    if saved:
                        col_saved += 1
                        tag_agg[suggested_tag]["columns_saved"] += 1

            except Exception as e:
                logger.error(
                    f"[FullScan] Column classification failed for "
                    f"'{col['column_name']}' in '{catalog['table_name']}': {e}"
                )

        total_columns_classified += col_classified
        total_columns_saved      += col_saved
        total_sensitive_columns  += col_sensitive

        table_results.append(TableScanResult(
            catalog_id=catalog_id,
            table_name=catalog["table_name"],
            full_name=catalog["full_name"],
            table_tag=table_tag,
            table_tag_id=table_tag_id,
            table_confidence=table_confidence,
            table_reasoning=table_reasoning,
            table_tag_saved=table_tag_saved,
            is_tagged=is_tagged,
            total_columns=len(table_cols),
            columns_classified=col_classified,
            columns_saved=col_saved,
            sensitive_columns=col_sensitive,
            column_tag_breakdown=dict(col_tag_breakdown),
        ))

    # -- 6. Build tag summary ---------------------------------------------
    tag_summary = sorted(
        [
            TagSummary(
                tag_name=tag_name,
                tables_tagged=agg["tables_tagged"],
                columns_tagged=agg["columns_tagged"],
                tables_saved=agg["tables_saved"],
                columns_saved=agg["columns_saved"],
                total_detected=agg["tables_tagged"] + agg["columns_tagged"],
                total_assigned=agg["tables_saved"]  + agg["columns_saved"],
            )
            for tag_name, agg in tag_agg.items()
        ],
        key=lambda x: x.columns_tagged + x.tables_tagged,
        reverse=True,
    )

    # -- 7. Return full report --------------------------------------------
    return FullScanResponse(
        source_id=request.source_id,
        source_name=source_name,
        total_tables=len(catalogs),
        tables_tagged=sum(1 for t in table_results if t.is_tagged),
        tables_saved=tables_saved_count,
        total_columns=len(all_columns),
        columns_classified=total_columns_classified,
        columns_saved=total_columns_saved,
        total_sensitive_columns=total_sensitive_columns,
        tag_summary=tag_summary,
        tables=table_results,
    )



from fastapi import FastAPI as _FastAPI  # noqa: E402 — used only for the shim below

router = APIRouter()
router.include_router(table_router)
router.include_router(column_router)
router.include_router(scan_router)