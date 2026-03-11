import { CatalogTag } from "@/services/dashboardApiServices";
import { IconType } from "react-icons/lib";

export type InlineStateType = "loading" | "empty" | "error";

export type Option = {
  value: string;
  label: string;
  description?: string;
};

export interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
}

export interface ComplianceFramework {
  id: string;
  name: string;
  score: number;
  policiesTotal: number;
  policiesComplete: number;
  status: "excellent" | "warning" | "critical";
  lastUpdated: string;
  items?: ComplianceItem[];
}

export interface ComplianceItem {
  label: string;
  completed: boolean;
  count?: number;
}

export interface ComplianceIssue {
  id: string;
  issue: string;
  framework: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  dataset: string;
  assignee: string;
  dueDate: string;
}

export interface ComplianceTrend {
  month: string;
  overall: number;
  gdpr: number;
  soc2: number;
  hipaa: number;
}

// ─── Compliance API Response Types ───────────────────────────────────────────────

export interface ApiComplianceIndicator {
  text: string;
  status: "success" | "error" | "warning";
}

export interface ApiComplianceFramework {
  name: string;
  score: number;
  status: "excellent" | "warning" | "critical" | "needs_attention";
  details: string;
  last_checked: string;
  indicators: ApiComplianceIndicator[];
}

export interface ApiComplianceIssue {
  issue: string;
  framework: string;
  severity: "HIGH" | "MEDIUM" | "LOW" | "CRITICAL";
  dataset: string;
  assignee: string;
  due_date: string;
  action_url: string;
}

export interface ApiComplianceRunResponse {
  timestamp: string;
  overall_compliance: {
    score: number;
    change_from_last_month: number;
    health_status: string;
    last_updated: string;
  };
  compliance_health: {
    score: number;
    trend_label: string;
  };
  trends: {
    labels: string[];
    datasets: {
      label: string;
      data: number[];
    }[];
  };
  frameworks: ApiComplianceFramework[];
  open_issues: {
    count: number;
    severity_summary: Record<string, number>;
    items: ApiComplianceIssue[];
  };
  ai_insights: {
    text: string;
    beta: boolean;
  };
  quick_actions: {
    label: string;
    action: string;
  }[];
}

export interface ApiOpenIssuesResponse {
  open_issues: number;
}

export interface ApiGovernanceScoreResponse {
  governance_score: number;
}

export interface ApiComplianceOverviewResponse {
  insight: string;
  framework_scores: {
    framework: string;
    score: number;
  }[];
}


export interface DashboardStats {
  totalAssets: number;
  totalAssetsChange?: string;
  governanceScore?: number;
  governanceScoreStatus?: string;
  classified: number;
  classifiedChange?: string;
  pendingReview?: number;
  aiRiskDomains?: number;
  activeDomains: number;
  activeTables: number;
  openIssues?: number;
}

export interface AIGovernanceSnapshot {
  modelsInProduction: number;
  flaggedPromptsToday: number;
  aiFairnessScore: number;
  modelsNeedingReview: number;
}

export interface ModelRiskTrend {
  day: string;
  risk: number;
}

export interface DomainAsset {
  domain: string;
  count: number;
  urn?: string;
}

export interface PlatformUsage {
  platform: string;
  count: number;
  urn?: string;
}

export interface RecentlyViewed {
  // id: string;
  // type: "Table" | "View";
  // name?: string;
  // platform?: string;

  id: string;
  name: string;
  platform: string;
  tag: string;
  tagColor: string;
  time: string;
  icon: IconType;
  iconColor: string;
}

export interface RecentActivity {
  id: string;
  name: string;
  type: string;
  platform?: string;
  time?: string;
  table?: string;
  timestamp?: string;
}

export interface NewRecentActivity {
  t: string;
  msg: string;
}

// API Responses

export interface BaseApiResponse {
  status: "success" | "error";
  timestamp: number;
}

export interface DashboardEntityMetricsResponse extends BaseApiResponse {
  total_assets: number;
  // counts: EntityCounts;
  total_datasets: number;
  total_domains: number;
  total_tags: number;
  pending_review?: number;
  open_issues?: number;
  governance_score?: number;
  at_risk_domains?: number;
}

export type EntityCounts = Record<EntityType, number>;

export type EntityType = "DOMAIN" | "TAG" | "DATASET" | "INCIDENT";

export interface DomainWithCount {
  urn: string;
  name: string;
  asset_count: number;
}

export interface TopDomainsWithCountsResponse extends BaseApiResponse {
  // total_domains: number;
  // total_returned: number;
  // total_assets_in_domains: number;
  // domains: DomainWithCount[];
  id: string;
  name: string;
  dataset_count: number;
}

export interface PlatformWithCount {
  // platform_urn: string;
  // platform_name: string;
  // dataset_count: number;
  platform: string;
  catalog_count: number;
}

export interface TopPlatformsWithCountsResponse extends BaseApiResponse {
  // total_datasets: number;
  // total_platforms: number;
  platforms: PlatformWithCount[];
}

export interface RecentAssetsActivityResponse extends BaseApiResponse {
  user_urn: string;
  recommendations: Recommendations;
}

export interface Recommendations {
  modules: RecommendationModule[];
}

export interface RecommendationModule {
  moduleId: string;
  content: RecommendationContentItem[];
}

export interface RecommendationContentItem {
  entity: RecommendationEntity;
}

export interface RecommendationEntity {
  urn: string;
  type: RecommendationEntityType;
  name?: string;
  platform?: EntityPlatform;
}

export interface EntityPlatform {
  name: string;
}

export type RecommendationEntityType =
  | "DATA_PLATFORM"
  | "DATASET"
  | "CONTAINER";

export interface RecentlyViewedDatasetsResponse extends BaseApiResponse {
  user_urn: string;
  total_datasets: number;
  recently_viewed_datasets: RecentlyViewedDataset[];
}

export interface IngestionLog {
  time: string;
  message: string;
  status: "success" | "error" | "info";
}

export interface RecentlyViewedDataset {
  urn: string;
  name: string;
  platform: string;
  description: string | null;
  source_module: string;
}

export type DataSourceStatus = "success" | "failed" | "running";

export interface DataSourceStats {
  totalDatasets: number;
  totalColumns: string;
  totalRows: string;
  piiDetected: number;
}

export interface DataSource {
  id: string;
  name: string;
  icon: string;
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

export interface ApiTag {
  id: string;
  name: string;
  color?: string;
}

export interface ApiColumn {
  name: string;
  data_type: string;
  description: string | null;
  comment: string | null;
  is_nullable: boolean;
  is_primary_key: boolean;
}

// ─── Dataset & Catalog ────────────────────────────────────────────────────────

export type DatasetType = "table" | "view" | "Materialized View";
export type DatasetStatus = "healthy" | "warning" | "error";

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
  tags: CatalogTag[]
}

export interface DatasetsBySource {
  [sourceId: string]: Dataset[];
}

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
