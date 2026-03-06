import { Button } from "@/components/ui/Button";
import { Download, Play, ChevronDown } from "lucide-react";

export function ComplianceHeader() {
  return (
    <div className="flex flex-col lg:flex-row items-center justify-between gap-4 mb-2">
      <div>
        <p className="text-sm text-gray-500 font-medium">
          Monitor your data governance health and activities
        </p>
      </div>
    </div>
  );
}
