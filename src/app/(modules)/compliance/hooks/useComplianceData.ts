import {
  useComplianceFrameworks,
  useComplianceIssues,
  useComplianceTrends,
} from "@/hooks/useDashboardQueries";

export function useComplianceData() {
  const frameworks = useComplianceFrameworks();
  const issues = useComplianceIssues();
  const trends = useComplianceTrends();

  return { frameworks, issues, trends } as const;
}

export type ComplianceData = ReturnType<typeof useComplianceData>;