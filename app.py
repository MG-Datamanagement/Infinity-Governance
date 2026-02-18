"""
Unified Metadata Ingestion API - Single File Application
Works with your Docker setup: PostgreSQL in Docker, DataHub network
"""

import os
import json
import logging
import asyncio
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from contextlib import asynccontextmanager
from enum import Enum

# FastAPI imports
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

# Database imports
import asyncpg
from asyncpg import Pool
import psycopg2
from psycopg2.extras import Json, execute_values
from psycopg2.pool import SimpleConnectionPool

# DataHub SDK imports
from datahub.ingestion.run.pipeline import Pipeline
from datahub.ingestion.api.sink import Sink, WriteCallback
from datahub.ingestion.api.common import RecordEnvelope
from datahub.metadata.schema_classes import (
    DatasetSnapshotClass,
    DatasetPropertiesClass,
    SchemaMetadataClass,
    SchemaFieldClass,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

class Settings:
    """Application settings from environment variables"""
    # Database
    PG_HOST: str = os.getenv("PG_HOST", "postgres_ig")
    PG_PORT: int = int(os.getenv("PG_PORT", "5432"))
    PG_DB: str = os.getenv("PG_DB", "semantic_search")
    PG_USER: str = os.getenv("PG_USER", "semantic_user")
    PG_PASS: str = os.getenv("PG_PASS", "semantic_pass")
    
    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8005"))
    
    # Ingestion
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "100"))
    MAX_CONCURRENT_INGESTIONS: int = int(os.getenv("MAX_CONCURRENT_INGESTIONS", "3"))
    
    # DataHub (optional - if you want to also push to DataHub)
    DATAHUB_GRAPHQL_URL: Optional[str] = os.getenv("DATAHUB_GRAPHQL_URL")

settings = Settings()

# ============================================================================
# ENUMS
# ============================================================================

class SourceType(str, Enum):
    POSTGRES = "postgres"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    SNOWFLAKE = "snowflake"
    COCKROACHDB = "cockroachdb"

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ConnectionDetails(BaseModel):
    """Base connection details model"""
    host_port: Optional[str] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    
    # MongoDB specific
    connect_uri: Optional[str] = None
    
    # Snowflake specific
    account_id: Optional[str] = None
    warehouse: Optional[str] = None
    role: Optional[str] = None
    
    class Config:
        extra = "allow"

class DataSourceCreate(BaseModel):
    name: str
    source_type: SourceType
    connection_details: ConnectionDetails
    description: Optional[str] = None
    include_views: bool = True
    include_tables: bool = True
    schema_pattern: Optional[List[str]] = None
    table_pattern: Optional[List[str]] = None

class DataSource(DataSourceCreate):
    id: str
    status: str = "active"
    created_at: datetime
    updated_at: datetime
    last_ingested_at: Optional[datetime]
    
    class Config:
        orm_mode = True

class IngestionRequest(BaseModel):
    source_id: str
    include_profiling: bool = False
    include_lineage: bool = True
    incremental: bool = False

class IngestionResponse(BaseModel):
    job_id: str
    source_id: str
    source_name: str
    status: str
    message: str

class ColumnInfo(BaseModel):
    name: str
    data_type: str
    ordinal_position: Optional[int]
    is_nullable: bool = True
    is_primary_key: bool = False
    is_foreign_key: bool = False
    description: Optional[str] = None

class CatalogInfo(BaseModel):
    id: Optional[str]
    database_name: Optional[str]
    schema_name: Optional[str]
    table_name: str
    full_name: Optional[str]
    description: Optional[str]
    source_name: Optional[str]
    source_type: Optional[str]
    columns: List[ColumnInfo] = []
    properties: Dict[str, Any] = Field(default_factory=dict)
    column_count: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class SearchRequest(BaseModel):
    query: str
    source_type: Optional[SourceType] = None
    limit: int = 50

class StatisticsResponse(BaseModel):
    total_sources: int
    active_sources: int
    total_datasets: int
    total_columns: int
    successful_jobs: int
    failed_jobs: int
    source_types_count: int
    sources_by_type: Dict[str, int]
    last_ingestion: Optional[datetime]

# ============================================================================
# DATABASE SCHEMA
# ============================================================================

INIT_DB_SQL = """
-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Data sources table
CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    connection_details JSONB NOT NULL,
    description TEXT,
    include_views BOOLEAN DEFAULT true,
    include_tables BOOLEAN DEFAULT true,
    schema_pattern JSONB,
    table_pattern JSONB,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_ingested_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(name)
);

-- Ingestion jobs table
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES data_sources(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    records_ingested INTEGER DEFAULT 0,
    error_message TEXT,
    config JSONB,
    metadata JSONB
);

-- Datasets/catalogs table
CREATE TABLE IF NOT EXISTS catalogs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES data_sources(id) ON DELETE CASCADE,
    database_name VARCHAR(255),
    schema_name VARCHAR(255),
    table_name VARCHAR(255) NOT NULL,
    full_name VARCHAR(512) GENERATED ALWAYS AS (
        CASE 
            WHEN database_name IS NOT NULL AND schema_name IS NOT NULL THEN database_name || '.' || schema_name || '.' || table_name
            WHEN schema_name IS NOT NULL THEN schema_name || '.' || table_name
            ELSE table_name
        END
    ) STORED,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(source_id, database_name, schema_name, table_name)
);

-- Columns table
CREATE TABLE IF NOT EXISTS columns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    catalog_id UUID REFERENCES catalogs(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    ordinal_position INTEGER,
    data_type VARCHAR(100),
    is_nullable BOOLEAN DEFAULT true,
    is_primary_key BOOLEAN DEFAULT false,
    is_foreign_key BOOLEAN DEFAULT false,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(catalog_id, name)
);

-- Relationships/Lineage table
CREATE TABLE IF NOT EXISTS relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_catalog_id UUID REFERENCES catalogs(id) ON DELETE CASCADE,
    target_catalog_id UUID REFERENCES catalogs(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) DEFAULT 'dependency',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Custom properties table
CREATE TABLE IF NOT EXISTS custom_properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    catalog_id UUID REFERENCES catalogs(id) ON DELETE CASCADE,
    key VARCHAR(255) NOT NULL,
    value TEXT,
    value_type VARCHAR(50) DEFAULT 'string',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(catalog_id, key)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_catalogs_source ON catalogs(source_id);
CREATE INDEX IF NOT EXISTS idx_catalogs_full_name ON catalogs(full_name);
CREATE INDEX IF NOT EXISTS idx_catalogs_search ON catalogs USING GIN (
    to_tsvector('english', COALESCE(table_name, '') || ' ' || COALESCE(description, ''))
);
CREATE INDEX IF NOT EXISTS idx_columns_catalog ON columns(catalog_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_source ON ingestion_jobs(source_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status ON ingestion_jobs(status);

-- Updated at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers
DROP TRIGGER IF EXISTS update_data_sources_updated_at ON data_sources;
CREATE TRIGGER update_data_sources_updated_at
    BEFORE UPDATE ON data_sources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_catalogs_updated_at ON catalogs;
CREATE TRIGGER update_catalogs_updated_at
    BEFORE UPDATE ON catalogs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Domains table
CREATE TABLE IF NOT EXISTS domains (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(20),                        -- optional UI color e.g. '#FF5733'
    parent_domain_id UUID REFERENCES domains(id) ON DELETE SET NULL,  -- for nested domains
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name)
);

-- Domain <-> Catalog (dataset) assignments
CREATE TABLE IF NOT EXISTS domain_catalog_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain_id UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    catalog_id UUID NOT NULL REFERENCES catalogs(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    assigned_by VARCHAR(255) DEFAULT 'system',
    UNIQUE(domain_id, catalog_id)
);

-- Index for fast lookup
CREATE INDEX IF NOT EXISTS idx_domain_catalog_domain ON domain_catalog_assignments(domain_id);
CREATE INDEX IF NOT EXISTS idx_domain_catalog_catalog ON domain_catalog_assignments(catalog_id);

-- Updated at trigger for domains
DROP TRIGGER IF EXISTS update_domains_updated_at ON domains;
CREATE TRIGGER update_domains_updated_at
    BEFORE UPDATE ON domains
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


"""

# ============================================================================
# SOURCE CONFIGURATION TEMPLATES
# ============================================================================

SOURCE_TEMPLATES = {
    "postgres": {
        "type": "postgres",
        "config": {
            "host_port": None,
            "database": None,
            "username": None,
            "password": None,
            "schema_pattern": {"allow": ["public"]},
            "table_pattern": {"allow": [".*"]},
            "include_views": True,
            "include_tables": True,
            "profiling": {"enabled": False},
            "stateful_ingestion": {"enabled": False}
        }
    },
    "mysql": {
        "type": "mysql",
        "config": {
            "host_port": None,
            "database": None,
            "username": None,
            "password": None,
            "schema_pattern": {"allow": [".*"]},
            "table_pattern": {"allow": [".*"]},
            "profiling": {"enabled": False}
        }
    },
    "mongodb": {
        "type": "mongodb",
        "config": {
            "connect_uri": None,
            "username": None,
            "password": None,
            "collection_pattern": {
                "allow": [".*"]
            },
            "platform_instance": "prod",
            "enableSchemaInference": False,
            "useRandomSampling": False,
            "maxSchemaSize": 300
        }
    },
    "snowflake": {
        "type": "snowflake",
        "config": {
            "account_id": None,
            "warehouse": None,
            "database": None,
            "username": None,
            "password": None,
            "role": None,
            "include_tables": True,
            "include_views": True,
            "profiling": {"enabled": False}
        }
    },
    "cockroachdb": {
        "type": "postgres", 
        "config": {
            "host_port": None,
            "database": None,
            "username": None,
            "password": None,
            "schema_pattern": {"allow": ["public"]},
            "table_pattern": {"allow": [".*"]},
            "include_views": True,
            "profiling": {"enabled": False}
        }
    }
}

# ============================================================================
# CUSTOM DATAHUB SINK
# ============================================================================

class PostgresSink:
    """Custom DataHub sink that writes metadata to PostgreSQL"""

    def __init__(self, ctx, config):
        self.config = config
        self.job_id = config.get('job_id')
        self.source_id = config.get('source_id')
        self.records_written = 0
        self.conn_pool = None
        self._init_connection_pool()
        # ensure report exists for base Sink expectations (always provide a report)
        try:
            self.report = self.get_report_class()()
        except Exception:
            logger.warning("Failed to instantiate report class; using default PostgresSinkReport")
            self.report = PostgresSinkReport()

    def _init_connection_pool(self):
        try:
            self.conn_pool = SimpleConnectionPool(
                1, 10,
                host=settings.PG_HOST,
                port=settings.PG_PORT,
                database=settings.PG_DB,
                user=settings.PG_USER,
                password=settings.PG_PASS
            )
            # Log database info for debugging (which DB/schema the sink connects to)
            try:
                conn = self._get_conn()
                if conn:
                    cur = conn.cursor()
                    try:
                        cur.execute('SELECT current_database(), current_schema()')
                        db_info = cur.fetchone()
                        logger.info(f"PostgresSink connected to database={db_info[0]}, schema={db_info[1]}")
                    finally:
                        cur.close()
                        self._put_conn(conn)
            except Exception:
                logger.debug("Could not query current_database() for sink connection")
        except Exception as e:
            logger.error(f"Failed to init Postgres sink pool: {e}")
            self.conn_pool = None

    def _get_conn(self):
        return self.conn_pool.getconn() if self.conn_pool else None

    def _put_conn(self, conn):
        if self.conn_pool and conn:
            self.conn_pool.putconn(conn)
    
    def handle_work_unit_start(self, workunit):
        """Called when a work unit starts."""
        return

    def handle_work_unit(self, workunit):
        """Process a work unit (records) synchronously."""
        for record_envelope in getattr(workunit, 'records', []):
            try:
                self._process_record(record_envelope)
            except Exception as e:
                logger.error(f"Error processing record: {e}")

    def handle_work_unit_end(self, workunit):
        """Called when a work unit ends."""
        return

    def _process_record(self, record_envelope: RecordEnvelope):
        """Process individual metadata record and store in PostgreSQL synchronously"""
        record = record_envelope.record
        
        # Handle MetadataChangeProposalWrapper format (MCP)
        if hasattr(record, 'aspect') and hasattr(record, 'entityUrn'):
            # Extract dataset info from entityUrn and aspect
            self._process_mcp_record(record)
        # Handle proposedSnapshot format (legacy)
        elif hasattr(record, 'proposedSnapshot'):
            snapshot = record.proposedSnapshot
            if snapshot and getattr(snapshot, 'urn', None) and getattr(snapshot, 'aspects', None):
                self._process_dataset(snapshot)
        else:
            logger.debug(f"Record format not recognized: {type(record).__name__}")
    
    def _process_mcp_record(self, record):
        """Process MetadataChangeProposal format record"""
        try:
            # Extract dataset name from entityUrn: urn:li:dataset:(platform,dataset_name,env)
            entity_urn = record.entityUrn
            
            if 'urn:li:dataset:' not in entity_urn:
                return
            
            # Parse URN to extract platform, name, env: urn:li:dataset:(platform,name,env)
            urn_parts = entity_urn.split('(')
            if len(urn_parts) < 2:
                logger.warning(f"Cannot parse URN: {entity_urn}")
                return
            
            dataset_tuple = urn_parts[1].rstrip(')')
            tuple_parts = [p.strip() for p in dataset_tuple.split(',')]
            
            if len(tuple_parts) >= 2:
                full_name = tuple_parts[1]  # dataset name
                
                # Parse database.schema.table format
                name_parts = full_name.split('.')
                database_name = None
                schema_name = None
                table_name = full_name
                
                if len(name_parts) >= 3:
                    database_name = name_parts[0]
                    schema_name = name_parts[1]
                    table_name = '.'.join(name_parts[2:])
                elif len(name_parts) == 2:
                    schema_name = name_parts[0]
                    table_name = name_parts[1]
                
                conn = None
                try:
                    conn = self._get_conn()
                    if not conn:
                        logger.error("No Postgres connection available for sink")
                        return
                    
                    cur = conn.cursor()
                    
                    # Insert catalog entry
                    sql = (
                        "INSERT INTO catalogs (source_id, database_name, schema_name, table_name, metadata)"
                        " VALUES (%s, %s, %s, %s, %s)"
                        " ON CONFLICT (source_id, database_name, schema_name, table_name)"
                        " DO UPDATE SET metadata = EXCLUDED.metadata, last_seen_at = NOW(), updated_at = NOW()"
                        " RETURNING id"
                    )
                    params = (str(self.source_id), database_name, schema_name, table_name, json.dumps({}))
                    cur.execute(sql, params)
                    res = cur.fetchone()
                    
                    if res:
                        catalog_id = res[0]
                        
                        # Process aspect if it's a schema or properties aspect
                        aspect = record.aspect
                        aspect_name = record.aspectName
                        
                        if aspect_name == 'schemaMetadata' or isinstance(aspect, SchemaMetadataClass):
                            self._process_schema(cur, catalog_id, aspect)
                        elif aspect_name == 'datasetProperties' or isinstance(aspect, DatasetPropertiesClass):
                            self._process_properties(cur, catalog_id, aspect)
                    
                    conn.commit()
                    
                    try:
                        cur.close()
                    except Exception:
                        pass
                    
                    self.records_written += 1
                    if hasattr(self, 'report') and self.report is not None:
                        self.report.records_written += 1
                        
                except Exception as e:
                    if conn:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                    logger.exception(f"Error processing MCP record {entity_urn}: {e}")
                finally:
                    if conn:
                        self._put_conn(conn)
        except Exception as e:
            logger.exception(f"Error in _process_mcp_record: {e}")
    
    def _process_dataset(self, snapshot: DatasetSnapshotClass):
        """Process and store dataset metadata synchronously"""
        try:
            urn = snapshot.urn
            if 'urn:li:dataset:' in urn:
                parts = urn.split(',')
                if len(parts) >= 2:
                    full_name = parts[1].rstrip(')')
                    name_parts = full_name.split('.')
                    database_name = None
                    schema_name = None
                    table_name = full_name

                    if len(name_parts) >= 3:
                        database_name = name_parts[0]
                        schema_name = name_parts[1]
                        table_name = '.'.join(name_parts[2:])
                    elif len(name_parts) == 2:
                        schema_name = name_parts[0]
                        table_name = name_parts[1]

                    conn = None
                    try:
                        conn = self._get_conn()
                        if not conn:
                            logger.error("No Postgres connection available for sink")
                            return
                        cur = conn.cursor()
                        sql = (
                            "INSERT INTO catalogs (source_id, database_name, schema_name, table_name, metadata)"
                            " VALUES (%s, %s, %s, %s, %s)"
                            " ON CONFLICT (source_id, database_name, schema_name, table_name)"
                            " DO UPDATE SET metadata = EXCLUDED.metadata, last_seen_at = NOW(), updated_at = NOW()"
                            " RETURNING id"
                        )
                        params = (str(self.source_id), database_name, schema_name, table_name, json.dumps({}))
                        cur.execute(sql, params)
                        res = cur.fetchone()
                        if res:
                            catalog_id = res[0]
                            # Process aspects
                            for aspect in snapshot.aspects:
                                if isinstance(aspect, SchemaMetadataClass):
                                    self._process_schema(cur, catalog_id, aspect)
                                elif isinstance(aspect, DatasetPropertiesClass):
                                    self._process_properties(cur, catalog_id, aspect)
                        conn.commit()
                        try:
                            cur.close()
                        except Exception:
                            pass
                        # Count this only after successful commit
                        try:
                            self.records_written += 1
                        except Exception:
                            pass
                        try:
                            if hasattr(self, 'report') and self.report is not None:
                                self.report.records_written += 1
                        except Exception:
                            pass
                    except Exception as e:
                        if conn:
                            try:
                                conn.rollback()
                            except Exception:
                                pass
                        logger.exception(f"Error processing dataset {getattr(snapshot, 'urn', None)}: {e}")
                    finally:
                        if conn:
                            self._put_conn(conn)
        except Exception as e:
            logger.error(f"Error processing dataset {getattr(snapshot, 'urn', 'unknown')}: {e}")
    
    def _process_schema(self, cur, catalog_id: str, schema: SchemaMetadataClass):
        """Process and store schema metadata synchronously"""
        try:
            cur.execute("DELETE FROM columns WHERE catalog_id = %s", (catalog_id,))
            if hasattr(schema, 'fields') and schema.fields:
                for idx, field in enumerate(schema.fields):
                    field_path = getattr(field, 'fieldPath', 'unknown')
                    field_type = str(getattr(field, 'type', 'unknown'))
                    column_name = field_path.split('.')[-1] if field_path else 'unknown'
                    cur.execute("""
                        INSERT INTO columns (catalog_id, name, ordinal_position, data_type, metadata)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (catalog_id, column_name, idx + 1, field_type, json.dumps({})))
        except Exception as e:
            logger.exception(f"Error processing schema for catalog_id={catalog_id}: {e}")
    
    def _process_properties(self, cur, catalog_id: str, properties: DatasetPropertiesClass):
        """Process and store custom properties synchronously"""
        try:
            cur.execute("DELETE FROM custom_properties WHERE catalog_id = %s", (catalog_id,))
            if hasattr(properties, 'customProperties') and properties.customProperties:
                for key, value in properties.customProperties.items():
                    cur.execute("""
                        INSERT INTO custom_properties (catalog_id, key, value) VALUES (%s, %s, %s)
                    """, (catalog_id, key, str(value)))
        except Exception as e:
            logger.exception(f"Error processing properties for catalog_id={catalog_id}: {e}")
    
    def write_record_async(self, record_envelope: RecordEnvelope, write_callback):
        """Process record synchronously and invoke callback.

        DataHub's pipeline calls `write_record_async` without awaiting it in
        some execution paths. Make this a synchronous method so it doesn't
        return a coroutine that would be left un-awaited by the pipeline.
        """
        try:
            # Process record synchronously; pipeline.run executes in a worker thread
            self._process_record(record_envelope)

            # Only mark success after processing (counters are updated on commit in _process_mcp_record)
            try:
                write_callback.on_success(record_envelope, {})
            except Exception:
                # Ensure callback exceptions do not break pipeline
                pass
        except Exception as e:
            logger.error(f"Error writing record: {e}")
            try:
                write_callback.on_failure(record_envelope, e, {})
            except Exception:
                pass

    def get_report_class(self):
        """Return the report class used by this sink"""
        return PostgresSinkReport

    def get_report(self):
        """Return the sink report instance (pipeline expects this)."""
        return self.report

    def close(self):
        """Close sink and connection pool"""
        try:
            if self.conn_pool:
                self.conn_pool.closeall()
        except Exception as e:
            logger.warning(f"Error closing sink pool: {e}")
        logger.info(f"PostgresSink closed. Total records written: {self.records_written}")
        # no base class close to call (we don't inherit from DataHub Sink)

class PostgresSinkReport:
    """Lightweight report for PostgresSink"""
    def __init__(self):
        self.records_written = 0
        # DataHub pipeline expects `failures` (iterable) and optionally `warnings`
        self.failures = []
        self.warnings = []
    def __repr__(self):
        return f"<PostgresSinkReport records_written={self.records_written}>"

# ============================================================================
# DATABASE CONNECTION
# ============================================================================

class Database:
    """Async database connection manager"""
    
    def __init__(self):
        self.pool: Optional[Pool] = None
    
    async def connect(self):
        """Create connection pool and initialize schema"""
        try:
            self.pool = await asyncpg.create_pool(
                host=settings.PG_HOST,
                port=settings.PG_PORT,
                database=settings.PG_DB,
                user=settings.PG_USER,
                password=settings.PG_PASS,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            
            # Initialize database schema
            async with self.pool.acquire() as conn:
                await conn.execute(INIT_DB_SQL)
            
            logger.info("Database connected and initialized")
            
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database disconnected")
    
    async def fetch_one(self, query: str, *args):
        """Fetch one row"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetch_all(self, query: str, *args):
        """Fetch all rows"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def execute(self, query: str, *args):
        """Execute query"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch_val(self, query: str, *args):
        """Fetch single value"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

db = Database()

# ============================================================================
# INGESTION MANAGER
# ============================================================================

class IngestionManager:
    """Manages metadata ingestion pipelines"""
    
    def __init__(self):
        self.active_jobs: Dict[str, Dict] = {}
        self.semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_INGESTIONS)
    
    async def create_job(self, source_id: str, config: Dict = None) -> str:
        """Create ingestion job record"""
        job_id = await db.fetch_val("""
            INSERT INTO ingestion_jobs (source_id, status, config)
            VALUES ($1, 'pending', $2)
            RETURNING id
        """, source_id, json.dumps(config) if config else None)
        return str(job_id)
    
    async def update_job(self, job_id: str, status: JobStatus, records: int = 0, error: str = None):
        """Update job status"""
        if error:
            await db.execute("""
                UPDATE ingestion_jobs 
                SET status = $1, completed_at = NOW(), records_ingested = $2, error_message = $3
                WHERE id = $4
            """, status.value, records, error, job_id)
        else:
            await db.execute("""
                UPDATE ingestion_jobs 
                SET status = $1, completed_at = NOW(), records_ingested = $2
                WHERE id = $3
            """, status.value, records, job_id)
    
    async def _extract_postgres_metadata(self, source_id: str, job_id: str, conn_details: Dict) -> int:
        """Run PostgreSQL metadata extraction in a thread to avoid blocking event loop
        
        This is a wrapper that offloads the synchronous extraction to a thread pool.
        """
        return await asyncio.to_thread(self._extract_postgres_metadata_sync, source_id, job_id, conn_details)
    
    def _extract_postgres_metadata_sync(self, source_id: str, job_id: str, conn_details: Dict) -> int:
        """Extract metadata directly from PostgreSQL using SQL queries (synchronous)"""
        try:
            import psycopg2
            import json
            
            # Safely parse host and port
            host_port = conn_details.get('host_port', 'localhost:5432')
            host = host_port.split(':')[0] if host_port else 'localhost'
            port = 5432
            if ':' in host_port:
                try:
                    port = int(host_port.split(':')[1])
                except (ValueError, IndexError):
                    port = 5432
            
            # Connect to source database (connection parameters are not SQL-injectable)
            src_conn = psycopg2.connect(
                host=host,
                port=port,
                database=conn_details['database'],
                user=conn_details['username'],
                password=conn_details['password']
            )
            
            src_cursor = src_conn.cursor()
            sink_conn = psycopg2.connect(
                host=settings.PG_HOST,
                port=settings.PG_PORT,
                database=settings.PG_DB,
                user=settings.PG_USER,
                password=settings.PG_PASS
            )
            sink_cursor = sink_conn.cursor()
            
            records_written = 0
            
            # Query tables and views (using parameterized query)
            src_cursor.execute("""
                SELECT table_schema, table_name, table_type
                FROM information_schema.tables
                WHERE table_catalog = %s
                ORDER BY table_schema, table_name
            """, (conn_details['database'],))
            
            tables = src_cursor.fetchall()
            
            for schema_name, table_name, table_type in tables:
                # Insert catalog (all parameters are bound, not interpolated)
                sink_cursor.execute("""
                    INSERT INTO catalogs (source_id, database_name, schema_name, table_name, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (source_id, database_name, schema_name, table_name)
                    DO UPDATE SET metadata = EXCLUDED.metadata, last_seen_at = NOW(), updated_at = NOW()
                    RETURNING id
                """, (str(source_id), conn_details['database'], schema_name, table_name, json.dumps({"table_type": table_type})))
                
                catalog_id = sink_cursor.fetchone()[0]
                
                # Query columns (using parameterized query)
                src_cursor.execute("""
                    SELECT column_name, ordinal_position, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_catalog = %s AND table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (conn_details['database'], schema_name, table_name))
                
                columns = src_cursor.fetchall()
                
                # Delete old columns (all parameters are bound)
                sink_cursor.execute("DELETE FROM columns WHERE catalog_id = %s", (catalog_id,))
                
                # Insert new columns (all parameters are bound)
                for col_name, ord_pos, data_type, is_nullable in columns:
                    sink_cursor.execute("""
                        INSERT INTO columns (catalog_id, name, ordinal_position, data_type, metadata)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (catalog_id, col_name, ord_pos, data_type, json.dumps({"is_nullable": is_nullable})))
                
                records_written += 1
            
            sink_conn.commit()
            sink_cursor.close()
            sink_conn.close()
            src_cursor.close()
            src_conn.close()
            
            return records_written
            
        except Exception as e:
            logger.exception(f"Error extracting Postgres metadata: {e}")
            raise
    
    async def ingest(self, source_id: str, job_id: str, config: Dict):
        """Run ingestion pipeline"""
        async with self.semaphore:
            try:
                # Update job to running
                await db.execute("""
                    UPDATE ingestion_jobs SET status = 'running' WHERE id = $1
                """, job_id)
                
                # Get source details
                source = await db.fetch_one("SELECT * FROM data_sources WHERE id = $1", source_id)
                if not source:
                    raise ValueError(f"Source {source_id} not found")
                
                # Build pipeline config
                source_type = source['source_type']
                template = SOURCE_TEMPLATES.get(source_type, {}).copy()
                
                if not template:
                    raise ValueError(f"Unsupported source type: {source_type}")
                
                # Merge connection details
                conn_details = json.loads(source['connection_details'])
                
                # Filter out invalid fields for specific source types
                if source_type == "mongodb":
                    # MongoDB doesn't accept 'database' field - it's in the connection URI
                    conn_details.pop('database', None)
                
                for key, value in conn_details.items():
                    if key in template['config']:
                        template['config'][key] = value
                
                # Parse pattern fields from JSON
                schema_pattern = None
                table_pattern = None
                
                if source.get('schema_pattern'):
                    schema_pattern = json.loads(source['schema_pattern']) if isinstance(source['schema_pattern'], str) else source['schema_pattern']
                
                if source.get('table_pattern'):
                    table_pattern = json.loads(source['table_pattern']) if isinstance(source['table_pattern'], str) else source['table_pattern']
                
                # Apply source-type-specific patterns
                if source_type == "mongodb":
                    # MongoDB uses collection_pattern as dict with "allow" key
                    if table_pattern:
                        template['config']['collection_pattern'] = {"allow": table_pattern}
                else:
                    # SQL databases use schema_pattern and table_pattern
                    if schema_pattern:
                        template['config']['schema_pattern'] = {"allow": schema_pattern}
                    if table_pattern:
                        template['config']['table_pattern'] = {"allow": table_pattern}
                    
                    # SQL databases have include_views and include_tables
                    template['config']['include_views'] = source.get('include_views', True)
                    template['config']['include_tables'] = source.get('include_tables', True)
                    
                    # Add profiling if requested
                    if config.get('include_profiling'):
                        template['config']['profiling'] = {"enabled": True}
                
                # Create and run pipeline with custom sink
                logger.info(f"Starting ingestion for source {source_id}, job {job_id}")
                
                # For Postgres sources, use direct SQL extraction to avoid DataHub threading issues
                if source_type == "postgres":
                    records_ingested = await self._extract_postgres_metadata(source_id, job_id, conn_details)
                else:
                    # Create custom sink
                    sink = PostgresSink(
                        None,
                        {"job_id": job_id, "source_id": source_id}
                    )
                    
                    # Build pipeline config with custom sink (use None type for custom)
                    pipeline_config = {
                        "source": template,
                        "sink": {
                            "type": "console"  # Use console as fallback, but we'll intercept with custom sink
                        }
                    }
                    
                    pipeline = Pipeline.create(pipeline_config)
                    
                    # Replace sink with custom sink
                    pipeline.sink = sink
                    
                    # Run in thread pool with error handling
                    loop = asyncio.get_event_loop()
                    try:
                        await loop.run_in_executor(None, pipeline.run)
                    except UnboundLocalError as e:
                        # Handle DataHub MongoDB connector bug
                        if "data_platform_instance" in str(e):
                            logger.error(f"MongoDB connector error (known DataHub bug): {e}")
                            logger.info("Attempting recovery with alternative approach...")
                            raise Exception("MongoDB schema inference encountered an issue. Try with enableSchemaInference=false")
                        raise
                    
                    # Close sink
                    sink.close()
                    
                    # Get record count from sink
                    records_ingested = sink.records_written
                
                await self.update_job(job_id, JobStatus.COMPLETED, records_ingested)
                
                # Update source last ingested
                await db.execute("""
                    UPDATE data_sources SET last_ingested_at = NOW() WHERE id = $1
                """, source_id)
                
                logger.info(f"Ingestion completed: {records_ingested} records for job {job_id}")
                
            except Exception as e:
                logger.error(f"Ingestion failed for job {job_id}: {e}")
                await self.update_job(job_id, JobStatus.FAILED, error=str(e))
                raise

ingestion_manager = IngestionManager()

# ============================================================================
# FASTAPI LIFESPAN
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager"""
    # Startup
    logger.info("Starting up...")
    await db.connect()
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await db.disconnect()

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="Unified Metadata Ingestion API",
    description="Ingest metadata from multiple sources using DataHub SDK",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# API ROUTES
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Unified Metadata Ingestion API",
        "version": "1.0.0",
        "status": "running",
        "supported_sources": list(SOURCE_TEMPLATES.keys()),
        "database": settings.PG_HOST
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        await db.fetch_val("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

# ============================================================================
# Data Source Management
# ============================================================================

@app.post("/sources", response_model=DataSource)
async def create_source(source: DataSourceCreate):
    """Register a new data source"""
    try:
        # Check if source with same name exists
        existing = await db.fetch_one("SELECT id FROM data_sources WHERE name = $1", source.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Source with name '{source.name}' already exists")
        
        # Insert source
        result = await db.fetch_one("""
            INSERT INTO data_sources (
                name, source_type, connection_details, description,
                include_views, include_tables, schema_pattern, table_pattern
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, name, source_type, connection_details, description,
                      include_views, include_tables, schema_pattern, table_pattern,
                      status, created_at, updated_at, last_ingested_at
        """, 
            source.name, 
            source.source_type.value, 
            json.dumps(source.connection_details.dict(exclude_none=True)),
            source.description,
            source.include_views,
            source.include_tables,
            json.dumps(source.schema_pattern) if source.schema_pattern else None,
            json.dumps(source.table_pattern) if source.table_pattern else None
        )
        
        # Parse JSON fields from database response
        data = dict(result)
        data['id'] = str(data['id'])
        data['connection_details'] = json.loads(data['connection_details']) if data['connection_details'] else {}
        data['schema_pattern'] = json.loads(data['schema_pattern']) if data['schema_pattern'] else None
        data['table_pattern'] = json.loads(data['table_pattern']) if data['table_pattern'] else None
        
        return data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating source: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sources", response_model=List[DataSource])
async def list_sources(
    source_type: Optional[SourceType] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """List all data sources"""
    try:
        query = "SELECT * FROM data_sources WHERE 1=1"
        params = []
        
        if source_type:
            query += f" AND source_type = ${len(params) + 1}"
            params.append(source_type.value)
        
        if status:
            query += f" AND status = ${len(params) + 1}"
            params.append(status)
        
        query += f" ORDER BY created_at DESC LIMIT ${len(params) + 1}"
        params.append(limit)
        
        results = await db.fetch_all(query, *params)
        
        # Parse JSON fields for all results
        parsed_results = []
        for row in results:
            data = dict(row)
            data['id'] = str(data['id'])
            data['connection_details'] = json.loads(data['connection_details']) if data['connection_details'] else {}
            data['schema_pattern'] = json.loads(data['schema_pattern']) if data['schema_pattern'] else None
            data['table_pattern'] = json.loads(data['table_pattern']) if data['table_pattern'] else None
            parsed_results.append(data)
        
        return parsed_results
    
    except Exception as e:
        logger.error(f"Error listing sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sources/{source_id}", response_model=DataSource)
async def get_source(source_id: str):
    """Get source by ID"""
    try:
        result = await db.fetch_one("SELECT * FROM data_sources WHERE id = $1", source_id)
        if not result:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Parse JSON fields
        data = dict(result)
        data['id'] = str(data['id'])
        data['connection_details'] = json.loads(data['connection_details']) if data['connection_details'] else {}
        data['schema_pattern'] = json.loads(data['schema_pattern']) if data['schema_pattern'] else None
        data['table_pattern'] = json.loads(data['table_pattern']) if data['table_pattern'] else None
        
        return data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting source: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sources/{source_id}")
async def delete_source(source_id: str):
    """Delete a data source"""
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

@app.post("/ingest", response_model=IngestionResponse)
async def start_ingestion(
    request: IngestionRequest,
    background_tasks: BackgroundTasks
):
    """Start metadata ingestion for a source"""
    try:
        # Get source details
        source = await db.fetch_one("SELECT * FROM data_sources WHERE id = $1", request.source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        if source['status'] != 'active':
            raise HTTPException(status_code=400, detail=f"Source is not active (status: {source['status']})")
        
        # Create job
        job_id = await ingestion_manager.create_job(
            request.source_id, 
            {"profiling": request.include_profiling, "lineage": request.include_lineage}
        )
        
        # Run ingestion in background
        background_tasks.add_task(
            ingestion_manager.ingest,
            request.source_id,
            job_id,
            {"include_profiling": request.include_profiling, "include_lineage": request.include_lineage}
        )
        
        return IngestionResponse(
            job_id=job_id,
            source_id=request.source_id,
            source_name=source['name'],
            status="started",
            message="Ingestion job started successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs")
async def list_jobs(
    source_id: Optional[str] = None,
    status: Optional[JobStatus] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """List ingestion jobs"""
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
        
        query += f" ORDER BY j.started_at DESC LIMIT ${len(params) + 1}"
        params.append(limit)
        
        results = await db.fetch_all(query, *params)
        return [dict(row) for row in results]
    
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job by ID"""
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

# ============================================================================
# Metadata Querying
# ============================================================================

@app.get("/catalogs", response_model=List[CatalogInfo])
async def list_catalogs(
    source_id: Optional[str] = None,
    database: Optional[str] = None,
    schema: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """List all catalogs/datasets"""
    try:
        query = """
            SELECT 
                c.id, c.database_name, c.schema_name, c.table_name, 
                c.full_name, c.description, c.created_at, c.updated_at,
                ds.name as source_name, ds.source_type,
                COUNT(DISTINCT col.id) as column_count
            FROM catalogs c
            JOIN data_sources ds ON c.source_id = ds.id
            LEFT JOIN columns col ON c.id = col.catalog_id
            WHERE 1=1
        """
        params = []
        
        if source_id:
            query += f" AND c.source_id = ${len(params) + 1}"
            params.append(source_id)
        
        if database:
            query += f" AND c.database_name = ${len(params) + 1}"
            params.append(database)
        
        if schema:
            query += f" AND c.schema_name = ${len(params) + 1}"
            params.append(schema)
        
        if search:
            query += f" AND (c.table_name ILIKE ${len(params) + 1} OR c.full_name ILIKE ${len(params) + 1})"
            params.append(f"%{search}%")
        
        query += " GROUP BY c.id, ds.name, ds.source_type ORDER BY c.table_name"
        query += f" LIMIT ${len(params) + 1}"
        params.append(limit)
        
        results = await db.fetch_all(query, *params)
        
        catalogs = []
        for row in results:
            catalog = dict(row)
            # Convert UUID to string
            catalog['id'] = str(catalog['id']) if catalog['id'] else None
            # Get columns for this catalog
            columns = await db.fetch_all("""
                SELECT name, data_type, ordinal_position, is_nullable, 
                       is_primary_key, is_foreign_key, description
                FROM columns
                WHERE catalog_id = $1
                ORDER BY ordinal_position
            """, catalog['id'])
            catalog['columns'] = [dict(col) for col in columns]
            catalogs.append(catalog)
        
        return catalogs
    
    except Exception as e:
        logger.error(f"Error listing catalogs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/catalogs/{catalog_id}", response_model=CatalogInfo)
async def get_catalog(catalog_id: str):
    """Get catalog by ID with full details"""
    try:
        # Get catalog
        catalog = await db.fetch_one("""
            SELECT 
                c.*, ds.name as source_name, ds.source_type
            FROM catalogs c
            JOIN data_sources ds ON c.source_id = ds.id
            WHERE c.id = $1
        """, catalog_id)
        
        if not catalog:
            raise HTTPException(status_code=404, detail="Catalog not found")
        
        # Get columns
        columns = await db.fetch_all("""
            SELECT name, data_type, ordinal_position, is_nullable,
                   is_primary_key, is_foreign_key, description
            FROM columns 
            WHERE catalog_id = $1 
            ORDER BY ordinal_position
        """, catalog_id)
        
        # Get custom properties
        properties = await db.fetch_all("""
            SELECT key, value FROM custom_properties 
            WHERE catalog_id = $1
        """, catalog_id)
        
        result = dict(catalog)
        result['id'] = str(result['id']) if result['id'] else None
        result['columns'] = [dict(col) for col in columns]
        result['properties'] = {row['key']: row['value'] for row in properties}
        result['column_count'] = len(columns)
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting catalog: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Search
# ============================================================================

@app.post("/search")
async def search_metadata(request: SearchRequest):
    """Search across metadata"""
    try:
        query = """
            SELECT DISTINCT 
                c.id,
                c.full_name,
                c.table_name,
                c.database_name,
                c.schema_name,
                c.description,
                ds.name as source_name,
                ds.source_type,
                COUNT(DISTINCT col.id) as column_count,
                ts_rank(
                    to_tsvector('english', 
                        COALESCE(c.table_name, '') || ' ' || 
                        COALESCE(c.description, '') || ' ' ||
                        COALESCE(c.full_name, '')
                    ), 
                    plainto_tsquery('english', $1)
                ) as rank
            FROM catalogs c
            JOIN data_sources ds ON c.source_id = ds.id
            LEFT JOIN columns col ON c.id = col.catalog_id
            WHERE to_tsvector('english', 
                COALESCE(c.table_name, '') || ' ' || 
                COALESCE(c.description, '') || ' ' ||
                COALESCE(c.full_name, '')
            ) @@ plainto_tsquery('english', $1)
        """
        params = [request.query]
        
        if request.source_type:
            query += f" AND ds.source_type = ${len(params) + 1}"
            params.append(request.source_type.value)
        
        query += " GROUP BY c.id, ds.name, ds.source_type ORDER BY rank DESC"
        query += f" LIMIT ${len(params) + 1}"
        params.append(request.limit)
        
        results = await db.fetch_all(query, *params)
        
        # Convert UUIDs to strings
        return [dict(row, id=str(row['id']) if row['id'] else None) for row in results]
    
    except Exception as e:
        logger.error(f"Error searching metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Statistics
# ============================================================================

@app.get("/statistics", response_model=StatisticsResponse)
async def get_statistics():
    """Get metadata statistics"""
    try:
        stats = await db.fetch_one("""
            SELECT
                (SELECT COUNT(*) FROM data_sources) as total_sources,
                (SELECT COUNT(*) FROM data_sources WHERE status = 'active') as active_sources,
                (SELECT COUNT(*) FROM catalogs) as total_datasets,
                (SELECT COUNT(*) FROM columns) as total_columns,
                (SELECT COUNT(*) FROM ingestion_jobs WHERE status = 'completed') as successful_jobs,
                (SELECT COUNT(*) FROM ingestion_jobs WHERE status = 'failed') as failed_jobs,
                (SELECT COUNT(DISTINCT source_type) FROM data_sources) as source_types_count,
                (SELECT MAX(last_ingested_at) FROM data_sources) as last_ingestion
        """)
        
        # Get sources by type
        sources_by_type = await db.fetch_all("""
            SELECT source_type, COUNT(*) as count
            FROM data_sources
            GROUP BY source_type
        """)
        
        result = dict(stats)
        result['sources_by_type'] = {row['source_type']: row['count'] for row in sources_by_type}
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))





# ==============================================================================
# STEP 2 — Pydantic Models (add after your existing model definitions)
# ==============================================================================

class DomainCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Domain name e.g. 'Finance'")
    description: Optional[str] = Field(None, description="What this domain covers")
    color: Optional[str] = Field(None, description="UI color hex e.g. '#3B82F6'")
    parent_domain_id: Optional[str] = Field(None, description="Parent domain UUID for nesting")

class DomainUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = None
    parent_domain_id: Optional[str] = None

class DomainResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    color: Optional[str]
    parent_domain_id: Optional[str]
    parent_domain_name: Optional[str]   # resolved from join
    dataset_count: int = 0
    created_at: datetime
    updated_at: datetime

class DomainAssignRequest(BaseModel):
    catalog_ids: List[str] = Field(..., description="List of catalog UUIDs to assign to this domain")
    assigned_by: Optional[str] = Field("system", description="Who is making this assignment")

class DomainCatalogResponse(BaseModel):
    """Catalog info when listed under a domain"""
    catalog_id: str
    full_name: Optional[str]
    table_name: str
    database_name: Optional[str]
    schema_name: Optional[str]
    source_name: Optional[str]
    source_type: Optional[str]
    assigned_at: datetime
    assigned_by: Optional[str]




# -------------------------------------------------------------------------------
# CREATE a domain
# POST /domains
# -------------------------------------------------------------------------------
@app.post("/domains", response_model=DomainResponse, status_code=201)
async def create_domain(payload: DomainCreate):
    """
    Create a new domain.
    
    Domains are top-level organizational units that group related datasets together.
    Example domains: Finance, Marketing, Engineering, HR, Operations
    
    You can also nest domains by providing a parent_domain_id.
    """
    try:
        # Validate parent domain exists if provided
        if payload.parent_domain_id:
            parent = await db.fetch_one(
                "SELECT id FROM domains WHERE id = $1",
                payload.parent_domain_id
            )
            if not parent:
                raise HTTPException(status_code=404, detail=f"Parent domain '{payload.parent_domain_id}' not found")

        domain = await db.fetch_one("""
            INSERT INTO domains (name, description, color, parent_domain_id)
            VALUES ($1, $2, $3, $4)
            RETURNING id, name, description, color, parent_domain_id, created_at, updated_at
        """, payload.name, payload.description, payload.color,
            payload.parent_domain_id)

        result = dict(domain)
        result['id'] = str(result['id'])
        result['parent_domain_id'] = str(result['parent_domain_id']) if result.get('parent_domain_id') else None
        result['parent_domain_name'] = None
        result['dataset_count'] = 0

        logger.info(f"Created domain: {payload.name} (id={result['id']})")
        return result

    except HTTPException:
        raise
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Domain '{payload.name}' already exists")
        logger.error(f"Error creating domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------------------------
# LIST all domains
# GET /domains
# -------------------------------------------------------------------------------
@app.get("/domains", response_model=List[DomainResponse])
async def list_domains(
    search: Optional[str] = None,
    parent_domain_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """
    List all domains with dataset counts.
    
    Optionally filter by name search or parent domain to browse the hierarchy.
    """
    try:
        query = """
            SELECT
                d.id,
                d.name,
                d.description,
                d.color,
                d.parent_domain_id,
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

        query += " GROUP BY d.id, d.name, d.description, d.color, d.parent_domain_id, p.name"
        query += " ORDER BY d.name"
        query += f" LIMIT ${len(params)+1}"
        params.append(limit)

        rows = await db.fetch_all(query, *params)
        results = []
        for row in rows:
            r = dict(row)
            r['id'] = str(r['id'])
            r['parent_domain_id'] = str(r['parent_domain_id']) if r.get('parent_domain_id') else None
            results.append(r)

        return results

    except Exception as e:
        logger.error(f"Error listing domains: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------------------------
# GET a single domain
# GET /domains/{domain_id}
# -------------------------------------------------------------------------------
@app.get("/domains/{domain_id}", response_model=DomainResponse)
async def get_domain(domain_id: str):
    """Get a single domain by ID with its dataset count."""
    try:
        row = await db.fetch_one("""
            SELECT
                d.id, d.name, d.description, d.color,
                d.parent_domain_id, p.name AS parent_domain_name,
                d.created_at, d.updated_at,
                COUNT(DISTINCT dca.catalog_id) AS dataset_count
            FROM domains d
            LEFT JOIN domains p ON d.parent_domain_id = p.id
            LEFT JOIN domain_catalog_assignments dca ON d.id = dca.domain_id
            WHERE d.id = $1
            GROUP BY d.id, d.name, d.description, d.color, d.parent_domain_id, p.name
        """, domain_id)

        if not row:
            raise HTTPException(status_code=404, detail="Domain not found")

        result = dict(row)
        result['id'] = str(result['id'])
        result['parent_domain_id'] = str(result['parent_domain_id']) if result.get('parent_domain_id') else None
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------------------------
# UPDATE a domain
# PUT /domains/{domain_id}
# -------------------------------------------------------------------------------
@app.put("/domains/{domain_id}", response_model=DomainResponse)
async def update_domain(domain_id: str, payload: DomainUpdate):
    """Update domain name, description, color, or parent."""
    try:
        existing = await db.fetch_one("SELECT id FROM domains WHERE id = $1", domain_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Domain not found")

        # Build dynamic update
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
            # Prevent self-referencing
            if payload.parent_domain_id == domain_id:
                raise HTTPException(status_code=400, detail="Domain cannot be its own parent")
            params.append(payload.parent_domain_id)
            set_clauses.append(f"parent_domain_id = ${len(params)}")

        if not set_clauses:
            raise HTTPException(status_code=400, detail="No fields to update")

        params.append(domain_id)
        await db.execute(
            f"UPDATE domains SET {', '.join(set_clauses)}, updated_at = NOW() WHERE id = ${len(params)}",
            *params
        )

        return await get_domain(domain_id)

    except HTTPException:
        raise
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Domain name already exists")
        logger.error(f"Error updating domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------------------------
# DELETE a domain
# DELETE /domains/{domain_id}
# -------------------------------------------------------------------------------
@app.delete("/domains/{domain_id}", status_code=204)
async def delete_domain(domain_id: str):
    """
    Delete a domain.
    
    All dataset assignments for this domain are automatically removed (CASCADE).
    Child domains will have their parent_domain_id set to NULL.
    """
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


# -------------------------------------------------------------------------------
# ASSIGN datasets to a domain
# POST /domains/{domain_id}/assign
# -------------------------------------------------------------------------------
@app.post("/domains/{domain_id}/assign")
async def assign_catalogs_to_domain(domain_id: str, payload: DomainAssignRequest):
    """
    Assign one or more datasets (catalogs) to a domain.
    
    Pass a list of catalog UUIDs. Already-assigned catalogs are silently skipped
    (idempotent). Invalid catalog IDs are reported back without failing the request.
    
    Example body:
        { "catalog_ids": ["uuid-1", "uuid-2"], "assigned_by": "alice" }
    """
    try:
        domain = await db.fetch_one("SELECT id, name FROM domains WHERE id = $1", domain_id)
        if not domain:
            raise HTTPException(status_code=404, detail="Domain not found")

        assigned = []
        skipped = []     # already assigned
        not_found = []   # catalog_id doesn't exist

        for catalog_id in payload.catalog_ids:
            # Check catalog exists
            cat = await db.fetch_one("SELECT id, full_name FROM catalogs WHERE id = $1", catalog_id)
            if not cat:
                not_found.append(catalog_id)
                continue

            try:
                await db.execute("""
                    INSERT INTO domain_catalog_assignments (domain_id, catalog_id, assigned_by)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (domain_id, catalog_id) DO NOTHING
                """, domain_id, catalog_id, payload.assigned_by)
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
            "total_assigned": len(assigned)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning catalogs to domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------------------------
# REMOVE a dataset from a domain
# DELETE /domains/{domain_id}/assign/{catalog_id}
# -------------------------------------------------------------------------------
@app.delete("/domains/{domain_id}/assign/{catalog_id}", status_code=204)
async def remove_catalog_from_domain(domain_id: str, catalog_id: str):
    """Remove a single dataset from a domain."""
    try:
        result = await db.execute("""
            DELETE FROM domain_catalog_assignments
            WHERE domain_id = $1 AND catalog_id = $2
        """, domain_id, catalog_id)

        # asyncpg returns 'DELETE N' as string
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Assignment not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing catalog from domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------------------------
# LIST datasets in a domain
# GET /domains/{domain_id}/datasets
# -------------------------------------------------------------------------------
@app.get("/domains/{domain_id}/datasets", response_model=List[DomainCatalogResponse])
async def list_domain_datasets(
    domain_id: str,
    limit: int = Query(200, ge=1, le=1000)
):
    """
    List all datasets assigned to a domain.
    
    Returns catalog metadata alongside assignment info (who assigned it, when).
    """
    try:
        domain = await db.fetch_one("SELECT id FROM domains WHERE id = $1", domain_id)
        if not domain:
            raise HTTPException(status_code=404, detail="Domain not found")

        rows = await db.fetch_all("""
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
        """, domain_id, limit)

        # Convert UUID catalog_id to string
        return [dict(row, catalog_id=str(row['catalog_id']) if row['catalog_id'] else None) for row in rows]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing domain datasets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------------------------
# GET domains for a specific dataset
# GET /catalogs/{catalog_id}/domains
# -------------------------------------------------------------------------------
@app.get("/catalogs/{catalog_id}/domains")
async def get_catalog_domains(catalog_id: str):
    """
    Get all domains a specific dataset belongs to.
    
    Useful when rendering a dataset page — shows which domains it is classified under.
    """
    try:
        cat = await db.fetch_one("SELECT id FROM catalogs WHERE id = $1", catalog_id)
        if not cat:
            raise HTTPException(status_code=404, detail="Catalog not found")

        rows = await db.fetch_all("""
            SELECT
                d.id, d.name, d.description, d.color,
                dca.assigned_at, dca.assigned_by
            FROM domain_catalog_assignments dca
            JOIN domains d ON dca.domain_id = d.id
            WHERE dca.catalog_id = $1
            ORDER BY d.name
        """, catalog_id)

        # Convert UUIDs to strings
        return [dict(row, id=str(row['id']) if row['id'] else None) for row in rows]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting catalog domains: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    )