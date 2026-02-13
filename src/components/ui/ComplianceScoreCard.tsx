import { TrendingUp } from "lucide-react";

interface ComplianceScoreCardProps {
  score: number;
  change: string;
}

export function ComplianceScoreCard({ score, change }: ComplianceScoreCardProps) {
  return (
    <div className="stat-card flex-col items-center bg-gradient-to-br from-green-50 to-white">
      <div className="mb-2">
        <h3 className="text-center text-sm font-medium text-gray-700">Overall Compliance Score</h3>
      </div>
      <div className="flex-col w-full gap-4">
        <div className="text-4xl text-center font-bold text-success">{score}%</div>
        <div className="mb-3 text-sm text-center flex justify-center items-center text-success font-medium gap-2"><TrendingUp size={14} />{change}</div>
      </div>
    </div>
  );
}
