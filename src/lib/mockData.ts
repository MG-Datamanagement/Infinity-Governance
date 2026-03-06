import {
  ComplianceFramework,
  ComplianceIssue,
  ComplianceTrend,
  DashboardStats,
  AIGovernanceSnapshot,
  ModelRiskTrend,
  DomainAsset,
  PlatformUsage,
  RecentActivity,
  RecentlyViewed,
} from "@/types";
import { DiPostgresql } from "react-icons/di";
import { FaRegSnowflake } from "react-icons/fa";
import { SiMongodb } from "react-icons/si";
import { BiLogoPostgresql } from "react-icons/bi";

export const MOCK_USER = {
  id: "1",
  name: "Shivam",
  email: "shivam@infinity.com",
  avatar: null,
};

export const MOCK_COMPLIANCE_FRAMEWORKS: ComplianceFramework[] = [
  {
    id: "gdpr",
    name: "GDPR",
    score: 96,
    policiesTotal: 24,
    policiesComplete: 23,
    status: "excellent",
    lastUpdated: "2 hours ago",
    items: [
      { label: "Data mapping complete", completed: true },
      { label: "DPA conducted", completed: true },
      { label: "more", completed: false, count: 2 },
    ],
  },
  {
    id: "soc2",
    name: "SOC 2",
    score: 98,
    policiesTotal: 32,
    policiesComplete: 31,
    status: "excellent",
    lastUpdated: "1 hour ago",
    items: [
      { label: "Access control", completed: true },
      { label: "Encryption at rest", completed: true },
      { label: "more", completed: false, count: 2 },
    ],
  },
  {
    id: "hipaa",
    name: "HIPAA",
    score: 79,
    policiesTotal: 19,
    policiesComplete: 15,
    status: "warning",
    lastUpdated: "3 hours ago",
    items: [
      {
        label: "Review data classification policies for healthcare data",
        completed: false,
      },
      { label: "4 datasets need proper PHI tagging", completed: false },
    ],
  },
  {
    id: "dpdpa",
    name: "DPDPA",
    score: 62,
    policiesTotal: 20,
    policiesComplete: 12,
    status: "warning",
    lastUpdated: "3 hours ago",
    items: [],
  },
  {
    id: "euaiact",
    name: "EU AI Act",
    score: 45,
    policiesTotal: 20,
    policiesComplete: 2,
    status: "critical",
    lastUpdated: "5 hours ago",
    items: [],
  },
  {
    id: "internal",
    name: "Internal",
    score: 92,
    policiesTotal: 20,
    policiesComplete: 18,
    status: "excellent",
    lastUpdated: "1 hours ago",
    items: [],
  },
];

export const MOCK_COMPLIANCE_ISSUES: ComplianceIssue[] = [
  {
    id: "1",
    issue: "Missing data classification for PHI fields",
    framework: "HIPAA",
    severity: "HIGH",
    dataset: "patient_records",
    assignee: "Sarah Chen",
    dueDate: "Feb 15, 2026",
  },
  {
    id: "2",
    issue: "Consent records incomplete for EU users",
    framework: "GDPR",
    severity: "HIGH",
    dataset: "user_preferences",
    assignee: "Mike Johnson",
    dueDate: "Feb 18, 2026",
  },
  {
    id: "3",
    issue: "Access logs retention policy not configured",
    framework: "SOC 2",
    severity: "MEDIUM",
    dataset: "system_logs",
    assignee: "Emma Wilson",
    dueDate: "Feb 22, 2026",
  },
  {
    id: "4",
    issue: "Encryption at rest not enabled",
    framework: "HIPAA",
    severity: "HIGH",
    dataset: "medical_images",
    assignee: "Alex Kumar",
    dueDate: "Feb 14, 2026",
  },
  {
    id: "5",
    issue: "Data minimization review needed",
    framework: "GDPR",
    severity: "MEDIUM",
    dataset: "customer_analytics",
    assignee: "Lisa Park",
    dueDate: "Feb 25, 2026",
  },
  {
    id: "6",
    issue: "Audit trail gaps detected",
    framework: "SOC 2",
    severity: "LOW",
    dataset: "application_events",
    assignee: "Tom Davis",
    dueDate: "Mar 1, 2026",
  },
];

export const MOCK_COMPLIANCE_TRENDS: ComplianceTrend[] = [
  { month: "Aug", overall: 82, gdpr: 89, soc2: 85, hipaa: 72 },
  { month: "Sep", overall: 84, gdpr: 91, soc2: 87, hipaa: 74 },
  { month: "Oct", overall: 86, gdpr: 93, soc2: 90, hipaa: 75 },
  { month: "Nov", overall: 88, gdpr: 94, soc2: 92, hipaa: 76 },
  { month: "Dec", overall: 89, gdpr: 95, soc2: 94, hipaa: 77 },
  { month: "Jan", overall: 91, gdpr: 96, soc2: 98, hipaa: 79 },
];

export const MOCK_DASHBOARD_STATS: DashboardStats = {
  totalAssets: 112,
  totalAssetsChange: "+12% vs last month",
  governanceScore: 87,
  governanceScoreStatus: "Above target",
  classified: 14,
  classifiedChange: "+8% vs last month",
  pendingReview: 243,
  aiRiskDomains: 16,
  activeDomains: 12,
  activeTables: 45,
};

export const MOCK_AI_SNAPSHOT: AIGovernanceSnapshot = {
  modelsInProduction: 12,
  flaggedPromptsToday: 23,
  aiFairnessScore: 0.89,
  modelsNeedingReview: 3,
};

export const MOCK_MODEL_RISK_TRENDS: ModelRiskTrend[] = [
  { day: "7 days", risk: 0.65 },
  { day: "6 days", risk: 0.72 },
  { day: "5 days", risk: 0.68 },
  { day: "4 days", risk: 0.78 },
  { day: "3 days", risk: 0.82 },
  { day: "2 days", risk: 0.75 },
  { day: "1 day", risk: 0.88 },
  { day: "today", risk: 0.92 },
];

export const MOCK_DOMAIN_ASSETS: DomainAsset[] = [
  { domain: "Business Term", count: 2 },
  { domain: "Human resource", count: 1 },
  { domain: "Customer Management", count: 1 },
];

export const MOCK_PLATFORM_USAGE: PlatformUsage[] = [
  { platform: "PostgreSQL", count: 85 },
  { platform: "Snowflake", count: 80 },
  { platform: "MongoDB", count: 22 },
  { platform: "Cockroach/Adv", count: 8 },
];

export const MOCK_RECENT_ACTIVITY: RecentActivity[] = [
  {
    id: "1",
    name: "hum_resources_department",
    type: "Postgres",
    table: "Table",
    timestamp: "1 hour ago",
  },
  {
    id: "2",
    name: "LINEITEM",
    type: "Snowflake",
    table: "Table",
    timestamp: "3 hours ago",
  },
  {
    id: "3",
    name: "CUSTOMER_LTV",
    type: "Snowflake",
    table: "View",
    timestamp: "3 hours ago",
  },
  {
    id: "4",
    name: "customer_ltv",
    type: "Postgres",
    table: "Table",
    timestamp: "4 hours ago",
  },
  {
    id: "5",
    name: "customer_lv",
    type: "Postgres",
    table: "Table",
    timestamp: "4 hours ago",
  },
  {
    id: "6",
    name: "customer_lv",
    type: "Postgres",
    table: "Table",
    timestamp: "4 hours ago",
  },
  {
    id: "7",
    name: "customers",
    type: "Postgres",
    table: "Table",
    timestamp: "5 hours ago",
  },
  {
    id: "8",
    name: "order_line_items",
    type: "Postgres",
    table: "Table",
    timestamp: "6 hours ago",
  },
];

export const MOCK_RECENTLY_VIEWED:RecentlyViewed[] = [
  {
    id: "1",
    name: "customers",
    platform: "postgres_db",
    tag: "PII",
    tagColor: "yellow",
    time: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
    icon: BiLogoPostgresql,
    iconColor: 'text-slate-600'
  },
  {
    id: "2",
    name: "transactions",
    platform: "snowflake_dw",
    tag: "Financial",
    tagColor: "blue",
    time: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    icon: FaRegSnowflake,
    iconColor: 'text-sky-600'
  },
  {
    id: "3",
    name: "medical_images",
    platform: "mongodb_atlas",
    tag: "PHI",
    tagColor: "red",
    time: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    icon: SiMongodb,
    iconColor: 'text-green-600'
  },
  {
    id: "4",
    name: "user_preferences",
    platform: "postgres_db",
    tag: "GDPR",
    tagColor: "green",
    time: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    icon: BiLogoPostgresql,
    iconColor: 'text-slate-600'
  },
  {
    id: "5",
    name: "patient_records",
    platform: "snowflake_dw",
    tag: "HIPAA",
    tagColor: "indigo",
    time: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    icon: FaRegSnowflake,
    iconColor: 'text-sky-600'
  },
];
