"""Enum definitions for the application."""

from enum import Enum


class SourceType(str, Enum):
    """Supported data source connector types."""
    POSTGRES = "postgres"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    SNOWFLAKE = "snowflake"
    COCKROACHDB = "cockroachdb"
    ATHENA = "athena"
    CSV = "csv"
    DYNAMODB = "dynamodb"
    GLUE = "glue"
    MSSQL = "mssql"
    REDSHIFT = "redshift"
    


class JobStatus(str, Enum):
    """
    Lifecycle status shared by both ingestion jobs and data sources.
    """
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class DataSourceStatus(str, Enum):
    """Status of a data source."""
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class OwnerRole(str, Enum):
    """Roles assignable to an owner (person or team) of a data asset."""
    DATA_STEWARD = "data_steward"
    ADMIN = "admin"
    TECHNICAL_OWNER = "technical_owner"
    BUSINESS_OWNER = "business_owner"
