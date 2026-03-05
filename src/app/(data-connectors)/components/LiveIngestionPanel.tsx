"use client";

import React, { useState, useEffect, useMemo, useRef } from 'react';

interface IngestionLog {
    timestamp: string;
    level: string;
    message: string;
}

interface IngestingDataset {
    name: string;
    rows: string | number;
    status: 'Ingesting' | 'Ready' | 'Error';
    piiTag?: string;
}

interface Step {
    label: string;
    status: 'pending' | 'active' | 'completed';
}

interface LiveIngestionPanelProps {
    jobId: string;
    sourceName: string;
    onClose: () => void;
    onNotFound?: () => void;
}

const LiveIngestionPanel: React.FC<LiveIngestionPanelProps> = ({ jobId, sourceName, onClose, onNotFound }) => {
    const [steps, setSteps] = useState<Step[]>([
        { label: "Establishing Connection", status: 'active' },
        { label: "Schema Discovery", status: 'pending' },
        { label: "Metadata Ingestion", status: 'pending' },
        { label: "PII Detection Scan", status: 'pending' },
        { label: "Metadata Extraction Summary", status: 'pending' },
    ]);

    const [datasets, setDatasets] = useState<IngestingDataset[]>([]);
    const [logs, setLogs] = useState<IngestionLog[]>([]);
    const [totalTables, setTotalTables] = useState<number | null>(null);
    const [completedTables, setCompletedTables] = useState(0);
    const [isComplete, setIsComplete] = useState(false);

    const eventSourceRef = useRef<EventSource | null>(null);

    useEffect(() => {
        if (!jobId) return;

        console.log(`Connecting to SSE for job: ${jobId}`);
        const url = `http://172.188.2.173:8005/api/v1/jobs/${jobId}/logs/stream`;
        const es = new EventSource(url);
        eventSourceRef.current = es;

        es.onmessage = (event) => {
            try {
                // SSE format might have "data: " prefix handled by EventSource
                const log: IngestionLog = JSON.parse(event.data);
                handleNewLog(log);
            } catch (err) {
                console.error("Failed to parse log message", err, event.data);
            }
        };

        es.addEventListener('log', (event: any) => {
            try {
                const log: IngestionLog = JSON.parse(event.data);
                handleNewLog(log);
            } catch (err) {
                console.error("Failed to parse log event", err);
            }
        });

        es.addEventListener('done', (event: any) => {
            console.log("Ingestion job completed.");
            setIsComplete(true);
            setSteps(prev => prev.map(s => ({ ...s, status: 'completed' as const })));
            es.close();
        });

        es.onerror = (err) => {
            console.error("SSE Error:", err);
            // If we get an error immediately and have no data, it's likely a 404 or connection issue
            if (datasets.length === 0 && logs.length === 0) {
                onNotFound?.();
            }
        };

        return () => {
            es.close();
            eventSourceRef.current = null;
        };
    }, [jobId]);

    const handleNewLog = (log: IngestionLog) => {
        setLogs(prev => [...prev, log]);

        const msg = log.message;

        // Parse Step transitions
        if (msg.includes("Job started")) {
            updateStep("Establishing Connection", 'completed');
            updateStep("Schema Discovery", 'active');
        } else if (msg.includes("Found") && msg.includes("total tables")) {
            const match = msg.match(/Found (\d+) total tables/);
            if (match) setTotalTables(parseInt(match[1]));
            updateStep("Schema Discovery", 'completed');
            updateStep("Metadata Ingestion", 'active');
        } else if (msg.includes("[Ingestion] Analyzing table")) {
            const tableName = msg.match(/'([^']+)'/)?.[1];
            if (tableName) {
                setDatasets(prev => {
                    if (prev.find(d => d.name === tableName)) return prev;
                    return [...prev, { name: tableName, rows: '-', status: 'Ingesting' }];
                });
            }
        } else if (msg.includes("Metadata ingestion complete")) {
            updateStep("Metadata Ingestion", 'completed');
            updateStep("PII Detection Scan", 'active');
        } else if (msg.includes("[AutoPII] Analyzing table")) {
            const tableName = msg.match(/'([^']+)'/)?.[1];
            if (tableName) {
                setDatasets(prev => prev.map(d => d.name === tableName ? { ...d, status: 'Ingesting' } : d));
            }
        } else if (msg.includes("→ tag=")) {
            const match = msg.match(/✓ '([^']+)' → tag='([^']+)'/);
            if (match) {
                const [_, tableName, tag] = match;
                setDatasets(prev => prev.map(d => d.name === tableName ? { ...d, status: 'Ready', piiTag: tag } : d));
                setCompletedTables(prev => prev + 1);
            }
        } else if (msg.includes("detection for source") && msg.includes("human_approval")) {
            // Started PII detection
            updateStep("PII Detection Scan", 'active');
        }
    };

    const updateStep = (label: string, status: Step['status']) => {
        setSteps(prev => prev.map(s => s.label === label ? { ...s, status } : s));
    };

    const progressPercent = useMemo(() => {
        if (!totalTables) return 0;
        return Math.round((completedTables / totalTables) * 100);
    }, [completedTables, totalTables]);

    return (
        <div className="bg-white border rounded-xl overflow-hidden shadow-sm">
            {/* Header / Progress Bar Area */}
            <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50">
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                        <div className={`w-2.5 h-2.5 rounded-full ${isComplete ? 'bg-green-500' : 'bg-indigo-600 animate-pulse'}`} />
                        <h3 className={`text-sm font-semibold ${isComplete ? 'text-green-700' : 'text-indigo-700'}`}>
                            {isComplete ? 'Ingestion complete — all datasets recorded' : 'Live ingestion in progress — updates happening in real time'}
                        </h3>
                    </div>
                    <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
                        {completedTables}/{totalTables || '?'} steps
                    </span>
                </div>
                {/* Progress Bar Container */}
                <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                    <div
                        className={`${isComplete ? 'bg-green-500' : 'bg-indigo-600'} h-full transition-all duration-500 ease-out`}
                        style={{ width: `${isComplete ? 100 : (progressPercent || 5)}%` }}
                    />
                </div>
            </div>

            <div className="grid grid-cols-12 gap-6 p-6">
                {/* Left Panel: Pipeline Steps */}
                <div className="col-span-4 border-r border-gray-100 pr-6">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center">
                            <svg className="w-6 h-6 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                            </svg>
                        </div>
                        <div>
                            <p className="text-sm font-bold text-gray-900">AI Pipeline</p>
                            <p className={`text-xs font-medium ${isComplete ? 'text-green-500' : 'text-indigo-500'}`}>
                                {isComplete ? 'Completed' : 'Ingesting...'}
                            </p>
                        </div>
                    </div>

                    <div className="space-y-4">
                        {steps.map((step, idx) => (
                            <div key={idx} className="flex items-start gap-3">
                                <div className="mt-1">
                                    {step.status === 'completed' ? (
                                        <div className="w-5 h-5 rounded-full bg-green-100 flex items-center justify-center">
                                            <svg className="w-3.5 h-3.5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                            </svg>
                                        </div>
                                    ) : step.status === 'active' ? (
                                        <div className="w-5 h-5 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin" />
                                    ) : (
                                        <div className="w-5 h-5 rounded-full bg-gray-100 border border-gray-200" />
                                    )}
                                </div>
                                <div>
                                    <p className={`text-xs font-medium ${step.status === 'completed' ? 'text-gray-900' :
                                        step.status === 'active' ? 'text-indigo-600' : 'text-gray-400'
                                        }`}>
                                        {step.label}
                                    </p>
                                    {step.status === 'active' && (
                                        <p className="text-[10px] text-indigo-400 animate-pulse mt-0.5">In progress...</p>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="mt-8 pt-8 border-t border-gray-100">
                        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-4">Force Complete</p>
                        <div className="space-y-2">
                            <button className="w-full flex items-center justify-center gap-2 bg-indigo-600 text-white text-xs font-semibold py-2 px-4 rounded-lg hover:bg-indigo-700 transition-colors">
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                Complete with PII scan
                            </button>
                            <button className="w-full flex items-center justify-center gap-2 border border-gray-200 text-gray-600 text-xs font-semibold py-2 px-4 rounded-lg hover:bg-gray-50 transition-colors">
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                                </svg>
                                Complete, skip PII
                            </button>
                        </div>
                    </div>
                </div>

                {/* Right Panel: Dataset Table */}
                <div className="col-span-8 flex flex-col">
                    <div className="flex items-center justify-between mb-4">
                        <h4 className="text-sm font-bold text-gray-900">Live Dataset Ingestion</h4>
                        <div className="flex items-center gap-2 px-2 py-1 bg-green-50 rounded-full border border-green-100">
                            <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                            <span className="text-[10px] font-bold text-green-600 uppercase">
                                {completedTables}/{datasets.length || (totalTables || 0)} ready
                            </span>
                        </div>
                    </div>

                    <div className="border border-gray-100 rounded-xl overflow-hidden bg-gray-50/30 flex-1">
                        <table className="w-full border-collapse">
                            <thead>
                                <tr className="border-b border-gray-100">
                                    <th className="px-4 py-2.5 text-left text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Dataset</th>
                                    <th className="px-4 py-2.5 text-left text-[11px] font-semibold text-gray-400 uppercase tracking-wider text-right">Rows</th>
                                    <th className="px-4 py-2.5 text-left text-[11px] font-semibold text-gray-400 uppercase tracking-wider text-right">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {datasets.length === 0 ? (
                                    <tr>
                                        <td colSpan={3} className="px-4 py-8 text-center text-xs text-gray-400 italic">
                                            Waiting for metadata discovery...
                                        </td>
                                    </tr>
                                ) : (
                                    datasets.map((ds, i) => (
                                        <tr key={i} className="hover:bg-white transition-colors group">
                                            <td className="px-4 py-3">
                                                <div className="flex items-center gap-2">
                                                    <svg className="w-4 h-4 text-gray-300 group-hover:text-indigo-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                                                    </svg>
                                                    <span className="text-sm font-medium text-gray-700">{ds.name}</span>
                                                </div>
                                            </td>
                                            <td className="px-4 py-3 text-right">
                                                <span className="text-xs font-mono text-gray-500">{ds.rows}</span>
                                            </td>
                                            <td className="px-4 py-3 text-right">
                                                <div className="flex items-center justify-end gap-2">
                                                    {ds.status === 'Ingesting' ? (
                                                        <>
                                                            <div className="w-3.5 h-3.5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
                                                            <span className="text-xs font-semibold text-indigo-500">Ingesting</span>
                                                        </>
                                                    ) : ds.status === 'Ready' ? (
                                                        <>
                                                            {ds.piiTag && (
                                                                <span className="text-[10px] font-bold bg-orange-100 text-orange-600 px-1.5 py-0.5 rounded uppercase">
                                                                    {ds.piiTag}
                                                                </span>
                                                            )}
                                                            <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                                                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                                            </svg>
                                                            <span className="text-xs font-semibold text-green-600">Ready</span>
                                                        </>
                                                    ) : (
                                                        <span className="text-xs font-semibold text-red-500">Error</span>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>

                    {/* PII Detection Banner */}
                    <div className="mt-4 bg-orange-50/50 border border-orange-100 rounded-xl p-3 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-lg bg-orange-100 flex items-center justify-center">
                                <svg className="w-4 h-4 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                            </div>
                            <div>
                                <p className="text-xs font-bold text-orange-800">Execute PII Detection on datasets</p>
                                <p className="text-[10px] text-orange-600">Scan for sensitive information automatically</p>
                            </div>
                        </div>
                        <button className="text-xs font-bold text-orange-600 hover:text-orange-700 transition-colors">
                            Configure →
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LiveIngestionPanel;
