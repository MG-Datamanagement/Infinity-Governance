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
        } else if (msg.includes("PostgresSink connected")) {
            updateStep("Metadata Ingestion", 'active');
        } else if (msg.includes("PostgresSink closed")) {
            const recordsMatch = msg.match(/Total records written: (\d+)/);
            if (recordsMatch) {
                setCompletedTables(prev => prev + 1); // Using this as a proxy for progress
            }
        } else if (msg.includes("Metadata ingestion complete")) {
            updateStep("Metadata Ingestion", 'completed');
            updateStep("PII Detection Scan", 'active');
        } else if (msg.includes("Duplicate key")) {
            // Log warning but don't break the UI
            console.warn("Ingestion warning:", msg);
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

            <div className="p-6">
                {/* Full Width Panel: Pipeline Steps */}
                <div className="max-w-2xl mx-auto">
                    <div className="flex items-center gap-4 mb-8 bg-indigo-50/50 p-4 rounded-2xl border border-indigo-100">
                        <div className="w-12 h-12 rounded-xl bg-white shadow-sm flex items-center justify-center">
                            <svg className="w-7 h-7 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                            </svg>
                        </div>
                        <div>
                            <p className="text-base font-bold text-gray-900">AI Ingestion Agent</p>
                            <p className={`text-sm font-medium ${isComplete ? 'text-green-600' : 'text-indigo-600'}`}>
                                {isComplete ? 'Process completed successfully' : 'Analyzing and extracting metadata...'}
                            </p>
                        </div>
                    </div>

                    <div className="space-y-6">
                        {steps.map((step, idx) => (
                            <div key={idx} className="flex items-start gap-4 p-3 rounded-xl hover:bg-gray-50 transition-colors">
                                <div className="mt-1">
                                    {step.status === 'completed' ? (
                                        <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center">
                                            <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                            </svg>
                                        </div>
                                    ) : step.status === 'active' ? (
                                        <div className="w-6 h-6 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin" />
                                    ) : (
                                        <div className="w-6 h-6 rounded-full bg-gray-50 border border-gray-200" />
                                    )}
                                </div>
                                <div className="flex-1">
                                    <p className={`text-sm font-bold ${step.status === 'completed' ? 'text-gray-900' :
                                        step.status === 'active' ? 'text-indigo-600' : 'text-gray-400'
                                        }`}>
                                        {step.label}
                                    </p>
                                    {step.status === 'active' && (
                                        <div className="flex gap-1.5 mt-2">
                                            <span className="w-1 h-1 bg-indigo-400 rounded-full animate-bounce" />
                                            <span className="w-1 h-1 bg-indigo-400 rounded-full animate-bounce delay-100" />
                                            <span className="w-1 h-1 bg-indigo-400 rounded-full animate-bounce delay-200" />
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="mt-10 pt-8 border-t border-gray-100 flex items-center justify-between">
                        <div>
                            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Status Report</p>
                            <p className="text-xs text-gray-500 font-medium">Auto-PII detection enabled</p>
                        </div>
                        <div className="flex gap-3">
                            <button className="flex items-center gap-2 bg-indigo-600 text-white text-xs font-bold py-2 px-6 rounded-xl hover:bg-indigo-700 transition-all shadow-md active:scale-95">
                                Complete Pipeline
                            </button>
                            <button className="flex items-center gap-2 border border-gray-200 text-gray-600 text-xs font-bold py-2 px-6 rounded-xl hover:bg-gray-50 transition-all active:scale-95">
                                Skip scan
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LiveIngestionPanel;
