

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
    UpstreamLineageClass,
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
            "profiling": {"enabled": False},
            "include_table_lineage": True,
            "include_column_lineage": True
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
    },
    "athena": {
        "type": "athena",
        "config": {
            "aws_region": None,
            "work_group": "primary",
            "s3_staging_dir": None,
            "schema_pattern": {"allow": [".*"]},
            "table_pattern": {"allow": [".*"]},
            "include_views": True,
            "include_tables": True,
            "profiling": {"enabled": False}
        }
    },
    "dynamodb": {
        
        "type": "dynamodb",
        "config": {
            "aws_access_key_id": None,
            "aws_secret_access_key": None,
            "table_pattern": {"allow": [".*"]}
        }
    },
    "glue": {
        
        "type": "glue",
        "config": {
            "aws_region": None,
            "catalog_id": None,
            "database_pattern": {"allow": [".*"]},
            "table_pattern": {"allow": [".*"]}
        }
    },
    "mssql": {
    "type": "mssql",
    "config": {
        "host_port": None,
        "database": None,
        "username": None,
        "password": None,
        "schema_pattern": {"allow": [".*"]},
        "table_pattern": {"allow": [".*"]},
        "include_views": True,
        "include_tables": True,
        "profiling": {"enabled": False}
        }
    },
    "csv": {
    "type": "csv",
    "config": {
        "file_url": None,
        "delimiter": ",",
        "array_delimiter": "|",
        "write_semantics": "PATCH"
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
            entity_urn = record.entityUrn

            if 'urn:li:dataset:' not in entity_urn:
                return

            urn_parts = entity_urn.split('(')
            if len(urn_parts) < 2:
                logger.warning(f"Cannot parse URN: {entity_urn}")
                return

            dataset_tuple = urn_parts[1].rstrip(')')
            tuple_parts = [p.strip() for p in dataset_tuple.split(',')]

            if len(tuple_parts) >= 2:
                full_name = tuple_parts[1]

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

                        aspect = record.aspect
                        aspect_name = record.aspectName

                        if aspect_name == 'schemaMetadata' or isinstance(aspect, SchemaMetadataClass):
                            self._process_schema(cur, catalog_id, aspect)
                        elif aspect_name == 'datasetProperties' or isinstance(aspect, DatasetPropertiesClass):
                            self._process_properties(cur, catalog_id, aspect)
                        elif aspect_name == 'datasetProfile' or isinstance(aspect, DatasetProfileClass):
                            self._process_profile(cur, catalog_id, aspect)
                        elif aspect_name == 'upstreamLineage' or isinstance(aspect, UpstreamLineageClass):
                            self._process_lineage(cur, catalog_id, entity_urn, aspect)

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
                    description = getattr(field, 'description', None)
                    cur.execute("""
                        INSERT INTO columns (catalog_id, name, ordinal_position, data_type, description, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (catalog_id, column_name, idx + 1, field_type, description, json.dumps({})))
                    column_count = idx + 1

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

            table_description = getattr(properties, 'description', None)
            if table_description:
                cur.execute("""
                    UPDATE catalogs SET description = %s WHERE id = %s
                """, (table_description, catalog_id))


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

            column_count = None
            cur.execute("SELECT COUNT(*) FROM columns WHERE catalog_id = %s", (catalog_id,))
            col_result = cur.fetchone()
            if col_result:
                column_count = col_result[0]

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

    def _process_lineage(self, cur, downstream_catalog_id: str, entity_urn: str, lineage: UpstreamLineageClass):
        """
        Store table-level and column-level lineage from Snowflake's UpstreamLineageClass.
        Writes into: table_lineage, lineage_column_mappings
        """
        try:
            if not hasattr(lineage, 'upstreams') or not lineage.upstreams:
                return

            for upstream in lineage.upstreams:
                upstream_urn = upstream.dataset

                # ── Resolve upstream URN → catalog_id in YOUR postgres ──────
                upstream_catalog_id = self._resolve_catalog_id_sync(cur, upstream_urn)
                if not upstream_catalog_id:
                    logger.debug(f"[Lineage] Upstream catalog not found for URN: {upstream_urn}")
                    continue

                # ── Get the SQL query that caused this lineage (if present) ──
                query_text = getattr(upstream, 'query', None)

                # ── Upsert into table_lineage ────────────────────────────────
                cur.execute("""
                    INSERT INTO table_lineage (
                        upstream_catalog_id,
                        downstream_catalog_id,
                        transformation_query,
                        is_active
                    )
                    VALUES (%s, %s, %s, TRUE)
                    ON CONFLICT (upstream_catalog_id, downstream_catalog_id)
                    DO UPDATE SET
                        transformation_query = EXCLUDED.transformation_query,
                        is_active = TRUE,
                        updated_at = NOW()
                    RETURNING id
                """, (str(upstream_catalog_id), str(downstream_catalog_id), query_text))

                lineage_row = cur.fetchone()
                if not lineage_row:
                    continue
                lineage_id = lineage_row[0]

                logger.info(
                    f"[Lineage] ✓ Table lineage stored: "
                    f"{upstream_catalog_id} → {downstream_catalog_id}"
                )

            # ── Column-level lineage (fineGrainedLineages) ──────────────────
            fine_grained = getattr(lineage, 'fineGrainedLineages', None)
            if not fine_grained:
                return

            for fg in fine_grained:
                up_col_urns = getattr(fg, 'upstreams', []) or []
                dn_col_urns = getattr(fg, 'downstreams', []) or []

                for up_col_urn in up_col_urns:
                    for dn_col_urn in dn_col_urns:
                        up_col_id = self._resolve_column_id_sync(cur, up_col_urn)
                        dn_col_id = self._resolve_column_id_sync(cur, dn_col_urn)

                        if not up_col_id or not dn_col_id:
                            continue

                        # Get lineage_id for this column pair's tables
                        tbl_lineage_id = self._resolve_lineage_id_sync(
                            cur, up_col_urn, dn_col_urn
                        )
                        if not tbl_lineage_id:
                            continue

                        cur.execute("""
                            INSERT INTO lineage_column_mappings (
                                lineage_id,
                                upstream_column_id,
                                downstream_column_id
                            )
                            VALUES (%s, %s, %s)
                            ON CONFLICT (lineage_id, upstream_column_id, downstream_column_id)
                            DO NOTHING
                        """, (str(tbl_lineage_id), str(up_col_id), str(dn_col_id)))

                        logger.info(
                            f"[Lineage] ✓ Column lineage stored: "
                            f"{up_col_id} → {dn_col_id}"
                        )

        except Exception as e:
            logger.exception(f"[Lineage] Error processing lineage for {entity_urn}: {e}")

    def _resolve_catalog_id_sync(self, cur, dataset_urn: str):
        """
        Convert a DataHub URN to a catalog UUID.
        URN format: urn:li:dataset:(urn:li:dataPlatform:snowflake,DB.SCHEMA.TABLE,PROD)
        """
        try:
            # Extract the dataset name part: DB.SCHEMA.TABLE
            match = re.search(r'urn:li:dataPlatform:\w+,([^,)]+)', dataset_urn)
            if not match:
                return None

            full_name = match.group(1)   # e.g. "STUDENT_DB.PUBLIC.ORDERS"
            parts = full_name.split('.')

            if len(parts) == 3:
                db, schema, table = parts[0], parts[1], parts[2]
            elif len(parts) == 2:
                db, schema, table = None, parts[0], parts[1]
            else:
                db, schema, table = None, None, parts[0]

            cur.execute("""
                SELECT id FROM catalogs
                WHERE source_id = %s
                  AND UPPER(table_name)    = UPPER(%s)
                  AND (%s IS NULL OR UPPER(schema_name)   = UPPER(%s))
                  AND (%s IS NULL OR UPPER(database_name) = UPPER(%s))
                LIMIT 1
            """, (str(self.source_id), table, schema, schema, db, db))

            row = cur.fetchone()
            return row[0] if row else None

        except Exception as e:
            logger.debug(f"[Lineage] _resolve_catalog_id_sync failed for {dataset_urn}: {e}")
            return None

    def _resolve_column_id_sync(self, cur, schema_field_urn: str):
        """
        Convert a schemaField URN to a column UUID.
        URN format: urn:li:schemaField:(urn:li:dataset:(...),COLUMN_NAME)
        """
        try:
            # Extract dataset URN and column name
            match = re.search(
                r'urn:li:schemaField:\((urn:li:dataset:[^)]+\))\s*,\s*(.+)\)',
                schema_field_urn
            )
            if not match:
                return None

            dataset_urn = match.group(1)
            col_name    = match.group(2).strip()

            catalog_id = self._resolve_catalog_id_sync(cur, dataset_urn)
            if not catalog_id:
                return None

            cur.execute("""
                SELECT id FROM columns
                WHERE catalog_id = %s
                  AND UPPER(name) = UPPER(%s)
                LIMIT 1
            """, (str(catalog_id), col_name))

            row = cur.fetchone()
            return row[0] if row else None

        except Exception as e:
            logger.debug(f"[Lineage] _resolve_column_id_sync failed for {schema_field_urn}: {e}")
            return None

    def _resolve_lineage_id_sync(self, cur, up_col_urn: str, dn_col_urn: str):
        """
        Look up the table_lineage.id for the tables that these two column URNs belong to.
        """
        try:
            up_match = re.search(r'urn:li:schemaField:\((urn:li:dataset:[^)]+\))', up_col_urn)
            dn_match = re.search(r'urn:li:schemaField:\((urn:li:dataset:[^)]+\))', dn_col_urn)
            if not up_match or not dn_match:
                return None

            up_catalog_id = self._resolve_catalog_id_sync(cur, up_match.group(1))
            dn_catalog_id = self._resolve_catalog_id_sync(cur, dn_match.group(1))
            if not up_catalog_id or not dn_catalog_id:
                return None

            cur.execute("""
                SELECT id FROM table_lineage
                WHERE upstream_catalog_id   = %s
                  AND downstream_catalog_id = %s
                LIMIT 1
            """, (str(up_catalog_id), str(dn_catalog_id)))

            row = cur.fetchone()
            return row[0] if row else None

        except Exception as e:
            logger.debug(f"[Lineage] _resolve_lineage_id_sync failed: {e}")
            return None

    def write_record_async(self, record_envelope: RecordEnvelope, write_callback):
        """Process record synchronously and invoke callback."""
        try:
            self._process_record(record_envelope)
            try:
                write_callback.on_success(record_envelope, {})
            except Exception:
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


_PIPELINE_RUNNER_SOURCES = {"snowflake", "athena", "dynamodb", "glue", "mssql"}

_AWS_ENV_VAR_SOURCES = {"athena", "glue"}


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
            host_port = conn_details.get('host_port', 'localhost:5432')
            host = host_port.split(':')[0] if host_port else 'localhost'
            port = 5432
            if ':' in host_port:
                try:
                    port = int(host_port.split(':')[1])
                except (ValueError, IndexError):
                    port = 5432

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
                sink_cursor.execute("""
                    INSERT INTO catalogs (source_id, database_name, schema_name, table_name, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (source_id, database_name, schema_name, table_name)
                    DO UPDATE SET metadata = EXCLUDED.metadata, last_seen_at = NOW(), updated_at = NOW()
                    RETURNING id
                """, (str(source_id), conn_details['database'], schema_name, table_name, json.dumps({"table_type": table_type})))

                catalog_id = sink_cursor.fetchone()[0]

                src_cursor.execute("""
                    SELECT 
                        c.column_name, 
                        c.ordinal_position, 
                        c.data_type, 
                        c.is_nullable,
                        pgd.description
                    FROM information_schema.columns c
                    LEFT JOIN pg_catalog.pg_statio_all_tables st 
                        ON st.schemaname = c.table_schema AND st.relname = c.table_name
                    LEFT JOIN pg_catalog.pg_description pgd 
                        ON pgd.objoid = st.relid AND pgd.objsubid = c.ordinal_position
                    WHERE c.table_catalog = %s AND c.table_schema = %s AND c.table_name = %s
                    ORDER BY c.ordinal_position
                """, (conn_details['database'], schema_name, table_name))

                columns = src_cursor.fetchall()

                sink_cursor.execute("DELETE FROM columns WHERE catalog_id = %s", (catalog_id,))

                for col_name, ord_pos, data_type, is_nullable, col_description in columns:
                    sink_cursor.execute("""
                        INSERT INTO columns (catalog_id, name, ordinal_position, data_type, description, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (catalog_id, col_name, ord_pos, data_type, col_description, json.dumps({"is_nullable": is_nullable})))

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

    async def _extract_snowflake_lineage(
            self, source_id: str, conn_details: dict, start_time
            ):
        """
        Fallback lineage extractor using QUERY_HISTORY (no lag).
        Parses CREATE TABLE AS SELECT and INSERT INTO ... SELECT statements
        to build upstream→downstream relationships.
        Writes directly into table_lineage in your Postgres.
        """
        import snowflake.connector
        import sqlglot
        import re

        logger.info("[Lineage] Starting QUERY_HISTORY based lineage extraction")

        try:
            sf_conn = snowflake.connector.connect(
                account   = conn_details.get("account_id"),
                user      = conn_details.get("username"),
                password  = conn_details.get("password"),
                warehouse = conn_details.get("warehouse"),
                role      = conn_details.get("role"),
                database  = conn_details.get("database", ""),
            )
            cursor = sf_conn.cursor()

            # ── Fetch recent CREATE TABLE AS SELECT / INSERT INTO SELECT ──────
            cursor.execute("""
                SELECT query_id, query_text, start_time
                FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
                WHERE START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP())
                AND EXECUTION_STATUS = 'SUCCESS'
                AND (
                    UPPER(query_text) LIKE '%CREATE%TABLE%AS%SELECT%'
                    OR UPPER(query_text) LIKE '%INSERT%INTO%SELECT%'
                )
                ORDER BY start_time DESC
                LIMIT 500
            """)
            rows = cursor.fetchall()
            logger.info(f"[Lineage] Found {len(rows)} lineage-producing queries in QUERY_HISTORY")

            lineage_pairs = []

            for query_id, query_text, start_time in rows:
                try:
                    # Parse SQL with sqlglot to extract source→target tables
                    statements = sqlglot.parse(query_text, dialect="snowflake")
                    for stmt in statements:
                        if stmt is None:
                            continue

                        # Find the target table (what's being written to)
                        target_table = None
                        sources = []

                        stmt_type = type(stmt).__name__
                        if stmt_type == "Create":
                            # CREATE TABLE target AS SELECT ... FROM source
                            if stmt.this:
                                target_table = stmt.this.name
                            # Walk AST for FROM tables
                            for node in stmt.walk():
                                if type(node).__name__ == "Table" and node.name != target_table:
                                    sources.append(node.name.upper())

                        elif stmt_type == "Insert":
                            # INSERT INTO target SELECT ... FROM source
                            if stmt.this:
                                target_table = stmt.this.name
                            for node in stmt.walk():
                                if type(node).__name__ == "Table" and node.name != target_table:
                                    sources.append(node.name.upper())

                        if target_table and sources:
                            for src in set(sources):
                                lineage_pairs.append((
                                    src.upper(),
                                    target_table.upper(),
                                    query_text
                                ))

                except Exception as parse_err:
                    logger.debug(f"[Lineage] Could not parse query {query_id}: {parse_err}")
                    continue

            cursor.close()
            sf_conn.close()

            if not lineage_pairs:
                logger.info("[Lineage] No lineage pairs extracted from QUERY_HISTORY")
                return 0

            # ── Write lineage pairs into your Postgres table_lineage ─────────
            sink_conn = psycopg2.connect(
                host     = self.settings.PG_HOST,
                port     = self.settings.PG_PORT,
                database = self.settings.PG_DB,
                user     = self.settings.PG_USER,
                password = self.settings.PG_PASS
            )
            cur = sink_conn.cursor()
            lineage_stored = 0

            for upstream_name, downstream_name, sql_text in lineage_pairs:
                # Resolve both table names to catalog IDs
                cur.execute("""
                    SELECT id FROM catalogs
                    WHERE source_id = %s AND UPPER(table_name) = %s
                    LIMIT 1
                """, (str(source_id), upstream_name))
                up_row = cur.fetchone()

                cur.execute("""
                    SELECT id FROM catalogs
                    WHERE source_id = %s AND UPPER(table_name) = %s
                    LIMIT 1
                """, (str(source_id), downstream_name))
                dn_row = cur.fetchone()

                if not up_row or not dn_row:
                    logger.debug(
                        f"[Lineage] Skipping {upstream_name}→{downstream_name}: "
                        f"catalog not found (up={bool(up_row)}, dn={bool(dn_row)})"
                    )
                    continue

                cur.execute("""
                    INSERT INTO table_lineage (
                        upstream_catalog_id,
                        downstream_catalog_id,
                        transformation_query,
                        is_active
                    )
                    VALUES (%s, %s, %s, TRUE)
                    ON CONFLICT (upstream_catalog_id, downstream_catalog_id)
                    DO UPDATE SET
                        transformation_query = EXCLUDED.transformation_query,
                        is_active = TRUE,
                        updated_at = NOW()
                """, (str(up_row[0]), str(dn_row[0]), sql_text[:2000]))

                logger.info(f"[Lineage] ✓ Stored: {upstream_name} → {downstream_name}")
                lineage_stored += 1

            sink_conn.commit()
            cur.close()
            sink_conn.close()

            logger.info(f"[Lineage] ✓ Total lineage pairs stored: {lineage_stored}")
            return lineage_stored

        except Exception as e:
            logger.exception(f"[Lineage] QUERY_HISTORY extraction failed: {e}")
            return 0
        
    async def _extract_athena_lineage(
            self, source_id: str, conn_details: dict
            ):
        """
        Lineage extractor for Athena using boto3 query execution history.
        Parses CTAS and INSERT INTO SELECT statements to extract lineage.
        Also captures per-query execution metadata:
            query_execution_id, query_start_time, query_end_time,
            query_runtime_ms, data_scanned_bytes, query_status,
            engine_version, s3_output_location
        Writes into table_lineage in your Postgres.
        """
        import boto3
        import sqlglot

        logger.info("[Lineage][Athena] Starting query history based lineage extraction")

        try:
            # ── Connect to Athena via boto3 ───────────────────────────────────
            aws_region         = conn_details.get("aws_region", os.environ.get("AWS_DEFAULT_REGION"))
            aws_access_key_id  = conn_details.get("aws_access_key_id") or os.environ.get("AWS_ACCESS_KEY_ID")
            aws_secret_key     = conn_details.get("aws_secret_access_key") or os.environ.get("AWS_SECRET_ACCESS_KEY")
            work_group         = conn_details.get("work_group", "primary")

            athena = boto3.client(
                "athena",
                region_name           = aws_region,
                aws_access_key_id     = aws_access_key_id,
                aws_secret_access_key = aws_secret_key,
            )

            all_query_ids = []
            paginator = athena.get_paginator("list_query_executions")

            for page in paginator.paginate(WorkGroup=work_group):
                all_query_ids.extend(page.get("QueryExecutionIds", []))
                if len(all_query_ids) >= 500:
                    break

            logger.info(f"[Lineage][Athena] Found {len(all_query_ids)} total query executions")

            if not all_query_ids:
                logger.info("[Lineage][Athena] No query executions found")
                return 0

            # ── Batch fetch query details (max 50 per call) ───────────────────
            from datetime import datetime, timedelta, timezone
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)

            # Each entry: dict with query_text + all execution metadata
            lineage_queries = []

            for i in range(0, len(all_query_ids), 50):
                batch = all_query_ids[i:i+50]
                response = athena.batch_get_query_execution(QueryExecutionIds=batch)

                for qe in response.get("QueryExecutions", []):
                    status      = qe.get("Status", {})
                    state       = status.get("State", "")
                    submit_time = status.get("SubmissionDateTime")

                    if state != "SUCCEEDED":
                        continue
                    if submit_time and submit_time < cutoff:
                        continue

                    query_text = qe.get("Query", "")
                    upper_q    = query_text.upper()

                    if not (
                        ("CREATE TABLE" in upper_q and "SELECT" in upper_q)
                        or ("INSERT INTO" in upper_q and "SELECT" in upper_q)
                    ):
                        continue

                    # ── Capture all execution metadata ────────────────────────
                    stats           = qe.get("Statistics", {})
                    engine_info     = qe.get("EngineVersion", {})
                    result_config   = qe.get("ResultConfiguration", {})

                    query_execution_id = qe.get("QueryExecutionId")
                    query_start_time   = status.get("SubmissionDateTime")   # tz-aware datetime
                    query_end_time     = status.get("CompletionDateTime")   # tz-aware datetime
                    query_runtime_ms   = stats.get("TotalExecutionTimeInMillis")
                    data_scanned_bytes = stats.get("DataScannedInBytes")
                    query_status       = state                               # "SUCCEEDED"
                    engine_version     = engine_info.get("EffectiveEngineVersion") or engine_info.get("SelectedEngineVersion")
                    s3_output_location = result_config.get("OutputLocation")

                    lineage_queries.append({
                        "query_text":          query_text,
                        "query_execution_id":  query_execution_id,
                        "query_start_time":    query_start_time,
                        "query_end_time":      query_end_time,
                        "query_runtime_ms":    query_runtime_ms,
                        "data_scanned_bytes":  data_scanned_bytes,
                        "query_status":        query_status,
                        "engine_version":      engine_version,
                        "s3_output_location":  s3_output_location,
                    })

            logger.info(f"[Lineage][Athena] {len(lineage_queries)} lineage-producing queries found")

            if not lineage_queries:
                logger.info("[Lineage][Athena] No CTAS or INSERT INTO SELECT queries found")
                return 0

            # ── Parse SQL → extract upstream/downstream pairs ─────────────────
            # Each entry: (upstream_name, downstream_name, query_meta_dict)
            lineage_pairs = []

            for qmeta in lineage_queries:
                query_text = qmeta["query_text"]
                try:
                    query_text = query_text.replace('\r\n', '\n').replace('\r', '\n')
                    upper_q    = query_text.upper().strip()

                    # ── Extract TARGET table ──────────────────────────────────
                    target_match = re.search(
                        r'CREATE\s+(?:OR\s+REPLACE\s+)?(?:EXTERNAL\s+)?TABLE\s+'
                        r'(?:IF\s+NOT\s+EXISTS\s+)?'
                        r'(?:"([^"]+)"\s*\.\s*"?([^"\s(,]+)"?'
                        r'|"([^"]+)"\s*\.\s*([^\s(,]+)'
                        r'|([^\s.(,]+)\s*\.\s*([^\s(,]+)'
                        r'|([^\s(,]+))',
                        query_text,
                        re.IGNORECASE
                    )

                    if not target_match:
                        logger.debug("[Lineage][Athena] Could not extract target table from query")
                        continue

                    g = target_match.groups()
                    if g[0] and g[1]:
                        target_table = g[1]
                    elif g[2] and g[3]:
                        target_table = g[3]
                    elif g[4] and g[5]:
                        target_table = g[5]
                    else:
                        target_table = g[6]

                    target_table = target_table.strip('"').upper()

                    # ── Find AS SELECT boundary ───────────────────────────────
                    as_select_match = re.search(
                        r'\bAS\s*[\n\r]+\s*SELECT\b|\bAS\s+SELECT\b',
                        upper_q,
                        re.IGNORECASE
                    )
                    if not as_select_match:
                        logger.debug("[Lineage][Athena] No AS SELECT boundary found")
                        continue

                    select_part = query_text[as_select_match.start():]

                    # ── Extract SOURCE tables from FROM / JOIN clauses ────────
                    source_pattern = re.compile(
                        r'(?:FROM|JOIN)\s+'
                        r'(?:"([^"]+)"\s*\.\s*"?([^"\s,()\r\n]+)"?'
                        r'|"([^"]+)"\s*\.\s*([^\s,()\r\n]+)'
                        r'|([a-zA-Z0-9_]+)\s*\.\s*([a-zA-Z0-9_]+)'
                        r'|([a-zA-Z0-9_]+))',
                        re.IGNORECASE
                    )

                    _SQL_KEYWORDS = {
                        'SELECT','WHERE','ON','AND','OR','NOT','NULL',
                        'TRUE','FALSE','INNER','LEFT','RIGHT','OUTER',
                        'CROSS','FULL','LATERAL','WITH','AS','HAVING',
                        'GROUP','ORDER','BY','LIMIT','UNION','ALL'
                    }

                    sources = []
                    for m in source_pattern.finditer(select_part):
                        g2 = m.groups()
                        if g2[0] and g2[1]:
                            src = g2[1].strip('"').upper()
                        elif g2[2] and g2[3]:
                            src = g2[3].strip('"').upper()
                        elif g2[4] and g2[5]:
                            src = g2[5].strip('"').upper()
                        elif g2[6]:
                            src = g2[6].strip('"').upper()
                        else:
                            continue

                        if src in _SQL_KEYWORDS or src == target_table:
                            continue

                        sources.append(src)

                    logger.info(f"[Lineage][Athena] Parsed: {sources} → {target_table}")

                    if target_table and sources:
                        for src in set(sources):
                            lineage_pairs.append((src, target_table, qmeta))

                except Exception as parse_err:
                    logger.debug(f"[Lineage][Athena] Parse error: {parse_err}")
                    continue

            if not lineage_pairs:
                logger.info("[Lineage][Athena] No lineage pairs extracted from queries")
                return 0

            # ── Write into your Postgres table_lineage ────────────────────────
            sink_conn = psycopg2.connect(
                host     = self.settings.PG_HOST,
                port     = self.settings.PG_PORT,
                database = self.settings.PG_DB,
                user     = self.settings.PG_USER,
                password = self.settings.PG_PASS
            )
            cur = sink_conn.cursor()
            lineage_stored = 0

            for upstream_name, downstream_name, qmeta in lineage_pairs:
                cur.execute("""
                    SELECT id FROM catalogs
                    WHERE source_id = %s AND UPPER(table_name) = %s
                    LIMIT 1
                """, (str(source_id), upstream_name))
                up_row = cur.fetchone()

                cur.execute("""
                    SELECT id FROM catalogs
                    WHERE source_id = %s AND UPPER(table_name) = %s
                    LIMIT 1
                """, (str(source_id), downstream_name))
                dn_row = cur.fetchone()

                if not up_row or not dn_row:
                    logger.info(
                        f"[Lineage][Athena] Skipping {upstream_name}→{downstream_name}: "
                        f"not found in catalogs (up={bool(up_row)}, dn={bool(dn_row)})"
                    )
                    continue

                cur.execute("""
                    INSERT INTO table_lineage (
                        upstream_catalog_id,
                        downstream_catalog_id,
                        transformation_query,
                        is_active,
                        query_execution_id,
                        query_start_time,
                        query_end_time,
                        query_runtime_ms,
                        data_scanned_bytes,
                        query_status,
                        engine_version,
                        s3_output_location
                    )
                    VALUES (%s, %s, %s, TRUE, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (upstream_catalog_id, downstream_catalog_id)
                    DO UPDATE SET
                        transformation_query = EXCLUDED.transformation_query,
                        is_active            = TRUE,
                        updated_at           = NOW(),
                        query_execution_id   = EXCLUDED.query_execution_id,
                        query_start_time     = EXCLUDED.query_start_time,
                        query_end_time       = EXCLUDED.query_end_time,
                        query_runtime_ms     = EXCLUDED.query_runtime_ms,
                        data_scanned_bytes   = EXCLUDED.data_scanned_bytes,
                        query_status         = EXCLUDED.query_status,
                        engine_version       = EXCLUDED.engine_version,
                        s3_output_location   = EXCLUDED.s3_output_location
                """, (
                    str(up_row[0]),
                    str(dn_row[0]),
                    qmeta["query_text"][:2000],
                    qmeta["query_execution_id"],
                    qmeta["query_start_time"],
                    qmeta["query_end_time"],
                    qmeta["query_runtime_ms"],
                    qmeta["data_scanned_bytes"],
                    qmeta["query_status"],
                    qmeta["engine_version"],
                    qmeta["s3_output_location"],
                ))

                logger.info(
                    f"[Lineage][Athena] ✓ Stored: {upstream_name} → {downstream_name} "
                    f"[exec_id={qmeta['query_execution_id']}, "
                    f"runtime={qmeta['query_runtime_ms']}ms, "
                    f"scanned={qmeta['data_scanned_bytes']}B]"
                )
                lineage_stored += 1

            sink_conn.commit()
            cur.close()
            sink_conn.close()

            logger.info(f"[Lineage][Athena] ✓ Total lineage pairs stored: {lineage_stored}")
            return lineage_stored

        except Exception as e:
            logger.exception(f"[Lineage][Athena] Extraction failed: {e}")
            return 0

    async def _sync_athena_descriptions(self, source_id: str):
        """
        Directly fetch table and column descriptions from AWS Glue API
        and update catalogs/columns tables.
        """
        import boto3

        logger.info(f"[Description] Starting Glue description sync for source={source_id}")

        try:
            source = await self.db.fetch_one(
                "SELECT connection_details FROM data_sources WHERE id = $1", source_id
            )
            if not source:
                return

            conn_details          = json.loads(source['connection_details'])
            aws_region            = conn_details.get("aws_region") or os.environ.get("AWS_DEFAULT_REGION")
            aws_access_key_id     = os.environ.get("AWS_ACCESS_KEY_ID")
            aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")

            glue = boto3.client(
                "glue",
                region_name           = aws_region,
                aws_access_key_id     = aws_access_key_id,
                aws_secret_access_key = aws_secret_access_key,
            )

            catalogs = await self.db.fetch_all(
                "SELECT id, table_name, schema_name FROM catalogs WHERE source_id = $1",
                source_id
            )

            sink_conn = psycopg2.connect(
                host     = self.settings.PG_HOST,
                port     = self.settings.PG_PORT,
                database = self.settings.PG_DB,
                user     = self.settings.PG_USER,
                password = self.settings.PG_PASS
            )
            cur = sink_conn.cursor()

            tables_updated  = 0
            columns_updated = 0

            for catalog in catalogs:
                catalog_id  = str(catalog['id'])
                table_name  = catalog['table_name']
                schema_name = catalog['schema_name']

                try:
                    response = glue.get_table(
                        DatabaseName=schema_name,
                        Name=table_name
                    )
                    table = response.get('Table', {})

                    # ── Table description ──────────────────────────────────
                    table_description = table.get('Description', '').strip()
                    if table_description:
                        cur.execute("""
                            UPDATE catalogs SET description = %s WHERE id = %s
                        """, (table_description, catalog_id))
                        logger.info(f"[Description] ✓ Table '{table_name}': {table_description[:60]}")
                        tables_updated += 1

                    # ── Column descriptions ────────────────────────────────
                    glue_columns = table.get('StorageDescriptor', {}).get('Columns', [])
                    for glue_col in glue_columns:
                        col_name    = glue_col.get('Name', '')
                        col_comment = glue_col.get('Comment', '').strip()
                        if col_name and col_comment:
                            cur.execute("""
                                UPDATE columns
                                SET description = %s
                                WHERE catalog_id = %s AND LOWER(name) = LOWER(%s)
                            """, (col_comment, catalog_id, col_name))
                            columns_updated += 1

                except Exception as e:
                    logger.warning(f"[Description] Failed for '{table_name}': {e}")
                    continue

            sink_conn.commit()
            cur.close()
            sink_conn.close()

            logger.info(
                f"[Description] ✓ Sync complete — "
                f"{tables_updated} tables updated, {columns_updated} columns updated"
            )

        except Exception as e:
            logger.error(f"[Description] Glue description sync failed (non-fatal): {e}")

    
    
    async def _sync_athena_row_counts(self, source_id: str):
        """
        For every catalog entry belonging to source_id, fire a SELECT COUNT(*)
        directly against Athena and persist the result into catalog_stats.
 
        Design notes
        ------------
        - Queries are submitted concurrently (up to MAX_CONCURRENT_COUNT_QUERIES
          at a time) to respect Athena's per-workgroup concurrency soft-limit
          while still finishing quickly for large catalogues.
        - Each query is polled synchronously in a thread-pool worker until it
          reaches a terminal state.  A per-query wall-clock timeout is enforced;
          stray queries are cancelled on timeout so they don't consume DPUs.
        - The entire module is non-fatal: any exception is caught and logged so
          that a COUNT failure can never roll back or corrupt the ingestion job.
        - Row counts are upserted (ON CONFLICT … DO UPDATE) so re-running the
          ingestion simply refreshes the numbers.
        """
        import boto3
        import time
 
        # ── Tunables ──────────────────────────────────────────────────────────
        MAX_CONCURRENT_COUNT_QUERIES = 5   # stay within Athena's 20-query soft limit
        POLL_INTERVAL_SECONDS        = 2   # how often to check query state
        QUERY_TIMEOUT_SECONDS        = 120 # cancel & skip after 2 minutes per table
 
        logger.info(f"[RowCount][Athena] Starting row-count sync for source={source_id}")
 
        try:
            # ── 1. Load source credentials from DB ───────────────────────────
            source = await self.db.fetch_one(
                "SELECT connection_details FROM data_sources WHERE id = $1", source_id
            )
            if not source:
                logger.warning(f"[RowCount][Athena] Source {source_id} not found — skipping")
                return
 
            conn_details = json.loads(source["connection_details"])
 
            aws_region            = conn_details.get("aws_region")            or os.environ.get("AWS_DEFAULT_REGION")
            aws_access_key_id     = conn_details.get("aws_access_key_id")     or os.environ.get("AWS_ACCESS_KEY_ID")
            aws_secret_access_key = conn_details.get("aws_secret_access_key") or os.environ.get("AWS_SECRET_ACCESS_KEY")
            work_group            = conn_details.get("work_group", "primary")
            s3_staging_dir        = conn_details.get("s3_staging_dir")
 
            if not s3_staging_dir:
                logger.warning(
                    "[RowCount][Athena] s3_staging_dir not configured — "
                    "cannot execute COUNT queries; skipping row-count sync"
                )
                return
 
            athena = boto3.client(
                "athena",
                region_name           = aws_region,
                aws_access_key_id     = aws_access_key_id,
                aws_secret_access_key = aws_secret_access_key,
            )
 
            # ── 2. Fetch all catalogs owned by this source ────────────────────
            catalogs = await self.db.fetch_all(
                "SELECT id, schema_name, table_name FROM catalogs WHERE source_id = $1",
                source_id
            )
 
            if not catalogs:
                logger.info("[RowCount][Athena] No catalogs found — nothing to count")
                return
 
            logger.info(
                f"[RowCount][Athena] Submitting COUNT(*) queries for "
                f"{len(catalogs)} table(s)"
            )
 
            # ── 3. Synchronous helpers (run inside thread-pool) ───────────────
 
            def _submit_count_query(schema_name: str, table_name: str) -> str | None:
                """
                Fire  SELECT COUNT(*) FROM "schema"."table"  and return the
                QueryExecutionId.  Returns None if submission fails.
                """
                sql = f'SELECT COUNT(*) FROM "{schema_name}"."{table_name}"'
                try:
                    resp = athena.start_query_execution(
                        QueryString           = sql,
                        QueryExecutionContext = {"Database": schema_name},
                        ResultConfiguration   = {"OutputLocation": s3_staging_dir},
                        WorkGroup             = work_group,
                    )
                    exec_id = resp["QueryExecutionId"]
                    logger.debug(
                        f'[RowCount][Athena] Submitted COUNT for '
                        f'"{schema_name}"."{table_name}" → exec_id={exec_id}'
                    )
                    return exec_id
                except Exception as e:
                    logger.warning(
                        f'[RowCount][Athena] Failed to submit COUNT for '
                        f'"{schema_name}"."{table_name}": {e}'
                    )
                    return None
 
            def _poll_and_fetch(exec_id: str, schema_name: str, table_name: str) -> int | None:
                """
                Poll until the query reaches a terminal state, then return the
                integer row count.  Returns None on failure or timeout.
                """
                deadline = time.monotonic() + QUERY_TIMEOUT_SECONDS
 
                while time.monotonic() < deadline:
                    resp  = athena.get_query_execution(QueryExecutionId=exec_id)
                    state = (
                        resp
                        .get("QueryExecution", {})
                        .get("Status", {})
                        .get("State", "")
                    )
 
                    if state == "SUCCEEDED":
                        results = athena.get_query_results(QueryExecutionId=exec_id)
                        rows    = results.get("ResultSet", {}).get("Rows", [])
                        # Rows[0] = header ("_col0"), Rows[1] = the count value
                        if len(rows) >= 2:
                            try:
                                count = int(rows[1]["Data"][0].get("VarCharValue", 0))
                                logger.debug(
                                    f'[RowCount][Athena] COUNT result: '
                                    f'"{schema_name}"."{table_name}" = {count:,}'
                                )
                                return count
                            except (ValueError, IndexError, KeyError) as parse_err:
                                logger.warning(
                                    f'[RowCount][Athena] Could not parse COUNT result '
                                    f'for "{schema_name}"."{table_name}": {parse_err}'
                                )
                        return None  # SUCCEEDED but unparseable
 
                    if state in ("FAILED", "CANCELLED"):
                        reason = (
                            resp
                            .get("QueryExecution", {})
                            .get("Status", {})
                            .get("StateChangeReason", "unknown reason")
                        )
                        logger.warning(
                            f'[RowCount][Athena] COUNT query {state} for '
                            f'"{schema_name}"."{table_name}": {reason}'
                        )
                        return None
 
                    time.sleep(POLL_INTERVAL_SECONDS)
 
                # ── Timed out — cancel to avoid wasting DPUs ─────────────────
                try:
                    athena.stop_query_execution(QueryExecutionId=exec_id)
                    logger.warning(
                        f'[RowCount][Athena] COUNT query timed out and was cancelled '
                        f'for "{schema_name}"."{table_name}" (exec_id={exec_id})'
                    )
                except Exception:
                    pass
                return None
 
            # ── 4. Async wrapper — one coroutine per table ────────────────────
            sem = asyncio.Semaphore(MAX_CONCURRENT_COUNT_QUERIES)
 
            async def _count_one(catalog_id: str, schema_name: str, table_name: str):
                """Returns (catalog_id, row_count | None)."""
                async with sem:
                    loop = asyncio.get_event_loop()
 
                    exec_id = await loop.run_in_executor(
                        None, _submit_count_query, schema_name, table_name
                    )
                    if exec_id is None:
                        return catalog_id, None
 
                    row_count = await loop.run_in_executor(
                        None, _poll_and_fetch, exec_id, schema_name, table_name
                    )
                    return catalog_id, row_count
 
            tasks   = [
                _count_one(str(c["id"]), c["schema_name"], c["table_name"])
                for c in catalogs
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
 
            # ── 5. Persist results into catalog_stats ─────────────────────────
            sink_conn = psycopg2.connect(
                host     = self.settings.PG_HOST,
                port     = self.settings.PG_PORT,
                database = self.settings.PG_DB,
                user     = self.settings.PG_USER,
                password = self.settings.PG_PASS,
            )
            cur     = sink_conn.cursor()
            updated = 0
 
            for result in results:
                # asyncio.gather with return_exceptions=True surfaces errors here
                if isinstance(result, Exception):
                    logger.warning(f"[RowCount][Athena] Unexpected task error: {result}")
                    continue
 
                catalog_id, row_count = result
                if row_count is None:
                    continue  # query failed or timed out — leave existing value intact
 
                cur.execute("""
                    INSERT INTO catalog_stats (catalog_id, row_count, computed_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (catalog_id)
                    DO UPDATE SET
                        row_count   = EXCLUDED.row_count,
                        computed_at = NOW()
                """, (catalog_id, row_count))

                cur.execute(
                    "UPDATE catalogs SET row_count = %s WHERE id = %s",
                    (row_count, catalog_id)
                )
 
                logger.info(
                    f"[RowCount][Athena] ✓ catalog_id={catalog_id}  "
                    f"row_count={row_count:,}"
                )
                updated += 1
 
            sink_conn.commit()
            cur.close()
            sink_conn.close()
 
            logger.info(
                f"[RowCount][Athena] ✓ Row-count sync complete — "
                f"{updated}/{len(catalogs)} table(s) updated"
            )
 
        except Exception as e:
            # Non-fatal: row-count failure must never affect the ingestion job
            logger.error(f"[RowCount][Athena] Row-count sync failed (non-fatal): {e}")

    

    async def _extract_csv_metadata(self, source_id: str, job_id: str, conn_details: dict) -> int:
        return await asyncio.to_thread(self._extract_csv_metadata_sync, source_id, job_id, conn_details)

    async def _extract_csv_metadata(self, source_id: str, job_id: str, conn_details: dict) -> int:
        return await asyncio.to_thread(self._extract_csv_metadata_sync, source_id, job_id, conn_details)

    def _extract_csv_metadata_sync(self, source_id: str, job_id: str, conn_details: dict) -> int:
        """Fetch CSV from URL and extract column metadata."""
        import urllib.request
        import csv as csv_module
        import io

        file_url = conn_details.get("file_url")
        delimiter = conn_details.get("delimiter", ",")

        if not file_url:
            raise ValueError("file_url is required for CSV ingestion")

        # To this:
        try:
            with urllib.request.urlopen(file_url, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except Exception as e:
            logger.exception(f"Failed to fetch CSV from URL '{file_url}': {e}")
            raise ValueError(f"Failed to fetch CSV from URL '{file_url}': {e}")

        reader = csv_module.DictReader(io.StringIO(raw), delimiter=delimiter)
        headers = reader.fieldnames
        if not headers:
            raise ValueError("CSV file has no headers")

        first_row = next(reader, None)
        column_types = {}
        if first_row:
            for col in headers:
                val = (first_row.get(col) or "").strip()
                if val.lstrip("-").isdigit():
                    column_types[col] = "integer"
                else:
                    try:
                        float(val)
                        column_types[col] = "float"
                    except ValueError:
                        column_types[col] = "varchar"
        else:
            column_types = {col: "varchar" for col in headers}

        from urllib.parse import urlparse
        parsed = urlparse(file_url)
        path_parts = parsed.path.rstrip("/").split("/")
        table_name = path_parts[-1].replace(".csv", "") if path_parts else "csv_table"
        if not table_name:
            table_name = "csv_table"

        sink_conn = psycopg2.connect(
            host=self.settings.PG_HOST,
            port=self.settings.PG_PORT,
            database=self.settings.PG_DB,
            user=self.settings.PG_USER,
            password=self.settings.PG_PASS
        )
        sink_cursor = sink_conn.cursor()

        try:
            sink_cursor.execute("""
                INSERT INTO catalogs (source_id, database_name, schema_name, table_name, metadata)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (source_id, database_name, schema_name, table_name)
                DO UPDATE SET metadata = EXCLUDED.metadata, last_seen_at = NOW(), updated_at = NOW()
                RETURNING id
            """, (str(source_id), None, "csv", table_name, json.dumps({"source_url": file_url})))

            catalog_id = sink_cursor.fetchone()[0]
            sink_cursor.execute("DELETE FROM columns WHERE catalog_id = %s", (catalog_id,))

            for idx, col_name in enumerate(headers):
                sink_cursor.execute("""
                    INSERT INTO columns (catalog_id, name, ordinal_position, data_type, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                """, (catalog_id, col_name, idx + 1, column_types.get(col_name, "varchar"), json.dumps({})))

            sink_conn.commit()
            return 1

        except Exception as e:
            sink_conn.rollback()
            raise
        finally:
            sink_cursor.close()
            sink_conn.close()

    
    async def ingest(self, source_id: str, job_id: str, config: Dict):
        """Run ingestion pipeline.

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
                # ── 1. Fetch source record ───────────────────────────────────
                source = await self.db.fetch_one("SELECT * FROM data_sources WHERE id = $1", source_id)
                if not source:
                    raise ValueError(f"Source {source_id} not found")

                source_type = source['source_type']
                template = copy.deepcopy(SOURCE_TEMPLATES.get(source_type, {}))

                if not template:
                    raise ValueError(f"Unsupported source type: {source_type}")

                logger.info(f"[Ingestion] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                logger.info(f"[Ingestion] Job started  — source_id={source_id}  job_id={job_id}")
                logger.info(f"[Ingestion] Source type  : {source_type}")
                logger.info(f"[Ingestion] Source name  : {source['name']}")

                # ── 2. Parse connection details ──────────────────────────────
                conn_details = json.loads(source['connection_details'])

                # ── 3. Source-type-specific credential/config transforms ─────
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
                        conn_details["database"] = db_value

                    include_lineage = config.get("include_lineage", False)
                    template['config']["include_table_lineage"]  = include_lineage
                    template['config']["include_column_lineage"] = include_lineage
                    if include_lineage:
                        from datetime import datetime, timedelta, timezone
                        template['config']["start_time"] = datetime.now(timezone.utc) - timedelta(days=7)
                        logger.info(f"[Lineage] Snowflake lineage enabled for source={source_id}")
                    else:
                        logger.info(f"[Lineage] Snowflake lineage SKIPPED (include_lineage=false)")

                elif source_type in _AWS_ENV_VAR_SOURCES:
                    
                    aws_access_key_id = (
                        conn_details.pop("aws_access_key_id", None)
                        or conn_details.pop("username", None)
                    )
                    aws_secret_access_key = (
                        conn_details.pop("aws_secret_access_key", None)
                        or conn_details.pop("password", None)
                    )
                    if aws_access_key_id:
                        os.environ["AWS_ACCESS_KEY_ID"] = aws_access_key_id
                    if aws_secret_access_key:
                        os.environ["AWS_SECRET_ACCESS_KEY"] = aws_secret_access_key

                    aws_region = conn_details.get("aws_region")
                    if aws_region:
                        os.environ["AWS_DEFAULT_REGION"] = aws_region

                elif source_type == "dynamodb":
                    
                    conn_details["aws_access_key_id"] = (
                        conn_details.pop("aws_access_key_id", None)
                        or conn_details.pop("username", None)
                    )
                    conn_details["aws_secret_access_key"] = (
                        conn_details.pop("aws_secret_access_key", None)
                        or conn_details.pop("password", None)
                    )
                    conn_details.pop("aws_region", None)

                # ── 4. Merge conn_details into template config ───────────────
                for key, value in conn_details.items():
                    if key in template['config']:
                        template['config'][key] = value

                # ── 5. Apply schema / table patterns ────────────────────────
                schema_pattern = None
                table_pattern  = None

                if source.get('schema_pattern'):
                    schema_pattern = (
                        json.loads(source['schema_pattern'])
                        if isinstance(source['schema_pattern'], str)
                        else source['schema_pattern']
                    )
                if source.get('table_pattern'):
                    table_pattern = (
                        json.loads(source['table_pattern'])
                        if isinstance(source['table_pattern'], str)
                        else source['table_pattern']
                    )

                if source_type == "mongodb":
                    if table_pattern:
                        template['config']['collection_pattern'] = {"allow": table_pattern}

                elif source_type == "dynamodb":
                    # DynamoDB has no schema concept — only table-level patterns
                    if table_pattern:
                        template['config']['table_pattern'] = {"allow": table_pattern}

                elif source_type == "glue":
                    
                    if schema_pattern:
                        template['config']['database_pattern'] = {"allow": schema_pattern}
                    if table_pattern:
                        template['config']['table_pattern'] = {"allow": table_pattern}

                else:
                    if schema_pattern:
                        template['config']['schema_pattern'] = {"allow": schema_pattern}
                    if table_pattern:
                        template['config']['table_pattern'] = {"allow": table_pattern}

                    template['config']['include_views']  = source.get('include_views', True)
                    template['config']['include_tables'] = source.get('include_tables', True)

                # ── 6. Profiling flag ────────────────────────────────────────
                
                _NO_PROFILING_SOURCES = {"mongodb", "dynamodb", "glue"}
                if source_type not in _NO_PROFILING_SOURCES:
                    if 'profiling' not in template['config']:
                        template['config']['profiling'] = {"enabled": True}
                    elif template['config'].get('profiling', {}).get('enabled') is not False:
                        template['config']['profiling'] = {"enabled": True}

                # ── 7. Run the appropriate ingestion pipeline ────────────────
                schemapattern = json.loads(source['schema_pattern']) if source.get('schema_pattern') else ['.*']
                tablepattern  = json.loads(source['table_pattern'])  if source.get('table_pattern')  else ['.*']

                if source_type == "postgres":
                    # Direct SQL extraction — fastest path for Postgres
                    records_ingested = await self._extract_postgres_metadata(
                        source_id, job_id, conn_details, schemapattern, tablepattern
                    )
                elif source_type == "csv":
                    records_ingested = await self._extract_csv_metadata(
                        source_id, job_id, conn_details
                    )    

                elif source_type in _PIPELINE_RUNNER_SOURCES:
                    
                    pipeline_config = {"source": template, "sink": {"type": "console"}}
                    sink_container  = {}

                    def run_pipeline():
                        _sink = PostgresSink(None, {"job_id": job_id, "source_id": source_id})
                        sink_container['sink'] = _sink
                        try:
                            _pipeline = Pipeline.create(pipeline_config)
                            _pipeline.sink = _sink
                            _pipeline.run()
                        finally:
                            _sink.close()

                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, run_pipeline)
                    sink = sink_container.get('sink')
                    records_ingested = sink.records_written if sink else 0

                else:
                    # Generic DataHub pipeline path (mysql, mongodb, cockroachdb, …)
                    sink = PostgresSink(None, {"job_id": job_id, "source_id": source_id})
                    pipeline_config = {"source": template, "sink": {"type": "console"}}

                    pipeline = Pipeline.create(pipeline_config)
                    pipeline.sink = sink

                    loop = asyncio.get_event_loop()
                    try:
                        await loop.run_in_executor(None, pipeline.run)
                    except UnboundLocalError as e:
                        if "data_platform_instance" in str(e):
                            logger.error(f"MongoDB connector error (known bug): {e}")
                            raise Exception(
                                "MongoDB schema inference encountered an issue. "
                                "Try with enableSchemaInference=false"
                            )
                        raise

                    sink.close()
                    records_ingested = sink.records_written

                # ── 7.5. Cleanup zero-column catalogs ────────────────────────
                try:
                    # Some sources emit duplicate or empty catalog entries without any columns.
                    if source_type in {"athena", "mongodb", "glue", "snowflake", "postgres"}:
                        await self.db.execute("""
                            DELETE FROM catalogs
                            WHERE source_id = $1
                              AND id NOT IN (
                                  SELECT DISTINCT catalog_id FROM columns WHERE catalog_id IS NOT NULL
                              )
                        """, source_id)
                        logger.info(f"[Ingestion] Cleaned up zero-column catalogs for {source_type}")
                except Exception as cleanup_err:
                    logger.warning(f"[Ingestion] Failed to clean up catalogs for {source_type}: {cleanup_err}")

                
                # ── 7.6. Athena row-count sync ──
                if source_type == "athena":
                    try:
                        await self._sync_athena_row_counts(source_id)
                    except Exception as rc_err:
                        logger.warning(f"[RowCount] Sync failed (non-fatal): {rc_err}")


                if source_type in {"athena", "glue"}:
                    try:
                        await self._sync_athena_descriptions(source_id)
                    except Exception as desc_err:
                        logger.warning(f"[Description] Sync failed (non-fatal): {desc_err}")

                # ── 8. Mark job success ──────────────────────────────────────
                await self.update_job(job_id, 'success', records_ingested)
                # ── 9. Snowflake fallback lineage via QUERY_HISTORY ──────────
                if config.get("include_lineage", False) and source_type in {"snowflake", "athena"}:
                    try:
                        if source_type == "snowflake":
                            lineage_count = await self._extract_snowflake_lineage(
                                source_id, conn_details, None
                            )
                        elif source_type == "athena":
                            lineage_count = await self._extract_athena_lineage(
                                source_id, conn_details
                            )
                        logger.info(f"[Lineage] Extracted {lineage_count} lineage pairs for {source_type}")
                    except Exception as le:
                        logger.error(f"[Lineage] Lineage extraction failed (non-fatal): {le}")

                await self.db.execute("""
                    UPDATE data_sources SET last_ingested_at = NOW(), status = 'success' WHERE id = $1
                """, source_id)

                logger.info(
                    f"[Ingestion] ✓ Metadata ingestion complete — "
                    f"{records_ingested} table(s) recorded for job {job_id}"
                )

                # ──  AUTO PII DETECTION ────────────────────────────────────
                # Only runs after data is fully committed to the database.
                # Triggered only when require_auto_pii_detection=True 
                
                if config.get("require_auto_pii_detection", False):
                    try:
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

                        await self.db.execute("""
                            UPDATE ingestion_jobs
                            SET metadata = COALESCE(metadata, '{}'::jsonb) || $1::jsonb
                            WHERE id = $2
                        """, json.dumps({"auto_pii_summary": pii_summary}), job_id)

                        cat = pii_summary.get("catalog_classification", {})
                        col = pii_summary.get("column_classification", {})
                        logger.info(
                            f"[AutoPII]  ✓ Detection complete — "
                            f"tables: {cat.get('classified',0)} classified, "
                            f"{cat.get('saved',0)} saved, {cat.get('pending',0)} pending | "
                            f"columns: {col.get('classified',0)} classified, "
                            f"{col.get('saved',0)} saved, {col.get('pending',0)} pending"
                        )
                        logger.info(f"[Ingestion] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                        logger.info(f"[Ingestion] ✓ Source ingestion fully complete — job_id={job_id}")

                    except Exception as pii_error:
                        # PII detection failure must NEVER fail or roll back the
                        # ingestion job — log it and continue.
                        logger.error(
                            f"[AutoPII] Detection failed for source={source_id} "
                            f"(ingestion itself succeeded): {pii_error}"
                        )
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
                
                deregister_job(job_id)
