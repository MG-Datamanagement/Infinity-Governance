/**
 * OverviewStatsGrid
 *
 * Top-level KPI stat cards row.
 * Accepts the resolved `stats` data so it stays a pure presentational
 * component — easy to test, easy to swap card layouts independently.
 */

import { Database, Shield, Tag, Eye, Globe, Table } from "lucide-react";
import { StatCard } from "@/components/ui/StatCard";
import { OverviewData } from "../../hooks/useOverviewData";
import { DashboardStats } from "@/types";

type Props = {
  stats: NonNullable<OverviewData["stats"]["data"]>;
};

const defaultStats: DashboardStats = {
  totalAssets: 0,
  // totalAssetsChange: "",
  // governanceScore: 0,
  // governanceScoreStatus: "",
  classified: 0,
  // classifiedChange: "",
  // aiRiskDomains: 0,
  activeDomains: 0,
  activeTables: 0,
  // pendingReview: 0,
};

export function OverviewStatsGrid({ stats = defaultStats }: Props) {
  return (
    <div className="grid xs:grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">
      {stats.totalAssets ? (
        <StatCard
          icon={Database}
          iconColor="text-blue-600"
          label="Total Assets"
          value={stats?.totalAssets}
          // change={stats?.totalAssetsChange ?? ""}
          changeType="positive"
        />
      ) : null}
      {/* {stats?.governanceScore ? (
        <StatCard
          icon={Shield}
          iconColor="text-green-600"
          label="Governance Score"
          value={`${stats?.governanceScore ?? 0}%`}
          change={stats?.governanceScoreStatus ?? ""}
          changeType="neutral"
        />
      ) : null} */}
      {stats?.classified ? (
        <StatCard
          icon={Tag}
          iconColor="text-blue-600"
          label="Classified"
          value={stats?.classified}
          change={""}
          changeType="positive"
        />
      ) : null}
      {/* {stats?.pendingReview ? (
        <StatCard
          icon={Eye}
          iconColor="text-yellow-600"
          label="Pending Review"
          value={stats?.pendingReview ?? 0}
        />
      ) : null} */}
      {stats?.activeDomains ? (
        <StatCard
          icon={Globe}
          iconColor="text-gray-600"
          label="Active Domains"
          value={stats?.activeDomains}
        />
      ) : null}
      {stats?.activeTables ? (
        <StatCard
          icon={Table}
          iconColor="text-gray-600"
          label="Active Tables"
          value={stats?.activeTables}
        />
      ) : null}
    </div>
  );
}
