import { Shield } from "lucide-react";
import { InlineState } from "@/components/ui/InlineState";
import { ComplianceFrameworkCard } from "@/components/compliance/ComplianceFrameworkCard";
import { ComplianceData } from "@/hooks/useComplianceData";
import { ApiComplianceFramework } from "@/types";
import { InfoIcon } from "lucide-react";


type Props = {
  query: ComplianceData["complianceRun"];
};

export function ComplianceFrameworksPanel({ query }: Props) {
  const { data: runData, isLoading, error, refetch } = query;
  const frameworks = runData?.frameworks;

  return (
    <div className="border border-gray-200 rounded-3xl bg-white col-span-4 border-l-4 border-l-indigo-600 shadow-sm overflow-hidden flex flex-col h-full sticky top-6">
      <div className="p-6 border-b border-gray-100 flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Shield className="text-indigo-600" size={18} />
            <h2 className="text-base font-bold text-gray-900">
              Compliance Frameworks
            </h2>
          </div>
          <p className="text-xs text-gray-400 font-medium pl-6">
            {frameworks?.length ?? 0} frameworks
          </p>
        </div>
        <button className="text-gray-300">
          <InfoIcon size={18} />
        </button>
      </div>

      <div className="grid grid-cols-1 gap-2 p-2 overflow-y-auto pr-1">
        {isLoading && (
          <InlineState type="loading" message="Loading compliance frameworks..." />
        )}
        {error && (
          <InlineState type="error" message="Failed to load frameworks." onRetry={refetch} />
        )}
        {!isLoading && !error && frameworks?.length === 0 && (
          <InlineState type="empty" message="No compliance frameworks configured." />
        )}
        {!isLoading && !error && frameworks && frameworks.length > 0 &&
          frameworks.map((framework: ApiComplianceFramework) => (
            <ComplianceFrameworkCard key={framework.name} framework={framework} />
          ))}
      </div>
    </div>
  );
}
