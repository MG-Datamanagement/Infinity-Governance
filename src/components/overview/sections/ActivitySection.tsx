/**
 * ActivitySection
 *
 * Right-column panel containing two tabs:
 *  - Recent Activity
 *  - Recently Viewed
 *
 * Local tab state lives here; the parent page passes the two query
 * slices without caring which tab is active.
 */

import { useState } from "react";
import { Activity, Clock, Database } from "lucide-react";
import { cn } from "@/lib/utils";
import { InlineState } from "@/components/ui/InlineState";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { OverviewData } from "@/hooks/useOverviewData";

type Tab = "recent" | "viewed";

type Props = {
  activityQuery: OverviewData["activity"];
  recentlyViewedQuery: OverviewData["recentlyViewed"];
};

const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: "recent", label: "Recent Activity", icon: Activity },
  { id: "viewed", label: "Recently Viewed", icon: Clock },
];

const MAX_VISIBLE_ITEMS = 10;

type ActivityItemProps = {
  name: string;
  platform: string;
  type: string;
};

function ActivityItem({ name, platform, type }: ActivityItemProps) {
  return (
    <div className="px-2 md:px-4 py-3 hover:bg-gray-50 cursor-pointer">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-purple-100 rounded flex items-center justify-center flex-shrink-0">
          <Database size={14} className="text-purple-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div title={name} className="text-xs font-medium text-gray-900 truncate">
            {name}
          </div>
          {/* {platform && type && (
            <div className="text-xs text-gray-500">
              {platform} • {type}
            </div>
          )} */}
        </div>
      </div>
    </div>
  );
}

function ActivityContent({ activityQuery, recentlyViewedQuery }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("recent");

  const {
    data: activity,
    isLoading: activityLoading,
    error: activityError,
    refetch: refetchActivity,
  } = activityQuery;

  const {
    data: recentlyViewed,
    isLoading: recentlyViewedLoading,
    error: recentlyViewedError,
    refetch: refetchRecentlyViewed,
  } = recentlyViewedQuery;

  const isRecent = activeTab === "recent";
  const isLoading = isRecent ? activityLoading : recentlyViewedLoading;
  const hasError = isRecent ? activityError : recentlyViewedError;
  const onRetry = isRecent ? refetchActivity : refetchRecentlyViewed;
  const items = isRecent ? activity : recentlyViewed;

  const viewAllLabel = isRecent
    ? "View all recent activity"
    : "View all recently viewed";

  return (
    <div className="card overflow-hidden flex flex-col">
      {/* Tab Header */}
      <div className="flex items-center justify-center">
        <div className="flex gap-2 border-b border-gray-200">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={cn(
                "px-1.5 py-2.5 text-xs/3 font-medium border-b-2 transition-colors flex items-center gap-1",
                activeTab === id
                  ? "text-primary border-primary"
                  : "text-gray-500 border-transparent hover:text-gray-700",
              )}
            >
              <Icon size={15} />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Body */}
      <div className="flex-1 overflow-y-auto">
        <div className="divide-y divide-gray-100">
          {isLoading && (
            <InlineState
              type="loading"
              message={
                isRecent
                  ? "Loading recent activity..."
                  : "Loading recently viewed..."
              }
            />
          )}

          {!isLoading && hasError && (
            <InlineState
              type="error"
              message={
                isRecent
                  ? "Failed to load recent activity."
                  : "Failed to load recently viewed."
              }
              onRetry={onRetry}
            />
          )}

          {!isLoading && !hasError && items?.length === 0 && (
            <InlineState
              type="empty"
              message={
                isRecent
                  ? "No recent activity yet."
                  : "You haven't viewed any assets yet."
              }
            />
          )}

          {!isLoading &&
            !hasError &&
            items &&
            items.length > 0 &&
            items
              .slice(0, MAX_VISIBLE_ITEMS)
              .map((item) => (
                <ActivityItem
                  key={item.id}
                  name={item.name || ""}
                  platform={item.platform || ""}
                  type={item.type}
                />
              ))}
        </div>
      </div>

      {/* Footer */}
      <div className="p-2 border-t border-gray-200">
        <button
          disabled
          className="text-primary text-sm font-medium hover:underline w-full text-center disabled:text-gray-300 disabled:cursor-not-allowed"
        >
          {viewAllLabel}
        </button>
      </div>
    </div>
  );
}

export function ActivitySection(props: Props) {
  return (
    <ErrorBoundary>
      <ActivityContent {...props} />
    </ErrorBoundary>
  );
}
