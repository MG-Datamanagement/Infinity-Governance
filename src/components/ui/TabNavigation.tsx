"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Select } from "./Select";
import { Option } from "@/types";

export function TabNavigation() {
  const pathname = usePathname();

  const tabs = [
    { name: "Overview", href: "/overview" },
    { name: "Compliance", href: "/compliance" },
  ];

  const QUICK_ACTIONS: Option[] = [
    {
      value: "addDomain",
      label: "Add Domain",
      description: "Create a new governance domain",
    },
    {
      value: "createPolicy",
      label: "Create Policy",
      description: "Define new compliance policy",
    },
    {
      value: "runComplianceCheck",
      label: "Run Compliance Check",
      description: "Scan assets for compliance",
    },
    {
      value: "aiClassifier",
      label: "AI Classifier",
      description: "Auto-classify data assets",
    },
  ] as const;

  return (
    <div className="border-b border-gray-200 px-0 py-1 flex items-center justify-between">
      <nav className="flex gap-6">
        {tabs.map((tab) => (
          <Link
            key={tab.href}
            href={tab.href}
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
        <Select placeholder="Quick Actions" options={QUICK_ACTIONS} />
      </div>
    </div>
  );
}
