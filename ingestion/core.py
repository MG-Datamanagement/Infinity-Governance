"""
Ingestion Core Module

Provides:
- SOURCE_TEMPLATES: Configuration templates for different database types
- PostgresSink: Custom sink for writing metadata to PostgreSQL
- PostgresSinkReport: Report class for PostgresSink
- Database: Async database connection manager
- IngestionManager: Manager for metadata ingestion pipelines
"""

import os
import re
import json
import logging
import asyncio
import asyncpg
import copy
import psycopg2

from typing import Optional, Dict, Any
from asyncpg import Pool
from psycopg2.pool import SimpleConnectionPool
from datahub.ingestion.api.common import RecordEnvelope
from datahub.metadata.schema_classes import (
    DatasetSnapshotClass,
    DatasetPropertiesClass,
    SchemaMetadataClass,
    DatasetProfileClass,
)

logger = logging.getLogger(__name__)


# ============================================================================
# SOURCE TEMPLATES
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
# CUSTOM SINK
# ============================================================================

class PostgresSink:
    """Custom sink that writes metadata to PostgreSQL"""

    def __init__(self, ctx, config):
        from config import Settings
        
        self.config = config
        self.job_id = config.get('job_id')
        self.source_id = config.get('source_id')
        self.records_written = 0
        self.conn_pool = None
        self.settings = Settings()
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
                host=self.settings.PG_HOST,
                port=self.settings.PG_PORT,
                database=self.settings.PG_DB,
                user=self.settings.PG_USER,
                password=self.settings.PG_PASS
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
                        elif aspect_name == 'datasetProfile' or isinstance(aspect, DatasetProfileClass):
                            self._process_profile(cur, catalog_id, aspect)
                    
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
                                elif isinstance(aspect, DatasetProfileClass):
                                    self._process_profile(cur, catalog_id, aspect)
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
            column_count = 0
            if hasattr(schema, 'fields') and schema.fields:
                for idx, field in enumerate(schema.fields):
                    field_path = getattr(field, 'fieldPath', 'unknown')
                    field_type = str(getattr(field, 'type', 'unknown'))
                    column_name = field_path.split('.')[-1] if field_path else 'unknown'
                    cur.execute("""
                        INSERT INTO columns (catalog_id, name, ordinal_position, data_type, metadata)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (catalog_id, column_name, idx + 1, field_type, json.dumps({})))
                    column_count = idx + 1
            
            # Store column count in catalog_stats
            if column_count > 0:
                cur.execute("""
                    INSERT INTO catalog_stats (catalog_id, column_count, computed_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (catalog_id)
                    DO UPDATE SET column_count = EXCLUDED.column_count, computed_at = NOW()
                """, (catalog_id, column_count))
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
    
    def _process_profile(self, cur, catalog_id: str, profile: DatasetProfileClass):
        """Process and store dataset profile statistics (row count) in catalog_stats"""
        try:
            row_count = None
            if hasattr(profile, 'rowCount') and profile.rowCount is not None:
                row_count = profile.rowCount
            
            # Get column count from schema if available
            column_count = None
            cur.execute("SELECT COUNT(*) FROM columns WHERE catalog_id = %s", (catalog_id,))
            col_result = cur.fetchone()
            if col_result:
                column_count = col_result[0]
            
            # Store or update in catalog_stats
            if row_count is not None or column_count is not None:
                cur.execute("""
                    INSERT INTO catalog_stats (catalog_id, row_count, column_count, computed_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (catalog_id)
                    DO UPDATE SET row_count = EXCLUDED.row_count, 
                                  column_count = EXCLUDED.column_count,
                                  computed_at = NOW()
                """, (catalog_id, row_count, column_count))
                logger.debug(f"Updated catalog_stats for {catalog_id}: row_count={row_count}, column_count={column_count}")
        except Exception as e:
            logger.exception(f"Error processing profile for catalog_id={catalog_id}: {e}")
    
    def write_record_async(self, record_envelope: RecordEnvelope, write_callback):
        """Process record synchronously and invoke callback.

        pipeline calls `write_record_async` without awaiting it in
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


class PostgresSinkReport:
    """Lightweight report for PostgresSink"""
    def __init__(self):
        self.records_written = 0
        # pipeline expects `failures` (iterable) and optionally `warnings`
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
    
    async def connect(self, settings):
        """Create connection pool and initialize schema"""
        from app import INIT_DB_SQL
        
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


# ============================================================================
# INGESTION MANAGER
# ============================================================================

class IngestionManager:
    """Manages metadata ingestion pipelines"""
    
    def __init__(self):
        self.active_jobs: Dict[str, Dict] = {}
        self.semaphore = None
    
    def set_db(self, db):
        """Set database instance"""
        self.db = db
    
    def set_settings(self, settings):
        """Set settings and semaphore"""
        self.settings = settings
        self.semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_INGESTIONS)
    
    async def create_job(self, source_id: str, config: Dict = None) -> str:
        """Create ingestion job record"""
        job_id = await self.db.fetch_val("""
            INSERT INTO ingestion_jobs (source_id, status, config)
            VALUES ($1, 'running', $2)
            RETURNING id
        """, source_id, json.dumps(config) if config else None)
        return str(job_id)
    
    async def update_job(self, job_id: str, status: str, records: int = 0, error: str = None):
        """Update job status"""
        if error:
            await self.db.execute("""
                UPDATE ingestion_jobs 
                SET status = $1, completed_at = NOW(), records_ingested = $2, error_message = $3
                WHERE id = $4
            """, status, records, error, job_id)
        else:
            await self.db.execute("""
                UPDATE ingestion_jobs 
                SET status = $1, completed_at = NOW(), records_ingested = $2
                WHERE id = $3
            """, status, records, job_id)
    
    async def _extract_postgres_metadata(self, source_id: str, job_id: str, conn_details: Dict, schemapattern=['.*'], tablepattern=['.*']) -> int:
        """Run PostgreSQL metadata extraction in a thread to avoid blocking event loop"""
        return await asyncio.to_thread(self._extract_postgres_metadata_sync, source_id, job_id, conn_details, schemapattern, tablepattern)
    
    def _extract_postgres_metadata_sync(self, source_id: str, job_id: str, conn_details: Dict, schemapattern=['.*'], tablepattern=['.*']) -> int:
        """Extract metadata directly from PostgreSQL using SQL queries (synchronous)"""
        try:
            # Safely parse host and port
            host_port = conn_details.get('host_port', 'localhost:5432')
            host = host_port.split(':')[0] if host_port else 'localhost'
            port = 5432
            if ':' in host_port:
                try:
                    port = int(host_port.split(':')[1])
                except (ValueError, IndexError):
                    port = 5432
            
            # Connect to source database
            src_conn = psycopg2.connect(
                host=host,
                port=port,
                database=conn_details['database'],
                user=conn_details['username'],
                password=conn_details['password']
            )
            
            src_cursor = src_conn.cursor()
            sink_conn = psycopg2.connect(
                host=self.settings.PG_HOST,
                port=self.settings.PG_PORT,
                database=self.settings.PG_DB,
                user=self.settings.PG_USER,
                password=self.settings.PG_PASS
            )
            sink_cursor = sink_conn.cursor()
            
            records_written = 0
            
            # Query tables and views
            src_cursor.execute("""
                SELECT table_schema, table_name, table_type
                FROM information_schema.tables
                WHERE table_catalog = %s
                ORDER BY table_schema, table_name
            """, (conn_details['database'],))
            
            tables = src_cursor.fetchall()
            
            filtered_tables = []
            for schema_name, table_name, table_type in tables:
                schema_match = any(re.match(pattern, schema_name) for pattern in schemapattern)
                table_match = any(re.match(pattern, table_name) for pattern in tablepattern)
                if schema_match and table_match:
                    filtered_tables.append((schema_name, table_name, table_type))
        
            logger.info(f"Found {len(tables)} total tables, filtered to {len(filtered_tables)} matching patterns")
            for schema_name, table_name, table_type in filtered_tables:
                # Insert catalog
                sink_cursor.execute("""
                    INSERT INTO catalogs (source_id, database_name, schema_name, table_name, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (source_id, database_name, schema_name, table_name)
                    DO UPDATE SET metadata = EXCLUDED.metadata, last_seen_at = NOW(), updated_at = NOW()
                    RETURNING id
                """, (str(source_id), conn_details['database'], schema_name, table_name, json.dumps({"table_type": table_type})))
                
                catalog_id = sink_cursor.fetchone()[0]
                
                # Query columns
                src_cursor.execute("""
                    SELECT column_name, ordinal_position, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_catalog = %s AND table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (conn_details['database'], schema_name, table_name))
                
                columns = src_cursor.fetchall()
                
                # Delete old columns
                sink_cursor.execute("DELETE FROM columns WHERE catalog_id = %s", (catalog_id,))
                
                # Insert new columns
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
        """Run ingestion pipeline
         After a successful ingest, if config['require_auto_pii_detection'] is True
        the auto_pii_service orchestrator is called automatically to classify
        all tables and columns that were just stored.

        config keys consumed here (all optional, default False/0.0):
            require_auto_pii_detection : bool
            required_human_approval    : bool  (only relevant when above is True)
            pii_min_confidence         : float (0.0–1.0)
        
        """
        from datahub.ingestion.run.pipeline import Pipeline
        from ingestion.job_log_handler import register_job, deregister_job

        register_job(job_id, source_id)

        async with self.semaphore:
            try:
                # Get source details
                source = await self.db.fetch_one("SELECT * FROM data_sources WHERE id = $1", source_id)
                if not source:
                    raise ValueError(f"Source {source_id} not found")
                
                # Build pipeline config
                source_type = source['source_type']
                template = copy.deepcopy(SOURCE_TEMPLATES.get(source_type, {}))
                
                if not template:
                    raise ValueError(f"Unsupported source type: {source_type}")
                
                # Merge connection details
                conn_details = json.loads(source['connection_details'])
                
                # Filter out invalid fields for specific source types
                if source_type == "mongodb":
                    MONGODB_ALLOWED_KEYS = {
                        "connect_uri", "username", "password",
                        "collection_pattern", "platform_instance",
                        "enableSchemaInference", "useRandomSampling", "maxSchemaSize"
                    }
                    conn_details = {k: v for k, v in conn_details.items() if k in MONGODB_ALLOWED_KEYS}

                elif source_type == "snowflake":
                    if "database" in conn_details:
                        db_value = conn_details.pop("database")
                        if db_value:
                            template['config']["database_pattern"] = {"allow": [db_value]}

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
                    if table_pattern:
                        template['config']['collection_pattern'] = {"allow": table_pattern}
                else:
                    if schema_pattern:
                        template['config']['schema_pattern'] = {"allow": schema_pattern}
                    if table_pattern:
                        template['config']['table_pattern'] = {"allow": table_pattern}
                    
                    template['config']['include_views'] = source.get('include_views', True)
                    template['config']['include_tables'] = source.get('include_tables', True)
                
                # Enable profiling by default
                if source_type != "mongodb":
                    if 'profiling' not in template['config']:
                        template['config']['profiling'] = {"enabled": True}
                    elif template['config'].get('profiling', {}).get('enabled') is False:
                        pass
                    else:
                        template['config']['profiling'] = {"enabled": True}
                
                # logger.info(f"Starting ingestion for source {source_id}, job {job_id}")
                logger.info(
                    f"[Ingestion] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )
                logger.info(f"[Ingestion] Job started  — source_id={source_id}  job_id={job_id}")
                logger.info(f"[Ingestion] Source type  : {source_type}")
                logger.info(f"[Ingestion] Source name  : {source['name']}")

                schemapattern = json.loads(source['schema_pattern']) if source.get('schema_pattern') else ['.*']
                tablepattern = json.loads(source['table_pattern']) if source.get('table_pattern') else ['.*']

                if source_type == "postgres":
                    records_ingested = await self._extract_postgres_metadata(source_id, job_id, conn_details, schemapattern, tablepattern)
                elif source_type == "snowflake":
                    pipeline_config = {
                        "source": template,
                        "sink": {"type": "console"}
                    }
                    sink_container = {}
                    def run_snowflake_pipeline():
                        _sink = PostgresSink(None, {"job_id": job_id, "source_id": source_id})
                        sink_container['sink'] = _sink
                        try:
                            _pipeline = Pipeline.create(pipeline_config)
                            _pipeline.sink = _sink
                            _pipeline.run()
                        finally:
                            _sink.close()

                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, run_snowflake_pipeline)
                    sink = sink_container.get('sink')
                    records_ingested = sink.records_written if sink else 0
                else:
                    # Create custom sink
                    sink = PostgresSink(
                        None,
                        {"job_id": job_id, "source_id": source_id}
                    )
                    
                    # Build pipeline config with custom sink
                    pipeline_config = {
                        "source": template,
                        "sink": {
                            "type": "console"
                        }
                    }
                    
                    pipeline = Pipeline.create(pipeline_config)
                    pipeline.sink = sink
                    
                    # Run in thread pool with error handling
                    loop = asyncio.get_event_loop()
                    try:
                        await loop.run_in_executor(None, pipeline.run)
                    except UnboundLocalError as e:
                        if "data_platform_instance" in str(e):
                            logger.error(f"MongoDB connector error (known bug): {e}")
                            logger.info("Attempting recovery with alternative approach...")
                            raise Exception("MongoDB schema inference encountered an issue. Try with enableSchemaInference=false")
                        raise
                    
                    sink.close()
                    records_ingested = sink.records_written
                
                await self.update_job(job_id, 'success', records_ingested)

                await self.db.execute("""
                    UPDATE data_sources SET last_ingested_at = NOW(), status = 'success' WHERE id = $1
                """, source_id)

                logger.info(
                    f"[Ingestion] ✓ Metadata ingestion complete — "
                    f"{records_ingested} table(s) recorded for job {job_id}"
                )
                
                # logger.info(f"Ingestion completed: {records_ingested} records for job {job_id}")


            # ── ✅ AUTO PII DETECTION ─────────────────────────────────────
                # Only runs after data is fully committed to the database.
                # Triggered only when require_auto_pii_detection=True in the
                # original ingestion request.
                #
                # required_human_approval=True  → results saved to pii_detection_pending
                #                                  (awaiting human review)
                # required_human_approval=False → results written directly to
                #                                  tag_catalog_assignments /
                #                                  tag_column_assignments
                # ─────────────────────────────────────────────────────────────
                if config.get("require_auto_pii_detection", False):
                    try:
                        # from auto_pii_service import run_auto_pii_detection
                        from ingestion.auto_pii_service import run_auto_pii_detection


                        human_approval = config.get("required_human_approval", False)
                        logger.info(f"[Ingestion] ────────────────────────────────────────────────────")
                        logger.info(f"[AutoPII]  PII / tag detection triggered for source={source_id}")
                        logger.info(f"[AutoPII]  Mode: {'PENDING (human approval required)' if human_approval else 'AUTO-ASSIGN (direct save)'}")
                        logger.info(f"[AutoPII]  Min confidence threshold: {config.get('pii_min_confidence', 0.0)}")


                        pii_summary = await run_auto_pii_detection(
                            db=self.db,
                            source_id=source_id,
                            require_auto_pii_detection=True,
                            required_human_approval=config.get("required_human_approval", False),
                            min_confidence=config.get("pii_min_confidence", 0.0),
                        )

                        # Persist the PII detection summary back onto the job record
                        # so it's visible in job-detail API response.
                        await self.db.execute("""
                            UPDATE ingestion_jobs
                            SET metadata = COALESCE(metadata, '{}'::jsonb) || $1::jsonb
                            WHERE id = $2
                        """, json.dumps({"auto_pii_summary": pii_summary}), job_id)

                        cat  = pii_summary.get("catalog_classification", {})
                        col  = pii_summary.get("column_classification", {})
                        logger.info(
                            f"[AutoPII]  ✓ Detection complete — "
                            f"tables: {cat.get('classified',0)} classified, "
                            f"{cat.get('saved',0)} saved, {cat.get('pending',0)} pending | "
                            f"columns: {col.get('classified',0)} classified, "
                            f"{col.get('saved',0)} saved, {col.get('pending',0)} pending"
                        )
                        logger.info(f"[Ingestion] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                        logger.info(f"[Ingestion] ✓ Source ingestion fully complete — job_id={job_id}")

                        # logger.info(f"[AutoPII] Completed for source={source_id}: {pii_summary}")

                    except Exception as pii_error:
                        # PII detection failure must NEVER fail or roll back the
                        # ingestion job — log it and continue.
                        logger.error(
                            f"[AutoPII] Detection failed for source={source_id} "
                            f"(ingestion itself succeeded): {pii_error}"
                        )
                        # Record the failure in job metadata so the caller can see it.
                        try:
                            await self.db.execute("""
                                UPDATE ingestion_jobs
                                SET metadata = COALESCE(metadata, '{}'::jsonb) || $1::jsonb
                                WHERE id = $2
                            """, json.dumps({"auto_pii_error": str(pii_error)}), job_id)
                        except Exception:
                            pass
                # ── END AUTO PII DETECTION ────────────────────────────────────

                
            except Exception as e:
                logger.error(f"Ingestion failed for job {job_id}: {e}")
                await self.update_job(job_id, 'failed', error=str(e))
                await self.db.execute("""
                    UPDATE data_sources SET status = 'failed' WHERE id = $1
                """, source_id)

                raise

            finally:
                # Always deregister — closes the SSE stream whether job
                # succeeded, failed, or raised an unexpected exception.
                deregister_job(job_id)