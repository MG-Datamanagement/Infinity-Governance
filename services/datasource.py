from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional
import json
import csv
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from models import (
    DataSource,
    SimpleDataSource,
    DataSourceCreatePostgres,
    DataSourceCreateMySQL,
    DataSourceCreateMongoDB,
    DataSourceCreateSnowflake,
    DataSourceCreateCockroachDB,
    DataSourceCreateAthena,
    DataSourceCreateCSV,
    DataSourceCreateDynamoDB,
    DataSourceCreateGlue,
    DataSourceCreateMSSQL,
    DataSourceCreateRedshift,
    IngestionRequest,
    IngestionResponse,
    SourceType,
    JobStatus,
)

router = APIRouter(tags=["Data Sources"])


# ============================================================================
# Data Source Management
# ============================================================================

@router.post("/api/v1/sources/postgres", response_model=DataSource)
async def create_source_postgres(source: DataSourceCreatePostgres):
    """Register a new PostgreSQL data source"""
    from app import db, log_api_action, logger

    try:
        existing = await db.fetch_one("SELECT id FROM data_sources WHERE name = $1", source.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Source with name '{source.name}' already exists")

        result = await db.fetch_one("""
            INSERT INTO data_sources (
                name, source_type, connection_details, description,
                include_views, include_tables, schema_pattern, table_pattern,
                schedule, owner_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id, name, source_type, connection_details, description,
                      include_views, include_tables, schema_pattern, table_pattern,
                      status, schedule, owner_id, created_at, updated_at, last_ingested_at
        """,
        source.name,
        source.source_type.value,
        json.dumps(source.connection_details.dict(exclude_none=True)),
        source.description,
        source.include_views,
        source.include_tables,
        json.dumps(source.schema_pattern) if source.schema_pattern else None,
        json.dumps(source.table_pattern) if source.table_pattern else None,
        source.schedule or "00:00 GMT+5:30",
        source.owner_id
        )

        data = dict(result)
        data['id'] = str(data['id'])
        data['owner_id'] = str(data['owner_id']) if data.get('owner_id') else None
        data['connection_details'] = json.loads(data['connection_details']) if data['connection_details'] else {}
        data['schema_pattern'] = json.loads(data['schema_pattern']) if data['schema_pattern'] else None
        data['table_pattern'] = json.loads(data['table_pattern']) if data['table_pattern'] else None

        await log_api_action(
            endpoint="/sources/postgres", method="POST",
            action_summary=f"New Postgres data source registered: {source.name}",
            entity_type="data_source", entity_id=data['id'], entity_name=source.name,
            owner_id=source.owner_id,
            request_body={"name": source.name, "source_type": source.source_type.value}
        )
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating postgres source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/sources/mysql", response_model=DataSource)
async def create_source_mysql(source: DataSourceCreateMySQL):
    """Register a new MySQL data source"""
    from app import db, log_api_action, logger

    try:
        existing = await db.fetch_one("SELECT id FROM data_sources WHERE name = $1", source.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Source with name '{source.name}' already exists")

        result = await db.fetch_one("""
            INSERT INTO data_sources (
                name, source_type, connection_details, description,
                include_views, include_tables, schema_pattern, table_pattern,
                schedule, owner_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id, name, source_type, connection_details, description,
                      include_views, include_tables, schema_pattern, table_pattern,
                      status, schedule, owner_id, created_at, updated_at, last_ingested_at
        """,
        source.name,
        source.source_type.value,
        json.dumps(source.connection_details.dict(exclude_none=True)),
        source.description,
        source.include_views,
        source.include_tables,
        json.dumps(source.schema_pattern) if source.schema_pattern else None,
        json.dumps(source.table_pattern) if source.table_pattern else None,
        source.schedule or "00:00 GMT+5:30",
        source.owner_id
        )

        data = dict(result)
        data['id'] = str(data['id'])
        data['owner_id'] = str(data['owner_id']) if data.get('owner_id') else None
        data['connection_details'] = json.loads(data['connection_details']) if data['connection_details'] else {}
        data['schema_pattern'] = json.loads(data['schema_pattern']) if data['schema_pattern'] else None
        data['table_pattern'] = json.loads(data['table_pattern']) if data['table_pattern'] else None

        await log_api_action(
            endpoint="/sources/mysql", method="POST",
            action_summary=f"New MySQL data source registered: {source.name}",
            entity_type="data_source", entity_id=data['id'], entity_name=source.name,
            owner_id=source.owner_id,
            request_body={"name": source.name, "source_type": source.source_type.value}
        )
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating mysql source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/sources/mongodb", response_model=DataSource)
async def create_source_mongodb(source: DataSourceCreateMongoDB):
    """Register a new MongoDB data source"""
    from app import db, log_api_action, logger

    try:
        existing = await db.fetch_one("SELECT id FROM data_sources WHERE name = $1", source.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Source with name '{source.name}' already exists")

        result = await db.fetch_one("""
            INSERT INTO data_sources (
                name, source_type, connection_details, description,
                include_views, include_tables, schema_pattern, table_pattern,
                schedule, owner_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id, name, source_type, connection_details, description,
                      include_views, include_tables, schema_pattern, table_pattern,
                      status, schedule, owner_id, created_at, updated_at, last_ingested_at
        """,
        source.name,
        source.source_type.value,
        json.dumps(source.connection_details.dict(exclude_none=True)),
        source.description,
        source.include_views,
        source.include_tables,
        json.dumps(source.schema_pattern) if source.schema_pattern else None,
        json.dumps(source.table_pattern) if source.table_pattern else None,
        source.schedule or "00:00 GMT+5:30",
        source.owner_id
        )

        data = dict(result)
        data['id'] = str(data['id'])
        data['owner_id'] = str(data['owner_id']) if data.get('owner_id') else None
        data['connection_details'] = json.loads(data['connection_details']) if data['connection_details'] else {}
        data['schema_pattern'] = json.loads(data['schema_pattern']) if data['schema_pattern'] else None
        data['table_pattern'] = json.loads(data['table_pattern']) if data['table_pattern'] else None

        await log_api_action(
            endpoint="/sources/mongodb", method="POST",
            action_summary=f"New MongoDB data source registered: {source.name}",
            entity_type="data_source", entity_id=data['id'], entity_name=source.name,
            owner_id=source.owner_id,
            request_body={"name": source.name, "source_type": source.source_type.value}
        )
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating mongodb source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/sources/snowflake", response_model=DataSource)
async def create_source_snowflake(source: DataSourceCreateSnowflake):
    """Register a new Snowflake data source"""
    from app import db, log_api_action, logger

    try:
        existing = await db.fetch_one("SELECT id FROM data_sources WHERE name = $1", source.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Source with name '{source.name}' already exists")

        result = await db.fetch_one("""
            INSERT INTO data_sources (
                name, source_type, connection_details, description,
                include_views, include_tables, schema_pattern, table_pattern,
                schedule, owner_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id, name, source_type, connection_details, description,
                      include_views, include_tables, schema_pattern, table_pattern,
                      status, schedule, owner_id, created_at, updated_at, last_ingested_at
        """,
        source.name,
        source.source_type.value,
        json.dumps(source.connection_details.dict(exclude_none=True)),
        source.description,
        source.include_views,
        source.include_tables,
        json.dumps(source.schema_pattern) if source.schema_pattern else None,
        json.dumps(source.table_pattern) if source.table_pattern else None,
        source.schedule or "00:00 GMT+5:30",
        source.owner_id
        )

        data = dict(result)
        data['id'] = str(data['id'])
        data['owner_id'] = str(data['owner_id']) if data.get('owner_id') else None
        data['connection_details'] = json.loads(data['connection_details']) if data['connection_details'] else {}
        data['schema_pattern'] = json.loads(data['schema_pattern']) if data['schema_pattern'] else None
        data['table_pattern'] = json.loads(data['table_pattern']) if data['table_pattern'] else None

        await log_api_action(
            endpoint="/sources/snowflake", method="POST",
            action_summary=f"New Snowflake data source registered: {source.name}",
            entity_type="data_source", entity_id=data['id'], entity_name=source.name,
            owner_id=source.owner_id,
            request_body={"name": source.name, "source_type": source.source_type.value}
        )
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating snowflake source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/sources/cockroachdb", response_model=DataSource)
async def create_source_cockroach(source: DataSourceCreateCockroachDB):
    """Register a new CockroachDB data source"""
    from app import db, log_api_action, logger

    try:
        existing = await db.fetch_one("SELECT id FROM data_sources WHERE name = $1", source.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Source with name '{source.name}' already exists")

        result = await db.fetch_one("""
            INSERT INTO data_sources (
                name, source_type, connection_details, description,
                include_views, include_tables, schema_pattern, table_pattern,
                schedule, owner_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id, name, source_type, connection_details, description,
                      include_views, include_tables, schema_pattern, table_pattern,
                      status, schedule, owner_id, created_at, updated_at, last_ingested_at
        """,
        source.name,
        source.source_type.value,
        json.dumps(source.connection_details.dict(exclude_none=True)),
        source.description,
        source.include_views,
        source.include_tables,
        json.dumps(source.schema_pattern) if source.schema_pattern else None,
        json.dumps(source.table_pattern) if source.table_pattern else None,
        source.schedule or "00:00 GMT+5:30",
        source.owner_id
        )

        data = dict(result)
        data['id'] = str(data['id'])
        data['owner_id'] = str(data['owner_id']) if data.get('owner_id') else None
        data['connection_details'] = json.loads(data['connection_details']) if data['connection_details'] else {}
        data['schema_pattern'] = json.loads(data['schema_pattern']) if data['schema_pattern'] else None
        data['table_pattern'] = json.loads(data['table_pattern']) if data['table_pattern'] else None

        await log_api_action(
            endpoint="/sources/cockroachdb", method="POST",
            action_summary=f"New CockroachDB data source registered: {source.name}",
            entity_type="data_source", entity_id=data['id'], entity_name=source.name,
            owner_id=source.owner_id,
            request_body={"name": source.name, "source_type": source.source_type.value}
        )
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating cockroachdb source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/sources/athena", response_model=DataSource)
async def create_source_athena(source: DataSourceCreateAthena):
    """Register a new Athena data source"""
    from app import db, log_api_action, logger

    try:
        existing = await db.fetch_one("SELECT id FROM data_sources WHERE name = $1", source.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Source with name '{source.name}' already exists")

        result = await db.fetch_one("""
            INSERT INTO data_sources (
                name, source_type, connection_details, description,
                include_views, include_tables, schema_pattern, table_pattern,
                schedule, owner_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id, name, source_type, connection_details, description,
                      include_views, include_tables, schema_pattern, table_pattern,
                      status, schedule, owner_id, created_at, updated_at, last_ingested_at
        """,
        source.name,
        source.source_type.value,
        json.dumps(source.connection_details.dict(exclude_none=True)),
        source.description,
        source.include_views,
        source.include_tables,
        json.dumps(source.schema_pattern) if source.schema_pattern else None,
        json.dumps(source.table_pattern) if source.table_pattern else None,
        source.schedule or "00:00 GMT+5:30",
        source.owner_id
        )

        data = dict(result)
        data['id'] = str(data['id'])
        data['owner_id'] = str(data['owner_id']) if data.get('owner_id') else None
        data['connection_details'] = json.loads(data['connection_details']) if data['connection_details'] else {}
        data['schema_pattern'] = json.loads(data['schema_pattern']) if data['schema_pattern'] else None
        data['table_pattern'] = json.loads(data['table_pattern']) if data['table_pattern'] else None

        await log_api_action(
            endpoint="/sources/athena", method="POST",
            action_summary=f"New Athena data source registered: {source.name}",
            entity_type="data_source", entity_id=data['id'], entity_name=source.name,
            owner_id=source.owner_id,
            request_body={"name": source.name, "source_type": source.source_type.value}
        )
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating athena source: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/sources/csv", response_model=DataSource)
async def create_source_csv(source: DataSourceCreateCSV):
    """Register a new CSV-over-URL data source"""
    from app import db, log_api_action, logger
    
    try:
        # Prevent duplicate names (same as Athena)
        existing = await db.fetch_one("SELECT id FROM data_sources WHERE name = $1", source.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Source with name '{source.name}' already exists")

        # Prepare values for insertion
        conn_details_dict = source.connection_details.dict(exclude_none=True)

        result = await db.fetch_one("""
            INSERT INTO data_sources (
                name, source_type, connection_details, description,
                include_views, include_tables,        -- you may ignore / set false for CSV
                schema_pattern, table_pattern,
                schedule, owner_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id, name, source_type, connection_details, description,
                      include_views, include_tables, schema_pattern, table_pattern,
                      status, schedule, owner_id, created_at, updated_at, last_ingested_at
        """,
            source.name,
            source.source_type.value,
            json.dumps(conn_details_dict),
            source.description,
            False,                               # include_views → usually false for CSV
            True,                                # include_tables → treat CSV as one table
            None,
            None,
            source.schedule or "00:00 GMT+5:30",
            source.owner_id
        )

        # Prepare response (same pattern as Athena)
        data = dict(result)
        data['id'] = str(data['id'])
        data['owner_id'] = str(data['owner_id']) if data.get('owner_id') else None
        data['connection_details'] = json.loads(data['connection_details']) if data['connection_details'] else {}
        data['schema_pattern'] = json.loads(data['schema_pattern']) if data['schema_pattern'] else None
        data['table_pattern'] = json.loads(data['table_pattern']) if data['table_pattern'] else None

        await log_api_action(
            endpoint="/sources/csv", method="POST",
            action_summary=f"New CSV data source registered: {source.name}",
            entity_type="data_source", entity_id=data['id'], entity_name=source.name,
            owner_id=source.owner_id,
            request_body={"name": source.name, "source_type": source.source_type.value}
        )

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating CSV source: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/sources/dynamodb", response_model=DataSource)
async def create_source_dynamodb(source: DataSourceCreateDynamoDB):
    """Register a new DynamoDB data source"""
    from app import db, log_api_action, logger  # adjust imports as needed

    try:
        # Prevent duplicate names (consistent with Athena)
        existing = await db.fetch_one("SELECT id FROM data_sources WHERE name = $1", source.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Source with name '{source.name}' already exists")

        # Prepare nested JSON blobs
        conn_details_dict = source.connection_details.dict(exclude_none=True)
        # advanced_dict = source.advanced.dict(exclude_none=True) if source.advanced else {}
        # advanced_dict = source.advanced if source.advanced else {}
        # advanced_dict = source.advanced.dict(exclude_none=True) if source.advanced else {}
        # advanced_dict = source.advanced if source.advanced else {}

        # For DynamoDB we usually set include_views=False (no views concept)
        result = await db.fetch_one("""
            INSERT INTO data_sources (
                name, source_type, connection_details, description,
                include_views, include_tables, schema_pattern, table_pattern,
                schedule, owner_id
                schedule, owner_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id, name, source_type, connection_details, description,
                      include_views, include_tables, schema_pattern, table_pattern,
                      status, schedule, owner_id, created_at, updated_at, last_ingested_at
                      status, schedule, owner_id, created_at, updated_at, last_ingested_at
        """,
            source.name,
            source.source_type.value,
            json.dumps(conn_details_dict),
            source.description,
            False,  # include_views – DynamoDB has no views
            source.include_tables,
            None,   # schema_pattern – rarely used for DynamoDB
            json.dumps(source.table_pattern) if source.table_pattern else None,
            source.schedule or "00:00 GMT+5:30",
            source.owner_id
            # json.dumps(advanced_dict) if advanced_dict else None
        )

        # Format response (same pattern as Athena)
        data = dict(result)
        data['id'] = str(data['id'])
        data['owner_id'] = str(data['owner_id']) if data.get('owner_id') else None
        data['connection_details'] = json.loads(data['connection_details']) if data['connection_details'] else {}
        data['table_pattern'] = json.loads(data['table_pattern']) if data['table_pattern'] else None
        # data['advanced_options'] = json.loads(data['advanced_options']) if data.get('advanced_options') else {}
        # data['advanced_options'] = json.loads(data['advanced_options']) if data.get('advanced_options') else {}

        await log_api_action(
            endpoint="/sources/dynamodb", method="POST",
            action_summary=f"New DynamoDB data source registered: {source.name}",
            entity_type="data_source", entity_id=data['id'], entity_name=source.name,
            owner_id=source.owner_id,
            request_body={"name": source.name, "source_type": source.source_type.value}
        )

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating DynamoDB source: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/sources/glue", response_model=DataSource)
async def create_source_glue(source: DataSourceCreateGlue):
    """Register a new AWS Glue Data Catalog data source"""
    from app import db, log_api_action, logger
    import json

    try:
        existing = await db.fetch_one("SELECT id FROM data_sources WHERE name = $1", source.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Source with name '{source.name}' already exists")

        # Prepare patterns as JSON (same as Athena)
        schema_json = json.dumps(source.schema_pattern) if source.schema_pattern else None
        table_json = json.dumps(source.table_pattern) if source.table_pattern else None

        result = await db.fetch_one("""
            INSERT INTO data_sources (
                name, source_type, connection_details, description,
                include_views, include_tables, schema_pattern, table_pattern,
                schedule, owner_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id, name, source_type, connection_details, description,
                      include_views, include_tables, schema_pattern, table_pattern,
                      status, schedule, owner_id, created_at, updated_at, last_ingested_at
        """,
            source.name,
            source.source_type.value,
            json.dumps(source.connection_details.dict(exclude_none=True)),
            source.description,
            source.include_views,
            source.include_tables,
            schema_json,
            table_json,
            source.schedule or "00:00 GMT+5:30",
            source.owner_id
        )

        data = dict(result)
        data['id'] = str(data['id'])
        data['owner_id'] = str(data['owner_id']) if data.get('owner_id') else None
        data['connection_details'] = json.loads(data['connection_details']) if data['connection_details'] else {}
        data['schema_pattern'] = json.loads(data['schema_pattern']) if data['schema_pattern'] else None
        data['table_pattern'] = json.loads(data['table_pattern']) if data['table_pattern'] else None

        await log_api_action(
            endpoint="/sources/glue", method="POST",
            action_summary=f"New Glue data source registered: {source.name}",
            entity_type="data_source", entity_id=data['id'], entity_name=source.name,
            owner_id=source.owner_id,
            request_body={"name": source.name, "source_type": source.source_type.value}
        )

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating glue source: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/sources/mssql", response_model=DataSource)
async def create_source_mssql(source: DataSourceCreateMSSQL):
    """Register a new Microsoft SQL Server data source"""
    from app import db, log_api_action, logger

    try:
        existing = await db.fetch_one("SELECT id FROM data_sources WHERE name = $1", source.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Source with name '{source.name}' already exists")

        result = await db.fetch_one("""
            INSERT INTO data_sources (
                name, source_type, connection_details, description,
                include_views, include_tables, schema_pattern, table_pattern,
                include_views, include_tables, schema_pattern, table_pattern,
                schedule, owner_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id, name, source_type, connection_details, description,
                      include_views, include_tables, schema_pattern, table_pattern,
                      status, schedule, owner_id, created_at, updated_at, last_ingested_at
                      include_views, include_tables, schema_pattern, table_pattern,
                      status, schedule, owner_id, created_at, updated_at, last_ingested_at
        """,
            source.name,
            source.source_type.value,
            json.dumps(source.connection_details.dict(exclude_none=True)),
            json.dumps(source.connection_details.dict(exclude_none=True)),
            source.description,
            source.include_views,
            source.include_tables,
            json.dumps(source.schema_pattern) if source.schema_pattern else None,
            json.dumps(source.table_pattern) if source.table_pattern else None,
            source.include_views,
            source.include_tables,
            json.dumps(source.schema_pattern) if source.schema_pattern else None,
            json.dumps(source.table_pattern) if source.table_pattern else None,
            source.schedule or "00:00 GMT+5:30",
            source.owner_id
        )

        data = dict(result)
        data['id'] = str(data['id'])
        data['owner_id'] = str(data['owner_id']) if data.get('owner_id') else None
        data['connection_details'] = json.loads(data['connection_details']) if data['connection_details'] else {}
        data['schema_pattern'] = json.loads(data['schema_pattern']) if data['schema_pattern'] else None
        data['table_pattern'] = json.loads(data['table_pattern']) if data['table_pattern'] else None
        data['schema_pattern'] = json.loads(data['schema_pattern']) if data['schema_pattern'] else None
        data['table_pattern'] = json.loads(data['table_pattern']) if data['table_pattern'] else None

        await log_api_action(
            endpoint="/sources/mssql", method="POST",
            action_summary=f"New MSSQL data source registered: {source.name}",
            entity_type="data_source", entity_id=data['id'], entity_name=source.name,
            owner_id=source.owner_id,
            request_body={"name": source.name, "source_type": source.source_type.value}
        )

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating mssql source: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/sources/redshift", response_model=DataSource)
async def create_source_redshift(source: DataSourceCreateRedshift):
    """Register a new Amazon Redshift data source"""
    from app import db, log_api_action, logger
    import json

    try:
        existing = await db.fetch_one("SELECT id FROM data_sources WHERE name = $1", source.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Source with name '{source.name}' already exists")

        # Prepare JSON for storage
        conn_dict = source.connection_details.dict(exclude_none=True)
        # Optionally flatten nested configs if needed for DB schema
        lineage_json = json.dumps(conn_dict.pop("lineage", {}))
        profiling_json = json.dumps(conn_dict.pop("profiling", {}))

        result = await db.fetch_one("""
            INSERT INTO data_sources (
                name, source_type, connection_details, description,
                include_tables, include_views,
                schedule, owner_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, name, source_type, connection_details, description,
                      include_tables, include_views, status,
                      schedule, owner_id, created_at, updated_at, last_ingested_at
        """,
            source.name,
            source.source_type.value,
            json.dumps(conn_dict),  # Includes host_port, patterns, stateful_ingestion, etc.
            source.description,
            source.connection_details.include_tables,
            source.connection_details.include_views,
            source.schedule or "00:00 GMT+5:30",
            source.owner_id
        )

        data = dict(result)
        data['id'] = str(data['id'])
        data['owner_id'] = str(data['owner_id']) if data.get('owner_id') else None
        data['connection_details'] = json.loads(data['connection_details']) if data['connection_details'] else {}

        # Enrich response with nested configs if desired
        if "lineage" in data['connection_details']:
            data['lineage_mode'] = data['connection_details']["lineage"].get("table_lineage_mode", "stlscan-based")

        await log_api_action(
            endpoint="/sources/redshift", method="POST",
            action_summary=f"New Redshift data source registered: {source.name}",
            entity_type="data_source", entity_id=data['id'], entity_name=source.name,
            owner_id=source.owner_id,
            request_body={"name": source.name, "source_type": source.source_type.value}
        )

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating redshift source: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/sources-list", response_model=List[SimpleDataSource])
async def list_sources(
    source_type: Optional[SourceType] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """List of all data sources"""
    from app import db, logger

    try:
        query = """
            SELECT 
                ds.id AS source_id,
                ds.name,
                o.name AS owner_name,
                ds.status,
                ds.schedule,
                ds.last_ingested_at,
                ds.created_at
            FROM data_sources ds
            LEFT JOIN owners o ON ds.owner_id = o.id
            WHERE 1=1
        """
        params = []

        if source_type:
            query += f" AND ds.source_type = ${len(params) + 1}"
            params.append(source_type.value)

        if status:
            query += f" AND ds.status = ${len(params) + 1}"
            params.append(status)

        query += f" ORDER BY ds.created_at DESC LIMIT ${len(params) + 1}"
        params.append(limit)

        results = await db.fetch_all(query, *params)

        response_data = []
        for row in results:
            item = dict(row)
            item['source_id'] = str(item['source_id'])
            response_data.append(item)

        return response_data

    except Exception as e:
        logger.error(f"Error listing sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/source-detail/{source_id}", response_model=DataSource)
async def get_source(source_id: str):
    """Get source by ID"""
    from app import db, logger

    try:
        result = await db.fetch_one("SELECT * FROM data_sources WHERE id = $1", source_id)
        if not result:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Parse JSON fields
        data = dict(result)
        data['id'] = str(data['id'])
        data['owner_id'] = str(data['owner_id']) if data.get('owner_id') else None
        data['connection_details'] = json.loads(data['connection_details']) if data['connection_details'] else {}
        data['schema_pattern'] = json.loads(data['schema_pattern']) if data['schema_pattern'] else None
        data['table_pattern'] = json.loads(data['table_pattern']) if data['table_pattern'] else None
        
        return data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/v1/delete-source/{source_id}")
async def delete_source(source_id: str):
    """Delete a data source"""
    from app import db, logger

    try:
        # Check if source exists
        source = await db.fetch_one("SELECT id FROM data_sources WHERE id = $1", source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Delete source (cascades to catalogs, columns, etc.)
        await db.execute("DELETE FROM data_sources WHERE id = $1", source_id)
        
        return {"message": "Source deleted successfully", "source_id": source_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting source: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ============================================================================
# Ingestion Management
# ============================================================================

@router.post("/api/v1/ingest-source", response_model=IngestionResponse)
async def start_ingestion(
    request: IngestionRequest,
    background_tasks: BackgroundTasks
):
    """
    Start metadata ingestion for a source.

    Auto-PII detection flags (both optional, default False)
    -------------------------------------------------------
    require_auto_pii_detection : bool
        When True, automatically classify all ingested tables and columns
        with AI-suggested tags once ingestion completes successfully.

    required_human_approval : bool
        Only valid when require_auto_pii_detection=True.
        - True  → AI suggestions are stored as PENDING and must be approved
                  by a human before being applied to the assignment tables.
        - False → AI suggestions are written directly to
                  tag_catalog_assignments / tag_column_assignments.

    Validation rule
    ---------------
    required_human_approval can only be True when require_auto_pii_detection
    is also True.  Setting required_human_approval=True while
    require_auto_pii_detection=False is rejected with HTTP 422.
    """
    from app import db, log_api_action, logger, ingestion_manager

    # ── Validate the flag dependency ────────────────────────────────────────
    if request.required_human_approval and not request.require_auto_pii_detection:
        raise HTTPException(
            status_code=422,
            detail=(
                "required_human_approval can only be enabled when "
                "require_auto_pii_detection is also True."
            ),
        )

    try:
        # Get source details
        source = await db.fetch_one("SELECT * FROM data_sources WHERE id = $1", request.source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        if source['status'] == JobStatus.FAILED.value:
            raise HTTPException(
                status_code=400,
                detail="Source is in a failed state. Please review and re-register if needed."
            )

        # Create job
        job_id = await ingestion_manager.create_job(
            request.source_id,
            {"profiling": request.include_profiling, "lineage": request.include_lineage}
        )

        # Run ingestion in background, passing PII flags through so the
        # ingestion manager can trigger auto_pii_service after success.
        background_tasks.add_task(
            ingestion_manager.ingest,
            request.source_id,
            job_id,
            {
                "include_profiling":          request.include_profiling,
                "include_lineage":            request.include_lineage,
                # ── PII detection flags ──────────────────────────────────
                "require_auto_pii_detection": request.require_auto_pii_detection,
                "required_human_approval":    request.required_human_approval,
                "pii_min_confidence":         request.pii_min_confidence,
            }
        )

        await log_api_action(
            endpoint="/ingest", method="POST",
            action_summary=(
                f"{source['source_type'].capitalize()} ingestion started "
                f"for source: {source['name']}"
                + (" [auto-PII enabled]" if request.require_auto_pii_detection else "")
            ),
            entity_type="ingestion_job", entity_id=job_id, entity_name=source['name'],
            owner_id=request.owner_id,
            request_body={
                "source_id":                  request.source_id,
                "job_id":                     job_id,
                "require_auto_pii_detection": request.require_auto_pii_detection,
                "required_human_approval":    request.required_human_approval,
            }
        )

        return IngestionResponse(
            job_id=job_id,
            source_id=request.source_id,
            source_name=source['name'],
            status="started",
            message=(
                "Ingestion job started successfully. "
                "Auto-PII detection will run after ingestion completes."
                if request.require_auto_pii_detection
                else "Ingestion job started successfully"
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# # ============================================================================
# # Ingestion Management
# # ============================================================================

# @router.post("/api/v1/ingest-source", response_model=IngestionResponse)
# async def start_ingestion(
#     request: IngestionRequest,
#     background_tasks: BackgroundTasks
# ):
#     """Start metadata ingestion for a source
#     trigger the ingestionof meta data 
#     """
#     from app import db, log_api_action, logger, ingestion_manager

#     try:
#         # Get source details
#         source = await db.fetch_one("SELECT * FROM data_sources WHERE id = $1", request.source_id)
#         if not source:
#             raise HTTPException(status_code=404, detail="Source not found")
        
#         if source['status'] == JobStatus.FAILED.value:
#             raise HTTPException(status_code=400, detail=f"Source is in a failed state. Please review and re-register if needed.")
        
#         # Create job
#         job_id = await ingestion_manager.create_job(
#             request.source_id, 
#             {"profiling": request.include_profiling, "lineage": request.include_lineage}
#         )
        
#         # Run ingestion in background
#         background_tasks.add_task(
#             ingestion_manager.ingest,
#             request.source_id,
#             job_id,
#             {"include_profiling": request.include_profiling, "include_lineage": request.include_lineage}
#         )

#         await log_api_action(
#             endpoint="/ingest", method="POST",
#             action_summary=f"{source['source_type'].capitalize()} ingestion started for source: {source['name']}",
#             entity_type="ingestion_job", entity_id=job_id, entity_name=source['name'],
#             owner_id=request.owner_id,
#             request_body={"source_id": request.source_id, "job_id": job_id}
#         )
        
#         return IngestionResponse(
#             job_id=job_id,
#             source_id=request.source_id,
#             source_name=source['name'],
#             status="started",
#             message="Ingestion job started successfully"
#         )
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error starting ingestion: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/jobs-list")
async def list_jobs(
    source_id: Optional[str] = None,
    status: Optional[JobStatus] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """List ingestion jobs"""
    from app import db, logger

    try:
        query = """
            SELECT j.*, s.name as source_name, s.source_type
            FROM ingestion_jobs j
            JOIN data_sources s ON j.source_id = s.id
            WHERE 1=1
        """
        params = []
        
        if source_id:
            query += f" AND j.source_id = ${len(params) + 1}"
            params.append(source_id)
        
        if status:
            query += f" AND j.status = ${len(params) + 1}"
            params.append(status.value)
        
        query += f" ORDER BY j.created_at DESC LIMIT ${len(params) + 1}"
        params.append(limit)
        
        results = await db.fetch_all(query, *params)
        return [dict(row) for row in results]
    
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/job-detail/{job_id}")
async def get_job(job_id: str):
    """Get job by ID"""
    from app import db, logger

    try:
        result = await db.fetch_one("""
            SELECT j.*, s.name as source_name, s.source_type
            FROM ingestion_jobs j
            JOIN data_sources s ON j.source_id = s.id
            WHERE j.id = $1
        """, job_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return dict(result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job: {e}")
        raise HTTPException(status_code=500, detail=str(e))







@router.get("/api/v1/sources/{source_id}/stats")
async def get_source_stats(
    source_id: str,
    type: Optional[str] = Query(None, description="Filter by type: table or view or all"),
    status: Optional[str] = Query(None, description="Filter by status: healthy, warning, risk"),
):
    from app import db
 
 
    try:
        source = await db.fetch_one("SELECT id, name, source_type FROM data_sources WHERE id = $1", source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
 
 
        filters = ["c.source_id = $1"]
        params = [source_id]
 
 
        if type and type.lower() != "all":
            params.append(type.lower())
            filters.append(f"c.type = ${len(params)}")
 
 
        if status:
            params.append(status.lower())
            filters.append(f"c.status = ${len(params)}")
 
        source_type = source['source_type']
 
        # Athena: emits multiple MCP aspects per table; filter out intermediate/duplicate
        # rows that have no columns ingested yet.
        # MongoDB: collections always have at least one field; rows with 0 columns are
        # incomplete ingestion artifacts and should be excluded.
        needs_column_filter = source_type in ("athena", "mongodb","glue","snowflake","postgres")
        if needs_column_filter:
            filters.append(
                "c.id IN ("
                "  SELECT DISTINCT catalog_id FROM columns"
                "  WHERE catalog_id IS NOT NULL"
                "  GROUP BY catalog_id HAVING COUNT(*) > 0"
                ")"
            )
 
        where_clause = "WHERE " + " AND ".join(filters)
        having_clause = "HAVING COUNT(DISTINCT col.id) > 0" if needs_column_filter else ""
 
        having_clause = "HAVING COUNT(DISTINCT col.id) > 0" if needs_column_filter else ""
 
        catalogs = await db.fetch_all(f"""
            SELECT
            SELECT
                c.id, c.full_name, c.table_name,
                c.row_count,
                c.type,
                c.status,
                c.last_seen_at AS last_sync,
                COUNT(DISTINCT col.id) AS column_count,
                COALESCE(
                    JSON_AGG(
                        DISTINCT JSONB_BUILD_OBJECT(
                            'tag_id', t.id,
                            'name',   t.name,
                            'color',  t.color
                        )
                    ) FILTER (WHERE t.id IS NOT NULL),
                    '[]'
                ) AS tags
                COUNT(DISTINCT col.id) AS column_count,
                COALESCE(
                    JSON_AGG(
                        DISTINCT JSONB_BUILD_OBJECT(
                            'tag_id', t.id,
                            'name',   t.name,
                            'color',  t.color
                        )
                    ) FILTER (WHERE t.id IS NOT NULL),
                    '[]'
                ) AS tags
            FROM catalogs c
            LEFT JOIN columns col ON c.id = col.catalog_id
            LEFT JOIN tag_catalog_assignments tca ON c.id = tca.catalog_id
            LEFT JOIN tags t ON tca.tag_id = t.id
            LEFT JOIN tag_catalog_assignments tca ON c.id = tca.catalog_id
            LEFT JOIN tags t ON tca.tag_id = t.id
            {where_clause}
            GROUP BY c.id, c.full_name, c.table_name, c.row_count, c.type, c.status, c.last_seen_at
            {having_clause}
            {having_clause}
            ORDER BY c.table_name
        """, *params)
 
 
        total_row_count = sum(r['row_count'] or 0 for r in catalogs)
        total_column_count = sum(r['column_count'] for r in catalogs)
        total_tables = len(catalogs)
 
        total_tables = len(catalogs)
 
        return {
            "source_id": source_id,
            "source_name": source['name'],
            "source_type": source['source_type'],
            "total_tables_ingested": total_tables,
            "total_row_count": total_row_count,
            "total_column_count": total_column_count,
            "filters": {
                "type": type,
                "status": status,
            },
            "catalogs": [
                {
                    "catalog_id": str(r['id']),
                    "full_name": r['full_name'],
                    "table_name": r['table_name'],
                    "row_count": r['row_count'],
                    "column_count": r['column_count'],
                    "type": r['type'],
                    "status": r['status'],
                    "last_sync": r['last_sync'].isoformat() if r['last_sync'] else None,
                    "tags": json.loads(r['tags']) if isinstance(r['tags'], str) else (r['tags'] or []),
                    "tags": json.loads(r['tags']) if isinstance(r['tags'], str) else (r['tags'] or []),
                }
                for r in catalogs
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# @router.get("/api/v1/sources/{source_id}/stats")
# async def get_source_stats(
#     source_id: str,
#     type: Optional[str] = Query(None, description="Filter by type: table or view or all"),
#     status: Optional[str] = Query(None, description="Filter by status: healthy, warning, risk"),
# ):
#     from app import db
 
#     try:
#         source = await db.fetch_one("SELECT id, name, source_type FROM data_sources WHERE id = $1", source_id)
#         if not source:
#             raise HTTPException(status_code=404, detail="Source not found")
 
#         total_tables = await db.fetch_val(
#             "SELECT COUNT(*) FROM catalogs WHERE source_id = $1", source_id
#         )
 
#         filters = ["c.source_id = $1"]
#         params = [source_id]
 
#         if type and type.lower() != "all":
#             params.append(type.lower())
#             filters.append(f"c.type = ${len(params)}")
 
#         if status:
#             params.append(status.lower())
#             filters.append(f"c.status = ${len(params)}")
 
#         source_type = source['source_type']
 
#         # Athena: emits multiple MCP aspects per table; filter out intermediate/duplicate
#         # rows that have no columns ingested yet.
#         # MongoDB: collections always have at least one field; rows with 0 columns are
#         # incomplete ingestion artifacts and should be excluded.
#         needs_column_filter = source_type in ("athena", "mongodb")
#         if needs_column_filter:
#             filters.append(
#                 "c.id IN ("
#                 "  SELECT DISTINCT catalog_id FROM columns"
#                 "  WHERE catalog_id IS NOT NULL"
#                 "  GROUP BY catalog_id HAVING COUNT(*) > 0"
#                 ")"
#             )
 
#         where_clause = "WHERE " + " AND ".join(filters)
#         having_clause = "HAVING COUNT(DISTINCT col.id) > 0" if needs_column_filter else ""
 
#         catalogs = await db.fetch_all(f"""
#             SELECT
#                 c.id, c.full_name, c.table_name,
#                 c.row_count,
#                 c.type,
#                 c.status,
#                 c.last_seen_at AS last_sync,
#                 COUNT(DISTINCT col.id) AS column_count,
#                 COALESCE(
#                     JSON_AGG(
#                         DISTINCT JSONB_BUILD_OBJECT(
#                             'tag_id', t.id,
#                             'name',   t.name,
#                             'color',  t.color
#                         )
#                     ) FILTER (WHERE t.id IS NOT NULL),
#                     '[]'
#                 ) AS tags
#             FROM catalogs c
#             LEFT JOIN columns col ON c.id = col.catalog_id
#             LEFT JOIN tag_catalog_assignments tca ON c.id = tca.catalog_id
#             LEFT JOIN tags t ON tca.tag_id = t.id
#             {where_clause}
#             GROUP BY c.id, c.full_name, c.table_name, c.row_count, c.type, c.status, c.last_seen_at
#             {having_clause}
#             ORDER BY c.table_name
#         """, *params)
 
#         total_row_count = sum(r['row_count'] or 0 for r in catalogs)
#         total_column_count = sum(r['column_count'] for r in catalogs)
 
#         return {
#             "source_id": source_id,
#             "source_name": source['name'],
#             "source_type": source['source_type'],
#             "total_tables_ingested": total_tables,
#             "total_row_count": total_row_count,
#             "total_column_count": total_column_count,
#             "filters": {
#                 "type": type,
#                 "status": status,
#             },
#             "catalogs": [
#                 {
#                     "catalog_id": str(r['id']),
#                     "full_name": r['full_name'],
#                     "table_name": r['table_name'],
#                     "row_count": r['row_count'],
#                     "column_count": r['column_count'],
#                     "type": r['type'],
#                     "status": r['status'],
#                     "last_sync": r['last_sync'].isoformat() if r['last_sync'] else None,
#                     "tags": json.loads(r['tags']) if isinstance(r['tags'], str) else (r['tags'] or []),
#                 }
#                 for r in catalogs
#             ],
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
    

    

# @router.get("/api/v1/sources/{source_id}/stats")
# async def get_source_stats(
#     source_id: str,
#     type: Optional[str] = Query(None, description="Filter by type: table or view or all"),
#     status: Optional[str] = Query(None, description="Filter by status: healthy, warning, risk"),
# ):
#     from app import db
 
#     try:
#         source = await db.fetch_one("SELECT id, name, source_type FROM data_sources WHERE id = $1", source_id)
#         if not source:
#             raise HTTPException(status_code=404, detail="Source not found")
 
#         total_tables = await db.fetch_val(
#             "SELECT COUNT(*) FROM catalogs WHERE source_id = $1", source_id
#         )
 
#         filters = ["c.source_id = $1"]
#         params = [source_id]
 
#         if type and type.lower() != "all":
#             params.append(type.lower())
#             filters.append(f"c.type = ${len(params)}")
 
#         if status:
#             params.append(status.lower())
#             filters.append(f"c.status = ${len(params)}")
 
#         source_type = source['source_type']
 
#         # Athena: emits multiple MCP aspects per table; filter out intermediate/duplicate
#         # rows that have no columns ingested yet.
#         # MongoDB: collections always have at least one field; rows with 0 columns are
#         # incomplete ingestion artifacts and should be excluded.
#         needs_column_filter = source_type in ("athena", "mongodb")
#         if needs_column_filter:
#             filters.append(
#                 "c.id IN ("
#                 "  SELECT DISTINCT catalog_id FROM columns"
#                 "  WHERE catalog_id IS NOT NULL"
#                 "  GROUP BY catalog_id HAVING COUNT(*) > 0"
#                 ")"
#             )
 
#         where_clause = "WHERE " + " AND ".join(filters)
#         having_clause = "HAVING COUNT(DISTINCT col.id) > 0" if needs_column_filter else ""
 
#         catalogs = await db.fetch_all(f"""
#             SELECT
#                 c.id, c.full_name, c.table_name,
#                 c.row_count,
#                 c.type,
#                 c.status,
#                 c.last_seen_at AS last_sync,
#                 COUNT(DISTINCT col.id) AS column_count,
#                 COALESCE(
#                     JSON_AGG(
#                         DISTINCT JSONB_BUILD_OBJECT(
#                             'tag_id', t.id,
#                             'name',   t.name,
#                             'color',  t.color
#                         )
#                     ) FILTER (WHERE t.id IS NOT NULL),
#                     '[]'
#                 ) AS tags
#             FROM catalogs c
#             LEFT JOIN columns col ON c.id = col.catalog_id
#             LEFT JOIN tag_catalog_assignments tca ON c.id = tca.catalog_id
#             LEFT JOIN tags t ON tca.tag_id = t.id
#             {where_clause}
#             GROUP BY c.id, c.full_name, c.table_name, c.row_count, c.type, c.status, c.last_seen_at
#             {having_clause}
#             ORDER BY c.table_name
#         """, *params)
 
#         total_row_count = sum(r['row_count'] or 0 for r in catalogs)
#         total_column_count = sum(r['column_count'] for r in catalogs)
 
#         return {
#             "source_id": source_id,
#             "source_name": source['name'],
#             "source_type": source['source_type'],
#             "total_tables_ingested": total_tables,
#             "total_row_count": total_row_count,
#             "total_column_count": total_column_count,
#             "filters": {
#                 "type": type,
#                 "status": status,
#             },
#             "catalogs": [
#                 {
#                     "catalog_id": str(r['id']),
#                     "full_name": r['full_name'],
#                     "table_name": r['table_name'],
#                     "row_count": r['row_count'],
#                     "column_count": r['column_count'],
#                     "type": r['type'],
#                     "status": r['status'],
#                     "last_sync": r['last_sync'].isoformat() if r['last_sync'] else None,
#                     "tags": json.loads(r['tags']) if isinstance(r['tags'], str) else (r['tags'] or []),
#                 }
#                 for r in catalogs
#             ],
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
    


@router.get("/api/v1/sources/{source_id}/summary")
async def get_source_summary(source_id: str):
    """
    Get metadata summary for a data source: total tables ingested,
    per-table row count and column count.
    """
    from app import db, logger

    try:
        source = await db.fetch_one("SELECT id, name, source_type FROM data_sources WHERE id = $1", source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        rows = await db.fetch_all("""
            SELECT
                c.id,
                c.full_name,
                c.table_name,
                c.database_name,
                c.schema_name,
                c.row_count,
                COUNT(col.id) AS column_count
            FROM catalogs c
            LEFT JOIN columns col ON c.id = col.catalog_id
            WHERE c.source_id = $1
            GROUP BY c.id, c.full_name, c.table_name, c.database_name, c.schema_name, c.row_count
            ORDER BY c.full_name
        """, source_id)

        tables = []
        for r in rows:
            tables.append({
                "catalog_id": str(r['id']),
                "full_name": r['full_name'],
                "table_name": r['table_name'],
                "database_name": r['database_name'],
                "schema_name": r['schema_name'],
                "row_count": r['row_count'] or 0,
                "column_count": r['column_count'] or 0,
            })

        return {
            "source_id": source_id,
            "source_name": source['name'],
            "source_type": source['source_type'],
            "total_tables": len(tables),
            "tables": tables
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting source summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))




# ── Colour palette ──────────────────────────────────────────────────────────
DARK_BLUE   = colors.HexColor("#1A2B4A")
MID_BLUE    = colors.HexColor("#2563EB")
LIGHT_BLUE  = colors.HexColor("#EFF6FF")
GREEN       = colors.HexColor("#16A34A")
GREEN_BG    = colors.HexColor("#F0FDF4")
ORANGE      = colors.HexColor("#D97706")
ORANGE_BG   = colors.HexColor("#FFFBEB")
RED         = colors.HexColor("#DC2626")
RED_BG      = colors.HexColor("#FEF2F2")
GREY_LIGHT  = colors.HexColor("#F3F4F6")
GREY_BORDER = colors.HexColor("#E5E7EB")
GREY_TEXT   = colors.HexColor("#6B7280")
WHITE       = colors.white
BLACK       = colors.HexColor("#111827")


# ── Helpers ─────────────────────────────────────────────────────────────────
def _status_color(status: str):
    s = (status or "").lower()
    if s == "healthy":
        return GREEN, GREEN_BG
    if s == "warning":
        return ORANGE, ORANGE_BG
    if s in ("risk", "error", "critical"):
        return RED, RED_BG
    return MID_BLUE, LIGHT_BLUE


def _format_rows(count) -> str:
    """1200000 → 1.2M, 12400 → 12.4k"""
    if count is None:
        return "—"
    count = int(count)
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}k"
    return str(count)


def _format_size(row_count, column_count) -> str:
    """Rough size estimate from row_count × column_count × avg bytes."""
    if row_count is None:
        return "—"
    bytes_est = int(row_count) * int(column_count or 1) * 50
    if bytes_est >= 1_073_741_824:
        return f"{bytes_est / 1_073_741_824:.1f} GB"
    if bytes_est >= 1_048_576:
        return f"{bytes_est / 1_048_576:.1f} MB"
    if bytes_est >= 1024:
        return f"{bytes_est / 1024:.1f} KB"
    return f"{bytes_est} B"


def _format_last_sync(last_sync) -> str:
    if not last_sync:
        return "—"
    if isinstance(last_sync, str):
        return last_sync
    now = datetime.utcnow()
    ls  = last_sync.replace(tzinfo=None) if hasattr(last_sync, "replace") else last_sync
    diff    = now - ls
    minutes = int(diff.total_seconds() / 60)
    if minutes < 60:
        return f"{minutes} mins ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hours ago"
    return f"{diff.days} days ago"


# ── PDF Generator ────────────────────────────────────────────────────────────
def generate_source_stats_pdf(source: dict, catalogs: list) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm,  bottomMargin=15*mm,
        title=f"{source['name']} Datasets",
        author="Data Governance Platform"
    )

    st = {
        "title": ParagraphStyle(
            "title", fontSize=20, textColor=WHITE,
            fontName="Helvetica-Bold", leading=26),
        "subtitle": ParagraphStyle(
            "subtitle", fontSize=9,
            textColor=colors.HexColor("#BFDBFE"),
            fontName="Helvetica"),
        "right": ParagraphStyle(
            "right", fontSize=9,
            textColor=colors.HexColor("#BFDBFE"),
            fontName="Helvetica", alignment=TA_RIGHT),
        "section": ParagraphStyle(
            "section", fontSize=11, textColor=DARK_BLUE,
            fontName="Helvetica-Bold", spaceAfter=4),
        "small": ParagraphStyle(
            "small", fontSize=8, textColor=BLACK,
            fontName="Helvetica", leading=12),
        "small_grey": ParagraphStyle(
            "small_grey", fontSize=8, textColor=GREY_TEXT,
            fontName="Helvetica", leading=12),
        "bold_small": ParagraphStyle(
            "bold_small", fontSize=8, textColor=BLACK,
            fontName="Helvetica-Bold", leading=12),
        "center_small": ParagraphStyle(
            "center_small", fontSize=8, textColor=BLACK,
            fontName="Helvetica", alignment=TA_CENTER),
        "footer": ParagraphStyle(
            "footer", fontSize=7.5, textColor=GREY_TEXT,
            fontName="Helvetica", alignment=TA_CENTER),
    }

    story = []

    # ── Header banner ──────────────────────────────────────────────────────
    left = [
        Paragraph(f"{source['name']} Datasets", st["title"]),
        Spacer(1, 4),
        Paragraph(
            "Browse and manage all datasets ingested from this source",
            st["subtitle"]),
    ]
    right = [
        Paragraph(f"Source Type: {source.get('source_type', '').upper()}", st["right"]),
        Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", st["right"]),
        Paragraph(f"Total Datasets: {len(catalogs)}", st["right"]),
    ]
    header = Table([[left, right]], colWidths=[160*mm, 107*mm])
    header.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), DARK_BLUE),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (0,  0),  10*mm),
        ("RIGHTPADDING",  (1, 0), (1,  0),  8*mm),
        ("TOPPADDING",    (0, 0), (-1, -1), 7*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7*mm),
    ]))
    story.append(header)
    story.append(Spacer(1, 6*mm))

    # ── Summary stats cards ────────────────────────────────────────────────
    total_cols    = sum(int(c.get("column_count") or 0) for c in catalogs)
    healthy_count = sum(1 for c in catalogs if (c.get("status") or "").lower() == "healthy")
    warning_count = sum(1 for c in catalogs if (c.get("status") or "").lower() == "warning")

    def _stat_cell(label, value, fg=DARK_BLUE):
        return [
            Paragraph(str(value),
                      ParagraphStyle("sv", fontSize=18, fontName="Helvetica-Bold",
                                     textColor=fg, alignment=TA_CENTER, leading=22)),
            Paragraph(label,
                      ParagraphStyle("sl", fontSize=8, fontName="Helvetica",
                                     textColor=GREY_TEXT, alignment=TA_CENTER)),
        ]

    stat_table = Table([[
        _stat_cell("Total Datasets",  len(catalogs),  DARK_BLUE),
        _stat_cell("Total Columns",   total_cols,     MID_BLUE),
        _stat_cell("Healthy",         healthy_count,  GREEN),
        _stat_cell("Warning",         warning_count,  ORANGE),
    ]], colWidths=[66.75*mm] * 4)
    stat_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), WHITE),
        ("BOX",           (0, 0), (-1, -1), 1,   GREY_BORDER),
        ("LINEBEFORE",    (1, 0), (-1, -1), 0.5, GREY_BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5*mm),
    ]))
    story.append(stat_table)
    story.append(Spacer(1, 6*mm))

    # ── Section heading ────────────────────────────────────────────────────
    story.append(Paragraph("Dataset List", st["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=GREY_BORDER, spaceAfter=5))

    # ── Main data table ────────────────────────────────────────────────────
    # Landscape A4 usable width ≈ 267mm
    col_widths = [110*mm, 28*mm, 32*mm, 52*mm, 45*mm]

    header_row = [
        Paragraph("<b>Name</b>",      st["bold_small"]),
        Paragraph("<b>Type</b>",      st["bold_small"]),
        Paragraph("<b>Columns</b>",   st["bold_small"]),
        Paragraph("<b>Last Sync</b>", st["bold_small"]),
        Paragraph("<b>Status</b>",    st["bold_small"]),
    ]

    rows = [header_row]
    for cat in catalogs:
        status    = cat.get("status") or ""
        fg, bg    = _status_color(status)
        row_count = cat.get("row_count")
        col_count = cat.get("column_count") or 0
        last_sync = cat.get("last_sync") or cat.get("last_seen_at")
        full_name = cat.get("full_name") or cat.get("table_name") or ""

        status_badge = Table(
            [[Paragraph(
                status.capitalize(),
                ParagraphStyle("sb", fontSize=7.5, textColor=fg,
                               fontName="Helvetica-Bold", alignment=TA_CENTER)
            )]],
            colWidths=[28*mm]
        )
        status_badge.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), bg),
            ("BOX",           (0, 0), (-1, -1), 0.5, fg),
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING",   (0, 0), (-1, -1), 3),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
        ]))

        rows.append([
            Paragraph(full_name, st["small"]),
            Paragraph((cat.get("type") or "Table").capitalize(), st["center_small"]),
            Paragraph(str(col_count), st["center_small"]),
            Paragraph(_format_last_sync(last_sync), st["small_grey"]),
            status_badge,
        ])

    data_table = Table(rows, colWidths=col_widths, repeatRows=1)
    data_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  MID_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GREY_LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.4, GREY_BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, 0), 8),
    ]))
    story.append(data_table)

    # ── Footer ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY_BORDER))
    story.append(Spacer(1, 2))
    story.append(Paragraph(
        f"Generated by Data Governance Platform &nbsp;|&nbsp; "
        f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} &nbsp;|&nbsp; Confidential",
        st["footer"]
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ── API Endpoint ─────────────────────────────────────────────────────────────
@router.get(
    "/api/v1/sources/{source_id}/stats/export",
    summary="Export List",
    description="Export the dataset list for a source as a downloadable PDF.",
    response_description="Export List",
    tags=["Data Sources"],
    responses={
        200: {
            "description": "Export List",
            "content": {"application/pdf": {}},
        }
    },
)
async def export_source_stats(
    source_id: str,
):
    """
    Fetches catalog stats for the given source from the DB
    and returns a downloadable PDF exported as 'Export List'.
    """
    from app import db

    try:
        # ── Fetch source ───────────────────────────────────────────────────
        source = await db.fetch_one(
            "SELECT id, name, source_type FROM data_sources WHERE id = $1::uuid",
            source_id
        )
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # ── Build query ────────────────────────────────────────────────────
        where_clause = "WHERE c.source_id = $1::uuid"
        params       = [source_id]

        catalogs = await db.fetch_all(f"""
            SELECT
                c.id,
                c.full_name,
                c.table_name,
                c.row_count,
                c.type,
                c.status,
                c.last_seen_at AS last_sync,
                COUNT(DISTINCT col.id) AS column_count
            FROM catalogs c
            LEFT JOIN columns col ON c.id = col.catalog_id
            {where_clause}
            GROUP BY c.id, c.full_name, c.table_name,
                     c.row_count, c.type, c.status, c.last_seen_at
            ORDER BY c.table_name
        """, *params)

        catalog_list = [dict(r) for r in catalogs]

        # ── Generate PDF ───────────────────────────────────────────────────
        pdf_bytes = generate_source_stats_pdf(dict(source), catalog_list)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"{source['name'].replace(' ', '_')}_datasets_{timestamp}.pdf"

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





# =============================================================================
# AI Summary — pipeline completion summary (matches UI summary card)
# =============================================================================

@router.get(
    "/api/v1/sources/{source_id}/ai-summary",
    summary="Get AI pipeline completion summary for a source",
    responses={
        200: {"description": "AI summary with badge stats for the latest ingestion"},
        404: {"description": "Source or job not found"},
        400: {"description": "No completed job found for this source"},
    },
)
async def get_source_pipeline_summary(source_id: str):
    """
    Returns the pipeline completion summary card data for a source's most recent job.

    Matches the UI summary card:
      - Badge counts: ingested, classified
      - One-line AI prose summary (e.g. "All 5 datasets ingested, PII scanned...")
      - Overall pipeline status
    """
    import os
    from openai import AsyncAzureOpenAI
    from app import db, logger

    

    # ── 1. Fetch source ──────────────────────────────────────────────────────
    source = await db.fetch_one(
        "SELECT id, name, source_type FROM data_sources WHERE id = $1",
        source_id,
    )
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")

    # ── 2. Fetch latest COMPLETED job ────────────────────────────────────────
    job = await db.fetch_one(
        """
        SELECT id, status, records_ingested, error_message, created_at, completed_at
        FROM   ingestion_jobs
        WHERE  source_id = $1
          AND  status IN ('success', 'failed')
        ORDER  BY created_at DESC
        LIMIT  1
        """,
        source_id,
    )
    if not job:
        raise HTTPException(
            status_code=400,
            detail="No completed ingestion job found for this source.",
        )

    job_id = str(job["id"])

    # ── 3. Fetch catalog stats for this source ───────────────────────────────
    catalog_stats = await db.fetch_one(
        """
        SELECT
            COUNT(*)                                            AS total_tables,
            COUNT(*) FILTER (WHERE status = 'healthy')         AS healthy_count,
            COUNT(*) FILTER (WHERE status = 'warning')         AS warning_count,
            COUNT(*) FILTER (WHERE status = 'risk')            AS risk_count,
            COALESCE(SUM(row_count), 0)                        AS total_rows
        FROM catalogs
        WHERE source_id = $1
        """,
        source_id,
    )

    # ── 4. Fetch PII / classified tag counts ─────────────────────────────────
    # "classified" = catalogs that have at least one tag assigned
    classified_count = await db.fetch_val(
        """
        SELECT COUNT(DISTINCT catalog_id)
        FROM   tag_catalog_assignments tca
        JOIN   catalogs c ON c.id = tca.catalog_id
        WHERE  c.source_id = $1
        """,
        source_id,
    )

    # Sensitive columns = columns with a tag assigned (PII detection)
    sensitive_columns = await db.fetch_val(
        """
        SELECT COUNT(DISTINCT tca.column_id)
        FROM   tag_column_assignments tca
        JOIN   catalogs c ON c.id = tca.catalog_id
        WHERE  c.source_id = $1
        """,
        source_id,
    )

    # ── 5. Fetch error/warning log counts for the job ────────────────────────
    log_counts = await db.fetch_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE level = 'error')   AS error_count,
            COUNT(*) FILTER (WHERE level = 'warning') AS warning_count,
            COUNT(*) FILTER (WHERE level = 'success') AS success_count
        FROM job_logs
        WHERE job_id = $1
        """,
        job_id,
    )

    # Top errors to give AI context (capped at 10)
    top_errors = await db.fetch_all(
        """
        SELECT message FROM job_logs
        WHERE  job_id = $1 AND level = 'error'
        ORDER  BY logged_at ASC
        LIMIT  10
        """,
        job_id,
    )

    # ── 6. Build stats dict ──────────────────────────────────────────────────
    total_tables     = int(catalog_stats["total_tables"]   or 0)
    healthy_count    = int(catalog_stats["healthy_count"]  or 0)
    warning_count    = int(catalog_stats["warning_count"]  or 0)
    risk_count       = int(catalog_stats["risk_count"]     or 0)
    total_rows       = int(catalog_stats["total_rows"]     or 0)
    classified       = int(classified_count                or 0)
    sensitive_cols   = int(sensitive_columns               or 0)
    error_log_count  = int(log_counts["error_count"]       or 0)
    warning_log_count= int(log_counts["warning_count"]     or 0)

    duration_seconds = None
    if job["created_at"] and job["completed_at"]:
        duration_seconds = int(
            (job["completed_at"] - job["created_at"]).total_seconds()
        )

    # ── 7. Build AI prompt ───────────────────────────────────────────────────
    error_lines = "\n".join(f"  - {r['message']}" for r in top_errors) or "  none"

    prompt_context = f"""
Source        : {source['name']} ({source['source_type']})
Job Status    : {job['status'].upper()}
Duration      : {f"{duration_seconds}s" if duration_seconds else "unknown"}

Ingestion Results:
  Tables/datasets ingested : {total_tables}
  Rows ingested            : {total_rows:,}
  Classified datasets      : {classified}
  Sensitive columns (PII)  : {sensitive_cols}
  Healthy datasets         : {healthy_count}
  Warning datasets         : {warning_count}
  At-risk datasets         : {risk_count}

Log Summary:
  Errors   : {error_log_count}
  Warnings : {warning_log_count}

Top Errors:
{error_lines}

Top-level error message: {job['error_message'] or 'none'}
""".strip()

    system_prompt = (
        "You are a data pipeline assistant. Based on the ingestion run metadata provided, "
        "write a single concise sentence (max 30 words) summarising the pipeline result. "
        "Format: start with an emoji (⚡ for success, ⚠️ for warnings, ❌ for failure), "
        "then state: datasets ingested, PII scanned with sensitive column count, and classification status. "
        "Example: '⚡ All 5 datasets ingested, PII scanned (3 sensitive columns found), classified and compliance-checked.' "
        "Be factual. No markdown. One sentence only."
    )

    # ── 8. Call Azure OpenAI ─────────────────────────────────────────────────
    try:
        client = AsyncAzureOpenAI(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        )
        response = await client.chat.completions.create(
            model=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": prompt_context},
            ],
            temperature=0.2,
            max_tokens=80,
        )
        ai_summary = response.choices[0].message.content.strip()

    except KeyError as e:
        raise HTTPException(status_code=500, detail=f"Missing env variable: {e}")
    except Exception as e:
        logger.error(f"Azure OpenAI failed for source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=f"AI summary failed: {str(e)}")

    # ── 9. Return response ───────────────────────────────────────────────────
    return {
        "source_id":   source_id,
        "source_name": source["name"],
        "job_id":      job_id,
        "pipeline_status": job["status"],       # "success" | "failed"
        "badges": {
            "ingested":   total_tables,          # → "5 ingested"
            "classified": classified,            # → "5 classified"
        },
        "stats": {
            "total_rows":       total_rows,
            "sensitive_columns": sensitive_cols,
            "healthy":          healthy_count,
            "warning":          warning_count,
            "risk":             risk_count,
            "duration_seconds": duration_seconds,
        },
        "log_counts": {
            "error":   error_log_count,
            "warning": warning_log_count,
        },
        "ai_summary": ai_summary,   # → one-line prose for the Summary card
    }