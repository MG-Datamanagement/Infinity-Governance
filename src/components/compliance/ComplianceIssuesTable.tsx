"use client";

import { ComplianceIssue } from "@/types";
import { getSeverityColor } from "@/lib/utils";
import { AlertCircle, Search } from "lucide-react";
import { useState } from "react";
import { InlineState } from "../ui/InlineState";

interface ComplianceIssuesTableProps {
  issues: ComplianceIssue[];
}

export function ComplianceIssuesTable({ issues }: ComplianceIssuesTableProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const filteredIssues = issues.filter(
    (issue) =>
      issue.issue.toLowerCase().includes(searchTerm.toLowerCase()) ||
      issue.dataset.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  return (
    <div className="card">
      {/* Header */}
      <div className="p-2 md:p-3 border-b border-gray-200">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-2">
          <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center flex-shrink-0">
            <AlertCircle className="text-red-600" size={20} />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-gray-900">
              Open Compliance Issues
            </h3>
            <p className="text-xs text-gray-500">
              {filteredIssues.length}
              {searchTerm && filteredIssues.length !== issues.length
                ? ` of ${issues.length}`
                : ""}{" "}
              items requiring attention
            </p>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            size={16}
          />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search issues or datasets..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          />

          {searchTerm && (
            <button
              onClick={() => setSearchTerm("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Table - Desktop */}
      <div className="hidden md:block overflow-x-auto max-h-[420px] overflow-y-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
            <tr>
              <th className="px-2.5 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Issue
              </th>
              <th className="px-2.5 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Framework
              </th>
              <th className="px-2.5 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Severity
              </th>
              <th className="px-2.5 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Dataset
              </th>
              <th className="px-2.5 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Assignee
              </th>
              <th className="px-2.5 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Due Date
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            <>
              {filteredIssues.length === 0 && (
                <tr>
                  <td colSpan={6}>
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
              )}

              {filteredIssues.map((issue) => (
                <tr key={issue.id} className="hover:bg-gray-50">
                  <td className="px-2.5 py-2.5">
                    <div className="text-sm text-gray-900">{issue.issue}</div>
                  </td>
                  <td className="px-2.5 py-2.5">
                    <span className="inline-flex items-center px-1.5 py-1 rounded-full text-xs/3 font-medium bg-blue-100 text-blue-800">
                      {issue.framework}
                    </span>
                  </td>
                  <td className="px-2.5 py-2.5">
                    <span
                      className={`inline-flex items-center px-1.5 py-1 rounded-full text-xs/3 font-medium ${getSeverityColor(issue.severity)}`}
                    >
                      {issue.severity}
                    </span>
                  </td>
                  <td className="px-2.5 py-2.5">
                    <div className="text-sm text-gray-600 font-mono">
                      {issue.dataset}
                    </div>
                  </td>
                  <td className="px-2.5 py-2.5">
                    <div className="text-sm text-gray-900">
                      {issue.assignee}
                    </div>
                  </td>
                  <td className="px-2.5 py-2.5">
                    <div className="text-sm text-gray-600">{issue.dueDate}</div>
                  </td>
                </tr>
              ))}
            </>
          </tbody>
        </table>
      </div>

      {/* Cards - Mobile */}
      <div className="md:hidden divide-y divide-gray-200 max-h-[420px] overflow-y-auto">
        {filteredIssues.map((issue) => (
          <div key={issue.id} className="p-4 hover:bg-gray-50">
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
                  {issue.assignee} • {issue.dueDate}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
