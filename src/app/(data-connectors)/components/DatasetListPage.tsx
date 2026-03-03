"use client";

import React, { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { datasetsBySource, Dataset } from "@/services/mock";

// ─── Status Badge ─────────────────────────────────────────────────────────────
const StatusBadge: React.FC<{ status: Dataset["status"] }> = ({ status }) => {
    const map = {
        Healthy: { bg: "bg-green-50", text: "text-green-700", border: "border-green-200" },
        Warning: { bg: "bg-yellow-50", text: "text-yellow-700", border: "border-yellow-200" },
        Error: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200" },
    };
    const s = map[status];
    return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${s.bg} ${s.text} ${s.border}`}>
            {status}
        </span>
    );
};

// ─── Dataset Type Icon ────────────────────────────────────────────────────────
const TypeIcon: React.FC<{ type: Dataset["type"] }> = ({ type }) => {
    if (type === "View" || type === "Materialized View") {
        return (
            <div className="w-7 h-7 rounded-md bg-purple-100 flex items-center justify-center flex-shrink-0">
                <svg className="w-4 h-4 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
            </div>
        );
    }
    return (
        <div className="w-7 h-7 rounded-md bg-blue-100 flex items-center justify-center flex-shrink-0">
            <svg className="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0112 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0c0 .621.504 1.125 1.125 1.125h17.25c.621 0 1.125-.504 1.125-1.125" />
            </svg>
        </div>
    );
};


interface DatasetListPageProps {
    sourceId: string;
}

const DatasetListPage: React.FC<DatasetListPageProps> = ({ sourceId }) => {
    const router = useRouter();
    const [search, setSearch] = useState("");
    const [typeFilter, setTypeFilter] = useState("All");
    const [statusFilter, setStatusFilter] = useState("All");
    const [piiFilter, setPIIFilter] = useState(false);

    const allDatasets = datasetsBySource[sourceId] ?? [];

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
                    <a href="/" className="hover:text-gray-600 transition-colors">Home</a>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                    <a href="/data-sources" className="hover:text-gray-600 transition-colors">Data Sources</a>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                    <span className="text-gray-600 font-medium">{sourceId}</span>
                </nav>

                {/* Header */}
                <div className="flex items-start justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => router.back()}
                            className="p-2 rounded-lg hover:bg-gray-200 text-gray-500 hover:text-gray-700 transition-colors"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
                        </button>
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
                                {sourceId} Datasets
                            </h1>
                            <p className="text-gray-400 mt-0.5 text-sm">
                                Browse and manage all datasets ingested from this source
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <button className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg bg-white hover:bg-gray-50 transition-colors">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                            Refresh
                        </button>
                        <button className="flex items-center gap-1.5 px-3 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors font-medium">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                            Export List
                        </button>
                    </div>
                </div>

                {/* Toolbar */}
                <div className="flex items-center justify-between mb-4 gap-3">
                    {/* Search */}
                    <div className="relative flex-1 max-w-xs">
                        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
                        </svg>
                        <input
                            type="text"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            placeholder="Search datasets..."
                            className="pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm bg-white w-full text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                        />
                    </div>

                    <div className="flex items-center gap-2">
                        {/* Type filter */}
                        <div className="relative">
                            <select
                                value={typeFilter}
                                onChange={(e) => setTypeFilter(e.target.value)}
                                className="appearance-none pl-8 pr-7 py-2 border border-gray-200 rounded-lg text-sm bg-white text-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 cursor-pointer"
                            >
                                <option value="All">Type</option>
                                <option value="Table">Table</option>
                                <option value="View">View</option>
                                <option value="Materialized View">Materialized View</option>
                            </select>
                            <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z" /></svg>
                        </div>

                        {/* Status filter */}
                        <div className="relative">
                            <select
                                value={statusFilter}
                                onChange={(e) => setStatusFilter(e.target.value)}
                                className="appearance-none pl-8 pr-7 py-2 border border-gray-200 rounded-lg text-sm bg-white text-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 cursor-pointer"
                            >
                                <option value="All">Status</option>
                                <option value="Healthy">Healthy</option>
                                <option value="Warning">Warning</option>
                                <option value="Error">Error</option>
                            </select>
                            <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z" /></svg>
                        </div>

                        {/* PII filter */}
                        <button
                            onClick={() => setPIIFilter((v) => !v)}
                            className={`flex items-center gap-1.5 pl-8 pr-3 py-2 border rounded-lg text-sm transition-colors relative ${piiFilter
                                    ? "bg-indigo-50 border-indigo-300 text-indigo-700"
                                    : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
                                }`}
                        >
                            <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z" /></svg>
                            PII
                        </button>

                        {/* Initiate PII classification */}
                        <div className="flex flex-col items-end gap-0.5">
                            <button className="flex items-center gap-1.5 px-3 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors font-medium whitespace-nowrap">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
                                Initiate PII Classification
                            </button>
                            <span className="text-[10px] text-gray-400">toggle: PII never ran</span>
                        </div>
                    </div>
                </div>

                {/* Table */}
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                    <table className="w-full">
                        <thead>
                            <tr className="border-b border-gray-100">
                                {["Name", "Type", "Rows", "Columns", "Size", "Last Sync", "Status", "Actions"].map((col) => (
                                    <th
                                        key={col}
                                        className={`py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide ${col === "Actions" ? "text-right" : ""
                                            }`}
                                    >
                                        {col}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map((dataset) => (
                                <tr
                                    key={dataset.id}
                                    className="border-b border-gray-50 hover:bg-gray-50 transition-colors"
                                >
                                    {/* Name */}
                                    <td className="py-3.5 px-4">
                                        <div className="flex items-start gap-2.5">
                                            <TypeIcon type={dataset.type} />
                                            <div>
                                                <p className="text-sm font-medium text-gray-800">{dataset.name}</p>
                                                {dataset.hasPII && (
                                                    <span className="inline-block mt-0.5 text-[10px] font-semibold text-yellow-600 bg-yellow-50 border border-yellow-200 rounded px-1.5 py-0.5">
                                                        PII Detected
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </td>

                                    {/* Type */}
                                    <td className="py-3.5 px-4 text-sm text-gray-500">{dataset.type}</td>

                                    {/* Rows */}
                                    <td className="py-3.5 px-4 text-sm text-indigo-600 font-medium">
                                        {dataset.rows ?? "—"}
                                    </td>

                                    {/* Columns */}
                                    <td className="py-3.5 px-4 text-sm text-gray-600">{dataset.columns}</td>

                                    {/* Size */}
                                    <td className="py-3.5 px-4 text-sm text-gray-600">{dataset.size ?? "—"}</td>

                                    {/* Last Sync */}
                                    <td className="py-3.5 px-4 text-sm text-gray-500">{dataset.lastSync}</td>

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
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                                            </svg>
                                        </button>
                                    </td>
                                </tr>
                            ))}

                            {filtered.length === 0 && (
                                <tr>
                                    <td colSpan={8} className="py-16 text-center text-sm text-gray-400">
                                        No datasets found
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>

                    {/* Footer */}
                    <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
                        <span className="text-xs text-gray-400">
                            Showing {filtered.length} dataset{filtered.length !== 1 ? "s" : ""}
                        </span>
                        <div className="flex items-center gap-2">
                            <button className="px-3 py-1.5 text-xs text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-40" disabled>
                                Previous
                            </button>
                            <button className="px-3 py-1.5 text-xs text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-40" disabled>
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
