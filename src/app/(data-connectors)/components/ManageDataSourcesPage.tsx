"use client";

import React, { useState, useMemo, useEffect } from "react";

import { useRouter } from "next/navigation";
import { dataSources, DataSource, dataSourcesService, ApiDataSource } from "@/services/mock";

import ConnectorIcon from "@/app/(data-connectors)/components/ConnectorIcon";
import AddDataSourceModal from "@/app/(data-connectors)/components/AddDataSourceModal";

// ─── Status Badge ─────────────────────────────────────────────────────────────
const StatusBadge: React.FC<{ status: DataSource["status"] }> = ({ status }) => {
    const map = {
        success: {
            dot: "bg-green-500",
            text: "text-green-600",
            bg: "bg-green-50",
            label: "Success",
        },
        failed: {
            dot: "bg-red-500",
            text: "text-red-600",
            bg: "bg-red-50",
            label: "Failed",
        },
        running: {
            dot: "bg-blue-500",
            text: "text-blue-600",
            bg: "bg-blue-50",
            label: "Running",
        },
    };
    const s = map[status];
    return (
        <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${s.bg} ${s.text}`}
        >
            <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
            {s.label}
        </span>
    );
};

// ─── Log status icon ─────────────────────────────────────────────────────────
const LogIcon: React.FC<{ status: "success" | "error" | "info" }> = ({ status }) => {
    if (status === "success")
        return (
            <svg className="w-4 h-4 text-green-500 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" />
            </svg>
        );
    if (status === "error")
        return (
            <svg className="w-4 h-4 text-red-400 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
            </svg>
        );
    return (
        <svg className="w-4 h-4 text-blue-400 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
        </svg>
    );
};

// ─── Expanded Row ─────────────────────────────────────────────────────────────
const ExpandedRow: React.FC<{ source: DataSource }> = ({ source }) => {
    const router = useRouter();
    const [stats, setStats] = useState<{
        totalTables: number;
        totalColumns: number;
        totalRows: number;
    } | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const getStats = async () => {
            setIsLoading(true);
            try {
                const apiStats = await dataSourcesService.fetchSourceStats(source.id);
                setStats({
                    totalTables: apiStats.total_tables_ingested,
                    totalColumns: apiStats.total_column_count,
                    totalRows: apiStats.total_row_count,
                });
            } catch (err) {
                console.error("Failed to fetch stats for expanded row", err);
            } finally {
                setIsLoading(false);
            }
        };
        getStats();
    }, [source.id]);

    const formatNumber = (num: number) => {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
        return num.toString();
    };

    return (
        <tr>
            <td colSpan={7} className="bg-gray-50 px-6 pb-4 pt-0">
                <div className="flex gap-4 pt-3">
                    {/* Left: stats + logs */}
                    <div className="flex-1 min-w-0">
                        {/* Stat cards */}
                        <div className="grid grid-cols-4 gap-3 mb-4">
                            {[
                                { label: "TOTAL TABLES", value: isLoading ? "..." : (stats?.totalTables.toLocaleString() || "0") },
                                { label: "TOTAL COLUMNS", value: isLoading ? "..." : (formatNumber(stats?.totalColumns || 0)) },
                                { label: "TOTAL ROWS", value: isLoading ? "..." : (formatNumber(stats?.totalRows || 0)) },
                                {
                                    label: "PII DETECTED",
                                    value: source.stats.piiDetected.toString(), // Keep using mock/source data for PII for now as it's not in stats API
                                    highlight: true,
                                },
                            ].map((stat) => (
                                <div
                                    key={stat.label}
                                    className="bg-white rounded-xl border border-gray-200 px-4 py-3"
                                >
                                    <p className="text-[10px] font-semibold text-gray-400 tracking-wide uppercase mb-1">
                                        {stat.label}
                                    </p>
                                    <p
                                        className={`text-2xl font-bold ${stat.highlight ? "text-orange-500" : "text-gray-900"
                                            }`}
                                    >
                                        {stat.value}
                                    </p>
                                </div>
                            ))}
                        </div>

                        {/* Ingestion logs */}
                        <div className="bg-white rounded-xl border border-gray-200 px-4 py-3">
                            <div className="flex items-center justify-between mb-3">
                                <h4 className="text-sm font-semibold text-gray-800">
                                    Recent Ingestion Logs
                                </h4>
                                <span className="text-xs text-gray-400">Last 24h</span>
                            </div>
                            <div className="space-y-2">
                                {source.ingestionLogs.map((log, i) => (
                                    <div key={i} className="flex items-center gap-3">
                                        <span className="text-xs text-gray-400 w-20 flex-shrink-0">
                                            {log.time}
                                        </span>
                                        <span className="text-xs text-gray-600 flex-1">{log.message}</span>
                                        <LogIcon status={log.status} />
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Right: Explore Datasets */}
                    <div className="w-64 flex-shrink-0 bg-white rounded-xl border border-gray-200 flex flex-col items-center justify-center p-6 text-center gap-3">
                        <div className="w-14 h-14 rounded-2xl bg-indigo-50 flex items-center justify-center">
                            <svg className="w-7 h-7 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 5.625c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
                            </svg>
                        </div>
                        <div>
                            <h4 className="text-sm font-semibold text-gray-800 mb-1">
                                Explore Datasets
                            </h4>
                            <p className="text-xs text-gray-400 leading-relaxed">
                                View detailed metadata, schema, and lineage for all{" "}
                                {isLoading ? "..." : (stats?.totalTables.toLocaleString() || "0")} ingested datasets.
                            </p>
                        </div>
                        <button
                            onClick={() => router.push(`/data-sources/${source.id}/datasets`)}
                            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold py-2 px-4 rounded-lg transition-colors"
                        >
                            View All Datasets
                        </button>
                    </div>
                </div>
            </td>
        </tr>
    );
};

// ─── Source Row ───────────────────────────────────────────────────────────────
const SourceRow: React.FC<{
    source: DataSource;
    checked: boolean;
    onCheck: (id: string) => void;
    onIngest: (id: string) => void;
}> = ({ source, checked, onCheck, onIngest }) => {
    const [expanded, setExpanded] = useState(false);

    return (
        <>
            <tr
                className={`border-b border-gray-100 hover:bg-gray-50 transition-colors ${expanded ? "bg-gray-50" : "bg-white"
                    }`}
            >
                {/* Checkbox */}
                <td className="pl-4 pr-2 py-3 w-10">
                    <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => onCheck(source.id)}
                        className="w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                </td>

                {/* Expand chevron + icon + name */}
                <td className="py-3 pr-4">
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setExpanded((v) => !v)}
                            className="text-gray-400 hover:text-gray-600 p-0.5 rounded transition-colors"
                        >
                            <svg
                                className={`w-4 h-4 transition-transform duration-200 ${expanded ? "rotate-90" : ""
                                    }`}
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                strokeWidth={2}
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                            </svg>
                        </button>
                        <span
                            className={`w-6 h-6 rounded flex items-center justify-center ${source.iconBg}`}
                        >
                            <ConnectorIcon icon={source.icon} className="w-4 h-4" />
                        </span>
                        <span className="text-sm font-medium text-gray-800">{source.name}</span>
                    </div>
                </td>

                {/* Schedule */}
                <td className="py-3 pr-4 text-sm text-gray-500">{source.schedule}</td>

                {/* Owner */}
                <td className="py-3 pr-4">
                    <div className="flex items-center gap-1.5">
                        <span className="w-5 h-5 rounded bg-indigo-600 text-white text-[9px] font-bold flex items-center justify-center">
                            {source.ownerIcon}
                        </span>
                        <span className="text-sm text-gray-600">{source.owner}</span>
                    </div>
                </td>

                {/* Last Run */}
                <td className="py-3 pr-4 text-sm text-gray-500">{source.lastRun}</td>

                {/* Status */}
                <td className="py-3 pr-4">
                    <StatusBadge status={source.status} />
                </td>

                {/* Actions */}
                <td className="py-3 pr-4">
                    <div className="flex items-center gap-1">
                        {/* Play button */}
                        <button 
                            onClick={() => onIngest(source.id)}
                            className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                        >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" />
                            </svg>
                        </button>
                        {/* More options */}
                        <button className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                <circle cx="12" cy="5" r="1.5" />
                                <circle cx="12" cy="12" r="1.5" />
                                <circle cx="12" cy="19" r="1.5" />
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>

            {expanded && <ExpandedRow source={source} />}
        </>
    );
};

// ─── Main Page ────────────────────────────────────────────────────────────────
const TABS = ["Sources", "Run History", "Secrets"] as const;
type Tab = (typeof TABS)[number];

const ManageDataSourcesPage: React.FC = () => {
    const [activeTab, setActiveTab] = useState<Tab>("Sources");
    const [search, setSearch] = useState("");
    const [filter, setFilter] = useState("All");
    const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());
    const [allChecked, setAllChecked] = useState(false);
    const [showAddModal, setShowAddModal] = useState(false);

    const [sources, setSources] = useState<DataSource[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchData = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const apiData = await dataSourcesService.fetchDataSources({
                status: filter !== "All" ? filter : undefined,
                limit: 20
            });

            // Map API data back to UI DataSource structure
            const mappedSources: DataSource[] = apiData.map(apiDs => {
                // Find original source to preserve detailed stats/logs for UI consistency if they exist in mocks
                const sourceId = apiDs.source_id || apiDs.id || "";
                const ownerName = apiDs.owner_name || apiDs.owner_id || "Unknown";
                
                // Find original source to preserve detailed stats/logs for UI consistency if they exist in mocks
                const original = dataSources.find(ds => ds.id === sourceId);

                // Format last run time
                let lastRun = "Never";
                if (apiDs.last_ingested_at) {
                    const date = new Date(apiDs.last_ingested_at);
                    const now = new Date();
                    const diffMs = now.getTime() - date.getTime();
                    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

                    if (diffDays === 0) lastRun = "Today";
                    else if (diffDays === 1) lastRun = "Yesterday";
                    else lastRun = `${diffDays} days ago`;
                }

                return {
                    id: sourceId,
                    name: apiDs.name,
                    icon: original?.icon || (apiDs.name.toLowerCase().includes('mongo') ? 'mongodb' : 'database'),
                    iconBg: original?.iconBg || 'bg-gray-100',
                    schedule: apiDs.schedule,
                    owner: ownerName,
                    ownerIcon: original?.ownerIcon || ownerName.substring(0, 2).toUpperCase(),
                    lastRun: lastRun,
                    status: apiDs.status,
                    stats: original?.stats || { totalDatasets: 0, totalColumns: '0', totalRows: '0', piiDetected: 0 },
                    ingestionLogs: original?.ingestionLogs || [],
                    totalDatasets: original?.totalDatasets || 0
                };
            });

            // Client side search filtering if needed, or pass search to API
            let finalSources = mappedSources;
            if (search.trim()) {
                const q = search.toLowerCase();
                finalSources = finalSources.filter(s => s.name.toLowerCase().includes(q));
            }

            setSources(finalSources);
        } catch (err) {
            setError("Failed to fetch data sources");
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [filter, search]);

    const toggleAll = () => {
        if (allChecked) {
            setCheckedIds(new Set());
            setAllChecked(false);
        } else {
            setCheckedIds(new Set(sources.map((s) => s.id)));
            setAllChecked(true);
        }
    };

    const toggleOne = (id: string) => {
        setCheckedIds((prev) => {
            const next = new Set(prev);
            next.has(id) ? next.delete(id) : next.add(id);
            return next;
        });
    };

    const handleIngest = async (id: string) => {
        try {
            await dataSourcesService.ingestSource(id);
            // Optional: Refresh data to show "running" status if the API updates it
            fetchData();
        } catch (err) {
            console.error("Failed to trigger ingestion", err);
            alert("Failed to start ingestion");
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 font-sans">
            {showAddModal && (
                <AddDataSourceModal onClose={() => setShowAddModal(false)} />
            )}
            <main className="max-w-7xl mx-auto px-8 py-8">

                {/* Breadcrumb */}
                <nav className="flex items-center gap-1.5 text-sm text-gray-400 mb-6">
                    <a href="/" className="hover:text-gray-600 transition-colors">Home</a>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    <span className="text-gray-600 font-medium">Data Sources</span>
                </nav>

                {/* Header */}
                <div className="flex items-start justify-between mb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
                            Manage Data Sources
                        </h1>
                        <p className="text-gray-400 mt-1 text-sm">
                            Configure and schedule syncs to import data from your data sources
                        </p>
                    </div>
                    <button
                        onClick={() => setShowAddModal(true)}
                        className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                        Add Data Source
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex items-center gap-0 border-b border-gray-200 mb-5">
                    {TABS.map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${activeTab === tab
                                ? "border-indigo-600 text-indigo-600"
                                : "border-transparent text-gray-500 hover:text-gray-700"
                                }`}
                        >
                            {tab}
                        </button>
                    ))}
                </div>

                {/* Toolbar */}
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                        {/* Search */}
                        <div className="relative">
                            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
                            </svg>
                            <input
                                type="text"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                placeholder="Search..."
                                className="pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm bg-white text-gray-700 placeholder-gray-400 w-52 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                            />
                        </div>

                        {/* Filter dropdown */}
                        <div className="relative">
                            <select
                                value={filter}
                                onChange={(e) => setFilter(e.target.value)}
                                className="appearance-none pl-3 pr-8 py-2 border border-gray-200 rounded-lg text-sm bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all cursor-pointer"
                            >
                                <option>All</option>
                                <option>Success</option>
                                <option>Failed</option>
                                <option>Running</option>
                            </select>
                            <svg className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                        </div>
                    </div>

                    {/* Refresh */}
                    <button
                        onClick={() => fetchData()}
                        disabled={isLoading}
                        className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg bg-white hover:bg-gray-50 transition-colors disabled:opacity-50"
                    >
                        <svg className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Refresh
                    </button>
                </div>

                {/* Table */}
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                    <table className="w-full">
                        <thead>
                            <tr className="border-b border-gray-100">
                                <th className="pl-4 pr-2 py-3 w-10">
                                    <input
                                        type="checkbox"
                                        checked={allChecked}
                                        onChange={toggleAll}
                                        className="w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                    />
                                </th>
                                <th className="py-3 pr-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                                    Name
                                </th>
                                <th className="py-3 pr-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                                    Schedule
                                </th>
                                <th className="py-3 pr-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                                    Owner
                                </th>
                                <th className="py-3 pr-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                                    Last Run
                                </th>
                                <th className="py-3 pr-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                                    Status
                                </th>
                                <th className="py-3 pr-4 w-20" />
                            </tr>
                        </thead>
                        <tbody>
                            {isLoading ? (
                                Array.from({ length: 5 }).map((_, i) => (
                                    <tr key={i} className="border-b border-gray-100 animate-pulse">
                                        <td className="p-4" colSpan={7}>
                                            <div className="h-5 bg-gray-100 rounded w-full"></div>
                                        </td>
                                    </tr>
                                ))
                            ) : sources.length > 0 ? (
                                sources.map((source) => (
                                    <SourceRow
                                        key={source.id}
                                        source={source}
                                        checked={checkedIds.has(source.id)}
                                        onCheck={toggleOne}
                                        onIngest={handleIngest}
                                    />
                                ))
                            ) : (
                                <tr>
                                    <td colSpan={7} className="py-16 text-center text-sm text-gray-400">
                                        {error || "No data sources found"}
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </main>
        </div>
    );
};

export default ManageDataSourcesPage;
