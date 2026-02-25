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

type Props = {
  stats: NonNullable<OverviewData["stats"]["data"]>;
};

export function OverviewStatsGrid({ stats }: Props) {
  return (
    <div className="grid xs:grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">
      <StatCard
        icon={Database}
        iconColor="text-blue-600"
        label="Total Assets"
        value={stats.totalAssets ?? 0}
        change={stats.totalAssetsChange}
        changeType="positive"
      />
      <StatCard
        icon={Shield}
        iconColor="text-green-600"
        label="Governance Score"
        value={stats.governanceScore ? `${stats.governanceScore}%` : "0%"}
        change={stats.governanceScoreStatus}
        changeType="neutral"
      />
      <StatCard
        icon={Tag}
        iconColor="text-blue-600"
        label="Classified"
        value={stats.classified ?? 0}
        change={stats.classifiedChange}
        changeType="positive"
      />
      <StatCard
        icon={Eye}
        iconColor="text-yellow-600"
        label="Pending Review"
        value={stats.pendingReview ?? 0}
      />
      <StatCard
        icon={Globe}
        iconColor="text-gray-600"
        label="Active Domains"
        value={stats.activeDomains ?? 0}
      />
      <StatCard
        icon={Table}
        iconColor="text-gray-600"
        label="Active Tables"
        value={stats.activeTables ?? 0}
      />
    </div>
  );
}
