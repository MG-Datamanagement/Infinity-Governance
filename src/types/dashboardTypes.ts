export type InlineStateType = "loading" | "empty" | "error";

export type Option = {
  value: string;
  label: string;
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

export interface DashboardStats {
  totalAssets: number;
  // totalAssetsChange: string;
  // governanceScore: number;
  // governanceScoreStatus: string;
  classified: number;
  // classifiedChange: string;
  // pendingReview: number;
  // aiRiskDomains: number;
  activeDomains: number;
  activeTables: number;
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
  urn: string;
}

export interface PlatformUsage {
  platform: string;
  count: number;
  urn: string;
}

export interface RecentlyViewed {
  id: string;
  type: "Table" | "View";
  name?: string;
  platform?: string;
}

export interface RecentActivity {
  id: string;
  name: string;
  type: string;
  platform: string;
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

export interface RecentlyViewedDataset {
  urn: string;
  name: string;
  platform: string;
  description: string | null;
  source_module: string;
}
