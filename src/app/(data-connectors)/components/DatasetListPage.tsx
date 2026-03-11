"use client";

import React, { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  ClassificationResponse,
  SourceCatalogResponse,
} from "@/services/dashboardApiServices";
import { Dataset } from "@/types";
import { downloadFileFromResponse, formatDateTime } from "@/lib/utils";
import { Check, CheckCircle2, Clock11, Loader2, XIcon } from "lucide-react";
import { ClassifyScanPhase } from "@/types/datasourcesTypes";
import { CONSTANTS } from "@/lib/constants";

// ─── Status Badge ─────────────────────────────────────────────────────────────
const StatusBadge: React.FC<{ status: Dataset["status"] }> = ({ status }) => {
  const map = {
    healthy: {
      bg: "bg-green-50",
      text: "text-green-700",
      border: "border-green-200",
    },
    warning: {
      bg: "bg-yellow-50",
      text: "text-yellow-700",
      border: "border-yellow-200",
    },
    error: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200" },
  };
  const s = map[status];
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${s.bg} ${s.text} ${s.border}`}
    >
      {status}
    </span>
  );
};

// ─── Dataset Type Icon ────────────────────────────────────────────────────────
// const TypeIcon: React.FC<{ type: Dataset["type"] }> = ({ type }) => {
//   if (type === "View" || type === "Materialized View") {
//     return (
//       <div className="w-7 h-7 rounded-md bg-purple-100 flex items-center justify-center flex-shrink-0">
//         <svg
//           className="w-4 h-4 text-purple-500"
//           fill="none"
//           viewBox="0 0 24 24"
//           stroke="currentColor"
//           strokeWidth={1.5}
//         >
//           <path
//             strokeLinecap="round"
//             strokeLinejoin="round"
//             d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
//           />
//         </svg>
//       </div>
//     );
//   }
//   return (
//     <div className="w-7 h-7 rounded-md bg-blue-100 flex items-center justify-center flex-shrink-0">
//       <svg
//         className="w-4 h-4 text-blue-500"
//         fill="none"
//         viewBox="0 0 24 24"
//         stroke="currentColor"
//         strokeWidth={1.5}
//       >
//         <path
//           strokeLinecap="round"
//           strokeLinejoin="round"
//           d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0112 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0c0 .621.504 1.125 1.125 1.125h17.25c.621 0 1.125-.504 1.125-1.125"
//         />
//       </svg>
//     </div>
//   );
// };

const TypeIcon: React.FC<{
  type: Dataset["type"];
  piiResult?: "scanning" | "pii" | "clean";
}> = ({ type, piiResult }) => {
  const bgColor =
    piiResult === "pii"
      ? "bg-yellow-100"
      : piiResult === "clean"
        ? "bg-green-100"
        : piiResult === "scanning"
          ? "bg-indigo-50"
          : "bg-blue-100";

  const iconColor =
    piiResult === "pii"
      ? "text-yellow-500"
      : piiResult === "clean"
        ? "text-green-500"
        : piiResult === "scanning"
          ? "text-indigo-300"
          : "bg-blue-100";

  if (type === "view" || type === "Materialized View") {
    return (
      <div
        className={`w-7 h-7 rounded-md ${bgColor} flex items-center justify-center flex-shrink-0`}
      >
        <svg
          className={`w-4 h-4 ${iconColor}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
          />
        </svg>
      </div>
    );
  }

  return (
    <div
      className={`w-7 h-7 rounded-md ${bgColor} flex items-center justify-center flex-shrink-0`}
    >
      <svg
        className={`w-4 h-4 ${iconColor}`}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.5}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0112 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0c0 .621.504 1.125 1.125 1.125h17.25c.621 0 1.125-.504 1.125-1.125"
        />
      </svg>
    </div>
  );
};

interface DatasetListPageProps {
  sourceId: string;
}

export type ScanState = "idle" | "queued" | "scanning" | "completed" | "error";

export interface DatasetScanState {
  datasetId: string;
  scanState: ScanState;
  progress?: number;
  tag?: string;
  confidence?: number;
}

const DatasetListPage: React.FC<DatasetListPageProps> = ({ sourceId }) => {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [piiFilter, setPIIFilter] = useState(false);

  const [allDatasets, setAllDatasets] = useState<Dataset[]>([]);
  const [sourceName, setSourceName] = useState<string>(sourceId);
  const [isLoading, setIsLoading] = useState(false);
  const [isExportListLoading, setIsExportListLoading] = useState(false);
  const [isPiiScanLoading, setIsPiiScanLoading] = useState(false);
  const [piiScanPhase, setPiiScanPhase] = useState<ClassifyScanPhase>("never");
  const [scannedDatasets, setScannedDatasets] = useState<
    Record<string, "scanning" | "pii" | "clean">
  >({});
  const [scanCount, setScanCount] = useState(0);

  React.useEffect(() => {
    const loadDatasets = async () => {
      setIsLoading(true);
      try {
        const { dashboardApiServices } = await import("@/services/dashboardApiServices");
        const stats: SourceCatalogResponse = await dashboardApiServices.fetchSourceStats(
          sourceId,
          // typeFilter?.toLowerCase(),
          // statusFilter?.toLowerCase(),
        );
        if (stats) {
          if (stats.source_name) setSourceName(stats.source_name);
          if (stats.catalogs) {
            const mapped: Dataset[] = stats.catalogs.map((cat) => {
            // keep only pii & phi tags
            const filteredTags =
              cat.tags?.filter((tag) =>
                ["pii", "phi"].includes(tag.name.toLowerCase())
              ) || [];

            return {
              id: cat.catalog_id,
              name: cat.table_name || cat.full_name,
              hasPII: filteredTags.length > 0,
              type: cat.type || "table",
              rows: cat.row_count ? cat.row_count.toString() : null,
              columns: cat.column_count || 0,
              size: null,
              lastSync: formatDateTime(cat.last_sync),
              status: cat.status || "healthy",
              tags: filteredTags
            };
          });

            setAllDatasets(mapped);
          }
        }
      } catch (err) {
        console.error("Error fetching datasets:", err);
      } finally {
        setIsLoading(false);
      }
    };
    loadDatasets();
  }, [sourceId, typeFilter, statusFilter]);

  const exportList = async () => {
    setIsExportListLoading(true);
    try {
      const { dashboardApiServices } = await import("@/services/dashboardApiServices");

      const response: any = await dashboardApiServices.downloadSourceStats(
        sourceId,
        // typeFilter?.toLowerCase(),
        // statusFilter?.toLowerCase()
      );
      await downloadFileFromResponse(response);
    } catch (err) {
      console.error("Error exporting catalogs:", err);
    } finally {
      setIsExportListLoading(false);
    }
  };

  const handleInitPiiClassification = async () => {
    setIsPiiScanLoading(true);
    setPiiScanPhase("scanning");
    setScanCount(0);

    // Mark all datasets as scanning
    const initialScanMap: Record<string, "scanning" | "pii" | "clean"> = {};
    allDatasets.forEach((d) => {
      initialScanMap[d.id] = "scanning";
    });
    setScannedDatasets(initialScanMap);

    try {
      const { dashboardApiServices } = await import("@/services/dashboardApiServices");

      const payload = {
        source_id: sourceId,
        Require_human_approval: CONSTANTS.RequireHumanApproval,
        assigned_by: CONSTANTS.assignedBy,
        min_confidence: CONSTANTS.minConfidence,
      };

      const response: ClassificationResponse =
        await dashboardApiServices.initPiiClassification(payload);

      // Create lookup map from response
      // const classificationMap: Record<string, "pii" | "clean"> = {};
      // (response?.results || []).forEach((r) => {
      //   const tag = (r.suggested_tag || "").toLowerCase();
      //   classificationMap[r.catalog_id] =
      //     tag === "error" ? "clean" : "pii";
      // });
      const classificationMap: Record<string, "pii" | "clean"> = {};
      (response?.results || []).forEach((r) => {
        const tag = (r.suggested_tag || "").toLowerCase();

        classificationMap[r.catalog_id] = ["pii", "phi"].includes(tag)
          ? "pii"
          : "clean";
      });

      // Preserve staggered animation but use real results
      const results = allDatasets.map((d) => ({
        id: d.id,
        result: classificationMap[d.id] || "clean",
      }));

      for (let i = 0; i < results.length; i++) {
        await new Promise((res) => setTimeout(res, 600));

        setScannedDatasets((prev) => ({
          ...prev,
          [results[i].id]: results[i].result,
        }));

        setScanCount(i + 1);
      }

      // Update dataset PII flag
      setAllDatasets((prev) =>
        prev.map((d) => {
          const result = classificationMap[d.id];
          return result ? { ...d, hasPII: ["pii", "phi"].includes(result) } : d;
        }),
      );

      setPiiScanPhase("complete");
    } catch (err) {
      console.error("Error during PII classification:", err);
      setPiiScanPhase("never");
      setScannedDatasets({});
    } finally {
      setIsPiiScanLoading(false);
    }
  };

  const filtered = useMemo(() => {
    let list = allDatasets;
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((d) => d.name.toLowerCase().includes(q));
    }
    if (typeFilter !== "All") {
      list = list.filter((d) => d.type === typeFilter);
    }
    if (statusFilter !== "All") {
      list = list.filter((d) => d.status === statusFilter);
    }
    if (piiFilter) {
      list = list.filter((d) => d.hasPII);
    }
    return list;
  }, [search, typeFilter, statusFilter, piiFilter, allDatasets]);

  const goToDetail = (datasetId: string) => {
    router.push(`/data-sources/${sourceId}/datasets/${datasetId}`);
  };

  return (
    <div className="min-h-screen bg-gray-50 font-sans">
      <main className="max-w-7xl mx-auto px-8 py-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 text-sm text-gray-400 mb-6">
          <a href="/" className="hover:text-gray-600 transition-colors">
            Home
          </a>
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
          <a
            href="/data-sources"
            className="hover:text-gray-600 transition-colors"
          >
            Data Sources
          </a>
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
          <span className="text-gray-600 font-medium">{sourceName}</span>
        </nav>

        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.back()}
              className="p-2 rounded-lg hover:bg-gray-200 text-gray-500 hover:text-gray-700 transition-colors"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 19l-7-7m0 0l7-7m-7 7h18"
                />
              </svg>
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
                {sourceName} Datasets
              </h1>
              <p className="text-gray-400 mt-0.5 text-sm">
                Browse and manage all datasets ingested from this source
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg bg-white hover:bg-gray-50 transition-colors">
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              Refresh
            </button>
            <button
              onClick={exportList}
              className="flex items-center gap-1.5 px-3 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors font-medium"
            >
              {isExportListLoading ? (
                <Loader2 size={16} className="animate-spin text-gray-50" />
              ) : (
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
                </svg>
              )}
              Export List
            </button>
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex items-start justify-between mb-4 gap-3">
          {/* Search */}
          <div className="relative flex-1 max-w-xs">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z"
              />
            </svg>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search datasets..."
              className="pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm bg-white w-full text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
            />
          </div>

          <div className="flex items-start gap-2">
            {/* Type filter */}
            <div className="relative">
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="appearance-none pl-8 pr-7 py-2 border border-gray-200 rounded-lg text-sm bg-white text-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 cursor-pointer"
              >
                <option value="All">All</option>
                <option value="Table">Table</option>
                <option value="View">View</option>
                {/* <option value="Materialized View">Materialized View</option> */}
              </select>
              <svg
                className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z"
                />
              </svg>
            </div>

            {/* Status filter */}
            <div className="relative">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="appearance-none pl-8 pr-7 py-2 border border-gray-200 rounded-lg text-sm bg-white text-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 cursor-pointer"
              >
                <option value="All">All</option>
                <option value="Healthy">Healthy</option>
                <option value="Warning">Warning</option>
                <option value="Risk">Risk</option>
              </select>
              <svg
                className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z"
                />
              </svg>
            </div>

            {/* PII filter */}
            {/* <button
              onClick={() => setPIIFilter((v) => !v)}
              className={`flex items-center gap-1.5 pl-8 pr-3 py-2 border rounded-lg text-sm transition-colors relative ${
                piiFilter
                  ? "bg-indigo-50 border-indigo-300 text-indigo-700"
                  : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              <svg
                className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z"
                />
              </svg>
              PII
            </button> */}

            {/* Initiate PII classification */}
            <div className="flex flex-col items-end gap-0.5">
              <>
                {piiScanPhase === "never" && (
                  <>
                    <button
                      onClick={handleInitPiiClassification}
                      className="flex items-center gap-1.5 px-3 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors font-medium whitespace-nowrap"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                        />
                      </svg>
                      Initiate PII Classification
                    </button>
                  </>
                )}

                {piiScanPhase === "re-scan" && (
                  <>
                    <button
                      onClick={handleInitPiiClassification}
                      className="flex items-center gap-1.5 px-3 py-2 text-sm text-indigo-600 border border-indigo-300 bg-white hover:bg-indigo-50 rounded-lg font-medium whitespace-nowrap"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                        />
                      </svg>
                      Reclassify PII
                    </button>
                  </>
                )}
              </>

              {piiScanPhase === "scanning" && (
                <button
                  disabled
                  className="flex items-center gap-1.5 px-3 py-2 text-sm text-indigo-600 border border-indigo-300 bg-white rounded-lg font-medium whitespace-nowrap cursor-not-allowed"
                >
                  <Loader2 size={16} className="animate-spin text-indigo-500" />
                  Scanning {scanCount}/{allDatasets.length} datasets...
                </button>
              )}

              {piiScanPhase === "complete" && (
                <div className="flex items-center gap-2">
                  <span className="flex items-center gap-1.5 px-3 py-2 text-sm text-green-700 border border-green-300 bg-green-50 rounded-lg font-medium whitespace-nowrap">
                    <CheckCircle2 size={16} className="text-green-600" />
                    PII scan complete
                  </span>
                  <button
                    onClick={() => {
                      setPiiScanPhase("re-scan");
                      setScannedDatasets({});
                      setScanCount(0);
                      setAllDatasets((prev) =>
                        prev.map((d) => ({ ...d, hasPII: false })),
                      );
                    }}
                    className="flex items-center gap-1.5 px-3 py-2 text-sm text-indigo-600 border border-indigo-300 bg-white hover:bg-indigo-50 rounded-lg font-medium whitespace-nowrap"
                  >
                    Re-run
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100">
                {[
                  "Name",
                  "Type",
                  "Rows",
                  "Columns",
                  "Size",
                  "Last Sync",
                  "Status",
                  "Actions",
                ].map((col) => (
                  <th
                    key={col}
                    className={`py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide ${
                      col === "Actions" ? "text-right" : ""
                    }`}
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-16 text-center">
                    <div className="flex flex-col items-center gap-2">
                      <div className="w-8 h-8 border-4 border-indigo-600/20 border-t-indigo-600 rounded-full animate-spin" />
                      <p className="text-sm text-gray-400">
                        Loading datasets...
                      </p>
                    </div>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="py-16 text-center text-sm text-gray-400"
                  >
                    No datasets found
                  </td>
                </tr>
              ) : (
                filtered.map((dataset) => (
                  <tr
                    key={dataset.id}
                    className="border-b border-gray-50 hover:bg-gray-50 transition-colors"
                  >
                    {/* Name */}
                    <td className="py-3.5 px-4">
                      <div className="flex items-start gap-2.5">
                        <TypeIcon
                          type={dataset.type}
                          piiResult={scannedDatasets[dataset.id]}
                        />
                        <div>
                          <p className="text-sm font-medium text-gray-800">
                            {dataset.name}
                          </p>

                          {/* Scanning state */}
                          {scannedDatasets[dataset.id] === "scanning" && (
                            <span className="inline-flex items-center gap-1 mt-0.5 text-[10px] font-medium text-indigo-500">
                              <Loader2 size={10} className="animate-spin" />
                              Scanning for PII...
                            </span>
                          )}

                          {/* PII found in scanning */}
                          {(scannedDatasets[dataset.id] === "pii" ||
                            (piiScanPhase !== "scanning" &&
                              dataset.hasPII &&
                              !scannedDatasets[dataset.id])) && (
                            <span className="inline-block mt-0.5 text-[10px] font-semibold text-yellow-600 bg-yellow-50 border border-yellow-200 rounded px-1.5 py-0.5">
                              PII Detected
                            </span>
                          )}

                          {/* No PII */}
                          {scannedDatasets[dataset.id] === "clean" && (
                            <span className="inline-flex items-center gap-1 mt-0.5 text-[10px] font-medium text-green-600">
                              <Check size={10} />
                              No PII found
                            </span>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* Type */}
                    <td className="py-3.5 px-4 text-sm text-gray-500">
                      {dataset.type}
                    </td>

                    {/* Rows */}
                    <td className="py-3.5 px-4 text-sm text-indigo-600 font-medium">
                      {dataset.rows ?? "—"}
                    </td>

                    {/* Columns */}
                    <td className="py-3.5 px-4 text-sm text-gray-600">
                      {dataset.columns}
                    </td>

                    {/* Size */}
                    <td className="py-3.5 px-4 text-sm text-gray-600">
                      {dataset.size ?? "—"}
                    </td>

                    {/* Last Sync */}
                    <td className="py-3.5 px-4 text-sm text-gray-500">
                      {dataset.lastSync}
                    </td>

                    {/* Status */}
                    <td className="py-3.5 px-4">
                      <StatusBadge status={dataset.status} />
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => goToDetail(dataset.id)}
                        className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800 font-medium transition-colors"
                      >
                        View Details
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M14 5l7 7m0 0l-7 7m7-7H3"
                          />
                        </svg>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {/* Footer */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
            <span className="text-xs text-gray-400">
              Showing {filtered.length} dataset
              {filtered.length !== 1 ? "s" : ""}
            </span>
            <div className="flex items-center gap-2">
              <button
                className="px-3 py-1.5 text-xs text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-40"
                disabled
              >
                Previous
              </button>
              <button
                className="px-3 py-1.5 text-xs text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-40"
                disabled
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default DatasetListPage;
