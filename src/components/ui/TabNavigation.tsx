"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Select } from "./Select";
import { Option } from "@/types";
import QuickActionsDropdown from "./QuickActionsDropdown";
import { Button } from "./Button";
import { DownloadIcon, PlayIcon } from "lucide-react";
import { DashboardTabType, useAppStore } from "@/store/appStore";

export function TabNavigation() {
  const pathname = usePathname();
  const dashboardTab = useAppStore((s) => s.dashboardTab);
  const setDashboardTab = useAppStore((s) => s.setDashboardTab);

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
                className={cn(
                  "flex items-center gap-2 px-3 py-2 rounded-md",
                  "border border-gray-300 bg-primary",
                  "text-gray-800 font-semibold text-base",
                  "transition-colors",
                  "text-gray-50",
                )}
                icon={<PlayIcon size={16} />}
              >
                Run Full Scan
              </Button>
            </div>
            <div>
              <Button
                className={cn(
                  "flex items-center gap-2 px-3 py-2 rounded-md",
                  "border border-gray-300 bg-gray-50",
                  "text-gray-800 font-semibold text-base",
                  "hover:bg-gray-100 transition-colors",
                )}
                icon={<DownloadIcon size={16} />}
                variant="outline"
              >
                Export Report
              </Button>
            </div>
          </>
        ) : null}
        <QuickActionsDropdown />
      </div>
    </div>
  );
}
