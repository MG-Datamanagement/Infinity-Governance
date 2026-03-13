"""Connection detail schemas for different database sources."""

from typing import Optional, List
from pydantic import BaseModel, Field, validator, SecretStr


class PostgresConnectionDetails(BaseModel):
    """Connection details for PostgreSQL sources."""
    host_port: str = Field(..., description="Host and port, e.g. localhost:5432")
    database: str = Field(..., description="Target database name")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")

    class Config:
        extra = "forbid"

    @validator("host_port")
    def validate_host_port(cls, v: str) -> str:
        parts = v.rsplit(":", 1)
        if len(parts) != 2 or not parts[1].isdigit():
            raise ValueError("host_port must be in 'host:port' format, e.g. localhost:5432")
        port = int(parts[1])
        if not (1 <= port <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v


class MySQLConnectionDetails(BaseModel):
    """Connection details for MySQL sources."""
    host_port: str = Field(..., description="Host and port, e.g. localhost:3306")
    database: str = Field(..., description="Target database name")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")

    class Config:
        extra = "forbid"

    @validator("host_port")
    def validate_host_port(cls, v: str) -> str:
        parts = v.rsplit(":", 1)
        if len(parts) != 2 or not parts[1].isdigit():
            raise ValueError("host_port must be in 'host:port' format, e.g. localhost:3306")
        port = int(parts[1])
        if not (1 <= port <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v


class MongoDBConnectionDetails(BaseModel):
    """Connection details for MongoDB sources."""
    connect_uri: str = Field(..., description="MongoDB connection string, e.g. mongodb://host:27017/db")
    username: Optional[str] = Field(None, description="Override username (if not in URI)")
    password: Optional[str] = Field(None, description="Override password (if not in URI)")
    enableSchemaInference: Optional[bool] = Field(True,  description="Infer schema from sampled documents")
    useRandomSampling: Optional[bool] = Field(True,  description="Use random sampling for schema inference")
    maxSchemaSize: Optional[int]  = Field(300,   ge=1, le=10_000, description="Max number of fields to infer")

    class Config:
        extra = "forbid"

    @validator("connect_uri")
    def validate_connect_uri(cls, v: str) -> str:
        if not v.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError("connect_uri must start with 'mongodb://' or 'mongodb+srv://'")
        return v


class SnowflakeConnectionDetails(BaseModel):
    """Connection details for Snowflake sources."""
    account_id: str = Field(..., description="Snowflake account identifier, e.g. xy12345.us-east-1")
    username: str = Field(..., description="Snowflake username")
    password: str = Field(..., description="Snowflake password")
    warehouse: str = Field(..., description="Snowflake warehouse name")
    role: Optional[str] = Field(None, description="Snowflake role (optional)")
    database: Optional[str] = Field(None, description="Default database (optional)")

    class Config:
        extra = "forbid"

    @validator("account_id")
    def validate_account_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("account_id must not be empty")
        return v


class CockroachDBConnectionDetails(BaseModel):
    """Connection details for CockroachDB sources."""
    host_port: str = Field(..., description="Host and port, e.g. localhost:26257")
    database: str = Field(..., description="Target database name")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")

    class Config:
        extra = "forbid"

    @validator("host_port")
    def validate_host_port(cls, v: str) -> str:
        parts = v.rsplit(":", 1)
        if len(parts) != 2 or not parts[1].isdigit():
            raise ValueError("host_port must be in 'host:port' format, e.g. localhost:26257")
        port = int(parts[1])
        if not (1 <= port <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v



class AthenaConnectionDetails(BaseModel):
    """Connection details for Athena sources."""
    username:str = Field(None, description="AWS Access Key ID")
    password: str = Field(None, description="AWS Secret Access Key")
    aws_region: str = Field(
        ..., description="AWS region where Athena is running (e.g. us-east-1, eu-west-1)"
    )
    work_group: str = Field(
        ..., description="Name of the Athena Workgroup to use (e.g. 'primary')"
    )
    s3_staging_dir: str = Field(
        ..., 
        description="S3 path where Athena stores query results (must be writable by the credentials)",
        pattern=r"^s3://.+",
        examples=["s3://my-athena-results-bucket/query-results/"]
    )

    class Config:
        extra = "forbid"

    @validator("s3_staging_dir")
    def validate_s3_staging_dir(cls, v: str) -> str:
        if not v.startswith("s3://"):
            raise ValueError("s3_staging_dir must start with 's3://'")
        if not v.endswith("/"):
            raise ValueError("s3_staging_dir should end with '/' for best practice")
        return v

    @validator("aws_region")
    def validate_region(cls, v: str) -> str:
        # Optional: you could add a list of valid AWS regions if desired
        if not v:
            raise ValueError("aws_region is required")
        return v

class CSVConnectionDetails(BaseModel):
    """Connection details for CSV over HTTP/URL sources."""
    file_url: str = Field(
        ...,
        description="Publicly accessible URL to the CSV file (http/https)",
        examples=[
            "https://docs.google.com/spreadsheets/d/.../pub?output=csv",
            "https://example.com/data.csv"
        ]
    )
    delimiter: str = Field(
        default=",",
        description="Field delimiter (usually , or ; or \\t)",
        min_length=1, max_length=1
    )
    array_delimiter: str = Field(
        default="|",
        description="Delimiter for array/list values inside a cell (e.g. tags: tag1|tag2|tag3)",
        min_length=1, max_length=1
    )
    write_semantics: str = Field(
        default="PATCH",
        description=(
            "How to handle repeated ingestions:\n"
            "- PATCH: update existing records + insert new ones (upsert behavior)\n"
            "- OVERRIDE: completely replace all previous data with the new content"
        )
    )

    class Config:
        extra = "forbid"

    @validator("file_url")
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("file_url must start with http:// or https://")
        return v

    @validator("delimiter", "array_delimiter")
    def validate_single_char(cls, v: str) -> str:
        if len(v) != 1:
            raise ValueError("delimiter and array_delimiter must be exactly one character")
        return v

class DynamoDBConnectionDetails(BaseModel):
    """Connection details for DynamoDB sources."""
    aws_access_key_id: Optional[str] = Field(
        None,
        description="AWS Access Key ID (leave empty if using IAM role / instance profile)"
    )
    aws_secret_access_key: Optional[str] = Field(
        None,
        description="AWS Secret Access Key (leave empty if using IAM role / instance profile)"
    )
    aws_region: str = Field(
        ...,
        description="AWS region of the DynamoDB tables (e.g. us-east-1, ap-south-1)"
    )
    # Optional: if you want to support cross-account or specific endpoint
    endpoint_url: Optional[str] = Field(None, description="Custom DynamoDB endpoint (rarely needed)")

    class Config:
        extra = "forbid"

    @validator("aws_region")
    def validate_region(cls, v: str) -> str:
        if not v:
            raise ValueError("aws_region is required")
        return v

class GlueConnectionDetails(BaseModel):
    """Connection details for AWS Glue Data Catalog sources."""
    aws_access_key_id: Optional[str] = Field(
        None, description="AWS Access Key ID (can be omitted if using role / default credentials)"
    )
    aws_secret_access_key: Optional[str] = Field(
        None, description="AWS Secret Access Key"
    )
    aws_region: str = Field(
        ..., description="AWS region where Glue Data Catalog is located (e.g. us-east-1)"
    )
    catalog_id: Optional[str] = Field(
        None,
        description="AWS Account ID of the Glue catalog to ingest (for cross-account access). If None → current caller account."
    )
    # You can add aws_session_token / role_arn later if needed

    class Config:
        extra = "forbid"

    @validator("aws_region")
    def validate_region(cls, v: str) -> str:
        if not v:
            raise ValueError("aws_region is required")
        return v
    

class MSSQLProfilingConfig(BaseModel):
    """Nested profiling settings (matches your YAML structure)"""
    enabled: bool = True
    table_level_only: bool = True                  # "profile_table_level_only"
    stateful_ingestion: Optional[dict] = Field(
        default_factory=lambda: {"enabled": True},
        description="Stateful ingestion settings"
    )

class MSSQLConnectionDetails(BaseModel):
    """Connection details for Microsoft SQL Server"""
    host_port: str = Field(
        ...,
        description="Host and port (e.g. 'mssql-server:1433')"
    )
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")  # ← changed from SecretStr
    database: str = Field(..., description="Specific database name")

    schema_allow_patterns: Optional[List[str]] = Field(None, alias="schema_allow")
    schema_deny_patterns: Optional[List[str]] = Field(None, alias="schema_deny")
    table_allow_patterns: Optional[List[str]] = Field(None, alias="table_allow")
    table_deny_patterns: Optional[List[str]] = Field(None, alias="table_deny")
    view_allow_patterns: Optional[List[str]] = Field(None, alias="view_allow")
    view_deny_patterns: Optional[List[str]] = Field(None, alias="view_deny")

    include_tables: bool = True
    include_views: bool = True
    profiling: MSSQLProfilingConfig = Field(default_factory=MSSQLProfilingConfig)

    class Config:
        extra = "forbid"
        allow_population_by_field_name = True

    @validator("host_port")
    def validate_host_port(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError("host_port must contain ':' (host:port)")
        return v
    
class RedshiftLineageConfig(BaseModel):
    """Nested lineage settings"""
    include_table_lineage: bool = True
    table_lineage_mode: str = Field("stlscan-based", description="Mode for table lineage (e.g., 'stlscan-based')")

    @validator("table_lineage_mode")
    def validate_lineage_mode(cls, v: str) -> str:
        allowed_modes = ["stlscan-based"]  # Add more if supported
        if v not in allowed_modes:
            raise ValueError(f"table_lineage_mode must be one of {allowed_modes}")
        return v


class RedshiftProfilingConfig(BaseModel):
    """Nested profiling settings"""
    enable_table_profiling: bool = True
    enable_column_profiling: bool = False
    # Add more if needed, e.g., sample_size

class RedshiftConnectionDetails(BaseModel):
    """Connection details for Amazon Redshift"""
    host_port: str = Field(
        ...,
        description="Host and port (e.g., 'redshift-company-us-west-1.redshift.amazonaws.com:5439')"
    )
    database: str = Field(..., description="Database name")
    username: str = Field(..., description="Database username")
    password: SecretStr = Field(..., description="Database password (stored as secret)")

    # Filter patterns (allow/deny lists)
    schema_allow_patterns: Optional[List[str]] = Field(None, alias="schema_allow")
    schema_deny_patterns: Optional[List[str]] = Field(None, alias="schema_deny")
    table_allow_patterns: Optional[List[str]] = Field(None, alias="table_allow")
    table_deny_patterns: Optional[List[str]] = Field(None, alias="table_deny")
    view_allow_patterns: Optional[List[str]] = Field(None, alias="view_allow")
    view_deny_patterns: Optional[List[str]] = Field(None, alias="view_deny")

    # Common toggles
    include_tables: bool = True
    include_views: bool = True

    # Nested configs
    lineage: RedshiftLineageConfig = Field(default_factory=RedshiftLineageConfig)
    profiling: RedshiftProfilingConfig = Field(default_factory=RedshiftProfilingConfig)
    enable_stateful_ingestion: bool = True

    class Config:
        extra = "forbid"
        allow_population_by_field_name = True  # Support aliases for patterns

    @validator("host_port")
    def validate_host_port(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError("host_port must contain ':' (host:port)")
        return v