import { useQuery } from '@tanstack/react-query';
import { dashboardMockApiService } from '@/services/mock/dashboardMockApiService';
import { dashbpardApiServices } from '@/services/dashbpardApiServices';

export const useComplianceFrameworks = () => {
  return useQuery({
    queryKey: ['compliance-frameworks'],
    queryFn: dashboardMockApiService.getComplianceFrameworks,
  });
};

export const useComplianceIssues = () => {
  return useQuery({
    queryKey: ['compliance-issues'],
    queryFn: dashboardMockApiService.getComplianceIssues,
  });
};

export const useComplianceTrends = () => {
  return useQuery({
    queryKey: ['compliance-trends'],
    queryFn: dashboardMockApiService.getComplianceTrends,
  });
};

export const useAISnapshot = () => {
  return useQuery({
    queryKey: ['ai-snapshot'],
    queryFn: dashboardMockApiService.getAISnapshot,
  });
};

export const useModelRiskTrends = () => {
  return useQuery({
    queryKey: ['model-risk-trends'],
    queryFn: dashboardMockApiService.getModelRiskTrends,
  });
};

export const useDashboardStats = () => {
  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: dashbpardApiServices.getDashboardStats,
    retry: 1
  });
};

export const useDomainAssets = () => {
  return useQuery({
    queryKey: ['domain-assets'],
    queryFn: dashbpardApiServices.getDomainAssets,
  });
};

export const usePlatformUsage = () => {
  return useQuery({
    queryKey: ['platform-usage'],
    queryFn: dashbpardApiServices.getPlatformUsage,
  });
};

export const useRecentlyViewed = (userUrn: string) => {
  return useQuery({
    queryKey: ['recently-viewed'],
    queryFn: () => dashbpardApiServices.getRecentlyViewed(userUrn),
    enabled: !!userUrn,
  });
};

export const useRecentActivity = (userUrn: string) => {
  return useQuery({
    queryKey: ['recent-activity'],
    queryFn: () => dashbpardApiServices.getRecentActivity(userUrn),
    enabled: !!userUrn,
  });
};
