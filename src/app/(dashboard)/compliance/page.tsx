'use client';

import { useComplianceFrameworks, useComplianceIssues, useComplianceTrends } from '@/hooks/useQueries';
import { ComplianceScoreCard } from '@/components/ui/ComplianceScoreCard';
import { ComplianceFrameworkCard } from '@/components/compliance/ComplianceFrameworkCard';
import { ComplianceTrendsChart } from '@/components/charts/ComplianceTrendsChart';
import { ComplianceIssuesTable } from '@/components/compliance/ComplianceIssuesTable';
import { LoadingFallback, DataErrorFallback } from '@/components/Fallbacks';
import { Sparkles, TrendingUp } from 'lucide-react';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { TabNavigation } from '@/components/ui/TabNavigation';

function ComplianceContent() {
  const { data: frameworks, isLoading: frameworksLoading, error: frameworksError, refetch: refetchFrameworks } = useComplianceFrameworks();
  const { data: issues, isLoading: issuesLoading, error: issuesError, refetch: refetchIssues } = useComplianceIssues();
  const { data: trends, isLoading: trendsLoading, error: trendsError, refetch: refetchTrends } = useComplianceTrends();

  const isLoading = frameworksLoading || issuesLoading || trendsLoading;
  const hasError = frameworksError || issuesError || trendsError;

  if (isLoading) {
    return <LoadingFallback />;
  }

  if (hasError) {
    return <DataErrorFallback retry={() => {
      refetchFrameworks();
      refetchIssues();
      refetchTrends();
    }} />;
  }

  return (
    <div className="p-4 md:p-3 space-y-2">
      {/* Tab Navigation */}
      <TabNavigation />

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <p className="text-sm text-gray-600">Monitor your data governance health and activities</p>
        <div className="flex flex-wrap gap-3">
          <button className="px-3 py-1.5 bg-primary text-white text-sm font-medium rounded-md hover:bg-primary-dark transition-colors flex items-center gap-2 whitespace-nowrap">
            <span>▶</span>
            Run Full Scan
          </button>
          <button className="px-3 py-1.5 border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-50 transition-colors flex items-center gap-2 whitespace-nowrap">
            <span>📄</span>
            Export Report
          </button>
        </div>
      </div>

      {/* Compliance Health Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* Score Card */}
        <div className="lg:col-span-1">
          <ComplianceScoreCard score={91} change="+4% from last month" />
        </div>

        {/* Trends Chart */}
        <div className="lg:col-span-2">
          <ErrorBoundary fallback={<DataErrorFallback retry={refetchTrends} />}>
            {trends && <ComplianceTrendsChart data={trends} />}
          </ErrorBoundary>
        </div>
      </div>

      {/* AI Insights */}
      <div className="card p-2 md:p-4 bg-gradient-to-r from-purple-50 to-blue-50 border-purple-200">
        <div className="flex flex-col sm:flex-row items-start gap-4">
          <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center flex-shrink-0">
            <Sparkles className="text-white" size={20} />
          </div>
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <h3 className="font-semibold text-gray-900">AI-Powered Insights</h3>
              <span className="px-2 py-0.5 bg-primary/10 text-primary text-xs font-medium rounded">
                BETA
              </span>
            </div>
            <p className="text-sm text-gray-700 mb-3">
              Your governance is in excellent shape! All critical compliance frameworks are above 90%, 
              with GDPR and SOC 2 leading at 96% and 98%. HIPAA needs attention at 79% — consider 
              reviewing data classification policies.
            </p>
            <button className="text-sm text-primary font-medium hover:underline flex items-center gap-1">
              View Details
              <TrendingUp size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Compliance Frameworks */}
      <div>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 gap-2">
          <h2 className="text-lg font-semibold text-gray-900">Compliance Frameworks</h2>
          <p className="text-sm text-gray-500">{frameworks?.length || 0} frameworks</p>
        </div>
        <ErrorBoundary fallback={<DataErrorFallback retry={refetchFrameworks} />}>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {frameworks?.map((framework) => (
              <ComplianceFrameworkCard key={framework.id} framework={framework} />
            ))}
          </div>
        </ErrorBoundary>
      </div>

      {/* Open Issues */}
      <ErrorBoundary fallback={<DataErrorFallback retry={refetchIssues} />}>
        {issues && <ComplianceIssuesTable issues={issues} />}
      </ErrorBoundary>
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
