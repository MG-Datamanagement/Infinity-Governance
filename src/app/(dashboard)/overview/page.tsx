'use client';

import {
  useDashboardStats,
  useAISnapshot,
  useModelRiskTrends,
  useDomainAssets,
  usePlatformUsage,
  useRecentActivity,
  useComplianceFrameworks,
} from '@/hooks/useQueries';
import { StatCard } from '@/components/ui/StatCard';
import { ModelRiskChart } from '@/components/charts/ModelRiskChart';
import { LoadingFallback, DataErrorFallback } from '@/components/Fallbacks';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { TabNavigation } from '@/components/ui/TabNavigation';
import {
  Database,
  Shield,
  Tag,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Eye,
  Clock,
  BarChart2,
  LucideMessageSquareWarning,
  Activity
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState } from 'react';


function OverviewContent() {
  const [activityTab, setActivityTab] = useState<'recent' | 'viewed'>('recent');
  const [showQuickActions, setShowQuickActions] = useState(false);

  const { data: stats, isLoading: statsLoading, error: statsError, refetch: refetchStats } = useDashboardStats();
  const { data: aiSnapshot, isLoading: aiLoading, error: aiError, refetch: refetchAI } = useAISnapshot();
  const { data: riskTrends, isLoading: trendsLoading } = useModelRiskTrends();
  const { data: domains, isLoading: domainsLoading } = useDomainAssets();
  const { data: platforms, isLoading: platformsLoading } = usePlatformUsage();
  const { data: activity, isLoading: activityLoading } = useRecentActivity();
  const { data: frameworks, isLoading: frameworksLoading } = useComplianceFrameworks();

  if (statsLoading) {
    return <LoadingFallback />;
  }

  if (statsError) {
    return <DataErrorFallback retry={refetchStats} />;
  }

  return (
    <div className="p-4 md:p-3 space-y-3">
      {/* Tab Navigation */}
      <TabNavigation />

      {/* Action Button */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm text-gray-600 font-medium">Monitor your data governance health and activities</p>
        </div>
        <div className='flex gap-3'>
          <div>
            <button className="p-2 bg-primary text-white text-xs font-medium rounded-md hover:bg-primary-dark transition-colors flex items-center gap-2 whitespace-nowrap">
              <Database size={16} />
              Add Data Source
            </button>
          </div>
          <div>
            <select aria-label='Quick Actions' className='p-2 text-gray-800 text-xs font-medium rounded-md border border-gray-200 hover:bg-white transition-colors flex items-center whitespace-nowrap'>
              <option disabled selected hidden value="">Quick Actions</option>
              <option value="exportReport">Export Report</option>
              <option value="runScan">Run Scan</option>
              <option value="settings">Settings</option>
            </select>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <ErrorBoundary fallback={<DataErrorFallback retry={refetchStats} />}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
          <StatCard
            icon={Database}
            iconColor="text-blue-600"
            label="Total Assets"
            value={stats?.totalAssets || 0}
            change={stats?.totalAssetsChange}
            changeType="positive"
          />
          <StatCard
            icon={Shield}
            iconColor="text-green-600"
            label="Governance Score"
            value={`${stats?.governanceScore}%` || '0%'}
            change={stats?.governanceScoreStatus}
            changeType="neutral"
          />
          <StatCard
            icon={Tag}
            iconColor="text-blue-600"
            label="Classified"
            value={stats?.classified || 0}
            change={stats?.classifiedChange}
            changeType="positive"
          />
          <StatCard
            icon={Eye}
            iconColor="text-yellow-600"
            label="Pending Review"
            value={stats?.pendingReview || 0}
          />
          <StatCard
            icon={LucideMessageSquareWarning}
            iconColor="text-gray-600"
            label="At Risk Domains"
            value={stats?.aiRiskDomains || 0}
          />
          <StatCard
            icon={LucideMessageSquareWarning}
            iconColor="text-gray-600"
            label="At Risk Domains"
            value={stats?.aiRiskDomains || 0}
          />
        </div>
      </ErrorBoundary>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-3">
        {/* Compliance Overview */}
        <div className="xl:col-span-4">
          <ErrorBoundary>
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-2">
                <h3 className="text-sm font-semibold text-gray-900">Compliance Overview</h3>
                <Shield className="text-green-600" size={16} />
              </div>

              {!frameworksLoading && frameworks && (
                <div className="space-y-3">
                  <div className='p-1.5 bg-green-100/40 rounded-lg'>
                    <p className="text-xs text-gray-600 leading-relaxed">
                      Your governance is in excellent shape! All critical compliance frameworks are above
                      90%, with GDPR and SOC 2 leading at 96% and 98%. HIPAA needs attention at 79% -
                      consider reviewing data classification policies.
                    </p>
                  </div>

                  {frameworks.map((framework) => (
                    <div key={framework.id} className="flex-col items-center justify-between space-y-1">
                      <div className='flex justify-between items-center'>
                        <div className="text-xs text-gray-700">{framework.name}</div>
                        <div className="text-sm font-medium text-gray-900 text-right">
                          {framework.score}%
                        </div>
                      </div>
                      <div className="gap-2">
                        <div className="bg-gray-200 rounded-full h-2">
                          <div
                            className={cn(
                              'h-2 rounded-full transition-all',
                              framework.status === 'excellent' ? 'bg-success' :
                                framework.status === 'warning' ? 'bg-warning' : 'bg-danger'
                            )}
                            style={{ width: `${framework.score}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}

                  <button className="w-full p-1 text-sm text-center rounded-md bg-gray-100 text-gray-800 font-medium hover:bg-gray-200 hover:text-primary">
                    Details →
                  </button>
                </div>
              )}
            </div>
          </ErrorBoundary>
        </div>

        {/* AI Governance Snapshot */}
        <div className="xl:col-span-4">
          <ErrorBoundary fallback={<DataErrorFallback retry={refetchAI} />}>
            <div className="card p-4">
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-gray-900">AI Governance Snapshot</h3>
                <p className="text-[10px] text-gray-400">Real-time AI model monitoring</p>
              </div>

              {!aiLoading && aiSnapshot && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckCircle size={15} className="text-green-600 flex-shrink-0" />
                      <span className="text-xs text-gray-700">Models in Production:</span>
                    </div>
                    <span className="text-xs font-semibold text-gray-900">
                      {aiSnapshot.modelsInProduction}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <AlertTriangle size={15} className="text-yellow-600 flex-shrink-0" />
                      <span className="text-xs text-gray-700">Flagged Prompts Today:</span>
                    </div>
                    <span className="text-xs font-semibold text-gray-900">
                      {aiSnapshot.flaggedPromptsToday}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <TrendingUp size={15} className="text-blue-600 flex-shrink-0" />
                      <span className="text-xs text-gray-700">AI Fairness Score:</span>
                    </div>
                    <span className="text-xs font-semibold text-gray-900">
                      {aiSnapshot.aiFairnessScore}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Eye size={15} className="text-red-600 flex-shrink-0" />
                      <span className="text-xs text-gray-700">Models Needing Review:</span>
                    </div>
                    <span className="text-xs font-semibold text-red-600">
                      {aiSnapshot.modelsNeedingReview}
                    </span>
                  </div>

                  {/* Model Risk Trend */}
                  <div className="mt-6 pt-2">
                    <div>
                      <h4 className="text-xs text-gray-500 uppercase mb-2">
                        Model Risk Trend
                      </h4>
                    </div>
                    <div>
                      {!trendsLoading && riskTrends && <ModelRiskChart data={riskTrends} />}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </ErrorBoundary>
        </div>

        {/* Bottom Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {/* Top Domains */}
          <ErrorBoundary>
            <div className="card p-4">
              <div className="flex items-center justify-between mb-4">
                <div className='flex justify-between items-center gap-2'>
                  <h3 className="font-semibold text-gray-900">Top Domains</h3>
                  <TrendingUp size={16} className='text-green-600' />
                </div>
                <button className="text-primary text-sm font-medium hover:underline">
                  View All →
                </button>
              </div>

              {!domainsLoading && domains && (
                <div className="space-y-2">
                  {domains.map((domain, idx) => (
                    <div key={idx} className="flex items-center justify-between py-1">
                      <span className="text-sm text-gray-700">{domain.domain}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-gray-900">
                          {domain.count} {domain.count === 1 ? 'asset' : 'assets'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </ErrorBoundary>

          <ErrorBoundary>
            {/* Top Platforms */}
            <div className="card p-4">
              <div className="flex items-center justify-between mb-4">
                <div className='flex justify-between items-center gap-2'>
                  <h3 className="font-semibold text-gray-900">Top Platforms</h3>
                  <Database size={16} className='text-blue-800' />
                </div>
                <button className="text-primary text-sm font-medium hover:underline">
                  View All →
                </button>
              </div>

              {!platformsLoading && platforms && (
                <div className="space-y-2">
                  {platforms.map((platform, idx) => (
                    <div key={idx} className="flex items-center justify-between py-1">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-primary flex-shrink-0"></div>
                        <span className="text-sm text-gray-700">{platform.platform}</span>
                      </div>
                      <span className="text-sm font-medium text-gray-900">{platform.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </ErrorBoundary>
        </div>

      </div>
      {/* Recent Activity */}
      <div className="xl:col-span-4">
        <ErrorBoundary>
          <div className="card overflow-hidden h-full flex flex-col">
            <div className='flex items-center justify-center'>
              {/* Tabs */}
              <div className="flex gap-3 border-b border-gray-200">
                <button
                  onClick={() => setActivityTab('recent')}
                  className={cn(
                    'px-4 py-3 text-xs font-medium border-b-2 transition-colors flex items-center gap-1',
                    activityTab === 'recent'
                      ? 'text-primary border-primary bg-gray-200'
                      : 'text-gray-500 border-transparent hover:text-gray-700'
                  )}
                >
                  <Activity size={16} />
                  Recent Activity
                </button>
                <button
                  onClick={() => setActivityTab('viewed')}
                  className={cn(
                    'px-4 py-3 text-xs font-medium border-b-2 transition-colors flex items-center gap-1',
                    activityTab === 'viewed'
                      ? 'text-primary border-primary bg-gray-200'
                      : 'text-gray-500 border-transparent hover:text-gray-700'
                  )}
                >
                  <Clock size={16} />
                  Recently Viewed
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto">
              <div className="divide-y divide-gray-100">
                {!activityLoading && activity && activity.slice(0, 10).map((item) => (
                  <div key={item.id} className="px-2 md:px-4 py-3 hover:bg-gray-50 cursor-pointer">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-purple-100 rounded flex items-center justify-center flex-shrink-0">
                        <Database size={14} className="text-purple-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium text-gray-900 truncate">
                          {item.name}
                        </div>
                        <div className="text-xs text-gray-500">
                          {item.type} • {item.table}
                        </div>
                      </div>
                      <div className="text-xs text-gray-400 flex-shrink-0">
                        {item.timestamp}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-2 border-t border-gray-200">
              <button className="text-primary text-sm font-medium hover:underline w-full text-center">
                View all recently viewed
              </button>
            </div>
          </div>
        </ErrorBoundary>
      </div>


    </div>
  );
}

export default function OverviewPage() {
  return (
    <ErrorBoundary>
      <OverviewContent />
    </ErrorBoundary>
  );
}
