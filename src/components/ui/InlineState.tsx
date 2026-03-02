import { InlineStateType } from "@/types";
import { AlertTriangle, Database, LucideLoader2 } from "lucide-react";

export interface InlineStateProps {
  type: InlineStateType;
  message: string;
  onRetry?: () => void;
}

export const InlineState = ({ type, message, onRetry }: InlineStateProps) => {
  return (
    <div className="flex flex-col items-center justify-center py-6 text-center">
      {type === "loading" && (
        <LucideLoader2 size={18} className="text-primary animate-spin mb-2" />
      )}

      {type === "empty" && (
        <Database size={18} className="text-gray-300 mb-2" />
      )}

      {type === "error" && (
        <AlertTriangle size={18} className="text-danger mb-2" />
      )}

      <p className="text-xs text-gray-500 max-w-xs">{message}</p>

      {type === "error" && onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 text-xs text-primary font-medium hover:underline"
        >
          Retry →
        </button>
      )}
    </div>
  );
};
