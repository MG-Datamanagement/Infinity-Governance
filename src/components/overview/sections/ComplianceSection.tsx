/**
 * ComplianceSection
 *
 * Compliance frameworks progress card.
 * Manages its own loading / error / empty states via InlineState.
 * Receives the raw query slice from useOverviewData so it is decoupled
 * from fetching but still independently retryable.
 */

import { ShieldCheckIcon, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { InlineState } from "@/components/ui/InlineState";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { OverviewData } from "@/hooks/useOverviewData";
import { MarkdownRenderer } from "@/components/ui/MarkdownRenderer";

type Props = {
  query: OverviewData["frameworks"];
  overviewQuery: OverviewData["complianceOverview"];
};

function ComplianceContent({ query, overviewQuery }: Props) {
  const { data: frameworks, isLoading: isFrameworksLoading, error: frameworksError, refetch: refetchFrameworks } = query;
  const { data: overview, isLoading: isOverviewLoading, error: overviewError, refetch: refetchOverview } = overviewQuery;

  const isLoading = isFrameworksLoading || isOverviewLoading;
  const error = frameworksError || overviewError;
  const refetch = () => {
    refetchFrameworks();
    refetchOverview();
  };

  return (
    <div className="card p-6 space-y-4 lg:col-span-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">
          Compliance Overview
        </h3>
        <div>
          <ShieldCheckIcon className="text-green-600" size={16} />
        </div>
      </div>

      {isLoading && (
        <InlineState
          type="loading"
          message="Checking compliance frameworks..."
        />
      )}

      {error && (
        <InlineState
          type="error"
          message="Failed to load compliance data."
          onRetry={refetch}
        />
      )}

      {!isLoading && !error && frameworks?.length === 0 && (
        <InlineState
          type="empty"
          message="No compliance frameworks configured yet."
        />
      )}

      {!isLoading && !error && frameworks && frameworks.length > 0 && (
        <div className="space-y-5">
          {overview?.insight && (
            <div className="p-3 bg-green-50 rounded-lg">
              <MarkdownRenderer content={overview.insight} />
            </div>
          )}

          <div className="pr-1 space-y-6">
            {(overview?.framework_scores || []).map((framework) => (
              <div
                key={framework.framework}
                className="flex-col items-center justify-between"
              >
                <div className="flex justify-between items-center">
                  <div className="text-xs font-medium text-gray-700">
                    {framework.framework}
                  </div>
                  <div className="text-sm font-semibold text-gray-900 text-right">
                    {framework.score}%
                  </div>
                </div>
                <div className="gap-2">
                  <div className="bg-gray-200 rounded-full h-2">
                    <div
                      className={cn(
                        "h-2 rounded-full transition-all",
                        framework.score >= 90
                          ? "bg-success"
                          : framework.score >= 70
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
        </div>
      )}
      <div>
        <button className="w-full mt-10 flex items-center justify-center gap-2 p-2 text-xs text-center rounded-md border border-gray-200 hover:bg-gray-100 text-gray-800 font-medium">
          Details <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
}

export function ComplianceSection(props: Props) {
  return (
    <ErrorBoundary>
      <ComplianceContent {...props} />
    </ErrorBoundary>
  );
}
