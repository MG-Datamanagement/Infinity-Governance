import { Shield, Sparkles } from "lucide-react";
import { ComplianceScoreCard } from "@/components/ui/ComplianceScoreCard";
import { ComplianceTrendsChart } from "@/components/charts/ComplianceTrendsChart";
import { InlineState } from "@/components/ui/InlineState";
import { ComplianceData } from "../../../hooks/useComplianceData";

type Props = {
  trendsQuery: ComplianceData["trends"];
};

function AIInsightsCard() {
  return (
    <div className="card p-2 md:p-6 border border-gray-200 bg-indigo-50 shadow-md">
      <div className="flex flex-col sm:flex-row items-start">
        <div className="flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center flex-shrink-0">
              <Sparkles className="text-white" size={20} />
            </div>
            <h3 className="text-sm font-medium text-gray-900">
              AI-Powered Insights
            </h3>
            <span className="px-1 py-0.5 bg-primary/10 text-primary text-xs font-medium rounded">
              BETA
            </span>
          </div>
          <p className="text-xs pl-9 text-gray-500 leading-relaxed">
            Your governance is in excellent shape! All critical compliance
            frameworks are above 90%, with GDPR and SOC 2 leading at 96% and
            98%. HIPAA needs attention at 79% — consider reviewing data
            classification policies.
          </p>
        </div>
      </div>
    </div>
  );
}

export function ComplianceHealthSection({ trendsQuery }: Props) {
  const { data: trends, isLoading, error, refetch } = trendsQuery;

  return (
    <div className="grid grid-cols-1 md:grid-rows-[1fr_9fr] p-6 border border-gray-200 rounded-lg gap-2 bg-gradient-to-br from-primary/5 via-white to-primary/5">
      {/* Section Header */}
      <div className="flex gap-2">
        <Shield size={35} className="bg-primary p-2 text-white rounded-lg" />
        <div className="flex flex-col">
          <h2 className="text-sm font-bold text-gray-900">Compliance Health</h2>
          <p className="text-xs/[10px] text-gray-500 my-1">
            Real-time governance monitoring
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-rows-[2fr_1fr] gap-5">
        {/* Left: Score + AI Insights */}
        <div className="grid grid-cols-[2fr_3fr] gap-5">
          <ComplianceScoreCard score={91} change="+4% from last month" />

          {/* Right: Trends Chart */}
          <div className="grid">
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

        <AIInsightsCard />
      </div>
    </div>
  );
}
