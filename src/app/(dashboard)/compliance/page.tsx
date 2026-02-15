'use client';

import { useComplianceFrameworks, useComplianceIssues, useComplianceTrends } from '@/hooks/useQueries';
import { ComplianceScoreCard } from '@/components/ui/ComplianceScoreCard';
import { ComplianceFrameworkCard } from '@/components/compliance/ComplianceFrameworkCard';
import { ComplianceTrendsChart } from '@/components/charts/ComplianceTrendsChart';
import { ComplianceIssuesTable } from '@/components/compliance/ComplianceIssuesTable';
import { LoadingFallback, DataErrorFallback } from '@/components/Fallbacks';
import { Database, File, PlayIcon, Shield, Sparkles, TrendingUp } from 'lucide-react';
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
      <div className="flex flex-col lg:flex-row items-center justify-between gap-2">
        <div>
          <p className="text-sm text-gray-600 font-medium">Monitor your data governance health and activities</p>
        </div>
        <div className='flex items-center gap-2'>
          <div>
            <button className="px-2 py-2 bg-primary text-white text-xs font-medium rounded-md hover:bg-primary-dark transition-colors flex items-center gap-2 whitespace-nowrap">
              <PlayIcon size={16} />
              Run Full Scan
            </button>
          </div>
          <div>
            <button className='px-2 py-2 text-gray-800 text-xs font-medium rounded-md border-2 border-gray-200 hover:bg-gray-200 transition-colors flex items-center gap-1 whitespace-nowrap'>
              <File size={16} />
              Export Report
            </button>
          </div>
        </div>
      </div>

      <div className='grid grid-cols-1 md:grid-cols-[6fr_2fr] gap-2'>
        <div className="grid grid-cols-1 gap-2">
          {/* Compliance Health Section */}
          <div className='grid grid-cols-1 md:grid-rows-[1fr_9fr] p-2.5 border border-gray-200 rounded-lg gap-2 bg-gradient-to-br from-primary/5 via-white to-primary/5'>
            <div className='flex gap-2'>
              <Shield size={35} className='bg-primary p-2 text-white rounded-lg' />
              <div className='flex flex-col'>
                <h2 className="text-sm font-bold text-gray-900">Compliance Health</h2>
                <p className="text-xs/[10px] text-gray-500 my-1">Real-time governance monitoring</p>
              </div>
            </div>

            <div className='grid grid-cols-1 md:grid-cols-[2fr_3fr] gap-2'>
              <div className='grid grid-cols-1 gap-2'>
                {/* Score Card */}
                <div className="grid">
                  <ComplianceScoreCard score={91} change="+4% from last month" />
                </div>

                {/* AI Insights */}
                <div className="card p-2 md:p-4 border-2 border-gray-200">
                  <div className="flex flex-col sm:flex-row items-start">
                    <div className="flex-1 space-y-1">
                      <div className="flex flex-wrap items-center gap-2 mb-2">
                        <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center flex-shrink-0">
                          <Sparkles className="text-white" size={20} />
                        </div>
                        <h3 className="text-sm font-medium text-gray-900">AI-Powered Insights</h3>
                        <span className="px-1 py-0.5 bg-primary/10 text-primary text-xs font-medium rounded">
                          BETA
                        </span>
                      </div>
                      <p className="text-xs/5 text-gray-600">
                        Your governance is in excellent shape! All critical compliance frameworks are above 90%,
                        with GDPR and SOC 2 leading at 96% and 98%. HIPAA needs attention at 79% — consider
                        reviewing data classification policies.
                      </p>
                      {/* <button className="text-sm text-primary font-medium hover:underline flex items-center gap-1">
                      View Details
                      <TrendingUp size={14} />
                    </button> */}
                    </div>
                  </div>
                </div>
              </div>

              {/* Trends Chart */}
              <div className="grid">
                {trends && <ComplianceTrendsChart data={trends} />}
              </div>
            </div>
          </div>

          <div className='grid grid-cols-1'>
            {/* Open Issues */}
            <ErrorBoundary fallback={<DataErrorFallback retry={refetchIssues} />}>
              {issues && <ComplianceIssuesTable issues={issues} />}
            </ErrorBoundary>
          </div>
        </div>

        {/* Compliance Frameworks */}
        <div className='gap-1 border rounded-lg'>
          <div className="p-2 border-b-2 border-primary bg-gradient-to-br from-primary/10 via-white to-primary/5 gap-2">
            <div className='gap-1 flex'>
              <Shield className='text-blue-600' size={16} />
              <h2 className="text-sm/3 font-bold text-gray-900">Compliance Frameworks</h2>
            </div>
            <p className="text-xs/[10px] text-gray-500 my-1">{frameworks?.length || 0} frameworks</p>
          </div>
          <div className="grid grid-cols-1 gap-2 p-2">
            {frameworks?.map((framework) => (
              <ComplianceFrameworkCard key={framework.id} framework={framework} />
            ))}
          </div>
        </div>
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
