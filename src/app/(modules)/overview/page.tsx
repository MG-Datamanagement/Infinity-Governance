/**
 * Overview Page
 *
 * Orchestrator only — owns layout and wires data to sections.
 * No rendering logic lives here; each section is independently
 * loadable, retryable, and swappable.
 */

"use client";

import { ErrorBoundary } from "@/components/ErrorBoundary";
import { LoadingFallback, DataErrorFallback } from "@/components/Fallbacks";
import { TabNavigation } from "@/components/ui/TabNavigation";
import { useOverviewData } from "./hooks/useOverviewData";
import { ActivitySection, AIGovernanceSection, ComplianceSection, DomainsSection, OverviewHeader, OverviewStatsGrid, PlatformsSection } from "./components/sections";

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
  } = useOverviewData();

  // Stats is the page's "critical path" — block only on this one query
  if (stats.isLoading) return <LoadingFallback />;
  if (stats.error) return <DataErrorFallback retry={stats.refetch} />;

  return (
    <div className="p-4 md:p-3 space-y-3">
      <TabNavigation />
      <OverviewHeader />

      {/* Main two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-[6fr_2fr] gap-2">
        {/* Left column */}
        <div className="grid lg:grid-rows-[1fr_5fr] gap-2">
          {/* KPI row */}
          <OverviewStatsGrid stats={stats.data!} />

          {/* Card grid: 2-up top, 2-up bottom */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            <ComplianceSection query={frameworks} />
            <AIGovernanceSection
              aiQuery={aiSnapshot}
              trendsQuery={riskTrends}
            />
            <DomainsSection query={domains} />
            <PlatformsSection query={platforms} />
          </div>
        </div>

        {/* Right column — activity panel */}
        <ActivitySection
          activityQuery={activity}
          recentlyViewedQuery={recentlyViewed}
        />
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
