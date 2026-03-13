"""Data source related schemas."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from .enums import SourceType, DataSourceStatus
from .connection_schemas import (
    PostgresConnectionDetails,
    MySQLConnectionDetails,
    MongoDBConnectionDetails,
    SnowflakeConnectionDetails,
    CockroachDBConnectionDetails,
    AthenaConnectionDetails,
    CSVConnectionDetails,  
    DynamoDBConnectionDetails,
    GlueConnectionDetails,
    MSSQLConnectionDetails,
    RedshiftConnectionDetails

)


class SimpleDataSource(BaseModel):
    """Simplified response for data source."""
    source_id: str
    name: str
    owner_name: Optional[str] = None
    status: str
    schedule: Optional[str] = None
    last_ingested_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        orm_mode = True


# Per-source create request models (use strict per-source connection classes)
class DataSourceCreatePostgres(BaseModel):
    """Create request for PostgreSQL data source."""
    name: str = Field(..., min_length=1, max_length=255)
    source_type: SourceType = Field(SourceType.POSTGRES)
    connection_details: PostgresConnectionDetails
    owner_id: str
    description: Optional[str] = None
    include_views: bool = True
    include_tables: bool = True
    schema_pattern: Optional[List[str]] = None
    table_pattern: Optional[List[str]] = None
    schedule: Optional[str] = Field("00:00 GMT+5:30")


class DataSourceCreateMySQL(BaseModel):
    """Create request for MySQL data source."""
    name: str = Field(..., min_length=1, max_length=255)
    source_type: SourceType = Field(SourceType.MYSQL)
    connection_details: MySQLConnectionDetails
    owner_id: str
    description: Optional[str] = None
    include_views: bool = True
    include_tables: bool = True
    schema_pattern: Optional[List[str]] = None
    table_pattern: Optional[List[str]] = None
    schedule: Optional[str] = Field("00:00 GMT+5:30")


class DataSourceCreateMongoDB(BaseModel):
    """Create request for MongoDB data source."""
    name: str = Field(..., min_length=1, max_length=255)
    source_type: SourceType = Field(SourceType.MONGODB)
    connection_details: MongoDBConnectionDetails
    owner_id: str
    description: Optional[str] = None
    include_views: bool = True
    include_tables: bool = True
    schema_pattern: Optional[List[str]] = None
    table_pattern: Optional[List[str]] = None
    schedule: Optional[str] = Field("00:00 GMT+5:30")


class DataSourceCreateSnowflake(BaseModel):
    """Create request for Snowflake data source."""
    name: str = Field(..., min_length=1, max_length=255)
    source_type: SourceType = Field(SourceType.SNOWFLAKE)
    connection_details: SnowflakeConnectionDetails
    owner_id: str
    description: Optional[str] = None
    include_views: bool = True
    include_tables: bool = True
    schema_pattern: Optional[List[str]] = None
    table_pattern: Optional[List[str]] = None
    schedule: Optional[str] = Field("00:00 GMT+5:30")


class DataSourceCreateCockroachDB(BaseModel):
    """Create request for CockroachDB data source."""
    name: str = Field(..., min_length=1, max_length=255)
    source_type: SourceType = Field(SourceType.COCKROACHDB)
    connection_details: CockroachDBConnectionDetails
    owner_id: str
    description: Optional[str] = None
    include_views: bool = True
    include_tables: bool = True
    schema_pattern: Optional[List[str]] = None
    table_pattern: Optional[List[str]] = None
    schedule: Optional[str] = Field("00:00 GMT+5:30")



class DataSourceCreateAthena(BaseModel):
    """Create request for Athena data source."""
    name: str = Field(..., min_length=1, max_length=255)
    source_type: SourceType = Field(SourceType.ATHENA)
    connection_details: AthenaConnectionDetails
    owner_id: str
    description: Optional[str] = None
    include_views: bool = True
    include_tables: bool = True
    schema_pattern: Optional[List[str]] = None
    table_pattern: Optional[List[str]] = None
    schedule: Optional[str] = Field("00:00 GMT+5:30")

class DataSourceCreateCSV(BaseModel):
    """Create request for CSV (URL-based) data source."""
    name: str = Field(..., min_length=1, max_length=255)
    source_type: SourceType = Field(SourceType.CSV)
    connection_details: CSVConnectionDetails
    owner_id: str
    description: Optional[str] = None
    schedule: Optional[str] = Field("00:00 GMT+5:30")

class DataSourceCreateDynamoDB(BaseModel):
    """Create request for DynamoDB data source."""
    name: str = Field(..., min_length=1, max_length=255)
    source_type: SourceType = Field(SourceType.DYNAMODB)
    connection_details: DynamoDBConnectionDetails
    owner_id: str
    description: Optional[str] = None

    # Common fields (DynamoDB usually doesn't use schema/table patterns the same way)
    include_tables: bool = Field(True, description="Ingest all tables (usually true)")
    table_pattern: Optional[List[str]] = Field(
        None,
        description="Optional glob-like patterns to filter which tables to ingest (e.g. ['prod_*', 'analytics_orders'])"
    )
    schedule: Optional[str] = Field("00:00 GMT+5:30")
    # advanced: Optional[dict] = None

class DataSourceCreateGlue(BaseModel):
    """Create request for Glue data source."""
    name: str = Field(..., min_length=1, max_length=255)
    source_type: SourceType = Field(SourceType.GLUE)
    connection_details: GlueConnectionDetails
    owner_id: str
    description: Optional[str] = None

    # Common filtering (same as your UI example)
    include_views: bool = True
    include_tables: bool = True
    schema_pattern: Optional[List[str]] = Field(
        None, description="List of database patterns to include (allow list)"
    )
    table_pattern: Optional[List[str]] = Field(
        None, description="List of table patterns to include (allow list)"
    )

    # You can add deny patterns later if needed
    # database_pattern_deny: Optional[List[str]] = None
    # table_pattern_deny: Optional[List[str]] = None

    schedule: Optional[str] = Field("00:00 GMT+5:30", description="Cron-like schedule string")

class DataSourceCreateMSSQL(BaseModel):
    """Create request for Microsoft SQL Server data source"""
    name: str = Field(..., min_length=1, max_length=255)
    source_type: SourceType = Field(SourceType.MSSQL)
    connection_details: MSSQLConnectionDetails
    owner_id: str
    description: Optional[str] = None
    include_views: bool = True
    include_tables: bool = True
    schema_pattern: Optional[List[str]] = None
    table_pattern: Optional[List[str]] = None
    schedule: Optional[str] = Field("00:00 GMT+5:30", description="Ingestion schedule")

class DataSourceCreateRedshift(BaseModel):
    """Create request for Amazon Redshift data source"""
    name: str = Field(..., min_length=1, max_length=255)
    source_type: SourceType = Field(SourceType.REDSHIFT)
    connection_details: RedshiftConnectionDetails
    owner_id: str
    description: Optional[str] = None
    schedule: Optional[str] = Field("00:00 GMT+5:30", description="Ingestion schedule")

    class Config:
        extra = "forbid"


class DataSource(BaseModel):
    """Returned by read/list endpoints."""
    id: str
    name: str
    source_type: SourceType
    # we store whatever JSON object was saved for the connection parameters
    connection_details: Dict[str, Any]
    description: Optional[str] = None
    include_views: bool = True
    include_tables: bool = True
    schema_pattern: Optional[List[str]] = None
    table_pattern: Optional[List[str]] = None
    status: DataSourceStatus = DataSourceStatus.RUNNING
    schedule: Optional[str] = "00:00 GMT+5:30"
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_ingested_at: Optional[datetime]

    class Config:
        orm_mode = True
