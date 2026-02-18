/**
 * SectionCard
 *
 * Generic card shell used by list-style overview sections (Domains, Platforms, etc.).
 * Provides the consistent header (title + icon + View All / loading spinner)
 * and scrollable list container so individual sections only define their row content.
 *
 * This is the shared pattern to adopt across overview-style pages.
 */

import { LucideLoader2 } from "lucide-react";

type Props = {
  title: string;
  icon: React.ReactNode;
  isLoading?: boolean;
  children: React.ReactNode;
};

export function SectionCard({ title, icon, isLoading, children }: Props) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-gray-900">{title}</h3>
          {icon}
        </div>

        {isLoading ? (
          <LucideLoader2 size={16} className="text-primary animate-spin" />
        ) : (
          <button
            disabled
            className="text-primary text-sm font-medium hover:underline disabled:text-gray-300 disabled:cursor-not-allowed"
          >
            View All →
          </button>
        )}
      </div>

      {children}
    </div>
  );
}