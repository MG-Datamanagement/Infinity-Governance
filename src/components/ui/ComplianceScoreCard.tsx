import { TrendingUp } from "lucide-react";

interface ComplianceScoreCardProps {
  score: number;
  change: string;
}

export function ComplianceScoreCard({ score, change }: ComplianceScoreCardProps) {
  return (
    <div className="stat-card flex flex-col items-center justify-center bg-gradient-to-br from-green-50 to-white gap-1 border-2 border-green-200/50">
      <div className="text-3xl text-center font-bold text-success">{score}%</div>
      <div>
        <h3 className="text-center text-sm font-medium text-gray-700">Overall Compliance Score</h3>
      </div>
      <div className="text-xs text-center flex justify-center items-center text-success font-medium gap-2"><TrendingUp size={14} />{change}</div>
    </div>
  );
}
