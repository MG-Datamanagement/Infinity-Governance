"use client";

import {
  useDashboardStats,
  useAISnapshot,
  useModelRiskTrends,
  useDomainAssets,
  usePlatformUsage,
  useRecentActivity,
  useComplianceFrameworks,
  useRecentlyViewed,
} from "@/hooks/useQueries";
import { StatCard } from "@/components/ui/StatCard";
import { ModelRiskChart } from "@/components/charts/ModelRiskChart";
import { LoadingFallback, DataErrorFallback } from "@/components/Fallbacks";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { TabNavigation } from "@/components/ui/TabNavigation";
import {
  Database,
  Shield,
  Tag,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Eye,
  Clock,
  Activity,
  Table,
  Globe,
  LucideLoader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";
import { InlineState } from "@/components/InlineState";

function OverviewContent() {
  const [activityTab, setActivityTab] = useState<"recent" | "viewed">("recent");
  const [showQuickActions, setShowQuickActions] = useState(false);

  const userUrn = "urn:li:corpuser:datahub";

  const {
    data: stats,
    isLoading: statsLoading,
    error: statsError,
    refetch: refetchStats,
  } = useDashboardStats();
  const {
    data: aiSnapshot,
    isLoading: aiLoading,
    error: aiError,
    refetch: refetchAI,
  } = useAISnapshot();
  const { data: riskTrends, isLoading: trendsLoading } = useModelRiskTrends();
  const {
    data: domains,
    isLoading: domainsLoading,
    error: domainsError,
    refetch: refetchDomains,
  } = useDomainAssets();
  const {
    data: platforms,
    isLoading: platformsLoading,
    error: platformsError,
    refetch: refetchPlatforms,
  } = usePlatformUsage();
  const {
    data: activity,
    isLoading: activityLoading,
    error: activityError,
    refetch: refetchActivity,
  } = useRecentActivity(userUrn);

  const {
    data: recentlyViewed,
    isLoading: recentlyViewedLoading,
    error: recentlyViewedError,
    refetch: refetchRecentlyViewed,
  } = useRecentlyViewed(userUrn);
  const {
    data: frameworks,
    isLoading: frameworksLoading,
    error: frameworksError,
    refetch: refetchFrameworks,
  } = useComplianceFrameworks();

  if (statsLoading) {
    return <LoadingFallback />;
  }

  if (statsError) {
    return <DataErrorFallback retry={refetchStats} />;
  }

  return (
    <div className="p-4 md:p-3 space-y-3">
      {/* Tab Navigation */}
      <TabNavigation />

      {/* Action Button */}
      <div className="flex flex-col lg:flex-row items-center justify-between gap-4">
        <div>
          <p className="text-sm text-gray-600 font-medium">
            Monitor your data governance health and activities
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div>
            <button
              onClick={() => {}}
              className="px-2 py-2 bg-primary text-white text-xs font-medium rounded-md hover:bg-primary-dark transition-colors flex items-center gap-2 whitespace-nowrap"
            >
              <Database size={16} />
              Add Data Source
            </button>
          </div>
          <div>
            <select
              aria-label="Quick Actions"
              className="px-2 py-2 text-gray-800 text-xs font-medium rounded-md border-2 border-gray-200 bg-white transition-colors flex items-center whitespace-nowrap"
            >
              <option disabled selected hidden defaultValue="">
                Quick Actions
              </option>
              <option value="exportReport">Export Report</option>
              <option value="runScan">Run Scan</option>
              <option value="settings">Settings</option>
            </select>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[6fr_2fr] gap-2">
        <div className="grid lg:grid-rows-[1fr_5fr] gap-2">
          {/* Stats Grid */}
          <div className="grid xs:grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">
            <StatCard
              icon={Database}
              iconColor="text-blue-600"
              label="Total Assets"
              value={stats?.totalAssets || 0}
              change={stats?.totalAssetsChange}
              changeType="positive"
            />
            <StatCard
              icon={Shield}
              iconColor="text-green-600"
              label="Governance Score"
              value={`${stats?.governanceScore}%` || "0%"}
              change={stats?.governanceScoreStatus}
              changeType="neutral"
            />
            <StatCard
              icon={Tag}
              iconColor="text-blue-600"
              label="Classified"
              value={stats?.classified || 0}
              change={stats?.classifiedChange}
              changeType="positive"
            />
            <StatCard
              icon={Eye}
              iconColor="text-yellow-600"
              label="Pending Review"
              value={stats?.pendingReview || 0}
            />
            <StatCard
              icon={Globe}
              iconColor="text-gray-600"
              label="Active Domains"
              value={stats?.activeDomains || 0}
            />
            <StatCard
              icon={Table}
              iconColor="text-gray-600"
              label="Active Tables"
              value={stats?.activeTables || 0}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {/* Compliance Overview */}
            <div className="grid">
              <ErrorBoundary>
                <div className="card p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="text-sm font-semibold text-gray-900">
                      Compliance Overview
                    </h3>
                    <Shield className="text-green-600" size={16} />
                  </div>
                  <>
                    {frameworksLoading && (
                      <InlineState
                        type="loading"
                        message="Checking compliance frameworks..."
                      />
                    )}

                    {frameworksError && (
                      <InlineState
                        type="error"
                        message="Failed to load compliance data."
                        onRetry={refetchFrameworks}
                      />
                    )}

                    {!frameworksLoading &&
                      !frameworksError &&
                      frameworks &&
                      frameworks.length === 0 && (
                        <InlineState
                          type="empty"
                          message="No compliance frameworks configured yet."
                        />
                      )}

                    {!frameworksLoading &&
                      !frameworksError &&
                      frameworks &&
                      frameworks.length > 0 && (
                        <div className="space-y-4">
                          <div className="p-1.5 bg-green-100/40 rounded-lg">
                            <p className="text-xs text-gray-600 leading-normal">
                              Your governance is in excellent shape! All
                              critical compliance frameworks are above 90%, with
                              GDPR and SOC 2 leading at 96% and 98%. HIPAA needs
                              attention at 79% - consider reviewing data
                              classification policies.
                            </p>
                          </div>

                          <div className="max-h-44 overflow-y-auto pr-1">
                            {frameworks.map((framework) => (
                              <div
                                key={framework.id}
                                className="flex-col items-center justify-between space-y-2"
                              >
                                <div className="flex justify-between items-center">
                                  <div className="text-xs text-gray-700">
                                    {framework.name}
                                  </div>
                                  <div className="text-sm font-medium text-gray-900 text-right">
                                    {framework.score}%
                                  </div>
                                </div>
                                <div className="gap-2">
                                  <div className="bg-gray-200 rounded-full h-2">
                                    <div
                                      className={cn(
                                        "h-2 rounded-full transition-all",
                                        framework.status === "excellent"
                                          ? "bg-success"
                                          : framework.status === "warning"
                                            ? "bg-warning"
                                            : "bg-danger",
                                      )}
                                      style={{ width: `${framework.score}%` }}
                                    />
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>

                          <div>
                            <button
                              disabled
                              className="w-full p-1 text-sm text-center rounded-md bg-gray-100 text-gray-800 font-medium hover:bg-gray-200 hover:text-primary disabled:cursor-not-allowed"
                            >
                              Details →
                            </button>
                          </div>
                        </div>
                      )}
                  </>
                </div>
              </ErrorBoundary>
            </div>

            {/* AI Governance Snapshot */}
            <div className="grid card p-4">
              <div className="mb-2">
                <h3 className="text-sm font-semibold text-gray-900">
                  AI Governance Snapshot
                </h3>
                <p className="text-[10px] text-gray-400">
                  Real-time AI model monitoring
                </p>
              </div>

              <>
                {aiLoading && (
                  <InlineState
                    type="loading"
                    message="Loading AI governance metrics..."
                  />
                )}

                {aiError && (
                  <InlineState
                    type="error"
                    message="Unable to fetch AI metrics."
                    onRetry={refetchAI}
                  />
                )}

                {!aiLoading && !aiError && !aiSnapshot && (
                  <InlineState
                    type="empty"
                    message="No AI models monitored yet."
                  />
                )}

                {!aiLoading && !aiError && aiSnapshot && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <CheckCircle
                          size={15}
                          className="text-green-600 flex-shrink-0"
                        />
                        <span className="text-xs text-gray-700">
                          Models in Production:
                        </span>
                      </div>
                      <span className="text-xs font-semibold text-gray-900">
                        {aiSnapshot.modelsInProduction}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <AlertTriangle
                          size={15}
                          className="text-yellow-600 flex-shrink-0"
                        />
                        <span className="text-xs text-gray-700">
                          Flagged Prompts Today:
                        </span>
                      </div>
                      <span className="text-xs font-semibold text-gray-900">
                        {aiSnapshot.flaggedPromptsToday}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <TrendingUp
                          size={15}
                          className="text-blue-600 flex-shrink-0"
                        />
                        <span className="text-xs text-gray-700">
                          AI Fairness Score:
                        </span>
                      </div>
                      <span className="text-xs font-semibold text-gray-900">
                        {aiSnapshot.aiFairnessScore}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Eye size={15} className="text-red-600 flex-shrink-0" />
                        <span className="text-xs text-gray-700">
                          Models Needing Review:
                        </span>
                      </div>
                      <span className="text-xs font-semibold text-red-600">
                        {aiSnapshot.modelsNeedingReview}
                      </span>
                    </div>

                    {/* Model Risk Trend */}
                    <div className="mt-6 pt-2">
                      <div>
                        <h4 className="text-xs text-gray-500 uppercase mb-2">
                          Model Risk Trend
                        </h4>
                      </div>
                      <div>
                        {!trendsLoading && riskTrends && (
                          <ModelRiskChart data={riskTrends} />
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </>
            </div>

            {/* Top Domains */}
            <div className="card p-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex justify-between items-center gap-2">
                  <h3 className="font-semibold text-gray-900">Top Domains</h3>
                  <TrendingUp size={16} className="text-green-600" />
                </div>
                {domainsLoading ? (
                  <LucideLoader2 size={16} className="text-primary" />
                ) : (
                  <button
                    disabled
                    className="text-primary text-sm font-medium hover:underline disabled:text-gray-300 disabled:cursor-not-allowed"
                  >
                    View All →
                  </button>
                )}
                {/* <button
                  disabled
                  className="text-primary text-sm font-medium hover:underline disabled:text-gray-300 disabled:cursor-not-allowed"
                >
                  View All →
                </button> */}
              </div>

              <>
                {domainsLoading && (
                  <InlineState type="loading" message="Loading domains..." />
                )}

                {domainsError && (
                  <InlineState
                    type="error"
                    message="Failed to load domains."
                    onRetry={refetchDomains}
                  />
                )}

                {!domainsLoading &&
                  !domainsError &&
                  domains &&
                  domains.length === 0 && (
                    <InlineState type="empty" message="No domains available." />
                  )}

                {!domainsLoading &&
                  !domainsError &&
                  domains &&
                  domains.length > 0 && (
                    <div className="space-y-2 max-h-44 overflow-y-auto pr-1">
                      {domains.map((domain, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between py-1"
                        >
                          <span className="text-sm text-gray-700">
                            {domain.domain}
                          </span>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-gray-900">
                              {domain.count}{" "}
                              {domain.count === 1 ? "asset" : "assets"}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
              </>
            </div>

            {/* Top Platforms */}
            <div className="card p-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex justify-between items-center gap-2">
                  <h3 className="font-semibold text-gray-900">Top Platforms</h3>
                  <Database size={16} className="text-blue-800" />
                </div>
                {platformsLoading ? (
                  <LucideLoader2 size={16} className="text-primary" />
                ) : (
                  <button
                    disabled
                    className="text-primary text-sm font-medium hover:underline disabled:text-gray-300 disabled:cursor-not-allowed"
                  >
                    View All →
                  </button>
                )}
                {/* <button
                  disabled
                  className="text-primary text-sm font-medium hover:underline disabled:text-gray-300 disabled:cursor-not-allowed"
                >
                  View All →
                </button> */}
              </div>

              <>
                {platformsLoading && (
                  <InlineState type="loading" message="Loading platforms..." />
                )}

                {platformsError && (
                  <InlineState
                    type="error"
                    message="Failed to load platforms."
                    onRetry={refetchPlatforms}
                  />
                )}

                {!platformsLoading &&
                  !platformsError &&
                  platforms &&
                  platforms.length === 0 && (
                    <InlineState
                      type="empty"
                      message="No platform activity detected."
                    />
                  )}

                {!platformsLoading &&
                  !platformsError &&
                  platforms &&
                  platforms.length > 0 && (
                    <div className="space-y-2 max-h-44 overflow-y-auto pr-1">
                      {platforms.map((platform, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between py-1"
                        >
                          <div className="flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-primary flex-shrink-0"></div>
                            <span className="text-sm text-gray-700">
                              {platform.platform}
                            </span>
                          </div>
                          <span className="text-sm font-medium text-gray-900">
                            {platform.count}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
              </>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="grid">
          <ErrorBoundary>
            <div className="card overflow-hidden flex flex-col">
              <div className="flex items-center justify-center">
                {/* Tabs */}
                <div className="flex gap-2 border-b border-gray-200">
                  <button
                    onClick={() => setActivityTab("recent")}
                    className={cn(
                      "px-1.5 py-2.5 text-xs/3 font-medium border-b-2 transition-colors flex items-center gap-1",
                      activityTab === "recent"
                        ? "text-primary border-primary"
                        : "text-gray-500 border-transparent hover:text-gray-700",
                    )}
                  >
                    <Activity size={15} />
                    Recent Activity
                  </button>
                  <button
                    onClick={() => setActivityTab("viewed")}
                    className={cn(
                      "px-1.5 py-2.5 text-xs/3 font-medium border-b-2 transition-colors flex items-center gap-1",
                      activityTab === "viewed"
                        ? "text-primary border-primary"
                        : "text-gray-500 border-transparent hover:text-gray-700",
                    )}
                  >
                    <Clock size={15} />
                    Recently Viewed
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto">
                <div className="divide-y divide-gray-100">
                  <>
                    {/* Loading State */}
                    {activityTab === "recent" && activityLoading && (
                      <InlineState
                        type="loading"
                        message="Loading recent activity..."
                      />
                    )}

                    {activityTab === "viewed" && recentlyViewedLoading && (
                      <InlineState
                        type="loading"
                        message="Loading recently viewed..."
                      />
                    )}

                    {/* Error State */}
                    {activityTab === "recent" && activityError && (
                      <InlineState
                        type="error"
                        message="Failed to load recent activity."
                        onRetry={refetchActivity}
                      />
                    )}

                    {activityTab === "viewed" && recentlyViewedError && (
                      <InlineState
                        type="error"
                        message="Failed to load recently viewed."
                        onRetry={refetchRecentlyViewed}
                      />
                    )}

                    {/* Empty State */}
                    {activityTab === "recent" &&
                      !activityLoading &&
                      !activityError &&
                      activity &&
                      activity.length === 0 && (
                        <InlineState
                          type="empty"
                          message="No recent activity yet."
                        />
                      )}

                    {activityTab === "viewed" &&
                      !recentlyViewedLoading &&
                      !recentlyViewedError &&
                      recentlyViewed &&
                      recentlyViewed.length === 0 && (
                        <InlineState
                          type="empty"
                          message="You haven't viewed any assets yet."
                        />
                      )}
                  </>

                  {activityTab === "recent" &&
                    !activityLoading &&
                    !activityError &&
                    activity &&
                    activity.length > 0 &&
                    activity.slice(0, 10).map((item) => (
                      <div
                        key={item.id}
                        className="px-2 md:px-4 py-3 hover:bg-gray-50 cursor-pointer"
                      >
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 bg-purple-100 rounded flex items-center justify-center flex-shrink-0">
                            <Database size={14} className="text-purple-600" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-xs font-medium text-gray-900 truncate">
                              {item.name}
                            </div>
                            <div className="text-xs text-gray-500">
                              {item.platform} • {item.type}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}

                  {activityTab === "viewed" &&
                    !recentlyViewedLoading &&
                    !recentlyViewedError &&
                    recentlyViewed &&
                    recentlyViewed.length > 0 &&
                    recentlyViewed.slice(0, 10).map((item) => (
                      <div
                        key={item.id}
                        className="px-2 md:px-4 py-3 hover:bg-gray-50 cursor-pointer"
                      >
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 bg-purple-100 rounded flex items-center justify-center flex-shrink-0">
                            <Database size={14} className="text-purple-600" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-xs font-medium text-gray-900 truncate">
                              {item.name}
                            </div>
                            <div className="text-xs text-gray-500">
                              {item.platform} • {item.type}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              <div className="p-2 border-t border-gray-200">
                <button
                  disabled
                  className="text-primary text-sm font-medium hover:underline w-full text-center disabled:text-gray-300 disabled:cursor-not-allowed"
                >
                  {activityTab === "viewed"
                    ? "View all recently viewed"
                    : "View all recent activity"}
                </button>
              </div>
            </div>
          </ErrorBoundary>
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
