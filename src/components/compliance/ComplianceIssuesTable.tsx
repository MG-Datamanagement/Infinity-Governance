import { ApiComplianceIssue } from "@/types";
import { cn, getSeverityColor } from "@/lib/utils";
import { AlertCircle, Search, ChevronDown, ExternalLink } from "lucide-react";
import { useState } from "react";
import { InlineState } from "../ui/InlineState";

interface ComplianceIssuesTableProps {
  issues: ApiComplianceIssue[];
}

export function ComplianceIssuesTable({ issues }: ComplianceIssuesTableProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const filteredIssues = issues.filter(
    (issue) =>
      issue.issue.toLowerCase().includes(searchTerm.toLowerCase()) ||
      issue.dataset.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  return (
    <div className="card p-6 border border-gray-200 rounded-3xl bg-white shadow-sm space-y-6">
      {/* Header & Search/Filter Row */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-red-50 text-red-500 rounded-xl flex items-center justify-center shrink-0">
            <AlertCircle size={24} />
          </div>
          <div className="flex-1">
            <h3 className="text-base font-bold text-gray-900 leading-tight">
              Open Compliance Issues
            </h3>
            <p className="text-xs text-gray-400 font-medium">
              {filteredIssues.length} items requiring attention
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              size={16}
            />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search issues or datasets..."
              className="w-full pl-10 pr-4 h-11 border border-gray-200 bg-gray-50/30 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            )}
          </div>
          <button className="flex items-center gap-2 h-11 px-6 border border-gray-200 rounded-xl text-sm font-bold text-gray-700 hover:bg-gray-50 transition-all bg-white">
            Filter
            <ChevronDown size={16} className="text-gray-400" />
          </button>
        </div>
      </div>

      {/* Table - Desktop */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="py-4 pr-4 text-left text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                Issue
              </th>
              <th className="py-4 px-4 text-left text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                Framework
              </th>
              <th className="py-4 px-4 text-left text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                Severity
              </th>
              <th className="py-4 px-4 text-left text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                Dataset
              </th>
              <th className="py-4 px-4 text-left text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                Assignee
              </th>
              <th className="py-4 px-4 text-left text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                Due Date
              </th>
              <th className="py-4 text-right text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredIssues.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12">
                  <InlineState
                    type="empty"
                    message={
                      searchTerm
                        ? "No issues match your search."
                        : "No open compliance issues."
                    }
                  />
                </td>
              </tr>
            ) : (
              filteredIssues.map((issue, idx) => (
                <tr key={`${issue.framework}-${idx}`} className="group hover:bg-gray-50/50 transition-colors">
                  <td className="py-4 pr-4">
                    <div className="text-xs font-semibold text-gray-900">{issue.issue}</div>
                  </td>
                  <td className="py-4 px-2">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-50 text-indigo-600 border border-indigo-100">
                      {issue.framework}
                    </span>
                  </td>
                  <td className="py-4 px-2">
                    <span
                      className={cn(
                        "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border",
                        issue.severity === "HIGH" ? "bg-red-50 text-red-600 border-red-100" :
                          issue.severity === "MEDIUM" ? "bg-orange-50 text-orange-600 border-orange-100" :
                            "bg-blue-50 text-blue-600 border-blue-100"
                      )}
                    >
                      {issue.severity}
                    </span>
                  </td>
                  <td className="py-4 px-2">
                    <div className="text-xs text-gray-500 font-medium font-mono">
                      {issue.dataset}
                    </div>
                  </td>
                  <td className="py-4 px-2">
                    <div className="text-xs text-gray-900 font-medium">
                      {issue.assignee}
                    </div>
                  </td>
                  <td className="py-4 px-2">
                    <div className="text-xs text-gray-500 font-medium">{issue.due_date}</div>
                  </td>
                  <td className="py-4 text-right">
                    <button className="text-xs font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1 ml-auto">
                      View Details
                      <ExternalLink size={12} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Cards - Mobile */}
      <div className="md:hidden divide-y divide-gray-200 max-h-[420px] overflow-y-auto">
        {filteredIssues.map((issue, idx) => (
          <div key={`${issue.framework}-${idx}`} className="p-4 hover:bg-gray-50">
            <div className="space-y-3">
              <div>
                <div className="text-sm font-medium text-gray-900 mb-2">
                  {issue.issue}
                </div>
                <div className="flex flex-wrap gap-2">
                  <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    {issue.framework}
                  </span>
                  <span
                    className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${getSeverityColor(issue.severity)}`}
                  >
                    {issue.severity}
                  </span>
                </div>
              </div>
              <div className="text-sm text-gray-600">
                <div className="font-mono mb-1">{issue.dataset}</div>
                <div>
                  {issue.assignee} • {issue.due_date}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
