from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from langchain_openai import AzureChatOpenAI
import os

router = APIRouter(tags=["lineage"])


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class ColumnInfo(BaseModel):
    id: str
    name: str
    data_type: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    is_nullable: bool = True
    query_expression: Optional[str] = None


class SourceInfo(BaseModel):
    id: str
    name: str
    source_type: str


class TagInfo(BaseModel):
    id: str
    name: str
    color: Optional[str] = None
    tag_type: Optional[str] = None


class ColumnMapping(BaseModel):
    upstream_column_id: str
    upstream_column_name: Optional[str] = None
    downstream_column_id: str
    downstream_column_name: Optional[str] = None


class QueryExecutionInfo(BaseModel):
    """Execution metadata from the table_lineage row."""
    query_execution_id: Optional[str] = None
    query_start_time: Optional[str] = None
    query_end_time: Optional[str] = None
    query_runtime_ms: Optional[int] = None
    data_scanned_bytes: Optional[int] = None
    query_status: Optional[str] = None
    engine_version: Optional[str] = None
    s3_output_location: Optional[str] = None


class VisualNode(BaseModel):
    """One catalog card in the visual graph."""
    id: str
    table_name: str
    full_name: Optional[str] = None
    schema_name: Optional[str] = None
    database_name: Optional[str] = None
    type: Optional[str] = "table"
    status: Optional[str] = "healthy"
    source: Optional[SourceInfo] = None
    columns: List[ColumnInfo] = []
    tags: List[TagInfo] = []
    lineage_id: Optional[str] = None
    transformation_query: Optional[str] = None
    query_execution: Optional[QueryExecutionInfo] = None
    column_mappings: List[ColumnMapping] = []
    depth: int = 1
    ai_summary: Optional[str] = None
    stats: Optional[str] = None
    notes: Optional[str] = None


class VisualLineageResponse(BaseModel):
    root: VisualNode
    upstreams: List[VisualNode] = []
    downstreams: List[VisualNode] = []


class CentricLineageNode(BaseModel):
    id: str
    table_name: str
    full_name: Optional[str] = None
    schema_name: Optional[str] = None
    database_name: Optional[str] = None
    type: Optional[str] = "table"
    status: Optional[str] = "healthy"
    source: Optional[SourceInfo] = None
    columns: List[ColumnInfo] = []
    tags: List[TagInfo] = []
    lineage_id: Optional[str] = None
    transformation_query: Optional[str] = None
    query_execution: Optional[QueryExecutionInfo] = None
    depth: int = 1
    ai_summary: Optional[str] = None
    stats: Optional[str] = None
    notes: Optional[str] = None
    upstream_nodes: List['CentricLineageNode'] = []
    downstream_nodes: List['CentricLineageNode'] = []


class CentricLineageResponse(BaseModel):
    base_node: CentricLineageNode


# ─── LLM ─────────────────────────────────────────────────────────────────────

llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    temperature=0.2
)


# ─── Hardcoded Mock Data ──────────────────────────────────────────────────────

# Table names (lowercased) whose upstream list always includes ALL mock nodes
MOCK_TRIGGER_TABLE_NAMES = {"all_booking", "all_booking_agent"}

# ODS upstream table names — when ods_profiles is the node, these are injected as upstreams.
# When any of these is a node, ods_profiles is injected as a downstream.
ODS_UPSTREAM_TABLE_NAMES = {
    "all_person", "all_personname", "all_personemail", "all_personphone",
    "all_personaddress", "all_passengertraveldoc", "all_bookingpassenger",
    "all_booking", "all_passengerfee", "all_passengerjseg", "all_passengerjleg",
    "all_bookingcontact", "all_agent",
}

# SFMC raw table names — NiFi upstream injection applies to these as well
SFMC_RAW_TABLE_NAMES = {
    "sfmc_all_sent", "sfmc_all_subscribers", "sfmc_all_open", "sfmc_all_click",
}

# Combined set: all tables that get NiFi + MSSQL injected as upstreams
NIFI_UPSTREAM_TABLE_NAMES = ODS_UPSTREAM_TABLE_NAMES | SFMC_RAW_TABLE_NAMES

# CIAM layer tables - get Lambda + API injected as upstreams
CIAM_UPSTREAM_TABLE_NAMES = {"edwcustomer"}

# ── Shared constants for ODS mock nodes ──────────────────────────────────────
_ODS_SOURCE = SourceInfo(
    id="e3d3fa59-5a34-4329-a849-e50f59b135cf",
    name="test-athena-source",
    source_type="athena",
)
_PII_TAG = TagInfo(id="ea1dcf08-d7ac-402d-86be-d7e35483777f", name="PII", color="#3B82F6", tag_type="general")
_ODS_QUERY_EXEC = QueryExecutionInfo(
    query_execution_id="78ae3e2f-202a-4fc4-b682-33fe5f561664",
    query_start_time="2026-03-25T20:45:15.437000+00:00",
    query_end_time="2026-03-25T20:45:18.298000+00:00",
    query_runtime_ms=2861,
    data_scanned_bytes=16486,
    query_status="SUCCEEDED",
    engine_version="Athena engine version 3",
    s3_output_location="s3://athena-query-results560/Unsaved/2026/03/26/tables/78ae3e2f-202a-4fc4-b682-33fe5f561664",
)
_ODS_TRANSFORM_QUERY = (
    "CREATE TABLE ods.ods_profiles\n"
    "WITH (\n"
    "  format = 'PARQUET',\n"
    "  write_compression = 'SNAPPY',\n"
    "  external_location = 's3://infinity-gov-dev/data/ods/ods_profiles/'\n"
    ") AS\n"
    "SELECT\n"
    "  p.person_id,\n"
    "  pn.first_name,\n"
    "  pn.last_name,\n"
    "  pe.primary_email,\n"
    "  ph.primary_phone,\n"
    "  pa.home_city,\n"
    "  pa.home_country,\n"
    "  pa.home_address_full,\n"
    "  ptd.passport_nationality,\n"
    "  ptd.passport_expiry,\n"
    "  bp.total_bookings,\n"
    "  b.booking_channel,\n"
    "  pf.total_ancillary_spend,\n"
    "  pjs.total_segments,\n"
    "  pjl.total_flight_hours,\n"
    "  bc.booker_name,\n"
    "  ag.preferred_agent_name\n"
    "FROM ods.all_person p\n"
    "LEFT JOIN ods.all_personname pn ON p.person_id = pn.person_id\n"
    "LEFT JOIN ods.all_personemail pe ON p.person_id = pe.person_id\n"
    "LEFT JOIN ods.all_personphone ph ON p.person_id = ph.person_id\n"
    "LEFT JOIN ods.all_personaddress pa ON p.person_id = pa.person_id\n"
    "LEFT JOIN ods.all_passengertraveldoc ptd ON p.person_id = ptd.person_id\n"
    "LEFT JOIN ods.all_bookingpassenger bp ON p.person_id = bp.person_id\n"
    "LEFT JOIN ods.all_booking b ON bp.booking_id = b.booking_id\n"
    "LEFT JOIN ods.all_passengerfee pf ON bp.passenger_id = pf.passenger_id\n"
    "LEFT JOIN ods.all_passengerjseg pjs ON bp.passenger_id = pjs.passenger_id\n"
    "LEFT JOIN ods.all_passengerjleg pjl ON bp.passenger_id = pjl.passenger_id\n"
    "LEFT JOIN ods.all_bookingcontact bc ON b.booking_id = bc.booking_id\n"
    "LEFT JOIN ods.all_agent ag ON b.agent_id = ag.agent_id"
)

# ── NiFi + Microsoft SQL Server mock nodes ────────────────────────────────────
# Injected as upstreams for every ODS raw table and every SFMC raw table.
# Microsoft SQL Server is the upstream of NiFi.
# Both carry status = "idempotent" (same treatment as inventory_management).

_NIFI_SOURCE = SourceInfo(
    id="nifi-source-mock-0001",
    name="apache-nifi",
    source_type="nifi",
)

_MSSQL_SOURCE = SourceInfo(
    id="mssql-source-mock-0001",
    name="microsoft-sql-server",
    source_type="sqlserver",
)

# Microsoft SQL Server — upstream of NiFi, origin of all raw data
MOCK_MSSQL_NODE = CentricLineageNode(
    id="mock-mssql-node-upstream-0001",
    table_name="microsoft_sql_server",
    full_name="sqlserver.microsoft_sql_server",
    schema_name="sqlserver",
    database_name=None,
    type="table",
    status="idempotent",
    source=_MSSQL_SOURCE,
    columns=[],
    tags=[],
    lineage_id="mock-mssql-lineage-0001",
    transformation_query="JDBC EXTRACT",
    query_execution=None,
    depth=3,
    ai_summary=(
        "Microsoft SQL Server is the operational source system that holds raw transactional "
        "and master data; records are extracted via JDBC and handed off to Apache NiFi, "
        "making it the true origin point of the entire data pipeline."
    ),
    stats="Columns: 0 | Rows: N/A",
    upstream_nodes=[],
    downstream_nodes=[],
)

# NiFi — upstream of ODS/SFMC raw tables, downstream of MSSQL
MOCK_NIFI_NODE = CentricLineageNode(
    id="mock-nifi-node-upstream-0001",
    table_name="nifi",
    full_name="nifi.nifi",
    schema_name="nifi",
    database_name=None,
    type="table",
    status="idempotent",
    source=_NIFI_SOURCE,
    columns=[],
    tags=[],
    lineage_id="mock-nifi-lineage-0001",
    transformation_query="1:1 LOAD",
    query_execution=None,
    depth=2,
    ai_summary=(
        "Apache NiFi acts as the ingestion and routing layer, performing a 1:1 load of raw "
        "records extracted from Microsoft SQL Server without any transformation, delivering "
        "data as-is into the downstream ODS and SFMC raw landing tables."
    ),
    stats="Columns: 0 | Rows: N/A",
    upstream_nodes=[MOCK_MSSQL_NODE],
    downstream_nodes=[],
)

# VisualNode equivalents for _traverse (flat-list endpoint)
MOCK_NIFI_VISUAL_NODE = VisualNode(
    id="mock-nifi-node-upstream-0001",
    table_name="nifi",
    full_name="nifi.nifi",
    schema_name="nifi",
    database_name=None,
    type="table",
    status="idempotent",
    source=_NIFI_SOURCE,
    columns=[],
    tags=[],
    lineage_id="mock-nifi-lineage-0001",
    transformation_query="1:1 LOAD",
    query_execution=None,
    column_mappings=[],
    depth=2,
    ai_summary=(
        "Apache NiFi acts as the ingestion and routing layer, performing a 1:1 load of raw "
        "records extracted from Microsoft SQL Server without any transformation, delivering "
        "data as-is into the downstream ODS and SFMC raw landing tables."
    ),
    stats="Columns: 0 | Rows: N/A",
)

MOCK_MSSQL_VISUAL_NODE = VisualNode(
    id="mock-mssql-node-upstream-0001",
    table_name="microsoft_sql_server",
    full_name="sqlserver.microsoft_sql_server",
    schema_name="sqlserver",
    database_name=None,
    type="table",
    status="idempotent",
    source=_MSSQL_SOURCE,
    columns=[],
    tags=[],
    lineage_id="mock-mssql-lineage-0001",
    transformation_query="JDBC EXTRACT",
    query_execution=None,
    column_mappings=[],
    depth=3,
    ai_summary=(
        "Microsoft SQL Server is the operational source system that holds raw transactional "
        "and master data; records are extracted via JDBC and handed off to Apache NiFi, "
        "making it the true origin point of the entire data pipeline."
    ),
    stats="Columns: 0 | Rows: N/A",
)

# ── CIAM API + Lambda mock nodes ──────────────────────────────────────────────
# Injected as upstreams for every CIAM table (e.g. edwcustomer).
# API is the upstream of Lambda. Lambda is the upstream of the CIAM table.
# Both carry status = "idempotent".

_CIAM_API_SOURCE = SourceInfo(
    id="ciam-api-source-mock-0001",
    name="ciam-api",
    source_type="api",
)

_CIAM_LAMBDA_SOURCE = SourceInfo(
    id="ciam-lambda-source-mock-0001",
    name="aws-lambda",
    source_type="lambda",
)

MOCK_CIAM_API_NODE = CentricLineageNode(
    id="mock-ciam-api-node-upstream-0001",
    table_name="api",
    full_name="api.ciam_api",
    schema_name="api",
    database_name=None,
    type="table",
    status="idempotent",
    source=_CIAM_API_SOURCE,
    columns=[],
    tags=[],
    lineage_id="mock-ciam-api-lineage-0001",
    transformation_query="CIAM API CALL",
    query_execution=None,
    depth=3,
    ai_summary="The CIAM API interfaces with the customer identity and access management system to securely fetch and manage user identity credentials and authorization parameters.",
    stats="Columns: 0 | Rows: N/A",
    upstream_nodes=[],
    downstream_nodes=[],
)

MOCK_CIAM_LAMBDA_NODE = CentricLineageNode(
    id="mock-ciam-lambda-node-upstream-0001",
    table_name="lambda",
    full_name="lambda.aws_lambda",
    schema_name="lambda",
    database_name=None,
    type="table",
    status="idempotent",
    source=_CIAM_LAMBDA_SOURCE,
    columns=[],
    tags=[],
    lineage_id="mock-ciam-lambda-lineage-0001",
    transformation_query="JSON → Parquet Load",
    query_execution=None,
    depth=2,
    ai_summary="The AWS Lambda function processes incoming real-time CIAM API payloads, converting JSON structures to Parquet format for optimal analytical storage and downstream processing.",
    stats="Columns: 0 | Rows: N/A",
    upstream_nodes=[MOCK_CIAM_API_NODE],
    downstream_nodes=[],
)

MOCK_CIAM_API_VISUAL_NODE = VisualNode(
    id="mock-ciam-api-node-upstream-0001",
    table_name="api",
    full_name="api.ciam_api",
    schema_name="api",
    database_name=None,
    type="table",
    status="idempotent",
    source=_CIAM_API_SOURCE,
    columns=[],
    tags=[],
    lineage_id="mock-ciam-api-lineage-0001",
    transformation_query="CIAM API CALL",
    query_execution=None,
    column_mappings=[],
    depth=3,
    ai_summary="The CIAM API interfaces with the customer identity and access management system to securely fetch and manage user identity credentials and authorization parameters.",
    stats="Columns: 0 | Rows: N/A",
)

MOCK_CIAM_LAMBDA_VISUAL_NODE = VisualNode(
    id="mock-ciam-lambda-node-upstream-0001",
    table_name="lambda",
    full_name="lambda.aws_lambda",
    schema_name="lambda",
    database_name=None,
    type="table",
    status="idempotent",
    source=_CIAM_LAMBDA_SOURCE,
    columns=[],
    tags=[],
    lineage_id="mock-ciam-lambda-lineage-0001",
    transformation_query="JSON → Parquet Load",
    query_execution=None,
    column_mappings=[],
    depth=2,
    ai_summary="The AWS Lambda function processes incoming real-time CIAM API payloads, converting JSON structures to Parquet format for optimal analytical storage and downstream processing.",
    stats="Columns: 0 | Rows: N/A",
)

# ── ODS upstream mock CentricLineageNodes ─────────────────────────────────────
# Each includes MOCK_NIFI_NODE (which itself contains MOCK_MSSQL_NODE) as upstream.

ODS_MOCK_ALL_PERSON = CentricLineageNode(
    id="ods-mock-001-all-person",
    table_name="all_person",
    full_name="ods.all_person",
    schema_name="ods",
    database_name=None,
    type="table",
    status="healthy",
    source=_ODS_SOURCE,
    columns=[
        ColumnInfo(id="ods-p-01", name="person_id",     data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-p-02", name="gender",        data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-p-03", name="nationality",   data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-p-04", name="date_of_birth", data_type="SchemaFieldDataTypeClass({'type': DateTypeClass({})})",   is_nullable=True),
        ColumnInfo(id="ods-p-05", name="title",         data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-p-06", name="created_date",  data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-p-07", name="modified_date", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
    ],
    tags=[_PII_TAG],
    lineage_id="ods-lineage-001",
    transformation_query=_ODS_TRANSFORM_QUERY,
    query_execution=_ODS_QUERY_EXEC,
    depth=2,
    ai_summary="The ods.all_person dataset captures core demographic identity records for each individual, sourced from upstream reservation systems, serving as the foundational person entity that anchors all profile enrichment in the ODS pipeline.",
    stats="Columns: 7 | Rows: 50",
    upstream_nodes=[MOCK_NIFI_NODE],
    downstream_nodes=[],
)

ODS_MOCK_ALL_PERSONNAME = CentricLineageNode(
    id="ods-mock-002-all-personname",
    table_name="all_personname",
    full_name="ods.all_personname",
    schema_name="ods",
    database_name=None,
    type="table",
    status="healthy",
    source=_ODS_SOURCE,
    columns=[
        ColumnInfo(id="ods-pn-01", name="person_id",    data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pn-02", name="first_name",   data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pn-03", name="last_name",    data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pn-04", name="full_name",    data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pn-05", name="name_type",    data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pn-06", name="created_date", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pn-07", name="modified_date",data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
    ],
    tags=[_PII_TAG],
    lineage_id="ods-lineage-002",
    transformation_query=_ODS_TRANSFORM_QUERY,
    query_execution=_ODS_QUERY_EXEC,
    depth=2,
    ai_summary="The ods.all_personname dataset stores name variants for each person sourced from booking and reservation systems, providing first name, last name, and full name fields that are used to enrich profile identity in the ODS pipeline.",
    stats="Columns: 7 | Rows: 50",
    upstream_nodes=[MOCK_NIFI_NODE],
    downstream_nodes=[],
)

ODS_MOCK_ALL_PERSONEMAIL = CentricLineageNode(
    id="ods-mock-003-all-personemail",
    table_name="all_personemail",
    full_name="ods.all_personemail",
    schema_name="ods",
    database_name=None,
    type="table",
    status="healthy",
    source=_ODS_SOURCE,
    columns=[
        ColumnInfo(id="ods-pe-01", name="person_id",     data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pe-02", name="primary_email", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pe-03", name="email_type",    data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pe-04", name="email_opt_in",  data_type="SchemaFieldDataTypeClass({'type': BooleanTypeClass({})})",is_nullable=True),
        ColumnInfo(id="ods-pe-05", name="created_date",  data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pe-06", name="modified_date", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
    ],
    tags=[_PII_TAG],
    lineage_id="ods-lineage-003",
    transformation_query=_ODS_TRANSFORM_QUERY,
    query_execution=_ODS_QUERY_EXEC,
    depth=2,
    ai_summary="The ods.all_personemail dataset holds email address records and opt-in consent flags per person, sourced from reservation systems, supplying primary contact data to enrich downstream profile and marketing datasets.",
    stats="Columns: 6 | Rows: 50",
    upstream_nodes=[MOCK_NIFI_NODE],
    downstream_nodes=[],
)

ODS_MOCK_ALL_PERSONPHONE = CentricLineageNode(
    id="ods-mock-004-all-personphone",
    table_name="all_personphone",
    full_name="ods.all_personphone",
    schema_name="ods",
    database_name=None,
    type="table",
    status="healthy",
    source=_ODS_SOURCE,
    columns=[
        ColumnInfo(id="ods-ph-01", name="person_id",     data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-ph-02", name="primary_phone", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-ph-03", name="phone_type",    data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-ph-04", name="sms_opt_in",    data_type="SchemaFieldDataTypeClass({'type': BooleanTypeClass({})})",is_nullable=True),
        ColumnInfo(id="ods-ph-05", name="created_date",  data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-ph-06", name="modified_date", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
    ],
    tags=[_PII_TAG],
    lineage_id="ods-lineage-004",
    transformation_query=_ODS_TRANSFORM_QUERY,
    query_execution=_ODS_QUERY_EXEC,
    depth=2,
    ai_summary="The ods.all_personphone dataset captures phone number records and SMS consent flags per person, sourced from upstream booking systems, providing primary phone contact data for profile enrichment and communication workflows.",
    stats="Columns: 6 | Rows: 50",
    upstream_nodes=[MOCK_NIFI_NODE],
    downstream_nodes=[],
)

ODS_MOCK_ALL_PERSONADDRESS = CentricLineageNode(
    id="ods-mock-005-all-personaddress",
    table_name="all_personaddress",
    full_name="ods.all_personaddress",
    schema_name="ods",
    database_name=None,
    type="table",
    status="healthy",
    source=_ODS_SOURCE,
    columns=[
        ColumnInfo(id="ods-pa-01", name="person_id",        data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pa-02", name="home_city",         data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pa-03", name="home_country",      data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pa-04", name="home_address_full", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pa-05", name="address_type",      data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pa-06", name="postal_code",       data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pa-07", name="created_date",      data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pa-08", name="modified_date",     data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
    ],
    tags=[_PII_TAG],
    lineage_id="ods-lineage-005",
    transformation_query=_ODS_TRANSFORM_QUERY,
    query_execution=_ODS_QUERY_EXEC,
    depth=2,
    ai_summary="The ods.all_personaddress dataset stores residential address information per person sourced from reservation records, supplying home city, country, and full address fields used for geographic segmentation and profile enrichment downstream.",
    stats="Columns: 8 | Rows: 50",
    upstream_nodes=[MOCK_NIFI_NODE],
    downstream_nodes=[],
)

ODS_MOCK_ALL_PASSENGERTRAVELDOC = CentricLineageNode(
    id="ods-mock-006-all-passengertraveldoc",
    table_name="all_passengertraveldoc",
    full_name="ods.all_passengertraveldoc",
    schema_name="ods",
    database_name=None,
    type="table",
    status="healthy",
    source=_ODS_SOURCE,
    columns=[
        ColumnInfo(id="ods-ptd-01", name="person_id",           data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})",  is_nullable=True),
        ColumnInfo(id="ods-ptd-02", name="passport_nationality", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_nullable=True),
        ColumnInfo(id="ods-ptd-03", name="passport_expiry",      data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_nullable=True),
        ColumnInfo(id="ods-ptd-04", name="has_expired_passport", data_type="SchemaFieldDataTypeClass({'type': BooleanTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-ptd-05", name="document_type",        data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_nullable=True),
        ColumnInfo(id="ods-ptd-06", name="document_number",      data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_nullable=True),
        ColumnInfo(id="ods-ptd-07", name="issuing_country",      data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_nullable=True),
        ColumnInfo(id="ods-ptd-08", name="created_date",         data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_nullable=True),
        ColumnInfo(id="ods-ptd-09", name="modified_date",        data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_nullable=True),
    ],
    tags=[_PII_TAG],
    lineage_id="ods-lineage-006",
    transformation_query=_ODS_TRANSFORM_QUERY,
    query_execution=_ODS_QUERY_EXEC,
    depth=2,
    ai_summary="The ods.all_passengertraveldoc dataset captures travel document details including passport nationality and expiry per passenger, sourced from booking records, enabling downstream passport validation and expired document flagging in the profile pipeline.",
    stats="Columns: 9 | Rows: 50",
    upstream_nodes=[MOCK_NIFI_NODE],
    downstream_nodes=[],
)

ODS_MOCK_ALL_BOOKINGPASSENGER = CentricLineageNode(
    id="ods-mock-007-all-bookingpassenger",
    table_name="all_bookingpassenger",
    full_name="ods.all_bookingpassenger",
    schema_name="ods",
    database_name=None,
    type="table",
    status="healthy",
    source=_ODS_SOURCE,
    columns=[
        ColumnInfo(id="ods-bp-01", name="passenger_id",         data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-bp-02", name="person_id",            data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-bp-03", name="booking_id",           data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-bp-04", name="total_bookings",       data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-bp-05", name="cancellation_count",   data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-bp-06", name="cancellation_rate",    data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True, query_expression="ROUND((cancellation_count * 100.0) / total_bookings, 2)"),
        ColumnInfo(id="ods-bp-07", name="first_booking_date",   data_type="SchemaFieldDataTypeClass({'type': DateTypeClass({})})",   is_nullable=True, query_expression="MIN(b.booking_date)"),
        ColumnInfo(id="ods-bp-08", name="last_booking_date",    data_type="SchemaFieldDataTypeClass({'type': DateTypeClass({})})",   is_nullable=True, query_expression="MAX(b.booking_date)"),
        ColumnInfo(id="ods-bp-09", name="days_since_last_book", data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True, query_expression="DATE_DIFF('day', MAX(b.booking_date), CURRENT_DATE)"),
        ColumnInfo(id="ods-bp-10", name="created_date",         data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True, query_expression="CURRENT_TIMESTAMP"),
        ColumnInfo(id="ods-bp-11", name="modified_date",        data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True, query_expression="CURRENT_TIMESTAMP"),
    ],
    tags=[_PII_TAG],
    lineage_id="ods-lineage-007",
    transformation_query=_ODS_TRANSFORM_QUERY,
    query_execution=_ODS_QUERY_EXEC,
    depth=2,
    ai_summary="The ods.all_bookingpassenger dataset links passengers to bookings and aggregates booking counts, cancellation rates, and recency metrics per person, sourced from reservation systems, forming the core booking behavior feed for downstream ODS profile construction.",
    stats="Columns: 11 | Rows: 50",
    upstream_nodes=[MOCK_NIFI_NODE],
    downstream_nodes=[],
)

ODS_MOCK_ALL_BOOKING = CentricLineageNode(
    id="ods-mock-008-all-booking",
    table_name="all_booking",
    full_name="ods.all_booking",
    schema_name="ods",
    database_name=None,
    type="table",
    status="healthy",
    source=_ODS_SOURCE,
    columns=[
        ColumnInfo(id="ods-b-01", name="booking_id",        data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-b-02", name="booking_channel",   data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-b-03", name="total_revenue",     data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-b-04", name="total_fare",        data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-b-05", name="avg_booking_value", data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-b-06", name="preferred_cabin",   data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-b-07", name="preferred_origin",  data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True, query_expression="MIN(b.origin)"),
        ColumnInfo(id="ods-b-08", name="preferred_dest",    data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True, query_expression="MIN(b.destination)"),
        ColumnInfo(id="ods-b-09", name="booked_via_agent",  data_type="SchemaFieldDataTypeClass({'type': BooleanTypeClass({})})",is_nullable=True, query_expression="CASE WHEN b.agent_id IS NOT NULL THEN TRUE ELSE FALSE END"),
        ColumnInfo(id="ods-b-10", name="agent_id",          data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True, query_expression="MIN(b.agent_id)"),
        ColumnInfo(id="ods-b-11", name="created_date",      data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True, query_expression="CURRENT_TIMESTAMP"),
        ColumnInfo(id="ods-b-12", name="modified_date",     data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True, query_expression="CURRENT_TIMESTAMP"),
    ],
    tags=[_PII_TAG],
    lineage_id="ods-lineage-008",
    transformation_query=_ODS_TRANSFORM_QUERY,
    query_execution=_ODS_QUERY_EXEC,
    depth=2,
    ai_summary="The ods.all_booking dataset contains booking-level financial and preference data including channel, revenue, cabin preference, and origin-destination pairs, sourced from the reservation system, feeding downstream booking behaviour metrics in the ODS profile.",
    stats="Columns: 12 | Rows: 50",
    upstream_nodes=[MOCK_NIFI_NODE],
    downstream_nodes=[],
)

ODS_MOCK_ALL_PASSENGERFEE = CentricLineageNode(
    id="ods-mock-009-all-passengerfee",
    table_name="all_passengerfee",
    full_name="ods.all_passengerfee",
    schema_name="ods",
    database_name=None,
    type="table",
    status="healthy",
    source=_ODS_SOURCE,
    columns=[
        ColumnInfo(id="ods-pf-01", name="passenger_id",          data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pf-02", name="fee_id",                data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pf-03", name="fee_type",              data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pf-04", name="fee_amount",            data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pf-05", name="total_ancillary_spend", data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pf-06", name="currency_code",         data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pf-07", name="created_date",          data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True, query_expression="CURRENT_TIMESTAMP"),
        ColumnInfo(id="ods-pf-08", name="modified_date",         data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
    ],
    tags=[_PII_TAG],
    lineage_id="ods-lineage-009",
    transformation_query=_ODS_TRANSFORM_QUERY,
    query_execution=_ODS_QUERY_EXEC,
    depth=2,
    ai_summary="The ods.all_passengerfee dataset records ancillary fee transactions per passenger sourced from the billing system, aggregating total ancillary spend that feeds downstream revenue metrics in the ODS profile pipeline.",
    stats="Columns: 8 | Rows: 50",
    upstream_nodes=[MOCK_NIFI_NODE],
    downstream_nodes=[],
)

ODS_MOCK_ALL_PASSENGERJSEG = CentricLineageNode(
    id="ods-mock-010-all-passengerjseg",
    table_name="all_passengerjseg",
    full_name="ods.all_passengerjseg",
    schema_name="ods",
    database_name=None,
    type="table",
    status="healthy",
    source=_ODS_SOURCE,
    columns=[
        ColumnInfo(id="ods-pjs-01", name="passenger_id",   data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pjs-02", name="segment_id",     data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pjs-03", name="total_segments", data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True, query_expression="COUNT(DISTINCT pjs.segmentid)"),
        ColumnInfo(id="ods-pjs-04", name="origin",         data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pjs-05", name="destination",    data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pjs-06", name="departure_date", data_type="SchemaFieldDataTypeClass({'type': DateTypeClass({})})",   is_nullable=True),
        ColumnInfo(id="ods-pjs-07", name="cabin_class",    data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pjs-08", name="created_date",   data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pjs-09", name="modified_date",  data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
    ],
    tags=[_PII_TAG],
    lineage_id="ods-lineage-010",
    transformation_query=_ODS_TRANSFORM_QUERY,
    query_execution=_ODS_QUERY_EXEC,
    depth=2,
    ai_summary="The ods.all_passengerjseg dataset records individual flight segment details per passenger sourced from the journey operations system, providing total segment counts and cabin-level flight data used to compute travel activity metrics in the ODS profile.",
    stats="Columns: 9 | Rows: 50",
    upstream_nodes=[MOCK_NIFI_NODE],
    downstream_nodes=[],
)

ODS_MOCK_ALL_PASSENGERJLEG = CentricLineageNode(
    id="ods-mock-011-all-passengerjleg",
    table_name="all_passengerjleg",
    full_name="ods.all_passengerjleg",
    schema_name="ods",
    database_name=None,
    type="table",
    status="healthy",
    source=_ODS_SOURCE,
    columns=[
        ColumnInfo(id="ods-pjl-01", name="passenger_id",       data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pjl-02", name="leg_id",             data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pjl-03", name="segment_id",         data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pjl-04", name="total_flight_hours", data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pjl-05", name="avg_delay_minutes",  data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pjl-06", name="departure_airport",  data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pjl-07", name="arrival_airport",    data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pjl-08", name="flight_duration_min",data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pjl-09", name="delay_minutes",      data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pjl-10", name="created_date",       data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-pjl-11", name="modified_date",      data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
    ],
    tags=[_PII_TAG],
    lineage_id="ods-lineage-011",
    transformation_query=_ODS_TRANSFORM_QUERY,
    query_execution=_ODS_QUERY_EXEC,
    depth=2,
    ai_summary="The ods.all_passengerjleg dataset captures flight leg operational data per passenger including total flight hours and delay minutes, sourced from flight operations logs, enabling downstream computation of travel time and punctuality metrics in the ODS profile.",
    stats="Columns: 11 | Rows: 50",
    upstream_nodes=[MOCK_NIFI_NODE],
    downstream_nodes=[],
)

ODS_MOCK_ALL_BOOKINGCONTACT = CentricLineageNode(
    id="ods-mock-012-all-bookingcontact",
    table_name="all_bookingcontact",
    full_name="ods.all_bookingcontact",
    schema_name="ods",
    database_name=None,
    type="table",
    status="healthy",
    source=_ODS_SOURCE,
    columns=[
        ColumnInfo(id="ods-bc-01", name="booking_id",   data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-bc-02", name="booker_name",  data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-bc-03", name="booker_email", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-bc-04", name="booker_phone", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-bc-05", name="contact_type", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-bc-06", name="created_date", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-bc-07", name="modified_date",data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
    ],
    tags=[_PII_TAG],
    lineage_id="ods-lineage-012",
    transformation_query=_ODS_TRANSFORM_QUERY,
    query_execution=_ODS_QUERY_EXEC,
    depth=2,
    ai_summary="The ods.all_bookingcontact dataset stores contact details of the booking originator per booking sourced from reservation records, providing the booker name and contact fields used to identify third-party or agent-initiated bookings in the ODS profile pipeline.",
    stats="Columns: 7 | Rows: 50",
    upstream_nodes=[MOCK_NIFI_NODE],
    downstream_nodes=[],
)

ODS_MOCK_ALL_AGENT = CentricLineageNode(
    id="ods-mock-013-all-agent",
    table_name="all_agent",
    full_name="ods.all_agent",
    schema_name="ods",
    database_name=None,
    type="table",
    status="healthy",
    source=_ODS_SOURCE,
    columns=[
        ColumnInfo(id="ods-ag-01", name="agent_id",             data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-ag-02", name="preferred_agent_name", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True, query_expression="MIN(a.agent_name)"),
        ColumnInfo(id="ods-ag-03", name="agency_name",          data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True, query_expression="MIN(a.agency_name)"),
        ColumnInfo(id="ods-ag-04", name="agent_type",           data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-ag-05", name="agent_code",           data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True, query_expression="MIN(a.agent_code)"),
        ColumnInfo(id="ods-ag-06", name="country",              data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True, query_expression="MIN(a.country)"),
        ColumnInfo(id="ods-ag-07", name="is_active",            data_type="SchemaFieldDataTypeClass({'type': BooleanTypeClass({})})",is_nullable=True, query_expression="CASE WHEN MAX(b.booking_id) IS NOT NULL THEN TRUE ELSE FALSE END"),
        ColumnInfo(id="ods-ag-08", name="created_date",         data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True, query_expression="CURRENT_TIMESTAMP"),
        ColumnInfo(id="ods-ag-09", name="modified_date",        data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
    ],
    tags=[_PII_TAG],
    lineage_id="ods-lineage-013",
    transformation_query=_ODS_TRANSFORM_QUERY,
    query_execution=_ODS_QUERY_EXEC,
    depth=2,
    ai_summary="The ods.all_agent dataset captures travel agent records sourced from the agency management system, providing preferred agent name and agency details that are used to attribute agent-assisted bookings in the downstream ODS profile.",
    stats="Columns: 9 | Rows: 50",
    upstream_nodes=[MOCK_NIFI_NODE],
    downstream_nodes=[],
)

# Ordered list of all ODS upstream mock nodes
ODS_UPSTREAM_MOCK_NODES: List[CentricLineageNode] = [
    ODS_MOCK_ALL_PERSON,
    ODS_MOCK_ALL_PERSONNAME,
    ODS_MOCK_ALL_PERSONEMAIL,
    ODS_MOCK_ALL_PERSONPHONE,
    ODS_MOCK_ALL_PERSONADDRESS,
    ODS_MOCK_ALL_PASSENGERTRAVELDOC,
    ODS_MOCK_ALL_BOOKINGPASSENGER,
    ODS_MOCK_ALL_BOOKING,
    ODS_MOCK_ALL_PASSENGERFEE,
    ODS_MOCK_ALL_PASSENGERJSEG,
    ODS_MOCK_ALL_PASSENGERJLEG,
    ODS_MOCK_ALL_BOOKINGCONTACT,
    ODS_MOCK_ALL_AGENT,
]
ODS_UPSTREAM_MOCK_IDS: List[str] = [n.id for n in ODS_UPSTREAM_MOCK_NODES]

# Mock downstream node for ods_profiles — injected when any ODS upstream table is the node
ODS_MOCK_ODS_PROFILES_DOWNSTREAM = CentricLineageNode(
    id="3512b23c-1996-4499-8615-705ff471c91d",
    table_name="ods_profiles",
    full_name="ods.ods_profiles",
    schema_name="ods",
    database_name=None,
    type="table",
    status="healthy",
    source=_ODS_SOURCE,
    columns=[
        ColumnInfo(id="ods-prof-01", name="person_id",            data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-02", name="date_of_birth",        data_type="SchemaFieldDataTypeClass({'type': DateTypeClass({})})",   is_nullable=True),
        ColumnInfo(id="ods-prof-03", name="gender",               data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-04", name="nationality",          data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-05", name="title",                data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-06", name="first_name",           data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-07", name="last_name",            data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-08", name="full_name",            data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-09", name="primary_email",        data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True, query_expression="MIN(pe.primary_email)"),
        ColumnInfo(id="ods-prof-10", name="email_opt_in",         data_type="SchemaFieldDataTypeClass({'type': BooleanTypeClass({})})",is_nullable=True),
        ColumnInfo(id="ods-prof-11", name="primary_phone",        data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-12", name="sms_opt_in",           data_type="SchemaFieldDataTypeClass({'type': BooleanTypeClass({})})",is_nullable=True, query_expression="MIN(pp.sms_opt_in)"),
        ColumnInfo(id="ods-prof-13", name="home_city",            data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-14", name="home_country",         data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-15", name="home_address_full",    data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-16", name="passport_nationality", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-17", name="passport_expiry",      data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-18", name="has_expired_passport", data_type="SchemaFieldDataTypeClass({'type': BooleanTypeClass({})})",is_nullable=True),
        ColumnInfo(id="ods-prof-19", name="total_bookings",       data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True, query_expression="COUNT(DISTINCT bp.booking_id)"),
        ColumnInfo(id="ods-prof-20", name="cancellation_count",   data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True, query_expression="COUNT(DISTINCT CASE WHEN bp.cancellation_rate > 0 THEN bp.booking_id END)"),
        ColumnInfo(id="ods-prof-21", name="total_revenue",        data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True, query_expression="SUM(b.total_revenue)"),
        ColumnInfo(id="ods-prof-22", name="total_fare",           data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True, query_expression="SUM(b.total_fare)"),
        ColumnInfo(id="ods-prof-23", name="avg_booking_value",    data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-24", name="first_booking_date",   data_type="SchemaFieldDataTypeClass({'type': DateTypeClass({})})",   is_nullable=True),
        ColumnInfo(id="ods-prof-25", name="last_booking_date",    data_type="SchemaFieldDataTypeClass({'type': DateTypeClass({})})",   is_nullable=True),
        ColumnInfo(id="ods-prof-26", name="days_since_last_book", data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-27", name="preferred_cabin",      data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-28", name="preferred_origin",     data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-29", name="preferred_dest",       data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-30", name="booking_channel",      data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-31", name="booked_via_agent",     data_type="SchemaFieldDataTypeClass({'type': BooleanTypeClass({})})",is_nullable=True),
        ColumnInfo(id="ods-prof-32", name="total_ancillary_spend",data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-33", name="total_segments",       data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True, query_expression="COUNT(DISTINCT pjs.segmentid)"),
        ColumnInfo(id="ods-prof-34", name="total_flight_hours",   data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-35", name="avg_delay_minutes",    data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-36", name="booker_name",          data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="ods-prof-37", name="preferred_agent_name", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
    ],
    tags=[_PII_TAG],
    lineage_id="78ae3e2f-202a-4fc4-b682-33fe5f561664",
    transformation_query=_ODS_TRANSFORM_QUERY,
    query_execution=_ODS_QUERY_EXEC,
    depth=1,
    ai_summary="The ods.ods_profiles dataset captures foundational personal information such as identity, contact details, and preferences, sourced from upstream systems, serving as a critical reference for enriching and validating downstream data processes within the pipeline.",
    stats="Columns: 37 | Rows: 31",
    upstream_nodes=[],
    downstream_nodes=[],
)

# ── Mock node 1: transaction ──────────────────────────────────────────────────
MOCK_TRANSACTION_ID = "b12f9e3a-7c44-4c91-9f12-3c8c9c2a1111"

MOCK_TRANSACTION_NODE = VisualNode(
    id=MOCK_TRANSACTION_ID,
    table_name="transaction",
    full_name="operational-data-store.transaction",
    schema_name="operational-data-store",
    database_name=None,
    type="table",
    status="unhealthy",
    source=SourceInfo(
        id="36ddfa2f-c9bf-4e9f-bdfb-69189f786606",
        name="run-test-athena",
        source_type="athena",
    ),
    columns=[
        ColumnInfo(id="col-001", name="transactionid",     data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})",  is_primary_key=True,  is_foreign_key=False, is_nullable=False),
        ColumnInfo(id="col-002", name="bookingid",         data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})",  is_primary_key=False, is_foreign_key=True,  is_nullable=True),
        ColumnInfo(id="col-003", name="agentid",           data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})",  is_primary_key=False, is_foreign_key=True,  is_nullable=True),
        ColumnInfo(id="col-004", name="transactionamount", data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True),
        ColumnInfo(id="col-005", name="address",           data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True),
        ColumnInfo(id="col-006", name="transactiontype",   data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True),
        ColumnInfo(id="col-007", name="transactionstatus", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True),
        ColumnInfo(id="col-008", name="paymentmethod",     data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True),
        ColumnInfo(id="col-009", name="transactiondate",   data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True),
        ColumnInfo(id="col-010", name="journey_time",      data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True),
        ColumnInfo(id="col-011", name="operationtype",     data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True),
        ColumnInfo(id="col-012", name="load_type",         data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True),
        ColumnInfo(id="col-013", name="filename",          data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True),
        ColumnInfo(id="col-014", name="ingestionsequence", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True),
        ColumnInfo(id="col-015", name="createdutc",        data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True),
        ColumnInfo(id="col-016", name="modifiedutc",       data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})",  is_primary_key=False, is_foreign_key=False, is_nullable=True),
    ],
    tags=[TagInfo(id="tag-001", name="Financial", color="#FF9800", tag_type="classification")],
    lineage_id="r9b7tb7e-bn86-4388-bd89-3324caa06866",
    transformation_query=(
        "CREATE TABLE booking_transaction\n"
        "COMMENT 'Derived from: booking, transaction tables'\n"
        "WITH (\n"
        "  format = 'PARQUET',\n"
        "  external_location = 's3://infinity-gov-test/data/data-lineage/booking_transaction/'\n"
        ") AS\n"
        "SELECT\n"
        "    b.bookingid,\n"
        "    b.bookingtype,\n"
        "    b.bookingutc,\n"
        "    b.currencycode,\n\n"
        "    t.transactionid,\n"
        "    t.transactionamount,\n"
        "    t.transactiontype,\n"
        "    t.transactionstatus,\n"
        "    t.paymentmethod,\n"
        "    t.journey_time,\n"
        "    t.transactiondate\n\n"
        "FROM booking b\n"
        "LEFT JOIN transaction t ON b.bookingid = t.bookingid"
    ),
    query_execution=QueryExecutionInfo(
        query_execution_id="g3b7tb7s-bn90-5378-bd89-3324caa89071",
        query_start_time="2026-03-19T05:00:00.000000+00:00",
        query_end_time="2026-03-19T05:00:01.200000+00:00",
        query_runtime_ms=1200,
        data_scanned_bytes=45200,
        query_status="FAILURE",
        engine_version="Athena engine version 3",
        s3_output_location="s3://athena-query-results-tmp-123/transaction/",
    ),
    column_mappings=[],
    depth=1,
    ai_summary="Convert or cast the date-formatted input into a string (VARCHAR) to align with the schema and ensure smooth data ingestion.",
    stats="Columns: 16 | Rows: 0",
    notes="The journey_time column is defined as VARCHAR(256), while the incoming data is in a date format, causing a type mismatch during ingestion.",
)

# ── Mock node 2: inventory_management ────────────────────────────────────────
MOCK_INVENTORY_ID = "5f2c7b9e-91c2-4d5b-8c6a-3f7a1b2e9d44"

MOCK_INVENTORY_NODE = VisualNode(
    id=MOCK_INVENTORY_ID,
    table_name="inventory_management",
    full_name="operational-data-store.inventory_management",
    schema_name="operational-data-store",
    database_name=None,
    type="table",
    status="healthy",
    source=SourceInfo(
        id="36ddfa2f-c9bf-4e9f-bdfb-69189f786606",
        name="run-test-athena",
        source_type="athena",
    ),
    columns=[
        ColumnInfo(id="c1",  name="inventoryid",        data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="c2",  name="productid",          data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_foreign_key=True, is_nullable=True),
        ColumnInfo(id="c3",  name="productname",        data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="c4",  name="category",           data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="c5",  name="stockquantity",      data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="c6",  name="reorderlevel",       data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="c7",  name="warehouse_location", data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="c8",  name="supplierid",         data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_foreign_key=True, is_nullable=True),
        ColumnInfo(id="c9",  name="lastrestockdate",    data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="c10", name="journaltime",        data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="c11", name="transactionid",      data_type="SchemaFieldDataTypeClass({'type': NumberTypeClass({})})", is_nullable=True),
        ColumnInfo(id="c12", name="operationtype",      data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="c13", name="load_type",          data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="c14", name="filename",           data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="c15", name="ingestionsequence",  data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="c16", name="createdutc",         data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
        ColumnInfo(id="c17", name="modifiedutc",        data_type="SchemaFieldDataTypeClass({'type': StringTypeClass({})})", is_nullable=True),
    ],
    tags=[TagInfo(id="0475716c-9715-4167-aa6e-deb655ec8809", name="Operational", color="#4CAF50", tag_type="classification")],
    lineage_id="a1b2c3d4-e5f6-7890-abcd-123456789000",
    transformation_query=(
        "CREATE TABLE inventory_summary\n"
        "COMMENT 'Derived from: inventory_management, supplier tables'\n"
        "WITH (\n"
        "  format = 'PARQUET',\n"
        "  external_location = 's3://infinity-gov-test/data/data-lineage/inventory_summary/'\n"
        ") AS\n"
        "SELECT\n"
        "    i.inventoryid,\n"
        "    i.productid,\n"
        "    i.productname,\n"
        "    i.category,\n"
        "    i.stockquantity,\n"
        "    i.reorderlevel,\n"
        "    i.warehouse_location,\n"
        "    s.suppliername\n"
        "FROM inventory_management i\n"
        "LEFT JOIN supplier s ON i.supplierid = s.supplierid"
    ),
    query_execution=QueryExecutionInfo(
        query_execution_id="b12d29da-3ee2-4213-9dc3-77c3ce6df681",
        query_start_time="2026-03-19T04:45:40.310000+00:00",
        query_end_time="2026-03-19T04:45:42.619000+00:00",
        query_runtime_ms=2309,
        data_scanned_bytes=45226,
        query_status="SUCCEEDED",
        engine_version="Athena engine version 3",
        s3_output_location="s3://athena-query-results-tmp-123/Unsaved/2026/03/19/tables/b12d29da-3ee2-4213-9dc3-77c3ce6df681",
    ),
    column_mappings=[],
    depth=1,
    ai_summary=(
        "The operational-data-store.inventory_management dataset captures detailed inventory "
        "records including product stock levels, supplier associations, and warehouse locations, "
        "serving as a critical dataset for supply chain monitoring, stock optimization, and "
        "operational analytics within the data pipeline."
    ),
    stats="Columns: 17 | Rows: 75",
)

# Ordered list of all mock nodes to inject for trigger tables
MOCK_NODES: List[VisualNode] = [MOCK_TRANSACTION_NODE, MOCK_INVENTORY_NODE]
MOCK_IDS: List[str]          = [MOCK_TRANSACTION_ID,   MOCK_INVENTORY_ID]


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _fetch_catalog_node(db, catalog_id: str) -> Optional[Dict]:
    """Return full catalog row joined with data_sources."""
    row = await db.fetch_one(
        """
        SELECT
            c.id, c.table_name, c.full_name, c.schema_name, c.database_name,
            c.type, c.status, c.row_count,
            ds.id   AS source_id,
            ds.name AS source_name,
            ds.source_type
        FROM catalogs c
        LEFT JOIN data_sources ds ON ds.id = c.source_id
        WHERE c.id = $1
        """,
        catalog_id,
    )
    return dict(row) if row else None


async def _fetch_columns(db, catalog_id: str) -> List[ColumnInfo]:
    rows = await db.fetch_all(
        """
        SELECT
            col.id,
            col.name,
            col.data_type,
            col.is_primary_key,
            col.is_foreign_key,
            col.is_nullable,
            cq.query_expression
        FROM columns col
        LEFT JOIN column_queries cq
            ON LOWER(cq.column_name) = LOWER(col.name)
        WHERE col.catalog_id = $1
        ORDER BY col.ordinal_position NULLS LAST, col.name
        """,
        catalog_id,
    )
    return [
        ColumnInfo(
            id=str(r["id"]),
            name=r["name"],
            data_type=r.get("data_type"),
            is_primary_key=bool(r.get("is_primary_key")),
            is_foreign_key=bool(r.get("is_foreign_key")),
            is_nullable=bool(r.get("is_nullable", True)),
            query_expression=r.get("query_expression"),
        )
        for r in rows
    ]


async def _fetch_tags(db, catalog_id: str) -> List[TagInfo]:
    rows = await db.fetch_all(
        """
        SELECT t.id, t.name, t.color, t.tag_type
        FROM   tags t
        JOIN   tag_catalog_assignments tca ON tca.tag_id = t.id
        WHERE  tca.catalog_id = $1
        """,
        catalog_id,
    )
    return [
        TagInfo(
            id=str(r["id"]),
            name=r["name"],
            color=r.get("color"),
            tag_type=r.get("tag_type"),
        )
        for r in rows
    ]


async def _fetch_col_mappings(db, lineage_id: str) -> List[ColumnMapping]:
    rows = await db.fetch_all(
        """
        SELECT
            lcm.upstream_column_id,   uc.name AS upstream_column_name,
            lcm.downstream_column_id, dc.name AS downstream_column_name
        FROM   lineage_column_mappings lcm
        LEFT JOIN columns uc ON uc.id = lcm.upstream_column_id
        LEFT JOIN columns dc ON dc.id = lcm.downstream_column_id
        WHERE  lcm.lineage_id = $1
        """,
        lineage_id,
    )
    return [
        ColumnMapping(
            upstream_column_id=str(r["upstream_column_id"]),
            upstream_column_name=r.get("upstream_column_name"),
            downstream_column_id=str(r["downstream_column_id"]),
            downstream_column_name=r.get("downstream_column_name"),
        )
        for r in rows
    ]


def _build_query_execution_info(row: Dict) -> Optional[QueryExecutionInfo]:
    fields = {
        "query_execution_id": row.get("query_execution_id"),
        "query_start_time": (
            row["query_start_time"].isoformat()
            if row.get("query_start_time") else None
        ),
        "query_end_time": (
            row["query_end_time"].isoformat()
            if row.get("query_end_time") else None
        ),
        "query_runtime_ms": row.get("query_runtime_ms"),
        "data_scanned_bytes": row.get("data_scanned_bytes"),
        "query_status": row.get("query_status"),
        "engine_version": row.get("engine_version"),
        "s3_output_location": row.get("s3_output_location"),
    }
    if all(v is None for v in fields.values()):
        return None
    return QueryExecutionInfo(**fields)


async def _generate_ai_summary(
    llm, node: Dict, upstream: List[str], downstream: List[str]
) -> str:
    columns = ", ".join([c["name"] for c in node.get("columns", [])[:10]])
    upstream_str   = ", ".join(upstream)   if upstream   else "None"
    downstream_str = ", ".join(downstream) if downstream else "None"

    prompt = f"""
You are a senior data platform architect.

Describe the role of this dataset in the data pipeline.

Dataset:
{node.get("full_name")}

Key Columns:
{columns}

Upstream Tables:
{upstream_str}

Downstream Tables:
{downstream_str}

Explain:
- what the dataset represents
- where its data originates
- how downstream datasets use it
- its role in the pipeline

Respond in only one concise sentence.
Note:
-- Provide a Short Summary do not exceed 50 words. Be concise and professional.
-- The response should be in a short paragraph format, suitable for display in a data catalog entry.
   Avoid technical jargon and focus on key insights about the dataset's content and relevance.
"""
    result = await llm.ainvoke(prompt)
    return result.content


async def _build_visual_node(
    db,
    llm,
    catalog_id: str,
    lineage_row: Optional[Dict],
    depth: int,
) -> Optional["VisualNode"]:
    data = await _fetch_catalog_node(db, catalog_id)
    if not data:
        return None

    lineage_id           = str(lineage_row["id"])             if lineage_row else None
    transformation_query = lineage_row.get("transformation_query") if lineage_row else None
    query_execution      = _build_query_execution_info(lineage_row) if lineage_row else None

    columns      = await _fetch_columns(db, catalog_id)
    tags         = await _fetch_tags(db, catalog_id)
    col_mappings = await _fetch_col_mappings(db, lineage_id) if lineage_id else []
    column_count = len(columns)
    row_count    = data.get("row_count")
    row_count_str = f"{row_count:,}" if row_count is not None else "N/A"
    status_text  = f"Columns: {column_count} | Rows: {row_count_str}"

    upstream_tables   = []
    downstream_tables = []
    if lineage_id and transformation_query:
        upstream_tables.append("upstream dependency")
        downstream_tables.append("downstream dependency")

    ai_summary = await _generate_ai_summary(
        llm,
        {
            "full_name": data.get("full_name"),
            "columns": [c.dict() for c in columns],
        },
        upstream=upstream_tables,
        downstream=downstream_tables,
    )

    source = None
    if data.get("source_id"):
        source = SourceInfo(
            id=str(data["source_id"]),
            name=data["source_name"] or "",
            source_type=data["source_type"] or "",
        )

    return VisualNode(
        id=str(data["id"]),
        table_name=data["table_name"],
        full_name=data.get("full_name"),
        schema_name=data.get("schema_name"),
        database_name=data.get("database_name"),
        type=data.get("type", "table"),
        status=data.get("status", "healthy"),
        source=source,
        columns=columns,
        tags=tags,
        lineage_id=lineage_id,
        transformation_query=transformation_query,
        query_execution=query_execution,
        column_mappings=col_mappings,
        depth=depth,
        ai_summary=ai_summary,
        stats=status_text,
    )


async def _traverse(
    db,
    catalog_id: str,
    direction: str,
    max_depth: int,
    current_depth: int,
    visited: set,
    root_table_name: str = "",
) -> List[VisualNode]:
    """
    BFS/DFS returning a flat, depth-ordered list of VisualNode objects.

    Mock injection rules (all at current_depth == 1):
      - upstream + root in MOCK_TRIGGER_TABLE_NAMES       → inject MOCK_NODES
      - upstream + root == 'ods_profiles'                 → inject ODS_UPSTREAM_MOCK_NODES + NiFi + MSSQL
      - upstream + root in NIFI_UPSTREAM_TABLE_NAMES      → inject NiFi + MSSQL visual nodes
      - downstream + root in ODS_UPSTREAM_TABLE_NAMES     → inject ods_profiles downstream mock
    """
    if current_depth > max_depth:
        return []

    results: List[VisualNode] = []

    # ── Inject all mock nodes at depth-1 for trigger tables ─────────────────
    if (
        direction == "upstream"
        and current_depth == 1
        and root_table_name.lower() in MOCK_TRIGGER_TABLE_NAMES
    ):
        for mock_id, mock_node in zip(MOCK_IDS, MOCK_NODES):
            if mock_id not in visited:
                visited.add(mock_id)
                mock = mock_node.copy(deep=True)
                mock.depth = current_depth
                results.append(mock)

    # ── Inject ODS upstream tables when root is ods_profiles ─────────────────
    if (
        direction == "upstream"
        and current_depth == 1
        and root_table_name.lower() == "ods_profiles"
    ):
        for mock_id, mock_node in zip(ODS_UPSTREAM_MOCK_IDS, ODS_UPSTREAM_MOCK_NODES):
            if mock_id not in visited:
                visited.add(mock_id)
                visual_mock = VisualNode(
                    id=mock_node.id,
                    table_name=mock_node.table_name,
                    full_name=mock_node.full_name,
                    schema_name=mock_node.schema_name,
                    database_name=mock_node.database_name,
                    type=mock_node.type,
                    status=mock_node.status,
                    source=mock_node.source,
                    columns=mock_node.columns,
                    tags=mock_node.tags,
                    lineage_id=mock_node.lineage_id,
                    transformation_query=mock_node.transformation_query,
                    query_execution=mock_node.query_execution,
                    column_mappings=[],
                    depth=current_depth,
                    ai_summary=mock_node.ai_summary,
                    stats=mock_node.stats,
                )
                results.append(visual_mock)
        # Also inject NiFi and MSSQL as further upstreams visible in the flat list
        nifi_v = MOCK_NIFI_VISUAL_NODE.copy(deep=True)
        nifi_v.depth = current_depth + 1
        if nifi_v.id not in visited:
            visited.add(nifi_v.id)
            results.append(nifi_v)
        mssql_v = MOCK_MSSQL_VISUAL_NODE.copy(deep=True)
        mssql_v.depth = current_depth + 2
        if mssql_v.id not in visited:
            visited.add(mssql_v.id)
            results.append(mssql_v)

    # ── Inject NiFi + MSSQL for ODS and SFMC raw tables ─────────────────────
    if (
        direction == "upstream"
        and current_depth == 1
        and root_table_name.lower() in NIFI_UPSTREAM_TABLE_NAMES
    ):
        nifi_v = MOCK_NIFI_VISUAL_NODE.copy(deep=True)
        nifi_v.depth = current_depth
        if nifi_v.id not in visited:
            visited.add(nifi_v.id)
            results.append(nifi_v)
        mssql_v = MOCK_MSSQL_VISUAL_NODE.copy(deep=True)
        mssql_v.depth = current_depth + 1
        if mssql_v.id not in visited:
            visited.add(mssql_v.id)
            results.append(mssql_v)

    # ── Inject CIAM API + Lambda for CIAM layer tables ──────────────────────
    if (
        direction == "upstream"
        and current_depth == 1
        and root_table_name.lower() in CIAM_UPSTREAM_TABLE_NAMES
    ):
        lambda_v = MOCK_CIAM_LAMBDA_VISUAL_NODE.copy(deep=True)
        lambda_v.depth = current_depth
        if lambda_v.id not in visited:
            visited.add(lambda_v.id)
            results.append(lambda_v)
        api_v = MOCK_CIAM_API_VISUAL_NODE.copy(deep=True)
        api_v.depth = current_depth + 1
        if api_v.id not in visited:
            visited.add(api_v.id)
            results.append(api_v)

    # ── Inject ods_profiles as downstream when root is an ODS upstream table ──
    if (
        direction == "downstream"
        and current_depth == 1
        and root_table_name.lower() in ODS_UPSTREAM_TABLE_NAMES
    ):
        mock_ds = ODS_MOCK_ODS_PROFILES_DOWNSTREAM
        if mock_ds.id not in visited:
            visited.add(mock_ds.id)
            visual_mock = VisualNode(
                id=mock_ds.id,
                table_name=mock_ds.table_name,
                full_name=mock_ds.full_name,
                schema_name=mock_ds.schema_name,
                database_name=mock_ds.database_name,
                type=mock_ds.type,
                status=mock_ds.status,
                source=mock_ds.source,
                columns=mock_ds.columns,
                tags=mock_ds.tags,
                lineage_id=mock_ds.lineage_id,
                transformation_query=mock_ds.transformation_query,
                query_execution=mock_ds.query_execution,
                column_mappings=[],
                depth=current_depth,
                ai_summary=mock_ds.ai_summary,
                stats=mock_ds.stats,
            )
            results.append(visual_mock)

    # ── Normal DB traversal ──────────────────────────────────────────────────
    if direction == "downstream":
        rows = await db.fetch_all(
            """
            SELECT
                id,
                downstream_catalog_id      AS next_id,
                transformation_query,
                query_execution_id,
                query_start_time,
                query_end_time,
                query_runtime_ms,
                data_scanned_bytes,
                query_status,
                engine_version,
                s3_output_location
            FROM   table_lineage
            WHERE  upstream_catalog_id = $1 AND is_active = TRUE
            """,
            catalog_id,
        )
    else:
        rows = await db.fetch_all(
            """
            SELECT
                id,
                upstream_catalog_id        AS next_id,
                transformation_query,
                query_execution_id,
                query_start_time,
                query_end_time,
                query_runtime_ms,
                data_scanned_bytes,
                query_status,
                engine_version,
                s3_output_location
            FROM   table_lineage
            WHERE  downstream_catalog_id = $1 AND is_active = TRUE
            """,
            catalog_id,
        )

    for row in rows:
        row_dict = dict(row)
        next_id  = str(row_dict["next_id"])
        if next_id in visited:
            continue
        visited.add(next_id)

        node = await _build_visual_node(
            db,
            llm,
            catalog_id=next_id,
            lineage_row=row_dict,
            depth=current_depth,
        )
        if node:
            results.append(node)
            deeper = await _traverse(
                db,
                next_id,
                direction,
                max_depth,
                current_depth + 1,
                visited,
                root_table_name=root_table_name,
            )
            results.extend(deeper)

    return results


async def _build_centric_hierarchy(
    db,
    catalog_id: str,
    traverse_dir: str,  # "upstream", "downstream", or "both"
    max_depth: int,
    current_depth: int,
    visited: set,
    lineage_id: Optional[str] = None,
    transformation_query: Optional[str] = None,
    query_execution_info: Optional[QueryExecutionInfo] = None,
) -> Optional[CentricLineageNode]:
    """Recursively builds the hierarchy from the centric_lineage table."""
    if current_depth > max_depth:
        return None

    if catalog_id in visited:
        return None
    visited.add(catalog_id)

    data = await _fetch_catalog_node(db, catalog_id)
    if not data:
        return None

    tags = await _fetch_tags(db, catalog_id)
    columns = await _fetch_columns(db, catalog_id)

    row_count = data.get("row_count")
    row_count_str = f"{row_count:,}" if row_count is not None else "N/A"

    col_row = await db.fetch_one("SELECT COUNT(*) FROM columns WHERE catalog_id = $1", catalog_id)
    column_count = col_row[0] if col_row else 0
    status_text = f"Columns: {column_count} | Rows: {row_count_str}"

    source = None
    if data.get("source_id"):
        source = SourceInfo(
            id=str(data["source_id"]),
            name=data["source_name"] or "",
            source_type=data["source_type"] or "",
        )

    upstream_tables = ["upstream dependency"] if traverse_dir in ("upstream", "both") else []
    downstream_tables = ["downstream dependency"] if traverse_dir in ("downstream", "both") else []

    ai_summary = await _generate_ai_summary(
        llm,
        {
            "full_name": data.get("full_name"),
            "columns": [c.dict() for c in columns],
        },
        upstream=upstream_tables,
        downstream=downstream_tables,
    )

    node = CentricLineageNode(
        id=str(data["id"]),
        table_name=data["table_name"],
        full_name=data.get("full_name"),
        schema_name=data.get("schema_name"),
        database_name=data.get("database_name"),
        type=data.get("type", "table"),
        status=data.get("status", "healthy"),
        source=source,
        columns=columns,
        tags=tags,
        lineage_id=lineage_id,
        transformation_query=transformation_query,
        query_execution=query_execution_info,
        depth=current_depth,
        ai_summary=ai_summary,
        stats=status_text,
        upstream_nodes=[],
        downstream_nodes=[]
    )

    # ── UPSTREAM traversal ────────────────────────────────────────────────────
    if traverse_dir in ("upstream", "both"):

        # ── Inject all mock nodes for trigger tables (any depth) ──────────────
        if data["table_name"].lower() in MOCK_TRIGGER_TABLE_NAMES:
            for mock_id, mock_node in zip(MOCK_IDS, MOCK_NODES):
                if mock_id not in visited:
                    visited.add(mock_id)
                    centric_mock = CentricLineageNode(
                        id=mock_node.id,
                        table_name=mock_node.table_name,
                        full_name=mock_node.full_name,
                        schema_name=mock_node.schema_name,
                        database_name=mock_node.database_name,
                        type=mock_node.type,
                        status=mock_node.status,
                        source=mock_node.source,
                        columns=mock_node.columns,
                        tags=mock_node.tags,
                        lineage_id=mock_node.lineage_id,
                        transformation_query=mock_node.transformation_query,
                        query_execution=mock_node.query_execution,
                        depth=current_depth + 1,
                        ai_summary=mock_node.ai_summary,
                        stats=mock_node.stats,
                        notes=mock_node.notes,
                        upstream_nodes=[],
                        downstream_nodes=[]
                    )
                    node.upstream_nodes.append(centric_mock)

        # ── Inject ODS upstream tables when node is ods_profiles (any depth) ──
        if data["table_name"].lower() == "ods_profiles":
            for mock_id, mock_node in zip(ODS_UPSTREAM_MOCK_IDS, ODS_UPSTREAM_MOCK_NODES):
                if mock_id not in visited:
                    visited.add(mock_id)
                    injected = mock_node.copy(deep=True)
                    injected.depth = current_depth + 1
                    # Each ODS mock already has MOCK_NIFI_NODE (with MOCK_MSSQL_NODE nested)
                    # in its upstream_nodes — so the full chain is automatically present.
                    node.upstream_nodes.append(injected)

        # ── Inject NiFi + MSSQL for ODS and SFMC raw tables (any depth) ──────
        if data["table_name"].lower() in NIFI_UPSTREAM_TABLE_NAMES:
            nifi_mock = MOCK_NIFI_NODE.copy(deep=True)
            nifi_mock.depth = current_depth + 1
            mssql_mock = MOCK_MSSQL_NODE.copy(deep=True)
            mssql_mock.depth = current_depth + 2
            nifi_mock.upstream_nodes = [mssql_mock]
            if nifi_mock.id not in visited:
                visited.add(nifi_mock.id)
                node.upstream_nodes.append(nifi_mock)

        # ── Inject CIAM API + Lambda for CIAM tables (any depth) ─────────────
        if data["table_name"].lower() in CIAM_UPSTREAM_TABLE_NAMES:
            lambda_mock = MOCK_CIAM_LAMBDA_NODE.copy(deep=True)
            lambda_mock.depth = current_depth + 1
            api_mock = MOCK_CIAM_API_NODE.copy(deep=True)
            api_mock.depth = current_depth + 2
            lambda_mock.upstream_nodes = [api_mock]
            if lambda_mock.id not in visited:
                visited.add(lambda_mock.id)
                node.upstream_nodes.append(lambda_mock)

        rows = await db.fetch_all(
            """
            SELECT c.id, c.upstream_catalog_id AS next_id, c.upstream_query_logic,
                   tl.query_execution_id, tl.query_start_time, tl.query_end_time,
                   tl.query_runtime_ms, tl.data_scanned_bytes, tl.query_status,
                   tl.engine_version, tl.s3_output_location
            FROM centric_lineage c
            LEFT JOIN table_lineage tl
              ON tl.downstream_catalog_id = c.base_catalog_id
             AND tl.upstream_catalog_id = c.upstream_catalog_id
             AND tl.is_active = TRUE
            WHERE c.base_catalog_id = $1 AND c.upstream_catalog_id IS NOT NULL
            """,
            catalog_id
        )
        for row in rows:
            exec_info = _build_query_execution_info(dict(row)) if row.get("query_execution_id") else None
            child = await _build_centric_hierarchy(
                db, str(row["next_id"]), "upstream", max_depth, current_depth + 1, visited.copy(),
                str(row["id"]), row.get("upstream_query_logic"), exec_info
            )
            if child:
                node.upstream_nodes.append(child)

    # ── DOWNSTREAM traversal ──────────────────────────────────────────────────
    if traverse_dir in ("downstream", "both"):

        # ── Inject ods_profiles as downstream when node is an ODS upstream table (any depth) ──
        if data["table_name"].lower() in ODS_UPSTREAM_TABLE_NAMES:
            mock_ds = ODS_MOCK_ODS_PROFILES_DOWNSTREAM
            if mock_ds.id not in visited:
                visited.add(mock_ds.id)
                injected_ds = mock_ds.copy(deep=True)
                injected_ds.depth = current_depth + 1
                node.downstream_nodes.append(injected_ds)

        rows = await db.fetch_all(
            """
            SELECT c.id, c.downstream_catalog_id AS next_id, c.downstream_query_logic,
                   tl.query_execution_id, tl.query_start_time, tl.query_end_time,
                   tl.query_runtime_ms, tl.data_scanned_bytes, tl.query_status,
                   tl.engine_version, tl.s3_output_location
            FROM centric_lineage c
            LEFT JOIN table_lineage tl
              ON tl.upstream_catalog_id = c.base_catalog_id
             AND tl.downstream_catalog_id = c.downstream_catalog_id
             AND tl.is_active = TRUE
            WHERE c.base_catalog_id = $1 AND c.downstream_catalog_id IS NOT NULL
            """,
            catalog_id
        )
        for row in rows:
            exec_info = _build_query_execution_info(dict(row)) if row.get("query_execution_id") else None
            child = await _build_centric_hierarchy(
                db, str(row["next_id"]), "downstream", max_depth, current_depth + 1, visited.copy(),
                str(row["id"]), row.get("downstream_query_logic"), exec_info
            )
            if child:
                node.downstream_nodes.append(child)

    return node


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/api/v1/lineage-visual/{catalog_id}",
    response_model=VisualLineageResponse,
    summary="Visual lineage graph for a table",
    description=(
        "Returns the root table with its columns (including any derived "
        "query_expression from column_queries), source info, and tags, "
        "plus flat lists of upstream and downstream nodes. "
        "Each non-root node includes a `query_execution` block sourced from "
        "the table_lineage edge. "
        "Use `depth` (1–6, default 2) to control traversal depth and "
        "`direction` (upstream | downstream | both) to limit the graph."
    ),
)
async def get_visual_lineage(
    catalog_id: str,
    depth:     int = Query(2, ge=1, le=6, description="Traversal depth (1-6), default 2"),
    direction: str = Query("both", enum=["upstream", "downstream", "both"]),
):
    from app import db, logger, log_api_action
    try:
        root_data = await _fetch_catalog_node(db, catalog_id)
        if not root_data:
            raise HTTPException(404, f"Catalog '{catalog_id}' not found")

        root_table_name = root_data.get("table_name", "")

        root_columns  = await _fetch_columns(db, catalog_id)
        root_tags     = await _fetch_tags(db, catalog_id)
        column_count  = len(root_columns)
        row_count     = root_data.get("row_count")
        row_count_str = f"{row_count:,}" if row_count is not None else "N/A"
        status_text   = f"Columns: {column_count} | Rows: {row_count_str}"

        root_source = None
        if root_data.get("source_id"):
            root_source = SourceInfo(
                id=str(root_data["source_id"]),
                name=root_data["source_name"] or "",
                source_type=root_data["source_type"] or "",
            )

        root_summary = await _generate_ai_summary(
            llm,
            {
                "full_name": root_data.get("full_name"),
                "columns": [c.dict() for c in root_columns],
            },
            upstream=[],
            downstream=[],
        )

        root_node = VisualNode(
            id=str(root_data["id"]),
            table_name=root_table_name,
            full_name=root_data.get("full_name"),
            schema_name=root_data.get("schema_name"),
            database_name=root_data.get("database_name"),
            type=root_data.get("type", "table"),
            status=root_data.get("status", "healthy"),
            source=root_source,
            columns=root_columns,
            tags=root_tags,
            depth=0,
            ai_summary=root_summary,
            stats=status_text,
        )

        upstreams: List[VisualNode] = []
        if direction in ("upstream", "both"):
            visited_up = {catalog_id}
            upstreams = await _traverse(
                db, catalog_id, "upstream", depth, 1, visited_up,
                root_table_name=root_table_name,
            )

        downstreams: List[VisualNode] = []
        if direction in ("downstream", "both"):
            visited_down = {catalog_id}
            downstreams = await _traverse(
                db, catalog_id, "downstream", depth, 1, visited_down,
                root_table_name=root_table_name,
            )

        await log_api_action(
            endpoint=f"/api/v1/lineage-visual/{catalog_id}",
            method="GET",
            action_summary="Viewed visual lineage",
            entity_type="catalog",
            entity_id=catalog_id
        )

        return VisualLineageResponse(
            root=root_node,
            upstreams=upstreams,
            downstreams=downstreams,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_visual_lineage error: %s", e)
        raise HTTPException(500, str(e))


@router.get(
    "/api/v1/lineage-centric/{catalog_id}",
    response_model=CentricLineageResponse,
    summary="Hierarchical centric view of lineage from centric_lineage table",
    description="Returns a deeply nested tree representing upstream and downstream lineage.",
)
async def get_centric_lineage(
    catalog_id: str,
    depth: int = Query(2, ge=1, le=5, description="Traversal depth"),
):
    from app import db, logger, log_api_action
    try:
        root_data = await _fetch_catalog_node(db, catalog_id)
        if not root_data:
            raise HTTPException(404, f"Catalog '{catalog_id}' not found")

        base_node = await _build_centric_hierarchy(
            db, catalog_id, "both", depth, 0, set()
        )

        await log_api_action(
            endpoint=f"/api/v1/lineage-centric/{catalog_id}",
            method="GET",
            action_summary="Viewed centric lineage",
            entity_type="catalog",
            entity_id=catalog_id
        )

        return CentricLineageResponse(base_node=base_node)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_centric_lineage error: %s", e)
        raise HTTPException(500, str(e))