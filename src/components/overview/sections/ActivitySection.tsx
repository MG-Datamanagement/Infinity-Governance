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

import { Activity, Clock, Database } from "lucide-react";
import { cn, formatTimeAgo } from "@/lib/utils";
import { InlineState } from "@/components/ui/InlineState";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { OverviewData } from "@/hooks/useOverviewData";
import { IconType } from "react-icons/lib";
import { ActivityTabType, useAppStore } from "@/store/appStore";
import { RecentActivity, RecentlyViewed } from "@/types";

type Props = {
  activityQuery: OverviewData["activity"];
  recentlyViewedQuery: OverviewData["recentlyViewed"];
};

const TABS: { id: ActivityTabType; label: string; icon: React.ElementType }[] =
  [
    { id: "recent", label: "Recent Activity", icon: Activity },
    { id: "viewed", label: "Recently Viewed", icon: Clock },
  ];

const MAX_RECENT_ACTIVITY_VISIBLE_ITEMS = 6;
const MAX_RECENTLY_VIEWED_VISIBLE_ITEMS = 5;

type ActivityItemProps = {
  name: string;
  platform: string;
  type: string;
};

function ActivityItem({ name, platform, type }: ActivityItemProps) {
  return (
    <div className="p-2 hover:bg-gray-50 cursor-pointer">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-purple-100 rounded flex items-center justify-center flex-shrink-0">
          <Database size={14} className="text-purple-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div
            title={name}
            className="text-xs font-medium text-gray-900 truncate"
          >
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

type ActivityItemV2Props = {
  name: string;
  platform?: string;
  tag?: string;
  tagColor?: string;
  time?: string;
  icon: IconType;
  iconColor: string;
};

function ActivityItemV2({
  name,
  platform,
  tag,
  tagColor,
  time,
  icon,
  iconColor,
}: ActivityItemV2Props) {
  const PlatformIcon = icon;
  return (
    <div className="p-3 hover:bg-gray-50 cursor-pointer transition-colors">
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="w-9 h-9 bg-gray-100 rounded-md flex items-center justify-center flex-shrink-0">
          <PlatformIcon size={16} className={cn(iconColor)} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <div
              title={name}
              className="text-sm font-medium text-gray-900 truncate"
            >
              {name}
            </div>

            {tag && <ComplianceBadge label={tag} color={tagColor || ""} />}
          </div>

          <div className="flex items-center justify-between mt-1">
            <div className="text-xs text-gray-500 truncate">{platform}</div>

            {time && (
              <div className="text-[10px] text-gray-400">
                {formatTimeAgo(time)}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

type TimelineActivityItemProps = {
  name: string;
  time: string;
};

function TimelineActivityItem({ name, time }: TimelineActivityItemProps) {
  return (
    <div className="relative pl-6 py-3">
      {/* Vertical Line */}
      <div className="absolute left-[10px] top-5 -bottom-6 w-px bg-gray-200" />

      {/* Dot */}
      <div className="absolute left-[5px] top-5 w-2.5 h-2.5 rounded-full bg-indigo-600 border-2 border-white" />

      {/* Content */}
      <div>
        <div className="text-xs font-medium text-gray-800 line-clamp-2">
          {name}
        </div>
        {time && (
          <div className="text-[10px] text-gray-500 mt-1">
            {formatTimeAgo(time)}
          </div>
        )}
      </div>
    </div>
  );
}

function ComplianceBadge({ label, color }: { label: string; color: string }) {
  const colorMap: Record<string, string> = {
    yellow: "bg-yellow-50 text-yellow-700 border-yellow-200",
    blue: "bg-blue-50 text-blue-700 border-blue-200",
    red: "bg-red-50 text-red-700 border-red-200",
    green: "bg-green-50 text-green-700 border-green-200",
    indigo: "bg-indigo-50 text-indigo-700 border-indigo-200",
  };

  return (
    <span
      className={cn(
        "text-[10px] px-2 py-0.5 rounded-md border font-medium",
        colorMap[color] || "bg-gray-100 text-gray-700 border-gray-200",
      )}
    >
      {label}
    </span>
  );
}

function ActivityContent({ activityQuery, recentlyViewedQuery }: Props) {
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

  const activeTab = useAppStore((s) => s.activityTab);
  const setActivityTab = useAppStore((s) => s.setActivityTab);
  const isRecent = activeTab === "recent";
  const isLoading = isRecent ? activityLoading : recentlyViewedLoading;
  const hasError = isRecent ? activityError : recentlyViewedError;
  const onRetry = isRecent ? refetchActivity : refetchRecentlyViewed;
  const items: RecentActivity[] | RecentlyViewed[] | undefined = isRecent
    ? activity
    : recentlyViewed;

  const viewAllLabel = isRecent ? "View All Activity" : "View All Datasets";

  return (
    <div className="overflow-hidden lg:col-span-3">
      {/* Tab Header */}
      <div className="px-2 py-0">
        <div className="flex justify-between items-center border-b border-gray-200">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActivityTab(id)}
              className={cn(
                "px-1 py-2 text-[10px] font-medium border-b-2 transition-colors flex items-center gap-1 outline-none",
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
      <div className="flex-1 max-h-[400px] p-2">
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

          {!isLoading && !hasError && activeTab === "recent" && (
            <>
              {items &&
                items.length > 0 &&
                items
                  .slice(0, MAX_RECENT_ACTIVITY_VISIBLE_ITEMS)
                  .map((item) => (
                    <TimelineActivityItem
                      key={item.id}
                      name={item.name}
                      time={item.time || ""}
                    />
                  ))}
            </>
          )}

          {!isLoading && !hasError && activeTab === "viewed" && (
            <>
              {items &&
                items.length > 0 &&
                (items as RecentlyViewed[])
                  .slice(0, MAX_RECENTLY_VIEWED_VISIBLE_ITEMS)
                  .map((item) => (
                    <ActivityItemV2
                      key={item.id}
                      name={item.name}
                      platform={item.platform}
                      tag={item.tag}
                      tagColor={item.tagColor}
                      time={item.time || ""}
                      icon={item.icon}
                      iconColor={item.iconColor}
                    />
                  ))}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-1">
          <button className="text-indigo-600 text-xs hover:text-indigo-600 hover:underline transition-colors">
            {viewAllLabel}
          </button>
        </div>
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
