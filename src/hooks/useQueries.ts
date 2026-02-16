import { useQuery } from '@tanstack/react-query';
import { mockApiService } from '@/services/mock';
import { apiServices } from '@/services/apiServices';

export const useComplianceFrameworks = () => {
  return useQuery({
    queryKey: ['compliance-frameworks'],
    queryFn: mockApiService.getComplianceFrameworks,
  });
};

export const useComplianceIssues = () => {
  return useQuery({
    queryKey: ['compliance-issues'],
    queryFn: mockApiService.getComplianceIssues,
  });
};

export const useComplianceTrends = () => {
  return useQuery({
    queryKey: ['compliance-trends'],
    queryFn: mockApiService.getComplianceTrends,
  });
};

export const useDashboardStats = () => {
  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: apiServices.getDashboardStats,
    retry: 1
  });
};

export const useAISnapshot = () => {
  return useQuery({
    queryKey: ['ai-snapshot'],
    queryFn: mockApiService.getAISnapshot,
  });
};

export const useModelRiskTrends = () => {
  return useQuery({
    queryKey: ['model-risk-trends'],
    queryFn: mockApiService.getModelRiskTrends,
  });
};

export const useDomainAssets = () => {
  return useQuery({
    queryKey: ['domain-assets'],
    queryFn: apiServices.getDomainAssets,
  });
};

export const usePlatformUsage = () => {
  return useQuery({
    queryKey: ['platform-usage'],
    queryFn: apiServices.getPlatformUsage,
  });
};

export const useRecentlyViewed = (userUrn: string) => {
  return useQuery({
    queryKey: ['recently-viewed'],
    queryFn: () => apiServices.getRecentlyViewed(userUrn),
    enabled: !!userUrn,
  });
};

export const useRecentActivity = (userUrn: string) => {
  return useQuery({
    queryKey: ['recent-activity'],
    queryFn: () => apiServices.getRecentActivity(userUrn),
    enabled: !!userUrn,
  });
};
