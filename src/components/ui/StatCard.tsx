import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  icon: LucideIcon;
  iconColor?: string;
  label: string;
  value: string | number;
  change?: string;
  changeType?: "positive" | "negative" | "neutral";
}

export function StatCard({
  icon: Icon,
  iconColor = "text-primary",
  label,
  value,
  change,
  changeType = "neutral",
}: StatCardProps) {
  return (
    <>
      <div className="stat-card flex flex-col justify-between space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-xs/3 text-gray-600">{label}</span>
          <Icon size={15} className={cn(iconColor, "shrink-0")} />
        </div>
        <div className="space-y-1">
          <div className="text-xl font-semibold text-gray-900">{value}</div>
          {change && (
            <div
              className={cn(
                "text-xs font-medium",
                changeType === "positive" && "text-success",
                changeType === "negative" && "text-danger",
                changeType === "neutral" && "text-gray-600",
              )}
            >
              {change}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
