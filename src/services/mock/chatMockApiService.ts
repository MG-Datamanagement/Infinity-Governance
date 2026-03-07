import {
  Agent,
  ChatResponse,
  ChatDataset,
  HistoryResponse,
  SessionDetailResponse,
} from "../../types";

import { GoWorkflow } from "react-icons/go";
import { FiGitBranch } from "react-icons/fi";
import { GoDatabase } from "react-icons/go";
import { TbZoomScan } from "react-icons/tb";
import { LuShieldCheck } from "react-icons/lu";
import { MdOutlinePolicy } from "react-icons/md";

export const MOCK_AGENTS: Agent[] = [
  {
    id: "schema_scout",
    name: "Schema Scout",
    description: "Analyzes table schemas and column types",
    icon: TbZoomScan,
    disabled: false,
  },
  {
    id: "pii_detective",
    name: "PII Detective",
    description: "Detects sensitive & personal data",
    icon: LuShieldCheck,
    disabled: false,
  },
  {
    id: "compliance_guardian",
    name: "Compliance Guardian",
    description: "Checks policy violations & enforcement",
    icon: MdOutlinePolicy,
    disabled: false,
  },
  {
    id: "lineage_tracker",
    name: "Lineage Tracker",
    description: "Maps upstream & downstream dependencies",
    icon: FiGitBranch,
    disabled: false,
  },
  {
    id: "sql_agent",
    name: "SQL Agent",
    description: "Generates & runs SQL queries",
    icon: GoDatabase,
    disabled: false,
  },
  {
    id: "orchestrator",
    name: "Orchestrator",
    description: "Coordinates multi-agent workflows",
    alert: `Enable "Multi-Agent" in preference`,
    tag: "Multi",
    icon: GoWorkflow,
    disabled: true,
  },
];

export const MOCK_DATASETS: ChatDataset[] = [
  {
    id: "customers_prod",
    name: "customers_prod",
    type: "PostgreSQL",
    columns: 18,
    rows: 12400,
  },
  {
    id: "orders_master",
    name: "orders_master",
    type: "PostgreSQL",
    columns: 24,
    rows: 450000,
  },
  {
    id: "transactions_ledger",
    name: "transactions_ledger",
    type: "Snowflake",
    columns: 32,
    rows: 1200000,
  },
  {
    id: "user_profiles",
    name: "user_profiles",
    type: "MongoDB",
    columns: 14,
    rows: 8300,
  },
  {
    id: "product_catalog",
    name: "product_catalog",
    type: "Snowflake",
    columns: 12,
    rows: 850,
  },
];

export const SUGGESTED_PROMPTS = [
  {
    icon: "📊",
    title: "List Snowflake Assets",
    description:
      "List all assets in the Snowflake platform related to finance.",
  },
  {
    icon: "🌐",
    title: "Domain Overview",
    description:
      'Give me an overview of the "Customer 360" domain and its critical assets.',
  },
  {
    icon: "📋",
    title: "Policy Check",
    description:
      "Which datasets are currently violating the GDPR retention policy?",
  },
  {
    icon: "⚡",
    title: "Impact Analysis",
    description:
      'What would be the downstream impact if I deprecate the "orders_master" table?',
  },
];

// Mock Data with Enhanced Response Structure
export const MOCK_CHAT_RESPONSE: ChatResponse = {
  answer:
    "This governance platform currently manages 1 data source of type MongoDB. It catalogs 17 tables with a total of 87 columns across these tables. The data is organized into 3 governance domains and classified with 10 different tags. There are 2 data owners responsible for the assets. So far, 1 ingestion job has been completed successfully with no failures. There are no recorded relationships between tables at this time.",
  reasoning: [
    "[Orchestrator] Question routed to: catalog, lineage",
    "[CatalogAgent] Starting CoT analysis for: overview of this application",
    "[CatalogAgent] Calling tool: get_platform_overview({})",
    "[CatalogAgent] get_platform_overview returned data successfully",
  ],
  reasoning_summary:
    "Retrieved full asset detail from governance catalog. Checked metadata catalog for all registered assets. Traced data lineage and pipeline dependencies.",
  reasoning_tools: [
    {
      label: "Asset Detail",
      icon: "tool",
      raw: "get_full_catalog_detail",
    },
    {
      label: "Catalog Listing",
      icon: "tool",
      raw: "list_catalogs",
    },
    {
      label: "Lineage Graph",
      icon: "tool",
      raw: "get_data_lineage",
    },
  ],
  reasoning_sources: [
    {
      label: "Governance Catalog",
      icon: "source",
      type: "System",
    },
    {
      label: "Lineage Graph",
      icon: "source",
      type: "System",
    },
  ],
  sources: [
    {
      label: "Governance Catalog",
      type: "System",
      pill: "Governance Catalog · System",
      icon: "database",
    },
    {
      label: "Lineage Graph",
      type: "System",
      pill: "Lineage Graph · System",
      icon: "database",
    },
  ],
  tools_detail: [
    {
      tool: "get_full_catalog_detail",
      args: {
        table_name: "orders_master",
      },
      result_preview: "No catalog found for table matching 'orders_master'.",
      source_label: "Governance Catalog",
      source_type: "System",
    },
    {
      tool: "list_catalogs",
      args: {},
      result_preview:
        "Retrieved 17 catalog entries from the governance system.",
      source_label: "Governance Catalog",
      source_type: "System",
    },
  ],
  tools_used: [
    "list_data_sources",
    "get_data_lineage",
    "list_catalogs",
    "get_full_catalog_detail",
  ],
  agents_used: ["catalog", "lineage"],
  suggestions: [
    "List all data sources connected",
    "Which tables contain PII data?",
    "Show all domains and their assets",
  ],
  session_id: "165ecc5b-3a90-4964-b8bf-4831ce763d59",
  timestamp: new Date().toISOString(),
  memory_enabled: true,
  reasoning_enabled: true,
};

export const MOCK_HISTORY: HistoryResponse = {
  total_sessions: 10,
  sessions: [
    {
      id: "dd7529d0-5162-4d01-9c12-7ed00e1b2073",
      title: "List all tags in the system and show which catalogs and colu",
      created_at: "2026-02-24T04:03:29.513731+05:30",
      last_active: "2026-02-24T04:03:41.859182+05:30",
      message_count: 1,
    },
    {
      id: "8eb2cc64-eaf3-4ef0-89e7-8837689a9e8e",
      title: "Who owns each catalog asset? List every table with its owner",
      created_at: "2026-02-24T04:01:15.468525+05:30",
      last_active: "2026-02-24T04:01:26.598219+05:30",
      message_count: 1,
    },
    {
      id: "4a72fd23-fb94-4b51-b34d-dcf44c634a53",
      title: "Show me all columns in the Patients table with their data ty",
      created_at: "2026-02-24T04:00:25.915582+05:30",
      last_active: "2026-02-24T04:00:32.325088+05:30",
      message_count: 1,
    },
    {
      id: "d9c16b5e-485a-4a26-8650-51c88f81aea6",
      title: "List all 17 catalog assets with their full name, schema, and",
      created_at: "2026-02-24T03:59:32.492338+05:30",
      last_active: "2026-02-24T03:59:45.018567+05:30",
      message_count: 1,
    },
    {
      id: "92dd3ecc-eccb-4237-b63b-03bc06fde38a",
      title: "Give me a complete platform overview with total assets, sour",
      created_at: "2026-02-24T03:57:17.344809+05:30",
      last_active: "2026-02-24T03:57:24.796511+05:30",
      message_count: 1,
    },
  ],
};

export const MOCK_SESSION_DETAIL: SessionDetailResponse = {
  session_id: "dd7529d0-5162-4d01-9c12-7ed00e1b2073",
  title: "List all tags in the system and show which catalogs and colu",
  created_at: "2026-02-24T04:03:29.513731",
  last_active: "2026-02-24T07:03:00.530994",
  message_count: 2,
  messages: [
    {
      id: "msg-1",
      role: "human",
      content:
        "List all tags in the system and show which catalogs and columns each tag is assigned to",
      created_at: "2026-02-24T09:33:29.934507+05:30",
      error: false,
    },
    {
      id: "msg-2",
      role: "ai",
      content:
        "Here are all the tags in the system along with the catalogs and columns they are assigned to:\n\n1. Tag: Confidential\n   - Description: Sensitive business or user data that must not be disclosed without authorization, including internal documents and trade secrets.\n   - Assigned Catalogs: 0\n   - Assigned Columns: 4",
      created_at: "2026-02-24T09:33:42.230729+05:30",
      error: false,
    },
  ],
};

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const chatMockApiService = {
  async sendMessage() {
    await delay(800);
    return MOCK_CHAT_RESPONSE;
  },

  async getHistory() {
    await delay(300);
    return MOCK_HISTORY;
  },

  async getSessionDetail() {
    await delay(300);
    return MOCK_SESSION_DETAIL;
  },
};
