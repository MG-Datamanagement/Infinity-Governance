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
} from "@/types";
import { AxiosRequestConfig } from "axios";

const config: AxiosRequestConfig = {
  headers: {
    "Content-Type": "application/json",
  },
};

export const dashbpardApiServices = {
  async getComplianceFrameworks() {
    await dashboardApiClient.get("", {});
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
    const response: DashboardEntityMetricsResponse = await dashboardApiClient.get(
      "/api/v1/overview/stats",
    );

    const dashboardStats: DashboardStats = {
      totalAssets: response?.total_assets,
      // totalAssetsChange: "",
      // governanceScore: 0,
      // governanceScoreStatus: "",
      classified: response?.total_tags,
      // classifiedChange: "",
      // pendingReview: 0,
      // aiRiskDomains: 0,
      activeDomains: response?.total_domains,
      activeTables: response?.total_datasets,
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
    const response: TopDomainsWithCountsResponse[] = await dashboardApiClient.get(
      "/api/v1/domains/dataset-count",
    );
    const topDomainsWithCount: DomainAsset[] = response?.map(
      (domain: TopDomainsWithCountsResponse) => ({
        domain: domain?.name,
        count: domain?.dataset_count,
        urn: domain?.id,
      }),
    );

    return topDomainsWithCount;
  },

  async getPlatformUsage() {
    const response: TopPlatformsWithCountsResponse = await dashboardApiClient.get(
      "/api/v1/overview/datasets-by-platform",
    );
    const topPlatformsWithCount: PlatformUsage[] = response?.platforms?.map(
      (platform: PlatformWithCount) => ({
        platform: platform?.platform,
        urn: platform?.platform,
        count: platform?.catalog_count,
      }),
    );

    return topPlatformsWithCount;
  },

  async getRecentlyViewed(userUrn: string) {
    const response: RecentlyViewedDatasetsResponse = await dashboardApiClient.get(
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
    const response: NewRecentActivity[] = await dashboardApiClient.get(
      `/api/v1/recent-activity`,
    );
    // const [recommendations] = response?.recommendations?.modules?.filter(
    //   (recommendation: RecommendationModule) =>
    //     recommendation?.moduleId === "HighUsageEntities" &&
    //     recommendation?.content,
    // );
    const RecentlyViewedDatasets: RecentActivity[] = response.map(
      (activity: NewRecentActivity) => ({
        id: activity.msg,
        name: activity.msg || "",
        type: "",
        platform: "",
      }),
    );

    return RecentlyViewedDatasets;
  },
};
