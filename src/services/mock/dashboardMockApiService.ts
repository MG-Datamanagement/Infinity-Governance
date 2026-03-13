import { SourceCatalogResponse } from "../dashboardApiServices";

export interface Connector {
  id: string;
  name: string;
  description: string;
  bgColor: string;
  borderColor: string;
  icon: string; // SVG icon key
}

// Mocks for static UI elements

export const connectors: Connector[] = [
  {
    id: "airflow",
    name: "Airflow",
    description: "Import DAGs, Tasks, and lineage from Airflow.",
    bgColor: "bg-orange-50",
    borderColor: "border-orange-100",
    icon: "airflow",
  },
  {
    id: "athena",
    name: "Athena",
    description:
      "Import Schemas, Tables, Views, and lineage to S3 from Athena.",
    bgColor: "bg-white",
    borderColor: "border-gray-100",
    icon: "athena",
  },
  {
    id: "azure-ad",
    name: "Azure AD",
    description: "Import Users and Groups from Azure Active Directory.",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-100",
    icon: "azure",
  },
  {
    id: "bigquery",
    name: "BigQuery",
    description:
      "Import Projects, Datasets, Tables, Views, lineage, queries, and statistics from BigQuery.",
    bgColor: "bg-white",
    borderColor: "border-gray-100",
    icon: "bigquery",
  },
  {
    id: "cassandradb",
    name: "CassandraDB",
    description: "Import Tables, Keyspaces, and column schemas from Cassandra.",
    bgColor: "bg-white",
    borderColor: "border-gray-100",
    icon: "cassandra",
  },
  {
    id: "clickhouse",
    name: "ClickHouse",
    description:
      "Import Tables, Views, Materialized Views, Dictionaries, statistics, queries, and lineage from ClickHouse.",
    bgColor: "bg-yellow-50",
    borderColor: "border-yellow-100",
    icon: "clickhouse",
  },
  {
    id: "cockroachdb",
    name: "CockroachDb",
    description:
      "Import Databases, Schemas, Tables, Views, statistics and lineage from CockroachDb.",
    bgColor: "bg-gray-50",
    borderColor: "border-gray-100",
    icon: "cockroach",
  },
  {
    id: "csv",
    name: "CSV",
    description: "Import metadata from a formatted CSV.",
    bgColor: "bg-green-50",
    borderColor: "border-green-100",
    icon: "csv",
  },
  {
    id: "dagster",
    name: "Dagster",
    description: "Import Pipelines, Jobs, Assets, and lineage from Dagster.",
    bgColor: "bg-purple-50",
    borderColor: "border-purple-100",
    icon: "dagster",
  },
  {
    id: "databricks",
    name: "Databricks",
    description:
      "Import Notebooks, Jobs, Clusters, and lineage from Databricks.",
    bgColor: "bg-red-50",
    borderColor: "border-red-100",
    icon: "databricks",
  },
  {
    id: "dbt",
    name: "dbt",
    description:
      "Import Models, Sources, Tests, and lineage from dbt projects.",
    bgColor: "bg-orange-50",
    borderColor: "border-orange-100",
    icon: "dbt",
  },
  {
    id: "elasticsearch",
    name: "Elasticsearch",
    description:
      "Import Indices, Mappings, and cluster metadata from Elasticsearch.",
    bgColor: "bg-teal-50",
    borderColor: "border-teal-100",
    icon: "elasticsearch",
  },
  {
    id: "kafka",
    name: "Kafka",
    description:
      "Import Topics, Schemas, Consumer Groups, and lineage from Kafka.",
    bgColor: "bg-gray-50",
    borderColor: "border-gray-100",
    icon: "kafka",
  },
  {
    id: "mongodb",
    name: "MongoDB",
    description:
      "Import Databases, Collections, and schema metadata from MongoDB.",
    bgColor: "bg-green-50",
    borderColor: "border-green-100",
    icon: "mongodb",
  },
  {
    id: "mysql",
    name: "MySQL",
    description:
      "Import Databases, Tables, Views, and stored procedures from MySQL.",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-100",
    icon: "mysql",
  },
  {
    id: "postgresql",
    name: "PostgreSQL",
    description:
      "Import Schemas, Tables, Views, Functions, and lineage from PostgreSQL.",
    bgColor: "bg-gray-50",
    borderColor: "border-gray-100",
    icon: "postgresql",
  },
  {
    id: "redshift",
    name: "Redshift",
    description:
      "Import Schemas, Tables, Views, and lineage from Amazon Redshift.",
    bgColor: "bg-red-50",
    borderColor: "border-red-100",
    icon: "redshift",
  },
  {
    id: "snowflake",
    name: "Snowflake",
    description:
      "Import Databases, Schemas, Tables, Views, Stages, and lineage from Snowflake.",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-100",
    icon: "snowflake",
  },
];

// ─── Manage Data Sources ────────────────────────────────────────────────────

export type DataSourceStatus = "success" | "failed" | "running";

export interface IngestionLog {
  time: string;
  message: string;
  status: "success" | "error" | "info";
}

export interface DataSourceStats {
  totalDatasets: number;
  totalColumns: string; // e.g. "15.4k"
  totalRows: string; // e.g. "450M"
  piiDetected: number;
}

export interface DataSource {
  id: string;
  name: string;
  icon: string; // reuse ConnectorIcon keys
  iconBg: string;
  schedule: string;
  owner: string;
  ownerIcon: string;
  lastRun: string;
  status: DataSourceStatus;
  stats: DataSourceStats;
  ingestionLogs: IngestionLog[];
  totalDatasets: number;
}

export const dataSources: DataSource[] = [
  {
    id: "mongo_db",
    name: "mongo_db",
    icon: "mongodb",
    iconBg: "bg-green-100",
    schedule: "12:00 am (GMT+5:30)",
    owner: "DataHub",
    ownerIcon: "DH",
    lastRun: "2 days ago",
    status: "success",
    totalDatasets: 1245,
    stats: {
      totalDatasets: 984,
      totalColumns: "11.2k",
      totalRows: "320M",
      piiDetected: 74,
    },
    ingestionLogs: [
      {
        time: "10:45 AM",
        message: "Schema extraction completed",
        status: "success",
      },
      {
        time: "10:44 AM",
        message: "Connection established successfully",
        status: "success",
      },
      {
        time: "10:42 AM",
        message: "Starting incremental sync",
        status: "info",
      },
    ],
  },
  {
    id: "my_cust_2_db",
    name: "My_cust_2_DB",
    icon: "mysql",
    iconBg: "bg-blue-100",
    schedule: "12:00 am (GMT+5:30)",
    owner: "DataHub",
    ownerIcon: "DH",
    lastRun: "2 days ago",
    status: "success",
    totalDatasets: 1245,
    stats: {
      totalDatasets: 1245,
      totalColumns: "15.4k",
      totalRows: "450M",
      piiDetected: 128,
    },
    ingestionLogs: [
      {
        time: "10:45 AM",
        message: "Schema extraction completed for customers",
        status: "success",
      },
      {
        time: "10:44 AM",
        message: "Connection established successfully",
        status: "success",
      },
      {
        time: "10:42 AM",
        message: "Starting incremental sync",
        status: "info",
      },
      {
        time: "Yesterday",
        message: "Failed to sync view sales_materialized",
        status: "error",
      },
    ],
  },
  {
    id: "postgres_db",
    name: "postgres_db",
    icon: "postgresql",
    iconBg: "bg-gray-100",
    schedule: "12:00 am (GMT+5:30)",
    owner: "DataHub",
    ownerIcon: "DH",
    lastRun: "2 days ago",
    status: "success",
    totalDatasets: 876,
    stats: {
      totalDatasets: 876,
      totalColumns: "9.8k",
      totalRows: "210M",
      piiDetected: 56,
    },
    ingestionLogs: [
      { time: "10:40 AM", message: "Full sync completed", status: "success" },
      {
        time: "10:38 AM",
        message: "Connection established",
        status: "success",
      },
      { time: "10:36 AM", message: "Starting full sync", status: "info" },
    ],
  },
  {
    id: "my_cust_warehouse",
    name: "My_cust_warehouse",
    icon: "snowflake",
    iconBg: "bg-blue-100",
    schedule: "12:00 am (GMT+5:30)",
    owner: "DataHub",
    ownerIcon: "DH",
    lastRun: "2 days ago",
    status: "failed",
    totalDatasets: 432,
    stats: {
      totalDatasets: 432,
      totalColumns: "5.1k",
      totalRows: "87M",
      piiDetected: 22,
    },
    ingestionLogs: [
      {
        time: "Yesterday",
        message: "Failed to connect to warehouse cluster",
        status: "error",
      },
      {
        time: "Yesterday",
        message: "Retrying connection (attempt 3/3)",
        status: "error",
      },
      { time: "Yesterday", message: "Starting sync", status: "info" },
    ],
  },
];

export interface ApiDataSource {
  id?: string;
  source_id?: string;
  name: string;
  source_type?: string;
  owner_id?: string;
  owner_name?: string;
  status: "success" | "failed" | "running";
  schedule: string;
  last_ingested_at: string | null;
  created_at: string;
  description?: string;
}

export interface ApiSourceStats {
  source_id: string;
  source_name: string;
  source_type: string;
  total_tables_ingested: number;
  total_row_count: number;
  total_column_count: number;
  type: string;
  status: string;
  catalogs?: Array<{
    catalog_id: string;
    full_name: string;
    table_name: string;
    row_count: number | null;
    column_count: number;
  }>;
}

export interface ApiOwner {
  id: string;
  name: string;
  role: string;
  email: string;
  created_at: string;
  updated_at: string;
}

export interface ApiCatalogDetail {
  id: string;
  table_name: string;
  full_name: string;
  database_name: string;
  schema_name: string;
  description: string | null;
  source_name: string;
  source_type: string;
  row_count: number | null;
  column_count: number;
  properties: any;
  created_at: string;
  updated_at: string;
  owner?: string | null;
  domains?: any[];
  tags?: any[];
  columns: any[];
}

export type ClassificationTag = "PII" | "Non-PII" | "Error";
export interface ApiRunHistory {
  total: number;
  limit: number;
  offset: number;
  results: Array<{
    job_id: string;
    source_id: string;
    source_name: string;
    source_type: string;
    schedule: string;
    owner_name: string;
    status: "success" | "failed" | "running";
    started_at: string;
    completed_at: string | null;
    duration_seconds: number | null;
    records_ingested: number;
    error_message: string | null;
  }>;
}

export interface ApiSourceLog {
  id: string;
  job_id: string;
  source_id: string;
  level: "error" | "warning" | "success";
  message: string;
  logged_at: string;
}

export interface ApiSourceLogs {
  source_id: string;
  total: number;
  filters: any;
  logs: ApiSourceLog[];
}

export interface PiiClassificationRequest {
  source_id: string;
  Require_human_approval: boolean;
  assigned_by: string;
  min_confidence: number;
}

export interface TableClassificationResult {
  catalog_id: string;
  table_name: string;
  full_name: string;

  suggested_tag: ClassificationTag;
  tag_id: string | null;

  confidence_score: number;
  reasoning: string;

  saved: boolean;
}

export interface ClassificationResponse {
  source_id: string;
  total_catalogs: number;
  classified: number;
  saved: number;
  results: TableClassificationResult[];
}

export interface ReclassifyWithAiRequest {
  source_id: string;
  // catalog_id: string;
  save_to_db: boolean;
  assigned_by: string;
  min_confidence: number;
}

export interface ReClassifyWithAiResponse {
  source_id: string;
  catalog_id: string;
  total_columns: number;
  classified: number;
  saved: number;
  results: ReClassifyWithAIColumn[];
}

export interface ReClassifyWithAIColumn {
  column_id: string;
  column_name: string;
  description: string;
  is_nullable: boolean;
  column_data_type: string;
  catalog_id: string;
  table_name: string;
  suggested_tag: string;
  tag: TagInfo;
  is_sensitive: boolean;
  confidence_score: number;
  reasoning: string;
  saved: boolean;
}

export interface TagInfo {
  tag_id: string;
  tag_name: string;
}

export interface ReclassificationActionWithAiRequest {
  catalog_id: string;
  save_to_db: boolean;
  assigned_by: string;
  min_confidence: number;
}

const BASE_DEV_API_URL = process.env.NEXT_PUBLIC_DEV_API_URL;

export const dataSourcesService = {
  async fetchDataSources(params: {
    source_type?: string;
    status?: string;
    limit?: number;
  }) {
    const url = new URL(`${BASE_DEV_API_URL}/api/v1/sources-list`);

    if (params.source_type)
      url.searchParams.append("source_type", params.source_type);
    if (params.status && params.status !== "All")
      url.searchParams.append("status", params.status.toLowerCase());
    if (params.limit) url.searchParams.append("limit", params.limit.toString());

    try {
      const response = await fetch(url.toString());
      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }
      const data = await response.json();
      return data as ApiDataSource[];
    } catch (error) {
      console.error("Failed to fetch data sources from API:", error);
      throw error;
    }
  },

  async createDataSource(
    type: "postgres" | "mongodb" | "postgresql",
    data: any,
  ) {
    const endpoint =
      type === "postgres" || type === "postgresql" ? "postgres" : "mongodb";
    const url = `${BASE_DEV_API_URL}/api/v1/sources/${endpoint}`;

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.message || `API error: ${response.statusText}`,
        );
      }

      return await response.json();
    } catch (error) {
      console.error(`Failed to create ${type} data source:`, error);
      throw error;
    }
  },

  async fetchSourceStats(
    id: string,
    typeFilter?: string,
    statusFilter?: string,
  ) {
    const url = new URL(`${BASE_DEV_API_URL}/api/v1/sources/${id}/stats`);
    if (typeFilter && typeFilter !== "all")
      url.searchParams.append("type", typeFilter);
    if (statusFilter && statusFilter !== "all")
      url.searchParams.append("status", statusFilter);

    try {
      const response = await fetch(url.toString());
      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }
      const data = await response.json();
      return data as SourceCatalogResponse;
    } catch (error) {
      console.error(`Failed to fetch stats for source ${id}:`, error);
      throw error;
    }
  },

  async ingestSource(sourceId: string): Promise<{
    job_id: string;
    source_id: string;
    status: string;
    message: string;
  }> {
    const url = `${BASE_DEV_API_URL}/api/v1/ingest-source`;
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ source_id: sourceId }),
      });

      if (!response.ok) {
        throw new Error(`Ingestion API error: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error(
        `Failed to trigger ingestion for source ${sourceId}:`,
        error,
      );
      throw error;
    }
  },

  async fetchOwnersList(limit: number = 100) {
    const url = `${BASE_DEV_API_URL}/api/v1/owners-list?limit=${limit}`;
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }
      const data = await response.json();
      return data as ApiOwner[];
    } catch (error) {
      console.error(`Failed to fetch owners list:`, error);
      throw error;
    }
  },

  async fetchCatalogDetail(catalogId: string) {
    const url = `${BASE_DEV_API_URL}/api/v1/catalogs/minimal-detail/${catalogId}`;
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }
      const data = await response.json();
      return data as ApiCatalogDetail;
    } catch (error) {
      console.error(`Failed to fetch catalog detail for ${catalogId}:`, error);
      throw error;
    }
  },

  async fetchRunHistory(
    limit: number = 50,
    offset: number = 0,
    status?: string,
  ) {
    const url = new URL("http://172.188.2.173:8005/api/v1/run-history");
    url.searchParams.append("limit", limit.toString());
    url.searchParams.append("offset", offset.toString());
    if (status && status !== "All")
      url.searchParams.append("status", status.toLowerCase());

    try {
      const response = await fetch(url.toString());
      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }
      return (await response.json()) as ApiRunHistory;
    } catch (error) {
      console.error("Failed to fetch run history:", error);
      throw error;
    }
  },

  async fetchSourceLogs(
    sourceId: string,
    params: { last_run?: boolean; level?: string; limit?: number } = {},
  ) {
    const url = new URL(
      `http://172.188.2.173:8005/api/v1/sources/${sourceId}/logs`,
    );
    if (params.last_run) url.searchParams.append("last_run", "true");
    if (params.level && params.level !== "All")
      url.searchParams.append("level", params.level.toLowerCase());
    if (params.limit) url.searchParams.append("limit", params.limit.toString());

    try {
      const response = await fetch(url.toString());
      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }
      return (await response.json()) as ApiSourceLogs;
    } catch (error) {
      console.error(`Failed to fetch logs for source ${sourceId}:`, error);
      throw error;
    }
  },

  async initPiiClassification(
    piiClassifyPayload: PiiClassificationRequest,
  ): Promise<ClassificationResponse> {
    const url = `${BASE_DEV_API_URL}/tables/classify-table/source`;
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(piiClassifyPayload),
      });

      if (!response.ok) {
        throw new Error(
          `Initiate PII Classification API error: ${response.statusText}`,
        );
      }
      return await response.json();
    } catch (error) {
      console.error(
        `Failed to trigger PII Classification for source ${piiClassifyPayload?.source_id}:`,
        error,
      );
      throw error;
    }
  },
  async downloadSourceStats(
    id: string,
    typeFilter?: string,
    statusFiter?: string,
  ) {
    // const url = `${BASE_DEV_API_URL}/api/v1/sources/${id}/stats/download?type=${typeFilter}&status=${statusFiter}`;
    const url = `${process.env.NEXT_PUBLIC_DEV_TUNNEL_API_URL}/api/v1/sources/${id}/stats/export`;
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      return response;
    } catch (error) {
      console.error(`Failed to fetch stats for source ${id}:`, error);
      throw error;
    }
  },
  async reclassifyWithAi(
    reClassifyPayload: ReclassifyWithAiRequest,
  ): Promise<ReClassifyWithAiResponse> {
    const url = `${BASE_DEV_API_URL}/columns/classify-column/source`;
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(reClassifyPayload),
      });

      if (!response.ok) {
        throw new Error(
          `ReClassification with Ai API error: ${response.statusText}`,
        );
      }
      return await response.json();
    } catch (error) {
      console.error(
        `Failed to trigger ReClassification with Ai for source ${reClassifyPayload?.source_id}:`,
        error,
      );
      throw error;
    }
  },

  async reclassificationActionWithAi(
    reClassificationActionPayload: ReclassificationActionWithAiRequest,
  ): Promise<ReClassifyWithAiResponse> {
    const url = `${BASE_DEV_API_URL}/columns/classify-column/catalog`;
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(reClassificationActionPayload),
      });

      if (!response.ok) {
        throw new Error(
          `ReClassification Action with Ai API error: ${response.statusText}`,
        );
      }
      return await response.json();
    } catch (error) {
      console.error(
        `Failed to trigger ReClassification with Ai for source ${reClassificationActionPayload?.catalog_id}:`,
        error,
      );
      throw error;
    }
  },
};

// ─── Dataset List ─────────────────────────────────────────────────────────────

export type DatasetType = "Table" | "View" | "Materialized View";
export type DatasetStatus = "Healthy" | "Warning" | "Error";

export interface Dataset {
  id: string;
  name: string;
  hasPII: boolean;
  type: DatasetType;
  rows: string | null; // null for views
  columns: number;
  size: string | null;
  lastSync: string;
  status: DatasetStatus;
}

export interface DatasetsBySource {
  [sourceId: string]: Dataset[];
}

export const datasetsBySource: DatasetsBySource = {
  postgres_db: [
    {
      id: "customers",
      name: "customers",
      hasPII: true,
      type: "Table",
      rows: "12.4k",
      columns: 18,
      size: "2.4 MB",
      lastSync: "2 hours ago",
      status: "Healthy",
    },
    {
      id: "orders",
      name: "orders",
      hasPII: false,
      type: "Table",
      rows: "450.2k",
      columns: 24,
      size: "156 MB",
      lastSync: "2 hours ago",
      status: "Healthy",
    },
    {
      id: "transactions",
      name: "transactions",
      hasPII: true,
      type: "Table",
      rows: "1.2M",
      columns: 32,
      size: "450 MB",
      lastSync: "2 hours ago",
      status: "Healthy",
    },
    {
      id: "products",
      name: "products",
      hasPII: false,
      type: "Table",
      rows: "850",
      columns: 12,
      size: "1.2 MB",
      lastSync: "2 hours ago",
      status: "Healthy",
    },
    {
      id: "inventory_logs",
      name: "inventory_logs",
      hasPII: false,
      type: "Table",
      rows: "89k",
      columns: 8,
      size: "12 MB",
      lastSync: "2 hours ago",
      status: "Warning",
    },
    {
      id: "customer_ltv_view",
      name: "customer_ltv_view",
      hasPII: true,
      type: "View",
      rows: null,
      columns: 5,
      size: null,
      lastSync: "2 hours ago",
      status: "Healthy",
    },
    {
      id: "daily_sales_report",
      name: "daily_sales_report",
      hasPII: false,
      type: "View",
      rows: null,
      columns: 10,
      size: null,
      lastSync: "2 hours ago",
      status: "Healthy",
    },
    {
      id: "audit_logs",
      name: "audit_logs",
      hasPII: false,
      type: "Table",
      rows: "2.5M",
      columns: 15,
      size: "890 MB",
      lastSync: "10 mins ago",
      status: "Healthy",
    },
  ],
  mongo_db: [
    {
      id: "users",
      name: "users",
      hasPII: true,
      type: "Table",
      rows: "5.2k",
      columns: 14,
      size: "1.1 MB",
      lastSync: "2 days ago",
      status: "Healthy",
    },
    {
      id: "sessions",
      name: "sessions",
      hasPII: false,
      type: "Table",
      rows: "180k",
      columns: 8,
      size: "42 MB",
      lastSync: "2 days ago",
      status: "Healthy",
    },
    {
      id: "events",
      name: "events",
      hasPII: false,
      type: "Table",
      rows: "3.4M",
      columns: 20,
      size: "780 MB",
      lastSync: "2 days ago",
      status: "Warning",
    },
  ],
  my_cust_2_db: [
    {
      id: "customers",
      name: "customers",
      hasPII: true,
      type: "Table",
      rows: "38k",
      columns: 22,
      size: "8.1 MB",
      lastSync: "2 days ago",
      status: "Healthy",
    },
    {
      id: "sales",
      name: "sales",
      hasPII: false,
      type: "Table",
      rows: "1.1M",
      columns: 15,
      size: "230 MB",
      lastSync: "2 days ago",
      status: "Healthy",
    },
  ],
  my_cust_warehouse: [
    {
      id: "fact_sales",
      name: "fact_sales",
      hasPII: false,
      type: "Table",
      rows: "2.2M",
      columns: 28,
      size: "512 MB",
      lastSync: "2 days ago",
      status: "Error",
    },
  ],
};

// ─── Dataset Detail ───────────────────────────────────────────────────────────

export interface KeyField {
  name: string;
  description: string;
}

export interface DatasetDetail {
  id: string;
  sourceId: string;
  name: string;
  type: string;
  overview: string;
  keyFields: KeyField[];
  freshness: string;
  volume: string;
  qualityScore: string;
  columnCount: number;
  owner: string;
  ownerInitials: string;
  tags: string[];
  lineageWarning?: string;
}

export const datasetDetails: Record<string, DatasetDetail> = {
  customers: {
    id: "customers",
    sourceId: "postgres_db",
    name: "customers",
    type: "Dataset",
    overview:
      "The customers dataset contains structured records related to customer profiles, contact information, and account status. It is designed to support CRM operations, marketing analytics, and customer lifetime value calculations.",
    keyFields: [
      { name: "customer_id", description: "Unique identifier" },
      { name: "email", description: "Primary contact email" },
      { name: "ltv_score", description: "Lifetime value metric" },
      { name: "ssn", description: "Social security number (encrypted)" },
    ],
    freshness: "2h ago",
    volume: "12.4k",
    qualityScore: "98%",
    columnCount: 18,
    owner: "Rajkumar S",
    ownerInitials: "RS",
    tags: ["Entity", "PII", "Sales"],
    lineageWarning: "Some upstreams are unhealthy",
  },
  orders: {
    id: "orders",
    sourceId: "postgres_db",
    name: "orders",
    type: "Dataset",
    overview:
      "The orders dataset captures all transactional order records including order date, status, items, and associated customer references.",
    keyFields: [
      { name: "order_id", description: "Unique order identifier" },
      { name: "customer_id", description: "Reference to customers table" },
      { name: "total", description: "Order total in USD" },
      {
        name: "status",
        description: "Order status (pending / shipped / delivered)",
      },
    ],
    freshness: "2h ago",
    volume: "450.2k",
    qualityScore: "100%",
    columnCount: 24,
    owner: "Rajkumar S",
    ownerInitials: "RS",
    tags: ["Transactions", "Sales"],
  },
};
