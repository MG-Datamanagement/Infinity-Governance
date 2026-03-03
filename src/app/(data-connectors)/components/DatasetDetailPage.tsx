"use client";

import React, { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { datasetDetails, datasetsBySource, Dataset } from "@/services/mock";
import ComplianceReportModal from "@/app/(data-connectors)/components/ComplianceReportModal";

const TABS = ["DataCard", "Columns", "Lineage", "Properties", "Queries", "Stats", "Quality", "Governance", "Incidents"] as const;
type Tab = (typeof TABS)[number];

// ─── Build a synthetic detail from Dataset ────────────────────────────────────
function buildFallbackDetail(dataset: Dataset, sourceId: string) {
    const typeLabel = dataset.type === "View" || dataset.type === "Materialized View" ? "View" : "Dataset";
    return {
        id: dataset.id,
        sourceId,
        name: dataset.name,
        type: typeLabel,
        overview: `The ${dataset.name} ${typeLabel.toLowerCase()} contains structured data ingested from ${sourceId}. It includes ${dataset.columns} columns${dataset.rows ? ` and approximately ${dataset.rows} rows` : ""}.`,
        keyFields: [
            { name: "id", description: "Primary identifier" },
            { name: "created_at", description: "Record creation timestamp" },
            { name: "updated_at", description: "Last modification timestamp" },
        ],
        freshness: dataset.lastSync,
        volume: dataset.rows ?? "—",
        qualityScore: dataset.status === "Healthy" ? "95%" : dataset.status === "Warning" ? "72%" : "N/A",
        columnCount: dataset.columns,
        owner: "DataHub",
        ownerInitials: "DH",
        tags: dataset.hasPII ? ["PII", sourceId] : [sourceId],
        lineageWarning: dataset.status === "Warning" || dataset.status === "Error" ? "Some upstreams are unhealthy" : undefined,
    };
}

interface DatasetDetailPageProps {
    sourceId: string;
    datasetId: string;
}

const DatasetDetailPage: React.FC<DatasetDetailPageProps> = ({ sourceId, datasetId }) => {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<Tab>("DataCard");
    const [showCompliance, setShowCompliance] = useState(false);

    // Resolve detail — prefer explicit mock, fall back to synthetic
    const detail = useMemo(() => {
        if (datasetDetails[datasetId]) return datasetDetails[datasetId];
        const sourceDatasets = datasetsBySource[sourceId] ?? [];
        const dataset = sourceDatasets.find((d) => d.id === datasetId);
        if (dataset) return buildFallbackDetail(dataset, sourceId);
        return null;
    }, [sourceId, datasetId]);

    if (!detail) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-4">
                        <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375" />
                        </svg>
                    </div>
                    <p className="text-gray-700 font-semibold">Dataset not found</p>
                    <p className="text-gray-400 text-sm mt-1">The dataset "{datasetId}" was not found in "{sourceId}"</p>
                    <button onClick={() => router.back()} className="mt-4 text-indigo-600 text-sm hover:underline">
                        ← Go back
                    </button>
                </div>
            </div>
        );
    }

    const tabs = TABS.map((tab) => {
        if (tab === "Columns") return { name: tab, count: detail.columnCount };
        if (tab === "Properties") return { name: tab, count: 1 };
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
                        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
                        </svg>
                        <input
                            type="text"
                            placeholder="Find tables, dashboards, people, and more"
                            className="pl-9 pr-16 py-2 border border-gray-200 rounded-lg text-sm bg-white w-full text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                        />
                        <span className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
                            <kbd className="text-[10px] text-gray-400 bg-gray-100 border border-gray-200 rounded px-1 py-0.5">⌘</kbd>
                            <kbd className="text-[10px] text-gray-400 bg-gray-100 border border-gray-200 rounded px-1 py-0.5">K</kbd>
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
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                        </svg>
                        Home
                    </button>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                    <a href="/data-sources" className="hover:text-gray-600 transition-colors">Data Sources</a>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                    <a href={`/data-sources/${sourceId}/datasets`} className="hover:text-gray-600 transition-colors">{sourceId}</a>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                    <span className="text-gray-700 font-medium">{detail.name}</span>
                </nav>

                {/* Dataset card header */}
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm px-5 pt-5 mb-5">
                    <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-11 h-11 rounded-xl bg-green-100 flex items-center justify-center flex-shrink-0">
                                <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 5.625c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
                                </svg>
                            </div>
                            <div>
                                <h1 className="text-xl font-bold text-gray-900">{detail.name}</h1>
                                <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-400">
                                    <span className="flex items-center gap-1">
                                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                                        {detail.type}
                                    </span>
                                    <span className="text-gray-300">|</span>
                                    <span className="flex items-center gap-1">
                                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2" /></svg>
                                        {sourceId}
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setShowCompliance(true)}
                                className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                                <svg className="w-4 h-4 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
                                View Compliance Report
                            </button>
                            <button className="p-2 text-gray-400 hover:text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                    <circle cx="5" cy="12" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="19" cy="12" r="1.5" />
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
                                className={`flex items-center gap-1 px-3 py-3 text-sm font-medium transition-colors border-b-2 -mb-px whitespace-nowrap ${activeTab === name
                                    ? "border-indigo-600 text-indigo-600"
                                    : "border-transparent text-gray-500 hover:text-gray-700"
                                    }`}
                            >
                                {name}
                                {count !== undefined && (
                                    <span className={`text-[11px] px-1.5 py-0.5 rounded-full font-semibold ${activeTab === name ? "bg-indigo-100 text-indigo-600" : "bg-gray-100 text-gray-500"
                                        }`}>
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

                            {/* Overview + Key Fields */}
                            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                                <h2 className="text-base font-semibold text-gray-900 mb-2">Dataset Overview</h2>
                                <p className="text-sm text-gray-600 leading-relaxed">{detail.overview}</p>

                                <h3 className="text-sm font-semibold text-gray-900 mt-5 mb-2">Key Fields</h3>
                                <ul className="space-y-1.5">
                                    {detail.keyFields.map((field) => (
                                        <li key={field.name} className="flex items-baseline gap-2 text-sm">
                                            <span className="w-2 h-2 rounded-full bg-gray-300 flex-shrink-0 mt-[5px]" />
                                            <span>
                                                <span className="font-medium text-gray-800">{field.name}:</span>{" "}
                                                <span className="text-gray-500">{field.description}</span>
                                            </span>
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            {/* Data Quality */}
                            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                                <h2 className="text-base font-semibold text-gray-900 mb-3">Data Quality</h2>
                                <div className="grid grid-cols-3 gap-3">
                                    {[
                                        { label: "FRESHNESS", value: detail.freshness, color: "text-green-600" },
                                        { label: "VOLUME", value: detail.volume, color: "text-green-600" },
                                        { label: "QUALITY SCORE", value: detail.qualityScore, color: qualityColor },
                                    ].map((metric) => (
                                        <div key={metric.label} className="bg-green-50 border border-green-100 rounded-xl px-4 py-4">
                                            <p className="text-[10px] font-semibold text-gray-400 tracking-wide uppercase mb-1">
                                                {metric.label}
                                            </p>
                                            <p className={`text-3xl font-extrabold ${metric.color}`}>{metric.value}</p>
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
                                        <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375" />
                                        </svg>
                                    </div>
                                    <div>
                                        <p className="text-sm font-semibold text-gray-900">{detail.name}</p>
                                        <p className="text-[11px] text-gray-400">{detail.type} | {sourceId}</p>
                                    </div>
                                </div>
                            </div>

                            {/* Documentation */}
                            <div className="p-4 border-b border-gray-100">
                                <div className="flex items-center justify-between mb-1.5">
                                    <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-700">
                                        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                                        Documentation
                                    </div>
                                    <button className="text-gray-400 hover:text-indigo-600 transition-colors">
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                                    </button>
                                </div>
                                <p className="text-xs text-gray-400">No documentation yet.</p>
                            </div>

                            {/* Lineage */}
                            <div className="p-4 border-b border-gray-100">
                                <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-700 mb-2">
                                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                                    Lineage
                                </div>
                                {detail.lineageWarning ? (
                                    <div className="flex items-center gap-1.5 bg-red-50 border border-red-100 rounded-lg px-2.5 py-2 text-xs text-red-600">
                                        <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                        </svg>
                                        {detail.lineageWarning}
                                    </div>
                                ) : (
                                    <p className="text-xs text-green-600 flex items-center gap-1">
                                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                                        All upstreams healthy
                                    </p>
                                )}
                            </div>

                            {/* Owners */}
                            <div className="p-4 border-b border-gray-100">
                                <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-700 mb-2">
                                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
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
                                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" /></svg>
                                    Tags
                                </div>
                                <div className="flex flex-wrap gap-1.5">
                                    {detail.tags.map((tag) => (
                                        <span key={tag} className="inline-block text-[11px] font-medium text-gray-600 bg-gray-100 rounded px-2 py-0.5">
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Other tabs — placeholder */}
                {activeTab !== "DataCard" && (
                    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-16 text-center">
                        <div className="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center mx-auto mb-3">
                            <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>
                        </div>
                        <p className="text-sm font-medium text-gray-500">{activeTab} — coming soon</p>
                    </div>
                )}
            </main>
        </div>
    );
};

export default DatasetDetailPage;
