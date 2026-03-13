import {
  DiPostgresql,
} from "react-icons/di";
import { FaRegSnowflake } from "react-icons/fa";
import { SiMongodb } from "react-icons/si";
import { BiLogoPostgresql } from "react-icons/bi";
import { Database } from "lucide-react";
import {
  MOCK_RECENTLY_VIEWED,
  MOCK_COMPLIANCE_FRAMEWORKS,
  MOCK_COMPLIANCE_ISSUES,
  MOCK_COMPLIANCE_TRENDS,
  MOCK_AI_SNAPSHOT,
  MOCK_MODEL_RISK_TRENDS,
} from "@/lib/mockData";
import { dashboardApiClient } from "@/lib/api-clients/dashboardApiClient";
import {
  DashboardEntityMetricsResponse,
  DashboardStats,
  DomainAsset,
  DomainWithCount,
  NewRecentActivity,
  PlatformUsage,
  PlatformWithCount,
  RecentActivity,
  RecentAssetsActivityResponse,
  RecentlyViewed,
  RecentlyViewedDataset,
  RecentlyViewedDatasetsResponse,
  RecommendationContentItem,
  RecommendationModule,
  TopDomainsWithCountsResponse,
  TopPlatformsWithCountsResponse,
  DataSource,
  DataSourceStatus,
  DataSourceStats,
  IngestionLog,
  ApiTag,
  ApiColumn,
  ApiComplianceRunResponse,
} from "@/types";
import { AxiosRequestConfig } from "axios";

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
    updated_at: string;
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
  owner?: string | ApiOwner | null;
  domains?: any[];
  tags?: ApiTag[];
  columns: ApiColumn[];
}

export interface ApiCatalogDatacard {
  catalog_id: string;
  table_name: string;
  full_name: string;
  data_card: string;
  generated_at: string;
  status: string;
}

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
  suggested_tag: string;
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

export interface SourceAiSummaryResponse {
  source_id: string;
  source_name: string;
  job_id: string;
  pipeline_status: PipelineStatus;
  badges: SourceAiSummaryBadges;
  stats: SourceAiSummaryStats;
  log_counts: SourceAiSummaryLogCounts;
  ai_summary: string;
}

export type PipelineStatus = "success" | "failed" | "running" | "pending";

export interface SourceAiSummaryBadges {
  ingested: number;
  classified: number;
}

export interface SourceAiSummaryStats {
  total_rows: number;
  sensitive_columns: number;
  healthy: number;
  warning: number;
  risk: number;
  duration_seconds: number;
}

export interface SourceAiSummaryLogCounts {
  error: number;
  warning: number;
}

export type CatalogStatus = "healthy" | "warning" | "error";
export type CatalogType = "table" | "view";

export interface SourceCatalogResponse {
  source_id: string;
  source_name: string;
  source_type: string;
  total_tables_ingested: number;
  total_row_count: number;
  total_column_count: number;
  filters: Filters;
  catalogs: Catalog[];
}

export interface Filters {
  type: string | null;
  status: string | null;
}

export interface Catalog {
  catalog_id: string;
  full_name: string;
  table_name: string;
  row_count: number | null;
  column_count: number;
  type: CatalogType;
  status: CatalogStatus;
  last_sync: string;
  tags: CatalogTag[];
}

export interface CatalogTag {
  name: string;
  color: string;
  tag_id: string;
}

const config: AxiosRequestConfig = {
  headers: {
    "Content-Type": "application/json",
  },
};

export const dashboardApiServices = {
  // ─── Compliance & Overview ───────────────────────────────────────────────
  async runCompliance(): Promise<ApiComplianceRunResponse> {
    return dashboardApiClient.get("/api/compliance/run");
  },

  async getComplianceLoadingSteps(): Promise<{ reasoning_loads: string[] }> {
    return dashboardApiClient.get("/api/compliance/loading");
  },

  async runComplianceScan(): Promise<{
    timestamp: string;
    summary: {
      frameworks_scanned: number;
      issues_found: number;
      policies_checked: number;
      overall_score: number;
      issue_summary: string;
    };
    reasoning: Array<{ title: string; description: string }>;
  }> {
    return dashboardApiClient.get("/api/compliance/summary");
  },
  async getComplianceFrameworks() {
    return MOCK_COMPLIANCE_FRAMEWORKS;
  },
  async getComplianceIssues() {
    return MOCK_COMPLIANCE_ISSUES;
  },
  async getComplianceTrends() {
    return MOCK_COMPLIANCE_TRENDS;
  },
  async getAISnapshot() {
    return MOCK_AI_SNAPSHOT;
  },
  async getModelRiskTrends() {
    return MOCK_MODEL_RISK_TRENDS;
  },

  async getDashboardStats() {
    const response: DashboardEntityMetricsResponse = await dashboardApiClient.get(
      "/api/v1/overview/stats",
    );

    const dashboardStats: DashboardStats = {
      totalAssets: response?.total_assets || 0,
      classified: response?.total_tags || 0,
      activeDomains: response?.total_domains || 0,
      activeTables: response?.total_datasets || 0,
      pendingReview: response?.pending_review || 0,
      openIssues: response?.open_issues || 0,
      governanceScore: response?.governance_score || 0,
      aiRiskDomains: response?.at_risk_domains || 0,
    };
    return dashboardStats;
  },

  async getPendingReviewCount() {
    return dashboardApiClient.get<{ pending_review: number }>(
      "/api/dashboard/pending-review",
    );
  },

  async getOpenIssues() {
    return dashboardApiClient.get<{ open_issues: number }>(
      "/api/dashboard/open-issues",
    );
  },

  async getGovernanceScore() {
    return dashboardApiClient.get<{ governance_score: number }>(
      "/api/dashboard/governance-score",
    );
  },

  async getComplianceOverview() {
    return dashboardApiClient.get<{
      insight: string;
      framework_scores: { framework: string; score: number }[];
    }>("/compliance-overview");
  },

  async getDomainAssets() {
    const response: TopDomainsWithCountsResponse[] = await dashboardApiClient.get(
      "/api/v1/domains/dataset-count",
    );
    return response?.map((domain: TopDomainsWithCountsResponse) => ({
      domain: domain?.name,
      count: domain?.dataset_count,
      urn: domain?.id,
    }));
  },

  async getPlatformUsage() {
    const response: TopPlatformsWithCountsResponse = await dashboardApiClient.get(
      "/api/v1/overview/datasets-by-platform",
    );
    return response?.platforms?.map((platform: PlatformWithCount) => ({
      platform: platform?.platform,
      urn: platform?.platform,
      count: platform?.catalog_count,
    }));
  },

  async getRecentlyViewed(userUrn: string) {
    try {
      const response = await dashboardApiClient.get<{ recently_viewed: any[] }>(
        "/api/v1/recently-viewed",
      );

      return response.recently_viewed.map((item, index) => {
        let icon: any = Database;
        let iconColor = "text-gray-600";
        let tagColor = "gray";

        const platform = (item.source || "").toLowerCase();

        if (platform.includes("postgres")) {
          icon = BiLogoPostgresql;
          iconColor = "text-slate-600";
        } else if (platform.includes("snowflake")) {
          icon = FaRegSnowflake;
          iconColor = "text-sky-600";
        } else if (platform.includes("mongo")) {
          icon = SiMongodb;
          iconColor = "text-green-600";
        }

        const tag = (item.tag || "").toLowerCase();
        if (tag === "pii") tagColor = "yellow";
        else if (tag === "financial") tagColor = "blue";
        else if (tag === "phi") tagColor = "red";
        else if (tag === "gdpr") tagColor = "green";
        else if (tag === "hipaa") tagColor = "indigo";
        else tagColor = "gray";

        return {
          id: `${item.dataset}-${index}`,
          name: item.dataset || "Unknown Dataset",
          platform: item.source || "Unknown Platform",
          tag: item.tag || "",
          tagColor,
          time: item.time || "",
          icon,
          iconColor,
        };
      });
    } catch (e) {
      console.error(e);
      return [];
    }
  },

  async getRecentActivity(userUrn: string) {
    const response: NewRecentActivity[] = await dashboardApiClient.get(
      `/api/v1/recent-activity`,
    );
    return response.map((activity: NewRecentActivity, index: number) => ({
      id: `${activity.t}-${index}`,
      name: activity.msg || "",
      type: "",
      platform: "",
      time: activity.t,
    }));
  },

  // ─── Data Sources ───────────────────────────────────────────────────────
  async fetchDataSources(params: {
    source_type?: string;
    status?: string;
    limit?: number;
  }) {
    const queryParams: any = {};
    if (params.source_type) queryParams.source_type = params.source_type;
    if (params.status && params.status !== "All")
      queryParams.status = params.status.toLowerCase();
    if (params.limit) queryParams.limit = params.limit;

    return dashboardApiClient.get<ApiDataSource[]>("/api/v1/sources-list", {
      params: queryParams,
    });
  },

  async createDataSource(
    type: "postgres" | "mongodb" | "postgresql" | "athena",
    payload: any,
  ): Promise<{ id?: string; source_id?: string }> {
    const endpoint =
      type === "athena" ? "athena" :
        (type === "postgres" || type === "postgresql" ? "postgres" : "mongodb");
    return dashboardApiClient.post(`/api/v1/sources/${endpoint}`, payload);
  },

  async fetchSourceStats(
    id: string,
    typeFilter?: string,
    statusFilter?: string,
  ) {
    const params: any = {};
    if (typeFilter && typeFilter !== "all") params.type = typeFilter;
    if (statusFilter && statusFilter !== "all") params.status = statusFilter;

    return dashboardApiClient.get<SourceCatalogResponse>(`/api/v1/sources/${id}/stats`, {
      params,
    });
  },

  async ingestSource(sourceId: string): Promise<{
    job_id: string;
    source_id: string;
    status: string;
    message: string;
  }> {
    return dashboardApiClient.post("/api/v1/ingest-source", {
      source_id: sourceId,
    });
  },

  async deleteSource(sourceId: string): Promise<{
    message: string;
    source_id: string;
  }> {
    return dashboardApiClient.delete(`/api/v1/delete-source/${sourceId}`);
  },

  async fetchOwnersList(limit: number = 100) {
    return dashboardApiClient.get<ApiOwner[]>("/api/v1/owners-list", {
      params: { limit },
    });
  },

  async fetchCatalogDetail(catalogId: string) {
    return dashboardApiClient.get<ApiCatalogDetail>(
      `/api/v1/catalogs/minimal-detail/${catalogId}`,
    );
  },

  async fetchCatalogDatacard(catalogId: string) {
    return dashboardApiClient.post<ApiCatalogDatacard>(
      `/api/v1/catalogs/${catalogId}/datacard`,
      {},
    );
  },

  async fetchRunHistory(
    limit: number = 50,
    offset: number = 0,
    status?: string,
  ) {
    const params: any = { limit, offset };
    if (status && status !== "All") params.status = status.toLowerCase();

    return dashboardApiClient.get<ApiRunHistory>("/api/v1/run-history", {
      params,
    });
  },

  async fetchSourceLogs(
    sourceId: string,
    params: { last_run?: boolean; level?: string; limit?: number } = {},
  ) {
    return dashboardApiClient.get<ApiSourceLogs>(
      `/api/v1/sources/${sourceId}/logs`,
      { params },
    );
  },

  async initPiiClassification(
    payload: PiiClassificationRequest,
  ): Promise<ClassificationResponse> {
    return dashboardApiClient.post("/tables/classify-table/source", payload);
  },

  async downloadSourceStats(
    id: string,
    typeFilter?: string,
    statusFilter?: string,
  ) {
    const baseUrl =
      process.env.NEXT_PUBLIC_DASHBOARD_API_URL || "http://localhost:8000";
    const url = `${baseUrl}/api/v1/sources/${id}/stats/export`;

    const token =
      typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;

    const response = await fetch(url, {
      method: "GET",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });

    if (!response.ok) {
      throw new Error(`Download failed: ${response.statusText}`);
    }
    return response;
  },

  async exportComplianceReport(): Promise<void> {
    const baseUrl =
      process.env.NEXT_PUBLIC_DASHBOARD_API_URL || "http://localhost:8000";
    const url = `${baseUrl}/api/compliance/report/export`;

    const token =
      typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;

    const response = await fetch(url, {
      method: "GET",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });

    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`);
    }

    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = `compliance-report-${new Date().toISOString().split("T")[0]}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(objectUrl);
  },

  async fetchIngestionAiSummary(sourceId: string) {
    return dashboardApiClient.get<SourceAiSummaryResponse>(
      `/api/v1/sources/${sourceId}/ai-summary`,
    );
  },

  // ─── Lineage Visual Types ─────────────────────────────────────────────────────

  async fetchLineageVisual(
    catalogId: string,
    depth: number = 2,
    direction: "upstream" | "downstream" | "both" = "both",
  ): Promise<LineageVisualResponse> {
    return dashboardApiClient.get<LineageVisualResponse>(
      `/api/v1/lineage-visual/${catalogId}`,
      { params: { depth, direction } },
    );
  },
};

export interface LineageApiColumn {
  id: string;
  name: string;
  data_type: string;
  is_primary_key: boolean;
  is_foreign_key: boolean;
  is_nullable: boolean;
}

export interface LineageApiTag {
  id: string;
  name: string;
  color: string | null;
  tag_type: string;
}

export interface LineageApiSource {
  id: string;
  name: string;
  source_type: string;
}

export interface LineageApiColumnMapping {
  source_column: string;
  target_column: string;
}

export interface LineageApiNode {
  id: string;
  table_name: string;
  full_name: string;
  schema_name: string;
  database_name: string;
  type: "table" | "view" | "dashboard";
  status: "healthy" | "warning" | "error";
  source: LineageApiSource;
  columns: LineageApiColumn[];
  tags: LineageApiTag[];
  lineage_id: string | null;
  transformation_query: string | null;
  column_mappings: LineageApiColumnMapping[];
  depth: number;
}

export interface LineageVisualResponse {
  root: LineageApiNode;
  upstreams: LineageApiNode[];
  downstreams: LineageApiNode[];
}

