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
  const { frameworks, issues, trends } = useComplianceData();

  const allLoading =
    frameworks.isLoading && issues.isLoading && trends.isLoading;
  const allError = frameworks.error && issues.error && trends.error;

  if (allLoading) return <LoadingFallback />;
  if (allError)
    return (
      <DataErrorFallback
        retry={() => {
          frameworks.refetch();
          issues.refetch();
          trends.refetch();
        }}
      />
    );

  return (
    <div className="p-4 md:p-6 space-y-5">
      <TabNavigation />
      <ComplianceHeader />

      <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
        <div className="grid grid-cols-1 gap-2 lg:col-span-8">
          <ComplianceHealthSection trendsQuery={trends} />
          <ComplianceIssuesSection query={issues} />
        </div>

        <ComplianceFrameworksPanel query={frameworks} />
      </div>
    </div>
  );
}

export default function CompliancePage() {
  return (
    <ErrorBoundary>
      <ComplianceContent />;
    </ErrorBoundary>
  );
}
