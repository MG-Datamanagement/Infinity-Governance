import React from "react";
import { formatDateTime } from "@/lib/utils";

interface MarkdownRendererProps {
  content: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  const lines = content.split("\n");
  let inTable = false;
  let tableHeaders: string[] = [];
  let tableRows: string[][] = [];

  const parseInlines = (text: string) => {
    const regex =
      /(\*\*.*?\*\*|\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})\b)/g;
    const parts = text.split(regex);
    return parts.map((part, i) => {
      if (!part) return part;
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={i} className="font-bold text-gray-900">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(part)) {
        return (
          <span key={i} className="font-semibold text-indigo-600">
            {formatDateTime(part)}
          </span>
        );
      }
      return part;
    });
  };

  const renderLine = (line: string, index: number) => {
    const trimmed = line.trim();

    if (trimmed.startsWith("|")) {
      const cells = trimmed
        .split("|")
        .map((c) => c.trim())
        .filter((_, i, arr) => i > 0 && i < arr.length - 1);
      if (!inTable) {
        inTable = true;
        tableHeaders = cells;
        return null;
      }
      if (trimmed.includes("---")) return null;
      tableRows.push(cells);
      return null;
    }

    if (inTable && !trimmed.startsWith("|")) {
      const table = (
        <div
          key={`table-${index}`}
          className="my-4 overflow-x-auto border border-gray-200 rounded-lg"
        >
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-50 text-gray-700 font-semibold border-b border-gray-200">
              <tr>
                {tableHeaders.map((h, i) => (
                  <th key={i} className="px-4 py-2">
                    {parseInlines(h)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tableRows.map((row, ri) => (
                <tr key={ri} className="bg-white">
                  {row.map((cell, ci) => (
                    <td
                      key={ci}
                      className="px-4 py-2 text-gray-600 font-medium"
                    >
                      {parseInlines(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      inTable = false;
      tableHeaders = [];
      tableRows = [];
      return (
        <React.Fragment key={`frag-${index}`}>
          {table}
          {renderLine(line, index + 1)}
        </React.Fragment>
      );
    }
    if (trimmed.startsWith("## "))
      return (
        <h2 key={index} className="text-xl font-bold text-gray-900 mt-6 mb-3">
          {parseInlines(trimmed.replace("## ", ""))}
        </h2>
      );
    if (trimmed.startsWith("### "))
      return (
        <h3 key={index} className="text-base font-bold text-gray-900 mt-5 mb-2">
          {parseInlines(trimmed.replace("### ", ""))}
        </h3>
      );
    if (trimmed.startsWith("- "))
      return (
        <li
          key={index}
          className="flex items-start gap-2 text-sm text-gray-600 mb-1"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-1.5 flex-shrink-0" />
          <span>{parseInlines(trimmed.replace("- ", ""))}</span>
        </li>
      );
    if (trimmed === "---")
      return <hr key={index} className="my-6 border-gray-200" />;
    if (!trimmed) return <div key={index} className="h-2" />;
    return (
      <p key={index} className="text-sm text-gray-600 leading-relaxed mb-3">
        {parseInlines(trimmed)}
      </p>
    );
  };

  return (
    <div className="markdown-body">
      {lines.map((line, i) => renderLine(line, i))}
      {inTable && (
        <div
          key="final-table"
          className="my-4 overflow-x-auto border border-gray-200 rounded-lg"
        >
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-50 text-gray-700 font-semibold border-b border-gray-200">
              <tr>
                {tableHeaders.map((h, i) => (
                  <th key={i} className="px-4 py-2">
                    {parseInlines(h)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tableRows.map((row, ri) => (
                <tr key={ri} className="bg-white">
                  {row.map((cell, ci) => (
                    <td
                      key={ci}
                      className="px-4 py-2 text-gray-600 font-medium"
                    >
                      {parseInlines(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
