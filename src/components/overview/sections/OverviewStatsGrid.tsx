/**
 * OverviewStatsGrid
 *
 * Top-level KPI stat cards row.
 * Accepts the resolved `stats` data so it stays a pure presentational
 * component — easy to test, easy to swap card layouts independently.
 */

import {
  Database,
  Shield,
  Tag,
  Eye,
  Globe,
  Table,
  ShieldCheckIcon,
  FileTextIcon,
  Activity,
  Users,
  AlertTriangleIcon,
} from "lucide-react";
import { StatCard } from "@/components/ui/StatCard";
import { OverviewData } from "@/hooks/useOverviewData";
import { DashboardStats } from "@/types";

type Props = {
  stats: NonNullable<OverviewData["stats"]["data"]>;
  pendingReviewCount?: number;
  governanceScore?: number;
  openIssuesCount?: number;
};

const defaultStats: DashboardStats = {
  totalAssets: 0,
  totalAssetsChange: "",
  governanceScore: 0,
  governanceScoreStatus: "",
  classified: 0,
  classifiedChange: "",
  aiRiskDomains: 0,
  activeDomains: 0,
  activeTables: 0,
  pendingReview: 0,
};

export function OverviewStatsGrid({
  stats = defaultStats,
  pendingReviewCount,
  governanceScore,
  openIssuesCount,
}: Props) {
  return (
    <div className="grid xs:grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
      <StatCard
        icon={Database}
        iconColor="text-blue-600"
        label="Total Assets"
        value={stats?.totalAssets}
        change={stats?.totalAssetsChange ?? "+12% vs last month"}
        changeType="positive"
        iconBg="bg-blue-100"
      />
      <StatCard
        icon={ShieldCheckIcon}
        iconColor="text-green-600"
        label="Governance Score"
        value={governanceScore ? `${governanceScore}%` : `${stats?.governanceScore ?? 0}%`}
        change={stats?.governanceScoreStatus ?? "Above target"}
        changeType="neutral"
        iconBg="bg-green-100"
      />
      <StatCard
        icon={FileTextIcon}
        iconColor="text-blue-600"
        label="Classified"
        value={stats?.classified}
        change={"+8% vs last month"}
        changeType="positive"
        iconBg="bg-blue-100"
      />
      <StatCard
        icon={Activity}
        iconColor="text-orange-600"
        label="Pending Review"
        value={pendingReviewCount ?? stats?.pendingReview ?? "0"}
        iconBg="bg-orange-100"
      />
      <StatCard
        icon={Users}
        iconColor="text-gray-600"
        label="Active Domains"
        value={stats?.activeDomains ?? "16"}
        iconBg="bg-gray-100"
      />
      <StatCard
        icon={AlertTriangleIcon}
        iconColor="text-red-600"
        label="Open Issues"
        value={openIssuesCount ?? stats?.openIssues ?? "0"}
        change="Needs attention"
        changeType="negative"
        iconBg="bg-red-100"
      />
    </div>
  );
}
