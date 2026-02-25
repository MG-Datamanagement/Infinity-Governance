import { Agent, Dataset } from "./types";

import { GoWorkflow } from "react-icons/go";
import { FiGitBranch } from "react-icons/fi";
import { GoDatabase } from "react-icons/go";
import { TbZoomScan } from "react-icons/tb";
import { LuShieldCheck } from "react-icons/lu";
import { MdOutlinePolicy } from "react-icons/md";

export const MOCK_AGENTS: Agent[] = [
  {
    id: "schema-scout",
    name: "Schema Scout",
    description: "Analyzes table schemas and column types",
    icon: TbZoomScan,
    disabled: false,
  },
  {
    id: "pii-detective",
    name: "PII Detective",
    description: "Detects sensitive & personal data",
    icon: LuShieldCheck,
    disabled: false,
  },
  {
    id: "compliance-guardian",
    name: "Compliance Guardian",
    description: "Checks policy violations & enforcement",
    icon: MdOutlinePolicy,
    disabled: false,
  },
  {
    id: "lineage-tracker",
    name: "Lineage Tracker",
    description: "Maps upstream & downstream dependencies",
    icon: FiGitBranch,
    disabled: false,
  },
  {
    id: "sql-agent",
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

export const MOCK_DATASETS: Dataset[] = [
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
  // {
  //   id: "audit_trail",
  //   name: "audit_trail",
  //   type: "PostgreSQl",
  //   columns: 14,
  //   rows: 8900,
  // },
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
