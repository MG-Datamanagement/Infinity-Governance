/**
 * OverviewHeader
 *
 * Top action bar for the Overview page.
 * Extracted so it can be independently tested, styled, or replaced
 * without touching page layout or data concerns.
 */

import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { Option } from "@/types";
import { Database } from "lucide-react";

const QUICK_ACTIONS: Option[] = [
  { value: "exportReport", label: "Export Report" },
  { value: "runScan", label: "Run Scan" },
  { value: "settings", label: "Settings" },
] as const;

export function OverviewHeader() {
  return (
    <div className="flex flex-col lg:flex-row items-center justify-between gap-4">
      <p className="text-sm text-gray-600 font-medium">
        Monitor your data governance health and activities
      </p>

      <div className="flex items-center gap-2">
        <Button icon={<Database size={16} />}>Add Data Source</Button>
        <Select placeholder="Quick Actions" options={QUICK_ACTIONS} />
      </div>
    </div>
  );
}
