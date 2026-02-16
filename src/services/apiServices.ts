import { apiClient } from "@/lib/api-client";
import {
  DashboardEntityMetricsResponse,
  DashboardStats,
  DomainAsset,
  DomainWithCount,
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
} from "@/types";
import { AxiosRequestConfig } from "axios";

const config: AxiosRequestConfig = {
  headers: {
    "Content-Type": "application/json",
  },
};

export const apiServices = {
  async getComplianceFrameworks() {
    await apiClient.get("", {});
    return [];
  },

  async getComplianceIssues() {
    await {};
    return [];
  },

  async getComplianceTrends() {
    await {};
    return [];
  },

  async getDashboardStats() {
    const response: DashboardEntityMetricsResponse = await apiClient.get(
      "/dashboard/entitymetrics",
    );

    const dashboardStats: DashboardStats = {
      totalAssets: response?.total_assets,
      totalAssetsChange: "",
      governanceScore: 0,
      governanceScoreStatus: "",
      classified: response?.counts?.TAG,
      classifiedChange: "",
      pendingReview: response?.counts?.INCIDENT,
      aiRiskDomains: 0,
      activeDomains: response?.counts?.DOMAIN,
      activeTables: response?.counts?.DATASET,
    };
    return dashboardStats;
  },

  async getAISnapshot() {
    await {};
    return [];
  },

  async getModelRiskTrends() {
    await {};
    return [];
  },

  async getDomainAssets() {
    const response: TopDomainsWithCountsResponse = await apiClient.get(
      "/dashboard/domain_with_counts",
    );
    const topDomainsWithCount: DomainAsset[] = response?.domains?.map(
      (domain: DomainWithCount) => ({
        domain: domain?.name,
        count: domain?.asset_count,
        urn: domain?.urn,
      }),
    );

    return topDomainsWithCount;
  },

  async getPlatformUsage() {
    const response: TopPlatformsWithCountsResponse = await apiClient.get(
      "/dashboard/platforms",
    );
    const topPlatformsWithCount: PlatformUsage[] = response?.platforms?.map(
      (platform: PlatformWithCount) => ({
        platform: platform?.platform_name,
        urn: platform?.platform_urn,
        count: platform?.dataset_count,
      }),
    );

    return topPlatformsWithCount;
  },

  async getRecentlyViewed(userUrn: string) {
    const response: RecentlyViewedDatasetsResponse = await apiClient.get(
      `/dashboard/recent?user_urn=${userUrn}`,
    );
    const RecentlyViewedDatasets: RecentlyViewed[] =
      response?.recently_viewed_datasets?.map(
        (recentDataset: RecentlyViewedDataset) => ({
          id: recentDataset?.urn,
          name: recentDataset?.name,
          platform: recentDataset?.platform,
          type: "Table",
        }),
      );

    return RecentlyViewedDatasets;
  },

  async getRecentActivity(userUrn: string) {
    const response: RecentAssetsActivityResponse = await apiClient.get(
      `/dashboard/recent-assets?user_urn=${userUrn}`,
    );
    const [recommendations] = response?.recommendations?.modules?.filter(
      (recommendation: RecommendationModule) =>
        recommendation?.moduleId === "HighUsageEntities" &&
        recommendation?.content,
    );
    const RecentlyViewedDatasets: RecentActivity[] = (
      recommendations || {}
    )?.content?.map((contentItem: RecommendationContentItem) => ({
      id: contentItem?.entity?.urn,
      type: contentItem?.entity?.type,
      name: contentItem?.entity?.name || "",
      platform: contentItem?.entity?.platform?.name || "",
    }));

    return RecentlyViewedDatasets;
  },
};
