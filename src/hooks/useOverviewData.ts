/**
 * useOverviewData
 *
 * Single aggregation hook for the Overview page.
 * All query calls live here so the page component stays clean and
 * other pages can import individual slices if needed.
 *
 * Pattern: each slice is independently loadable — the page renders
 * progressively rather than waiting for a single monolithic fetch.
 */

import {
  useDashboardStats,
  useAISnapshot,
  useModelRiskTrends,
  useDomainAssets,
  usePlatformUsage,
  useRecentActivity,
  useComplianceFrameworks,
  useRecentlyViewed,
  usePendingReviewCount,
  useOpenIssues,
  useGovernanceScore,
  useComplianceOverview,
} from "@/hooks/useDashboardQueries";

const USER_URN = "urn:li:corpuser:datahub";

export function useOverviewData() {
  const stats = useDashboardStats();
  const aiSnapshot = useAISnapshot();
  const riskTrends = useModelRiskTrends();
  const domains = useDomainAssets();
  const platforms = usePlatformUsage();
  const activity = useRecentActivity(USER_URN);
  const recentlyViewed = useRecentlyViewed(USER_URN);
  const frameworks = useComplianceFrameworks();
  const pendingReviewCount = usePendingReviewCount();
  const openIssues = useOpenIssues();
  const governanceScore = useGovernanceScore();
  const complianceOverview = useComplianceOverview();

  return {
    stats,
    aiSnapshot,
    riskTrends,
    domains,
    platforms,
    activity,
    recentlyViewed,
    frameworks,
    pendingReviewCount,
    openIssues,
    governanceScore,
    complianceOverview,
  } as const;
}

/** Re-export the type so sections can import it without re-running the hook */
export type OverviewData = ReturnType<typeof useOverviewData>;