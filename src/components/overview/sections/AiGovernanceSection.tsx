/**
 * AIGovernanceSection
 *
 * AI Governance Snapshot card with embedded Model Risk Trend chart.
 * Owns the rendering logic for aiSnapshot and riskTrends slices.
 */

import { CheckCircle, AlertTriangle, TrendingUp, Eye } from "lucide-react";
import { InlineState } from "@/components/ui/InlineState";
import { ModelRiskChart } from "@/components/charts/ModelRiskChart";
import { OverviewData } from "@/hooks/useOverviewData";
import { cn } from "@/lib/utils";

type Props = {
  aiQuery: OverviewData["aiSnapshot"];
  trendsQuery: OverviewData["riskTrends"];
};

type MetricRowProps = {
  icon: React.ElementType;
  iconClass: string;
  label: string;
  value: React.ReactNode;
  valueClass?: string;
  bgColor?: string;
};

function MetricRow({
  icon: Icon,
  iconClass,
  label,
  value,
  valueClass,
  bgColor,
}: MetricRowProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Icon size={15} className={`${iconClass} flex-shrink-0`} />
        <span className="text-sm text-gray-700">{label}</span>
      </div>
      <span
        className={cn(
          "text-sm font-semibold",
          valueClass ?? "text-gray-900",
          bgColor ? `${bgColor} rounded-md px-2 py-0.5` : "",
        )}
      >
        {value}
      </span>
    </div>
  );
}

export function AIGovernanceSection({ aiQuery, trendsQuery }: Props) {
  const { data: aiSnapshot, isLoading, error, refetch } = aiQuery;
  const { data: riskTrends, isLoading: trendsLoading } = trendsQuery;

  return (
    <div className="card p-6 space-y-5 lg:col-span-5">
      <div>
        <h3 className="text-sm font-semibold text-gray-900 mb-1">
          AI Governance Snapshot
        </h3>
        <p className="text-[10px] text-gray-400">
          Real-time AI model monitoring
        </p>
      </div>

      {isLoading && (
        <InlineState
          type="loading"
          message="Loading AI governance metrics..."
        />
      )}

      {error && (
        <InlineState
          type="error"
          message="Unable to fetch AI metrics."
          onRetry={refetch}
        />
      )}

      {!isLoading && !error && !aiSnapshot && (
        <InlineState type="empty" message="No AI models monitored yet." />
      )}

      {!isLoading && !error && aiSnapshot && (
        <div className="space-y-4">
          <MetricRow
            icon={CheckCircle}
            iconClass="text-green-600"
            label="Models in Production:"
            value={aiSnapshot.modelsInProduction}
          />
          <MetricRow
            icon={AlertTriangle}
            iconClass="text-yellow-600"
            label="Flagged Prompts Today:"
            value={aiSnapshot.flaggedPromptsToday}
          />
          <MetricRow
            icon={TrendingUp}
            iconClass="text-blue-600"
            label="AI Fairness Score:"
            value={aiSnapshot.aiFairnessScore}
          />
          <MetricRow
            icon={Eye}
            iconClass="text-red-600"
            label="Models Needing Review:"
            value={aiSnapshot.modelsNeedingReview}
            valueClass="text-red-600"
            bgColor="bg-red-50"
          />

          <div className="mt-10 pt-2">
            <h4 className="text-xs text-gray-500 uppercase mb-2">
              Model Risk Trend
            </h4>
            {!trendsLoading && riskTrends && (
              <ModelRiskChart data={riskTrends} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
