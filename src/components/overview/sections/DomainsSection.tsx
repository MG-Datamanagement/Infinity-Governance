/**
 * DomainsSection
 *
 * Top Domains list card.
 * Uses SectionCard for the consistent header pattern.
 */

import { TrendingUp, ArrowUpRight } from "lucide-react";
import { InlineState } from "@/components/ui/InlineState";
import { OverviewData } from "@/hooks/useOverviewData";
import { SectionCard } from "../cards/SectionCard";

type Props = {
  query: OverviewData["domains"];
};

export function DomainsSection({ query }: Props) {
  const { data: domains, isLoading, error, refetch } = query;

  return (
    <SectionCard
      title="Top Domains"
      icon={<ArrowUpRight size={16} className="text-green-600" />}
      isLoading={isLoading}
    >
      {isLoading && (
        <InlineState type="loading" message="Loading domains..." />
      )}

      {error && (
        <InlineState
          type="error"
          message="Failed to load domains."
          onRetry={refetch}
        />
      )}

      {!isLoading && !error && domains?.length === 0 && (
        <InlineState type="empty" message="No domains available." />
      )}

      {!isLoading && !error && domains && domains.length > 0 && (
        <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
          {domains.map((domain, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between py-1"
            >
              <span className="text-sm text-gray-700">{domain.domain}</span>
              <span className="text-sm font-medium text-gray-900">
                {domain.count} {domain.count === 1 ? "asset" : "assets"}
              </span>
            </div>
          ))}
        </div>
      )}
    </SectionCard>
  );
}