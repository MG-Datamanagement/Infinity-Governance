"use client";

import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Loader2, Check, Zap, X } from 'lucide-react';

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
    sourceId: string;
    sourceName: string;
    onClose: () => void;
    onNotFound?: () => void;
}

const LiveIngestionPanel: React.FC<LiveIngestionPanelProps> = ({ jobId, sourceId, sourceName, onClose, onNotFound }) => {
    const [isScanning, setIsScanning] = useState(false);
    const [steps, setSteps] = useState<Step[]>([
        { label: "Establishing connection", status: 'active' },
        { label: "Schema Discovery", status: 'pending' },
        { label: "Ingestion started", status: 'pending' },
        { label: "Ingestion completed", status: 'pending' },
        { label: "PII Detection Scan", status: 'pending' },
        { label: "Metadata Execution Summary", status: 'pending' },
    ]);

    const [datasets, setDatasets] = useState<IngestingDataset[]>([]);
    const [logs, setLogs] = useState<IngestionLog[]>([]);
    const [totalTables, setTotalTables] = useState<number | null>(null);
    const [completedTables, setCompletedTables] = useState(0);
    const [isComplete, setIsComplete] = useState(false);

    const eventSourceRef = useRef<EventSource | null>(null);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    useEffect(() => {
        if (!jobId) return;

        console.log(`Connecting to SSE for job: ${jobId}`);
        const url = `${process.env.NEXT_PUBLIC_DASHBOARD_API_URL || 'http://172.188.2.173:8005'}/api/v1/jobs/${jobId}/logs/stream`;
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
            updateStep("Establishing connection", 'completed');
            updateStep("Schema Discovery", 'active');
        } else if (msg.includes("Found") && msg.includes("total tables")) {
            const match = msg.match(/Found (\d+) total tables/);
            if (match) setTotalTables(parseInt(match[1]));
            updateStep("Schema Discovery", 'completed');
        } else if (msg.includes("PostgresSink connected")) {
            updateStep("Ingestion started", 'active');
        } else if (msg.includes("PostgresSink closed")) {
            const recordsMatch = msg.match(/Total records written: (\d+)/);
            if (recordsMatch) {
                setCompletedTables(prev => prev + 1);
            }
        } else if (msg.includes("Metadata ingestion complete")) {
            updateStep("Ingestion started", 'completed');
            updateStep("Ingestion completed", 'completed');
            updateStep("PII Detection Scan", 'active');
        } else if (msg.includes("Ingestion job completed")) {
            setIsComplete(true);
            updateStep("PII Detection Scan", 'completed');
            updateStep("Metadata Execution Summary", 'completed');
            setSteps(prev => prev.map(s => ({ ...s, status: 'completed' })));
        } else if (msg.includes("Duplicate key")) {
            console.warn("Ingestion warning:", msg);
        }
    };

    const updateStep = (label: string, status: Step['status']) => {
        setSteps(prev => prev.map(s => s.label === label ? { ...s, status } : s));
    };

    const handlePiiScan = async () => {
        setIsScanning(true);
        try {
            const response = await fetch('http://172.188.2.173:8005/api/v1/scan/source', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    source_id: sourceId,
                    save_to_db: true,
                    assigned_by: "ai-auto",
                    min_confidence: 0
                })
            });
            if (response.ok) {
                alert("PII Scan triggered successfully");
            } else {
                alert("Failed to trigger PII Scan");
            }
        } catch (err) {
            console.error("PII Scan error:", err);
            alert("Error connecting to scan service");
        } finally {
            setIsScanning(false);
        }
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
                <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                    <div
                        className={`${isComplete ? 'bg-green-500' : 'bg-indigo-600'} h-full transition-all duration-500 ease-out`}
                        style={{ width: `${isComplete ? 100 : (progressPercent || 5)}%` }}
                    />
                </div>
            </div>

            <div className="p-6">
                <div className="grid grid-cols-12 gap-8">
                    {/* Left Column: AI Pipeline */}
                    <div className="col-span-4 border-r border-gray-100 pr-8">
                        <div className="flex items-center gap-3 mb-6 bg-indigo-50/50 p-3 rounded-xl border border-indigo-100">
                            <div className="w-10 h-10 rounded-lg bg-white shadow-sm flex items-center justify-center">
                                <Zap className="w-6 h-6 text-indigo-600 fill-indigo-100" />
                            </div>
                            <div>
                                <p className="text-sm font-bold text-gray-900">AI Pipeline: {sourceName}</p>
                                <p className={`text-[11px] font-medium ${isComplete ? 'text-green-600' : 'text-indigo-600'}`}>
                                    {isComplete ? 'Ready' : 'Ingesting...'}
                                </p>
                            </div>
                        </div>

                        <div className="space-y-5">
                            {steps.map((step, idx) => (
                                <div key={idx} className="flex items-start gap-3 group">
                                    <div className="mt-1 flex-shrink-0">
                                        {step.status === 'completed' ? (
                                            <div className="w-5 h-5 rounded-full bg-green-100 flex items-center justify-center">
                                                <Check className="w-3.5 h-3.5 text-green-600 stroke-[3]" />
                                            </div>
                                        ) : step.status === 'active' ? (
                                            <div className="w-5 h-5 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin" />
                                        ) : (
                                            <div className="w-5 h-5 rounded-full bg-gray-50 border border-gray-200" />
                                        )}
                                    </div>
                                    <div className="flex-1">
                                        <p className={`text-[12px] font-bold tracking-tight ${step.status === 'completed' ? 'text-gray-500 line-through' :
                                            step.status === 'active' ? 'text-indigo-600 font-extrabold' : 'text-gray-300'
                                            }`}>
                                            {step.label}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="mt-10 pt-6 border-t border-gray-50">
                            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-4">Force Complete</p>
                            <div className="space-y-2">
                                <button
                                    onClick={handlePiiScan}
                                    disabled={isScanning}
                                    className="w-full flex items-center justify-center gap-2 bg-indigo-600 text-white text-[11px] font-bold py-2.5 px-4 rounded-xl hover:bg-indigo-700 transition-all shadow-md active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {isScanning ? (
                                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                    ) : (
                                        <Check className="w-3.5 h-3.5 stroke-[3]" />
                                    )}
                                    {isScanning ? 'Triggering Scan...' : 'Complete with PII scan'}
                                </button>
                                <button className="w-full flex items-center justify-center gap-2 border border-gray-200 text-gray-500 text-[11px] font-bold py-2 px-4 rounded-xl hover:bg-gray-50 transition-all active:scale-95">
                                    <Zap className="w-3.5 h-3.5" />
                                    Complete, skip PII
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Right Column: Live Ingestion Log */}
                    <div className="col-span-8">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-sm font-bold text-gray-800">Live Execution Log</h3>
                            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-green-100 text-green-700 text-[10px] font-bold uppercase tracking-tighter">
                                <div className={`w-1.5 h-1.5 rounded-full bg-green-500 ${isComplete ? '' : 'animate-pulse'}`} />
                                {completedTables}/{totalTables || 0} ready
                            </div>
                        </div>

                        <div
                            ref={scrollRef}
                            className="bg-gray-900 rounded-xl p-5 font-mono text-[10px] leading-relaxed h-[420px] overflow-y-auto custom-scrollbar-dark shadow-inner border border-gray-800"
                        >
                            {logs.length === 0 ? (
                                <div className="text-gray-600 flex items-center gap-2 italic">
                                    <Loader2 className="w-3 h-3 animate-spin" />
                                    Waiting for live event stream...
                                </div>
                            ) : (
                                logs.map((log, i) => (
                                    <div key={i} className="mb-1.5 flex gap-4 group">
                                        <span className="text-gray-600 shrink-0 select-none w-16">
                                            {new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                        </span>
                                        <span className={`shrink-0 font-bold uppercase w-12 ${log.level === 'error' ? 'text-red-400' :
                                            log.level === 'warning' ? 'text-orange-400' :
                                                'text-green-400'
                                            }`}>
                                            [{log.level}]
                                        </span>
                                        <span className="text-gray-300 break-all group-hover:text-white transition-colors">
                                            {log.message}
                                        </span>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            </div>

            <style jsx>{`
                .custom-scrollbar-dark::-webkit-scrollbar {
                    width: 4px;
                }
                .custom-scrollbar-dark::-webkit-scrollbar-track {
                    background: #111827;
                }
                .custom-scrollbar-dark::-webkit-scrollbar-thumb {
                    background: #374151;
                    border-radius: 10px;
                }
                .custom-scrollbar-dark::-webkit-scrollbar-thumb:hover {
                    background: #4b5563;
                }
            `}</style>
        </div>
    );
};

export default LiveIngestionPanel;
