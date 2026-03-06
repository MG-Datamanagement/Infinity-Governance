import { ApiComplianceFramework } from "@/types";
import { cn } from "@/lib/utils";
import { Check, Clock, InfoIcon, AlertCircle, XCircle } from "lucide-react";

interface ComplianceFrameworkCardProps {
  framework: ApiComplianceFramework;
}

export function ComplianceFrameworkCard({
  framework,
}: ComplianceFrameworkCardProps) {
  const getStatusInfo = (status: string) => {
    switch (status.toLowerCase()) {
      case "excellent":
        return { color: "emerald", label: "Excellent", bg: "bg-emerald-500", text: "text-emerald-500" };
      case "warning":
      case "needs_attention":
        return { color: "orange", label: "Warning", bg: "bg-orange-500", text: "text-orange-500" };
      case "critical":
        return { color: "red", label: "Critical", bg: "bg-red-500", text: "text-red-500" };
      default:
        return { color: "gray", label: status, bg: "bg-gray-400", text: "text-gray-500" };
    }
  };

  const status = getStatusInfo(framework.status);

  return (
    <div className="p-5 space-y-4 border-b border-gray-100 last:border-0">
      {/* Header Row */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-1.5">
            <h3 className="text-sm font-bold text-gray-900">
              {framework.name}
            </h3>
            <InfoIcon size={14} className="text-gray-300" />
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <div className="text-xl font-bold text-gray-900">
            {framework.score}%
          </div>
          <div className={cn(
            "text-[10px] font-bold px-2 py-0.5 rounded-full border",
            status.color === "emerald" ? "bg-emerald-50 border-emerald-100 text-emerald-600" :
            status.color === "orange" ? "bg-orange-50 border-orange-100 text-orange-600" :
            "bg-red-50 border-red-100 text-red-600"
          )}>
            {status.label}
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-100 rounded-full h-2">
        <div
          className={cn("h-2 rounded-full transition-all", status.bg)}
          style={{ width: `${framework.score}%` }}
        />
      </div>

      {/* Policy Info Row */}
      <div className="flex items-center justify-between">
        <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">
          {framework.details}
        </div>
        <div className="flex items-center gap-1 text-[10px] text-gray-400 font-medium">
          <Clock size={12} />
          <span>{framework.last_checked}</span>
        </div>
      </div>

      {/* Indicators */}
      {framework.indicators && framework.indicators.length > 0 && (
        <div className="space-y-2">
          {framework.indicators.slice(0, 2).map((indicator, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <div className={cn(
                "w-4 h-4 rounded-full flex items-center justify-center shrink-0",
                indicator.status === "success" ? "bg-emerald-50" : "bg-red-50"
              )}>
                {indicator.status === "success" ? (
                  <Check size={10} className="text-emerald-500" strokeWidth={3} />
                ) : (
                  <AlertCircle size={10} className="text-red-500" strokeWidth={3} />
                )}
              </div>
              <span className="text-[10px] font-medium text-gray-600 line-clamp-1">
                {indicator.text}
              </span>
            </div>
          ))}
          {framework.indicators.length > 2 && (
            <div className="text-[10px] font-medium text-gray-400 pl-6">
              +{framework.indicators.length - 2} more
            </div>
          )}
        </div>
      )}

      {/* Action Required Box (Mockup style for Warnings) */}
      {(framework.status === "warning" || framework.status === "needs_attention") && (
        <div className="bg-orange-50 border border-orange-100 rounded-lg p-3 space-y-2">
          <div className="flex items-center gap-2">
            <AlertCircle size={14} className="text-orange-600" />
            <span className="text-[10px] font-bold text-orange-800">Action Required:</span>
          </div>
          <p className="text-[10px] text-orange-700 leading-normal pl-5">
            Review data classification policies for healthcare data. 4 datasets need proper PHI tagging.
          </p>
          <div className="flex justify-end pt-1">
            <button className="text-[10px] font-bold text-orange-600 hover:text-orange-700 flex items-center gap-1">
              Fix Now <span>&rarr;</span>
            </button>
          </div>
        </div>
      )}

      {/* View Details Link */}
      <div className="flex justify-end pt-1">
        <button className="text-[10px] font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1">
          View Details <span>&rarr;</span>
        </button>
      </div>
    </div>
  );
}
