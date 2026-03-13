"use client";

import React, { useState, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  dashboardApiServices,
  ClassificationResponse,
  ApiCatalogDetail,
  ApiCatalogDatacard,
} from "@/services/dashboardApiServices";
import { Dataset, ApiTag, ApiColumn } from "@/types";
import ComplianceReportModal from "@/app/(data-connectors)/components/ComplianceReportModal";
import { formatDateTime } from "@/lib/utils";
import { CONSTANTS } from "@/lib/constants";
import { ClassifyScanPhase } from "@/types/datasourcesTypes";
import { cn } from "@/lib/utils";
import { CheckCircle2, Loader2 } from "lucide-react";

const TABS = [
  "DataCard",
  "Columns",
  "Lineage",
  "Properties",
  "Queries",
  "Stats",
  "Quality",
  "Governance",
  "Incidents",
] as const;
type Tab = (typeof TABS)[number];

interface DatasetDetailPageProps {
  sourceId: string;
  datasetId: string;
}

import { MarkdownRenderer } from "@/components/ui/MarkdownRenderer";

const DatasetDetailPage: React.FC<DatasetDetailPageProps> = ({
  sourceId,
  datasetId,
}) => {
  const router = useRouter();
  const [catalogData, setCatalogData] = useState<ApiCatalogDetail | null>(null);
  const [datacardData, setDatacardData] = useState<ApiCatalogDatacard | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("DataCard");
  const [showCompliance, setShowCompliance] = useState(false);
  const [isReclassifyAiLoading, setIsReclassifyAiLoading] = useState(false);
  const [reclassifyAiScanPhase, setReclassifyAiScanPhase] =
    useState<ClassifyScanPhase>("never");
  const [aiResults, setAiResults] = useState<any>({});

  useEffect(() => {
    const fetchAll = async () => {
      setIsLoading(true);
      try {
        const [detailRes, datacardRes] = await Promise.all([
          dashboardApiServices.fetchCatalogDetail(datasetId),
          dashboardApiServices.fetchCatalogDatacard(datasetId).catch((err) => {
            console.error("Failed to fetch datacard", err);
            return null;
          }),
        ]);
        setCatalogData(detailRes);
        setDatacardData(datacardRes);
      } catch (err) {
        console.error("Failed to fetch catalog detail", err);
      } finally {
        setIsLoading(false);
      }
    };

    const handleFetchClassifyApi = async() => {
      // await handleReclassifyWithAI();
      await fetchAll();
    }
    
    handleFetchClassifyApi()
  }, [datasetId]);

  const detail = useMemo(() => {
    if (!catalogData) return null;
    const ownerName =
      typeof catalogData.owner === "string"
        ? catalogData.owner
        : (catalogData?.owner as any)?.name || "Unknown";
    return {
      id: catalogData.id,
      sourceId: sourceId,
      sourceName: catalogData.source_name,
      name: catalogData.table_name,
      type: catalogData.source_type
        ? catalogData.source_type.charAt(0).toUpperCase() +
          catalogData.source_type.slice(1)
        : "Dataset",
      overview:
        catalogData.description ||
        `The ${catalogData.table_name} dataset contains structured records ingested from ${catalogData.source_name}. It belongs to the ${catalogData.schema_name} schema within the ${catalogData.database_name} database.`,
      keyFields: catalogData.columns?.map((c: any) => ({
        name: c.name,
        description: c.comment || "Column metadata",
      })),
      freshness: formatDateTime(catalogData.updated_at),
      volume:
        catalogData.row_count !== null
          ? catalogData.row_count.toLocaleString()
          : "—",
      qualityScore: "95%",
      columnCount: catalogData.column_count || 0,
      owner: ownerName,
      ownerInitials: ownerName.slice(0, 2).toUpperCase(),
      tags: catalogData.tags || [],
      lineageWarning: undefined,
      dataCardContent: datacardData?.data_card,
    };
  }, [catalogData, datacardData, sourceId]);


  const handleReclassifyWithAI = async (manual: boolean = false) => {
    if(manual) {
      setIsReclassifyAiLoading(true);
      setReclassifyAiScanPhase("scanning");
    }

    try {
      const payload = {
        source_id: sourceId,
        save_to_db: CONSTANTS.saveToDb,
        assigned_by: CONSTANTS.assignedBy,
        min_confidence: CONSTANTS.minConfidence,
      };

      const { dataSourcesService } = await import("@/services/mock");
      const response: any = await dataSourcesService.reclassifyWithAi(payload);

      const map: any = {};
      response?.results?.forEach((r: any) => {
        map[r.column_name] = ["pii", "phi"].includes(r)
          ? "pii"
          : r
      });

      setAiResults(map);

      await new Promise((res) => setTimeout(res, 1000));
      if(manual) setReclassifyAiScanPhase("complete");
    } catch (err) {
      console.error("Error during PII classification:", err);
      if(manual) setReclassifyAiScanPhase("never");
    } finally {
      if(manual) {
        setIsReclassifyAiLoading(false);
        setReclassifyAiScanPhase("re-scan");
      }
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-indigo-600/20 border-t-indigo-600 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-sm text-gray-400 font-medium">
            Loading dataset details...
          </p>
        </div>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375"
              />
            </svg>
          </div>
          <p className="text-gray-700 font-semibold">Dataset not found</p>
          <p className="text-gray-400 text-sm mt-1">
            The dataset "{datasetId}" was not found or failed to load.
          </p>
          <button
            onClick={() => router.back()}
            className="mt-4 text-indigo-600 text-sm hover:underline"
          >
            ← Go back
          </button>
        </div>
      </div>
    );
  }

  const tabs = TABS.map((tab) => {
    if (tab === "Columns")
      return { name: tab, count: catalogData?.columns?.length || 0 };
    if (tab === "Properties")
      return {
        name: tab,
        count: Object.keys(catalogData?.properties || {}).length || 0,
      };
    return { name: tab, count: undefined };
  });

  const qualityColor =
    detail.qualityScore === "N/A"
      ? "text-gray-400"
      : parseInt(detail.qualityScore) >= 90
        ? "text-green-600"
        : "text-yellow-600";

  return (
    <div className="min-h-screen bg-gray-50 font-sans">
      {/* Compliance Report Modal */}
      {showCompliance && (
        <ComplianceReportModal
          datasetName={detail.name}
          onClose={() => setShowCompliance(false)}
        />
      )}

      {/* Global search bar */}
      <div className="bg-white border-b border-gray-200 px-8 py-3">
        <div className="max-w-7xl mx-auto">
          <div className="relative max-w-lg">
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
              placeholder="Find tables, dashboards, people, and more"
              className="pl-9 pr-16 py-2 border border-gray-200 rounded-lg text-sm bg-white w-full text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
              <kbd className="text-[10px] text-gray-400 bg-gray-100 border border-gray-200 rounded px-1 py-0.5">
                ⌘
              </kbd>
              <kbd className="text-[10px] text-gray-400 bg-gray-100 border border-gray-200 rounded px-1 py-0.5">
                K
              </kbd>
            </span>
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-8 py-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 text-sm text-gray-400 mb-6">
          <button
            onClick={() => router.push("/")}
            className="hover:text-gray-600 transition-colors flex items-center gap-1"
          >
            <svg
              className="w-3.5 h-3.5"
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
            Home
          </button>
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
          <a
            href={`/data-sources/${sourceId}/datasets`}
            className="hover:text-gray-600 transition-colors"
          >
            {detail.sourceName || sourceId}
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
          <span className="text-gray-700 font-medium">{detail.name}</span>
        </nav>

        {/* Dataset card header */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm px-5 pt-5 mb-5">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-xl bg-green-100 flex items-center justify-center flex-shrink-0">
                <svg
                  className="w-6 h-6 text-green-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 5.625c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125"
                  />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  {detail.name}
                </h1>
                <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-400">
                  <span className="flex items-center gap-1">
                    <svg
                      className="w-3.5 h-3.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                    {detail.type}
                  </span>
                  <span className="text-gray-300">|</span>
                  <span className="flex items-center gap-1">
                    <svg
                      className="w-3.5 h-3.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2"
                      />
                    </svg>
                    {detail.sourceName || sourceId}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowCompliance(true)}
                className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <svg
                  className="w-4 h-4 text-indigo-500"
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
                View Compliance Report
              </button>
              <button className="p-2 text-gray-400 hover:text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                <svg
                  className="w-4 h-4"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <circle cx="5" cy="12" r="1.5" />
                  <circle cx="12" cy="12" r="1.5" />
                  <circle cx="19" cy="12" r="1.5" />
                </svg>
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-0 border-b border-gray-200 mt-5">
            {tabs.map(({ name, count }) => (
              <button
                key={name}
                onClick={() => setActiveTab(name as Tab)}
                className={`flex items-center gap-1 px-3 py-3 text-sm font-medium transition-colors border-b-2 -mb-px whitespace-nowrap ${
                  activeTab === name
                    ? "border-indigo-600 text-indigo-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {name}
                {count !== undefined && name !== "Properties" && (
                  <span
                    className={`text-[11px] px-1.5 py-0.5 rounded-full font-semibold ${
                      activeTab === name
                        ? "bg-indigo-100 text-indigo-600"
                        : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* DataCard tab body */}
        {activeTab === "DataCard" && (
          <div className="flex gap-4">
            {/* Left content */}
            <div className="flex-1 min-w-0 space-y-4">
              {detail.dataCardContent ? (
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
                  <MarkdownRenderer content={detail.dataCardContent} />
                </div>
              ) : (
                <>
                  <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                    <h2 className="text-base font-semibold text-gray-900 mb-2">
                      Dataset Overview
                    </h2>
                    <p className="text-sm text-gray-600 leading-relaxed">
                      {detail.overview}
                    </p>

                    <h3 className="text-sm font-semibold text-gray-900 mt-5 mb-2">
                      Key Fields
                    </h3>
                    <ul className="space-y-1.5">
                      {detail.keyFields.map((field) => (
                        <li
                          key={field.name}
                          className="flex items-baseline gap-2 text-sm"
                        >
                          <span className="w-2 h-2 rounded-full bg-gray-300 flex-shrink-0 mt-[5px]" />
                          <span>
                            <span className="font-medium text-gray-800">
                              {field.name}:
                            </span>{" "}
                            <span className="text-gray-500">
                              {field.description}
                            </span>
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              )}

              {/* Data Quality */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                <h2 className="text-base font-semibold text-gray-900 mb-3">
                  Data Quality
                </h2>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    {
                      label: "FRESHNESS",
                      value: detail.freshness,
                      color: "text-green-600",
                    },
                    {
                      label: "VOLUME",
                      value: detail.volume,
                      color: "text-green-600",
                    },
                    {
                      label: "QUALITY SCORE",
                      value: detail.qualityScore,
                      color: qualityColor,
                    },
                  ].map((metric) => (
                    <div
                      key={metric.label}
                      className="bg-green-50 border border-green-100 rounded-xl px-4 py-4"
                    >
                      <p className="text-[10px] font-semibold text-gray-400 tracking-wide uppercase mb-1">
                        {metric.label}
                      </p>
                      <p className={`text-3xl font-extrabold ${metric.color}`}>
                        {metric.value}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right sidebar */}
            <div className="w-64 flex-shrink-0 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden self-start">
              {/* Identity */}
              <div className="p-4 border-b border-gray-100">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-md bg-green-100 flex items-center justify-center flex-shrink-0">
                    <svg
                      className="w-4 h-4 text-green-600"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={1.5}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375"
                      />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-900">
                      {detail.name}
                    </p>
                    <p className="text-[11px] text-gray-400">
                      {detail.type} | {detail.sourceName}
                    </p>
                  </div>
                </div>
              </div>

              {/* Documentation */}
              <div className="p-4 border-b border-gray-100">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-700">
                    <svg
                      className="w-4 h-4 text-gray-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                    Documentation
                  </div>
                  <button className="text-gray-400 hover:text-indigo-600 transition-colors">
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
                        d="M12 4v16m8-8H4"
                      />
                    </svg>
                  </button>
                </div>
                <p className="text-xs text-gray-400">No documentation yet.</p>
              </div>

              {/* Lineage */}
              <div className="p-4 border-b border-gray-100">
                <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-700 mb-2">
                  <svg
                    className="w-4 h-4 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                  </svg>
                  Lineage
                </div>
                {detail.lineageWarning ? (
                  <div className="flex items-center gap-1.5 bg-red-50 border border-red-100 rounded-lg px-2.5 py-2 text-xs text-red-600">
                    <svg
                      className="w-3.5 h-3.5 flex-shrink-0"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                      />
                    </svg>
                    {detail.lineageWarning}
                  </div>
                ) : (
                  <p className="text-xs text-green-600 flex items-center gap-1">
                    <svg
                      className="w-3.5 h-3.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    All upstreams healthy
                  </p>
                )}
              </div>

              {/* Owners */}
              <div className="p-4 border-b border-gray-100">
                <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-700 mb-2">
                  <svg
                    className="w-4 h-4 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                    />
                  </svg>
                  Owners
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-indigo-600 text-white text-[10px] font-bold flex items-center justify-center flex-shrink-0">
                    {detail.ownerInitials}
                  </span>
                  <span className="text-xs text-gray-700">{detail.owner}</span>
                </div>
              </div>

              {/* Tags */}
              <div className="p-4">
                <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-700 mb-2">
                  <svg
                    className="w-4 h-4 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                    />
                  </svg>
                  Tags
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {detail.tags.map((tag: ApiTag) => (
                    <span
                      key={tag.id}
                      className="inline-block text-[11px] font-medium text-gray-600 bg-gray-100 rounded px-2 py-0.5"
                    >
                      {tag.name}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Columns tab body */}
        {activeTab === "Columns" && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/30">
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-gray-900">
                  Schema Definition
                </h2>
                <span className="px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-600 text-[11px] font-bold border border-indigo-100">
                  {catalogData?.columns?.length || 0} Columns
                </span>
              </div>
              <div className="flex items-center gap-2">
                {reclassifyAiScanPhase === "never" && (
                  <button
                    onClick={() => handleReclassifyWithAI(true)}
                    className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-indigo-600 border border-indigo-200 rounded-lg hover:bg-indigo-50 transition-colors"
                  >
                    <svg
                      className="w-3.5 h-3.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 10V3L4 14h7v7l9-11h-7z"
                      />
                    </svg>
                    Reclassify with AI
                  </button>
                )}
                {reclassifyAiScanPhase === "scanning" && (
                  <button
                    disabled
                    className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-indigo-600 border border-indigo-200 rounded-lg hover:bg-indigo-50 transition-colors disabled:opacity-50"
                  >
                    <div>
                      <Loader2
                        className="text-indigo-400 animate-spin"
                        size={16}
                      />
                    </div>
                    Reclassifying...
                  </button>
                )}
                {["re-scan", "complete"].includes(reclassifyAiScanPhase) && (
                  <button
                    onClick={() => {
                      setReclassifyAiScanPhase("re-scan");
                      handleReclassifyWithAI(true);
                    }}
                    className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-indigo-600 border border-indigo-200 rounded-lg hover:bg-indigo-50 transition-colors"
                  >
                    <div>
                      <CheckCircle2 size={16} className="text-green-400" />
                    </div>
                    Reclassified
                  </button>
                )}
                <button className="p-1.5 text-gray-400 hover:text-gray-600 border border-gray-200 rounded-lg bg-white transition-colors">
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
                      d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z"
                    />
                  </svg>
                </button>
              </div>
            </div>

            <div className="overflow-x-auto">
              {reclassifyAiScanPhase === "scanning" && (
                <div
                  className={cn(
                    "p-4 flex items-center w-full gap-2",
                    reclassifyAiScanPhase === "scanning" && "bg-indigo-50",
                  )}
                >
                  <>
                    <div>
                      <Loader2
                        className="text-indigo-400 animate-spin"
                        size={16}
                      />
                    </div>
                    <div>
                      <h3 className="text-sm text-indigo-600">
                        AI Reclassification in progress...
                      </h3>
                      <p className="text-xs text-indigo-500">
                        Analyzing column patterns, data types, and semantic
                        context
                      </p>
                    </div>
                  </>
                </div>
              )}

              {["complete", "re-scan"].includes(reclassifyAiScanPhase) && (
                <div
                  className={cn(
                    "p-4 flex items-center w-full gap-2 bg-green-50",
                  )}
                >
                  <div>
                    <CheckCircle2 size={16} className="text-green-400" />
                  </div>
                  <div>
                    <p className="text-sm text-green-700">
                      Reclassification complete — confidence scores updated.
                      Review any changes below.
                    </p>
                  </div>
                </div>
              )}

              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50/50">
                    <th className="py-3 px-6 text-[10px] font-bold text-gray-400 uppercase tracking-wider w-16">
                      #
                    </th>
                    <th className="py-3 px-6 text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                      Column Name
                    </th>
                    <th className="py-3 px-6 text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="py-3 px-6 text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                      Description
                    </th>
                    <th className="py-3 px-6 text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                      Classification
                    </th>
                    <th className="py-3 px-6 text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                      Terms
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {catalogData?.columns?.map((col: any, idx: number) => {
                    const ai = aiResults[col.name];

                    return (
                      <tr
                        key={col.name}
                        className="border-b border-gray-50 hover:bg-gray-50/80 transition-colors"
                      >
                        <td className="py-4 px-6 text-xs text-gray-400">
                          {idx + 1}
                        </td>
                        <td className="py-4 px-6">
                          <div className="flex flex-col">
                            <span className="text-sm font-bold text-gray-800">
                              {col.name}
                            </span>
                            <span className="text-[10px] font-bold text-gray-400 mt-0.5">
                              {col.is_nullable ? "NULLABLE" : "NOT NULL"}
                            </span>
                          </div>
                        </td>
                        <td className="py-4 px-6">
                          <span className="px-2 py-0.5 rounded-lg bg-gray-100 text-gray-600 text-[10px] font-bold border border-gray-200">
                            {(
                              col.type ||
                              col.data_type ||
                              "UNKNOWN"
                            ).toUpperCase()}
                          </span>
                        </td>
                        <td className="py-4 px-6 text-sm text-gray-500 italic max-w-xs truncate">
                          {col.description || "No description yet."}
                        </td>
                        {/* <td className="py-4 px-6 text-sm text-gray-600 font-medium">
                        <div className="flex flex-col gap-1.5">
                          <div className="flex items-center gap-2">
                            {col.is_primary_key && (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 text-[10px] font-bold border border-indigo-100">
                                Primary Key
                                <span className="text-[8px] opacity-70">
                                  ✦ AI
                                </span>
                              </span>
                            )}
                            {!col.is_primary_key && (
                              <span className="text-[10px] text-gray-300">
                                —
                              </span>
                            )}
                          </div>

                          {col.is_primary_key && (
                            <div className="w-16 h-1 bg-gray-100 rounded-full overflow-hidden">
                              <div className="w-[99%] h-full bg-green-500 rounded-full" />
                            </div>
                          )}
                        </div>
                      </td> */}
                        <td className="py-2 px-6 text-sm text-gray-600 font-medium">
                          <div className="flex flex-col justify-center items-start gap-1">
                            {ai ? (
                              <>
                                <span className="gap-1 px-2 py-0.5 rounded-xl bg-yellow-100 text-yellow-800 text-[10px] font-bold border border-yellow-200">
                                  {ai.tag_name}
                                </span>

                                <span className="items-center gap-1 px-2 rounded-xl bg-indigo-50 text-indigo-700 text-[10px] font-bold border border-indigo-100 w-fit">
                                  ✦ AI
                                </span>

                                <div className="flex items-center gap-2">
                                  <div className="w-16 h-1 bg-gray-100 rounded-full overflow-hidden">
                                    <div
                                      style={{
                                        width: `${ai.confidence_score * 100}%`,
                                      }}
                                      className="h-full bg-green-500 rounded-full"
                                    />
                                  </div>

                                  <span className="text-[10px] text-gray-500">
                                    {Math.round(ai.confidence_score * 100)}%
                                  </span>
                                </div>
                              </>
                            ) : col.tags?.length ? (
                              col.tags.map((tag: any) => (
                                <span
                                  key={tag.id}
                                  className="px-2 py-0.5 rounded-xl bg-gray-100 text-gray-600 text-[10px] font-bold border border-gray-200 capitalize"
                                >
                                  {tag.name}
                                </span>
                              ))
                            ) : (
                              <span className="text-[10px] text-gray-300">
                                —
                              </span>
                            )}
                          </div>
                        </td>
                        {/* <td className="py-4 px-6">
                        <div className="flex flex-wrap gap-1">
                          <span className="text-[10px] text-gray-300">—</span>
                        </div>
                      </td> */}
                        <td className="py-2 px-6">
                          <div className="flex flex-wrap gap-1">
                            {/* {ai ? (
                              <span className="px-2 py-0.5 rounded-xl bg-blue-50 text-blue-700 text-[10px] font-bold border border-blue-200">
                                {ai.tag_name}
                              </span>
                            ) : col.tags?.length ? (
                              col.tags.map((tag: any) => (
                                <span
                                  key={tag.id}
                                  className="px-2 py-0.5 rounded-xl bg-gray-100 text-gray-600 text-[10px] font-bold border border-gray-200"
                                >
                                  {tag.name}
                                </span>
                              ))
                            ) : ( */}
                            <span className="text-[10px] text-gray-300">—</span>
                            {/* )} */}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                  {(!catalogData?.columns ||
                    catalogData.columns.length === 0) && (
                    <tr>
                      <td
                        colSpan={6}
                        className="py-12 text-center text-sm text-gray-400 italic"
                      >
                        No columns found for this dataset.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Other tabs — placeholder */}
        {activeTab !== "DataCard" && activeTab !== "Columns" && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-16 text-center">
            <div className="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center mx-auto mb-3">
              <svg
                className="w-6 h-6 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                />
              </svg>
            </div>
            <p className="text-sm font-medium text-gray-500">
              {activeTab} — coming soon
            </p>
          </div>
        )}
      </main>
    </div>
  );
};

export default DatasetDetailPage;
