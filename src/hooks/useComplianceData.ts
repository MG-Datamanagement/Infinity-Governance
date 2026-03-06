import { useComplianceRun } from "@/hooks/useDashboardQueries";

export function useComplianceData() {
  const complianceRun = useComplianceRun();

  return { 
    complianceRun,
    // Keep these for backward compatibility if needed, but they should eventually be removed
    frameworks: { ...complianceRun, data: complianceRun.data?.frameworks },
    issues: { ...complianceRun, data: complianceRun.data?.open_issues?.items },
    trends: { ...complianceRun, data: complianceRun.data?.trends }
  } as const;
}

export type ComplianceData = ReturnType<typeof useComplianceData>;