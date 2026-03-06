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