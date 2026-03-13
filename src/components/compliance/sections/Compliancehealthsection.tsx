import { Shield, Sparkles, ChevronUp } from "lucide-react";
import { ComplianceScoreCard } from "@/components/ui/ComplianceScoreCard";
import { ComplianceTrendsChart } from "@/components/charts/ComplianceTrendsChart";
import { InlineState } from "@/components/ui/InlineState";
import { ComplianceData } from "../../../hooks/useComplianceData";

type Props = {
  complianceRunQuery: ComplianceData["complianceRun"];
};

export function AIInsightsCard({ text }: { text?: string }) {
  return (
    <div className="card p-4 md:p-6 border border-indigo-100 bg-indigo-50/30 rounded-2xl">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shrink-0">
          <Sparkles className="text-white" size={20} />
        </div>
        <div className="space-y-1.5 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-gray-900">
              AI-Powered Insights
            </h3>
            <span className="px-1.5 py-0.5 bg-indigo-100 text-indigo-700 text-[10px] font-bold rounded-md">
              BETA
            </span>
          </div>
          <p className="text-xs text-gray-600 leading-relaxed max-w-4xl whitespace-pre-wrap">
            {text?.replace(/\*\*/g, "") || "Generating AI insights based on your compliance data..."}
          </p>
        </div>
      </div>
    </div>
  );
}

export function ComplianceHealthSection({ complianceRunQuery }: Props) {
  const { data: runData, isLoading, error, refetch } = complianceRunQuery;
  const trends = runData?.trends;
  const health = runData?.compliance_health;
  const insights = runData?.ai_insights;

  return (
    <div className="p-6 border border-gray-200 rounded-3xl bg-white shadow-sm space-y-6">
      {/* Section Header */}
      <div className="flex items-start justify-between">
        <div className="flex gap-3">
          <div className="w-10 h-10 bg-primary/20 p-2 text-indigo-700 rounded-xl flex items-center justify-center">
            <Shield size={24} />
          </div>
          <div className="flex flex-col justify-center">
            <h2 className="text-base font-bold text-gray-900 leading-tight">Compliance Health</h2>
            <p className="text-xs text-gray-400 mt-0.5 font-medium">
              Real-time governance monitoring
            </p>
          </div>
        </div>
        <button className="text-gray-400 hover:text-gray-600 transition-colors">
          <ChevronUp size={20} />
        </button>
      </div>

      <div className="space-y-6">
        {/* Row 1: Score + Trends */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-stretch">
          {/* Left: Score Card */}
          <div className="md:col-span-5">
            <ComplianceScoreCard
              score={health?.score ?? 0}
              change={health?.trend_label ?? "No change"}
            />
          </div>

          {/* Right: Trends Chart */}
          <div className="md:col-span-7">
            <div className="h-full relative">
              {isLoading && (
                <InlineState
                  type="loading"
                  message="Loading compliance trends..."
                />
              )}
              {error && (
                <InlineState
                  type="error"
                  message="Failed to load trends."
                  onRetry={refetch}
                />
              )}
              {!isLoading && !error && !trends && (
                <InlineState type="empty" message="No trend data available." />
              )}
              {!isLoading && !error && trends && (
                <ComplianceTrendsChart data={trends} />
              )}
            </div>
          </div>
        </div>

        {insights?.text && (
          <AIInsightsCard text={insights.text} />
        )}
      </div>
    </div>
  );
}
