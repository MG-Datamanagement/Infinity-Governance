"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Select } from "./Select";
import { Option } from "@/types";
import QuickActionsDropdown from "./QuickActionsDropdown";
import { Button } from "./Button";
import { Download, Play, ChevronDown, Loader2 } from "lucide-react";
import { DashboardTabType, useAppStore } from "@/store/appStore";
import { useState } from "react";
import { dashboardApiServices } from "@/services/dashboardApiServices";
import { ComplianceScanPanel } from "@/components/compliance/ComplianceScanPanel";

export function TabNavigation() {
  const pathname = usePathname();
  const dashboardTab = useAppStore((s) => s.dashboardTab);
  const setDashboardTab = useAppStore((s) => s.setDashboardTab);
  const [isExporting, setIsExporting] = useState(false);
  const [isScanOpen, setIsScanOpen] = useState(false);

  const handleExportReport = async () => {
    if (isExporting) return;
    setIsExporting(true);
    try {
      await dashboardApiServices.exportComplianceReport();
    } catch (err) {
      console.error("Failed to export compliance report:", err);
      alert("Failed to export report. Please try again.");
    } finally {
      setIsExporting(false);
    }
  };

  const tabs = [
    { name: "Overview", href: "/overview" },
    { name: "Compliance", href: "/compliance" },
  ];

  return (
    <div className="border-b border-gray-200 px-0 py-1 flex items-center justify-between">
      <nav className="flex gap-5">
        {tabs.map((tab) => (
          <Link
            key={tab.href}
            href={tab.href}
            onClick={() => setDashboardTab(tab.name as DashboardTabType)}
            className={cn(
              "pb-2 px-1 text-sm font-medium transition-colors border-b-2",
              pathname === tab.href
                ? "text-primary border-primary font-bold"
                : "text-gray-500 border-transparent hover:text-gray-900",
            )}
          >
            {tab.name}
          </Link>
        ))}
      </nav>
      <div className="flex items-center gap-2">
        {pathname === "/compliance" ? (
          <>
            <div>
              <Button
                variant="primary"
                onClick={() => setIsScanOpen(true)}
                className="bg-indigo-600 hover:bg-indigo-700 h-9 px-4 rounded-lg flex items-center gap-2"
                icon={<Play size={16} fill="currentColor" />}
              >
                Run Full Scan
              </Button>
            </div>
            <div>
              <Button
                variant="outline"
                onClick={handleExportReport}
                disabled={isExporting}
                className="h-9 px-4 border-gray-300 rounded-lg text-gray-700 font-medium flex items-center gap-2 bg-white disabled:opacity-60"
                icon={
                  isExporting ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Download size={16} />
                  )
                }
              >
                {isExporting ? "Exporting..." : "Export Report"}
              </Button>
            </div>
          </>
        ) : null}
        <QuickActionsDropdown />
      </div>

      <ComplianceScanPanel
        isOpen={isScanOpen}
        onClose={() => setIsScanOpen(false)}
      />
    </div>
  );
}
