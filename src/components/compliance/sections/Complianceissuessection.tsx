import { ErrorBoundary } from "@/components/ErrorBoundary";
import { DataErrorFallback } from "@/components/Fallbacks";
import { InlineState } from "@/components/ui/InlineState";
import { ComplianceIssuesTable } from "@/components/compliance/ComplianceIssuesTable";
import { ComplianceData } from "../../../hooks/useComplianceData";

type Props = {
  query: ComplianceData["issues"];
};

function IssuesContent({ query }: Props) {
  const { data: issues, isLoading, error, refetch } = query;

  if (isLoading) return <InlineState type="loading" message="Loading compliance issues..." />;
  if (error) return <InlineState type="error" message="Failed to load compliance issues." onRetry={refetch} />;
  if (!issues || issues.length === 0) return <InlineState type="empty" message="No open compliance issues." />;

  return <ComplianceIssuesTable issues={issues} />;
}

export function ComplianceIssuesSection(props: Props) {
  return (
    <ErrorBoundary fallback={<DataErrorFallback retry={props.query.refetch} />}>
      <IssuesContent {...props} />
    </ErrorBoundary>
  );
}