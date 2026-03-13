/**
 * Overview Page
 *
 * Orchestrator only — owns layout and wires data to sections.
 * No rendering logic lives here; each section is independently
 * loadable, retryable, and swappable.
 */

"use client";

import { LoadingFallback, DataErrorFallback } from "@/components/Fallbacks";
import { TabNavigation } from "@/components/ui/TabNavigation";
import { useOverviewData } from "../../../hooks/useOverviewData";
import {
  ActivitySection,
  AIGovernanceSection,
  ComplianceSection,
  DomainsSection,
  OverviewHeader,
  OverviewStatsGrid,
  PlatformsSection,
} from "@/components/overview/sections";
import { ErrorBoundary } from "@/components/ErrorBoundary";

// ---------------------------------------------------------------------------
// Inner content — rendered only after the critical stats fetch resolves
// ---------------------------------------------------------------------------
function OverviewContent() {
  const {
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
  } = useOverviewData();

  // Stats is the page's "critical path" — block only on this one query
  if (stats.isLoading) return <LoadingFallback />;
  if (stats.error) return <DataErrorFallback retry={stats.refetch} />;

  return (
    <div className="max-w-7xl mx-auto px-8 py-8 space-y-5">
      <TabNavigation />
      <OverviewHeader />

      {/* Main two-column layout */}
      <div className="flex flex-col gap-5">
        <OverviewStatsGrid
          stats={stats.data!}
        />

        <div className="grid lg:grid-cols-12 gap-5">
          <ComplianceSection query={frameworks} overviewQuery={complianceOverview} />
          <AIGovernanceSection aiQuery={aiSnapshot} trendsQuery={riskTrends} />
          <ActivitySection
            activityQuery={activity}
            recentlyViewedQuery={recentlyViewed}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <DomainsSection query={domains} />
          <PlatformsSection query={platforms} />
        </div>
      </div>
    </div>
  );
}

export default function OverviewPage() {
  return (
    <ErrorBoundary>
      <OverviewContent />
    </ErrorBoundary>
  );
}
