import { Button } from "@/components/ui/Button";
import { File, PlayIcon } from "lucide-react";

export function ComplianceHeader() {
  return (
    <div className="flex flex-col lg:flex-row items-center justify-between gap-2">
      <p className="text-sm text-gray-600 font-medium">
        Monitor your data governance health and activities
      </p>

      <div className="flex items-center gap-2">
        <Button icon={<PlayIcon size={16} />}>Run Full Scan</Button>
        <Button icon={<File size={16} />} variant="outline">Export Report</Button>
      </div>
    </div>
  );
}
