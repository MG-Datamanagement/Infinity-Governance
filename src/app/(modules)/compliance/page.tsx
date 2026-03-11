"use client";

import { LoadingFallback, DataErrorFallback } from "@/components/Fallbacks";
import { TabNavigation } from "@/components/ui/TabNavigation";
import { useComplianceData } from "@/hooks/useComplianceData";
import {
  ComplianceHeader,
  ComplianceHealthSection,
  ComplianceIssuesSection,
  ComplianceFrameworksPanel,
} from "@/components/compliance/sections";
import { ErrorBoundary } from "@/components/ErrorBoundary";

function ComplianceContent() {
  const { complianceRun } = useComplianceData();

  const isLoading = complianceRun.isLoading;
  const error = complianceRun.error;

  if (isLoading) return <LoadingFallback />;
  if (error)
    return (
      <DataErrorFallback
        retry={() => complianceRun.refetch()}
      />
    );

  return (
    <div className="max-w-7xl mx-auto px-8 py-8 space-y-5">
      <TabNavigation />
      <ComplianceHeader />

      <div className="grid grid-cols-1 md:grid-cols-12 gap-5 items-start">
        <div className="grid grid-cols-1 gap-5 col-span-8 min-w-0">
          <ComplianceHealthSection complianceRunQuery={complianceRun} />
          <ComplianceIssuesSection query={complianceRun} />
        </div>

        <ComplianceFrameworksPanel query={complianceRun} />
      </div>
    </div>
  );
}

export default function CompliancePage() {
  return (
    <ErrorBoundary>
      <ComplianceContent />
    </ErrorBoundary>
  );
}
