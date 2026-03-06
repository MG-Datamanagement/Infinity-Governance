import { TrendingUp } from "lucide-react";

interface ComplianceScoreCardProps {
  score: number;
  change: string;
}

export function ComplianceScoreCard({ score, change }: ComplianceScoreCardProps) {
  return (
    <div className="flex flex-col items-center justify-center bg-green-50/50 rounded-2xl border border-green-100 p-6 h-full">
      <div className="text-5xl font-bold text-emerald-500 mb-2">{score}%</div>
      <div className="text-sm font-semibold text-gray-900 mb-1">
        Overall Compliance Score
      </div>
      <div className="flex items-center gap-1.5 text-xs text-emerald-600 font-medium">
        <TrendingUp size={14} />
        <span>{change}</span>
      </div>
    </div>
  );
}
