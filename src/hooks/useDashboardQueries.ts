import { useQuery } from '@tanstack/react-query';
import { dashboardApiServices } from '@/services/dashboardApiServices';

export const useComplianceFrameworks = () => {
  return useQuery({
    queryKey: ['compliance-frameworks'],
    queryFn: dashboardApiServices.getComplianceFrameworks,
  });
};

export const useComplianceIssues = () => {
  return useQuery({
    queryKey: ['compliance-issues'],
    queryFn: dashboardApiServices.getComplianceIssues,
  });
};

export const useComplianceTrends = () => {
  return useQuery({
    queryKey: ['compliance-trends'],
    queryFn: dashboardApiServices.getComplianceTrends,
  });
};

export const useComplianceRun = () => {
  return useQuery({
    queryKey: ['compliance-run'],
    queryFn: dashboardApiServices.runCompliance,
  });
};

export const useAISnapshot = () => {
  return useQuery({
    queryKey: ['ai-snapshot'],
    queryFn: dashboardApiServices.getAISnapshot,
  });
};

export const useModelRiskTrends = () => {
  return useQuery({
    queryKey: ['model-risk-trends'],
    queryFn: dashboardApiServices.getModelRiskTrends,
  });
};

export const useDashboardStats = () => {
  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardApiServices.getDashboardStats,
    retry: 1
  });
};

export const usePendingReviewCount = () => {
  return useQuery({
    queryKey: ['pending-review-count'],
    queryFn: dashboardApiServices.getPendingReviewCount,
  });
};

export const useOpenIssues = () => {
  return useQuery({
    queryKey: ['open-issues-count'],
    queryFn: dashboardApiServices.getOpenIssues,
  });
};

export const useGovernanceScore = () => {
  return useQuery({
    queryKey: ['governance-score'],
    queryFn: dashboardApiServices.getGovernanceScore,
  });
};

export const useComplianceOverview = () => {
  return useQuery({
    queryKey: ['compliance-overview'],
    queryFn: dashboardApiServices.getComplianceOverview,
  });
};

export const useDomainAssets = () => {
  return useQuery({
    queryKey: ['domain-assets'],
    queryFn: dashboardApiServices.getDomainAssets,
  });
};

export const usePlatformUsage = () => {
  return useQuery({
    queryKey: ['platform-usage'],
    queryFn: dashboardApiServices.getPlatformUsage,
  });
};

export const useRecentlyViewed = (userUrn: string) => {
  return useQuery({
    queryKey: ['recently-viewed'],
    queryFn: () => dashboardApiServices.getRecentlyViewed(userUrn),
    enabled: !!userUrn,
  });
};

export const useRecentActivity = (userUrn: string) => {
  return useQuery({
    queryKey: ['recent-activity'],
    queryFn: () => dashboardApiServices.getRecentActivity(userUrn),
    enabled: !!userUrn,
  });
};
