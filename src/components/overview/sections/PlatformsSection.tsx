/**
 * PlatformsSection
 *
 * Top Platforms list card.
 * Uses SectionCard for the consistent header pattern.
 */

import { Database } from "lucide-react";
import { InlineState } from "@/components/ui/InlineState";
import { SectionCard } from "../cards/SectionCard";
import { OverviewData } from "@/hooks/useOverviewData";
import { getPlatformColor } from "@/lib/utils";

type Props = {
  query: OverviewData["platforms"];
};

export function PlatformsSection({ query }: Props) {
  const { data: platforms, isLoading, error, refetch } = query;

  return (
    <SectionCard
      title="Top Platforms"
      icon={<Database size={16} className="text-blue-800" />}
      isLoading={isLoading}
    >
      {isLoading && (
        <InlineState type="loading" message="Loading platforms..." />
      )}

      {error && (
        <InlineState
          type="error"
          message="Failed to load platforms."
          onRetry={refetch}
        />
      )}

      {!isLoading && !error && platforms?.length === 0 && (
        <InlineState type="empty" message="No platform activity detected." />
      )}

      {!isLoading && !error && platforms && platforms.length > 0 && (
        <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
          {platforms.map((platform, idx) => (
            <div key={idx} className="flex items-center justify-between py-1">
              <div className="flex items-center gap-2">
                {/* <div className="w-2 h-2 rounded-full bg-primary flex-shrink-0" /> */}
                <div
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{
                    backgroundColor: getPlatformColor(platform.platform),
                  }}
                />
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
    </SectionCard>
  );
}
