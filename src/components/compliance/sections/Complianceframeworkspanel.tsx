import { Shield } from "lucide-react";
import { InlineState } from "@/components/ui/InlineState";
import { ComplianceFrameworkCard } from "@/components/compliance/ComplianceFrameworkCard";
import { ComplianceData } from "@/hooks/useComplianceData";

type Props = {
  query: ComplianceData["frameworks"];
};

export function ComplianceFrameworksPanel({ query }: Props) {
  const { data: frameworks, isLoading, error, refetch } = query;

  return (
    <div className="gap-1 border rounded-lg bg-white lg:col-span-4">
      <div className="p-2 lg:p-6 border-b border-gray-200 space-y-2">
        <div className="gap-2 flex">
          <Shield className="text-blue-600" size={16} />
          <h2 className="text-sm font-bold text-gray-900">
            Compliance Frameworks
          </h2>
        </div>
        <p className="text-xs text-gray-500">
          {frameworks?.length ?? 0} frameworks
        </p>
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
          frameworks.map((framework) => (
            <ComplianceFrameworkCard key={framework.id} framework={framework} />
          ))}
      </div>
    </div>
  );
}