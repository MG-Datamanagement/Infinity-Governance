/**
 * ComplianceSection
 *
 * Compliance frameworks progress card.
 * Manages its own loading / error / empty states via InlineState.
 * Receives the raw query slice from useOverviewData so it is decoupled
 * from fetching but still independently retryable.
 */

import { Shield } from "lucide-react";
import { cn } from "@/lib/utils";
import { InlineState } from "@/components/InlineState";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { OverviewData } from "../../hooks/useOverviewData";

type Props = {
  query: OverviewData["frameworks"];
};

function ComplianceContent({ query }: Props) {
  const { data: frameworks, isLoading, error, refetch } = query;

  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 mb-2">
        <h3 className="text-sm font-semibold text-gray-900">
          Compliance Overview
        </h3>
        <Shield className="text-green-600" size={16} />
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
        <div className="space-y-4">
          <div className="p-1.5 bg-green-100/40 rounded-lg">
            <p className="text-xs text-gray-600 leading-normal">
              Your governance is in excellent shape! All critical compliance
              frameworks are above 90%, with GDPR and SOC 2 leading at 96% and
              98%. HIPAA needs attention at 79% - consider reviewing data
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
                  <div className="text-xs text-gray-700">{framework.name}</div>
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

          <button
            disabled
            className="w-full p-1 text-sm text-center rounded-md bg-gray-100 text-gray-800 font-medium hover:bg-gray-200 hover:text-primary disabled:cursor-not-allowed"
          >
            Details →
          </button>
        </div>
      )}
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