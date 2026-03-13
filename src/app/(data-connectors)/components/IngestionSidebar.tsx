"use client";

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { X, Bell, History, Check, Loader2, Database, Shield, Zap, Search, AlertCircle, ShieldCheckIcon, ArrowRight, CheckCircle2 } from 'lucide-react';
import { useAppStore } from '@/store/appStore';
import { Button } from '@/components/ui/Button';
import { CONSTANTS } from '@/lib/constants';
import { dashboardApiServices, SourceAiSummaryResponse } from '@/services/dashboardApiServices';
import { RiRobot2Fill } from 'react-icons/ri';
import { useRouter } from 'next/navigation';

interface IngestionLog {
    timestamp: string;
    level: string;
    message: string;
}

interface Step {
    label: string;
    status: 'pending' | 'active' | 'completed';
}

interface IngestionSidebarProps {
    jobId: string;
    sourceName: string;
    isOpen: boolean;
    onClose: (viewIngestedDataset: boolean) => void;
}

const IngestionSidebar: React.FC<IngestionSidebarProps> = ({ jobId, sourceName, isOpen, onClose }) => {
    const [steps, setSteps] = useState<Step[]>([
        { label: "Establishing connection", status: 'active' },
        { label: "Schema Discovery", status: 'pending' },
        { label: "Ingestion started", status: 'pending' },
        { label: "Ingestion completed", status: 'pending' },
        { label: "PII Detection Scan", status: 'pending' },
        { label: "Metadata Execution Summary", status: 'pending' },
    ]);

    const [isThinking, setIsThinking] = useState(true);
    const [progress, setProgress] = useState(1);
    const [totalSteps] = useState(12);
    const [showNotification, setShowNotification] = useState(true);
    const [logs, setLogs] = useState<IngestionLog[]>([]);
    const [isComplete, setIsComplete] = useState(false);

    const eventSourceRef = useRef<EventSource | null>(null);
    const scrollRef = useRef<HTMLDivElement>(null);
    const [streamStatus, setStreamStatus] = useState<"connecting" | "connected" | "completed" | "error">("connecting");
    const { addDsConfig, setAddDsConfig } = useAppStore();
    const router = useRouter();

    const [sourceAiSummary, setSourceAiSummary] = useState<SourceAiSummaryResponse | null>(null);
    const [isSourceAiSummaryLoading, setIsSourceAiSummaryLoading] = useState<boolean>(false);

    const mainScrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    useEffect(() => {
        if (isOpen) {
            const timer = setTimeout(() => setShowNotification(false), 5000);
            return () => clearTimeout(timer);
        }
    }, [isOpen]);

    useEffect(() => {
        if (!jobId || !isOpen) return;

        console.log(`Sidebar connecting to SSE for job: ${jobId}`);
        const url = `${process.env.NEXT_PUBLIC_DASHBOARD_API_URL || 'http://172.188.2.173:8005'}/api/v1/jobs/${jobId}/logs/stream`;
        const es = new EventSource(url);
        eventSourceRef.current = es;

        es.onopen = () => {
            setStreamStatus("connected");
        };

        es.onmessage = (event) => {
            try {
                const log: IngestionLog = JSON.parse(event.data);
                handleNewLog(log);
            } catch (err) {
                console.error("Sidebar failed to parse log", err);
            }
        };

        es.addEventListener('log', (event: any) => {
            try {
                const log: IngestionLog = JSON.parse(event.data);
                handleNewLog(log);
            } catch (err) {
                console.error("Sidebar failed to parse log event", err);
            }
        });

        es.addEventListener('done', () => {
            setIsComplete(true);
            setIsThinking(false);
            setSteps(prev => prev.map(s => ({ ...s, status: 'completed' })));
            setProgress(totalSteps);
            setStreamStatus("completed");
            es.close();

            if (addDsConfig && !addDsConfig.piiApproval) {
                handleBatchApis();
            }
        });

        es.onerror = (err) => {
            setStreamStatus("error");
            console.error("Sidebar SSE Error:", err);
        };

        return () => {
            es.close();
            eventSourceRef.current = null;
        };
    }, [jobId, isOpen]);

     const handleBatchApis = async () => {
       setIsSourceAiSummaryLoading(true);
       try {
         await handleTableClassification();
         await handleColumnClassification();
         await handleFetchIngestionSourceAiSummary();
       } catch (error) {
         console.error("Error during classification and Ai summary:", error);
         setIsSourceAiSummaryLoading(false);
       } finally {
         setIsSourceAiSummaryLoading(false);
       }
     };

     const handleTableClassification = async () => {
       try {
         const payload = {
           source_id: addDsConfig.sourceId,
           Require_human_approval: addDsConfig.piiApproval,
           assigned_by: CONSTANTS.assignedBy,
           min_confidence: CONSTANTS.minConfidence,
         };

         const response: any =
           await dashboardApiServices.initPiiClassification(payload);
       } catch (err) {
         console.error("Error during PII classification:", err);
       }
     };

     const handleColumnClassification = async () => {
       try {
         const payload = {
           source_id: addDsConfig.sourceId,
           save_to_db: CONSTANTS.saveToDb,
           assigned_by: CONSTANTS.assignedBy,
           min_confidence: CONSTANTS.minConfidence,
         };

         const { dataSourcesService } = await import("@/services/mock");
         const response: any =
           await dataSourcesService.reclassifyWithAi(payload);
       } catch (err) {
         console.error("Error during PII classification:", err);
       }
     };

     const handleFetchIngestionSourceAiSummary = async () => {
       try {
         const response: SourceAiSummaryResponse =
           await dashboardApiServices.fetchIngestionAiSummary(
             addDsConfig?.sourceId,
           );
         setSourceAiSummary(response);
       } catch (err) {
         console.error("Error during classification and Ai summary:", err);
         setIsSourceAiSummaryLoading(false);
       }
     };

    const handleNewLog = (log: IngestionLog) => {
        setLogs(prev => [...prev.slice(-100), log]);
        const msg = log.message;

        if (msg.includes("Job started")) {
            updateStep("Establishing connection", 'completed');
            updateStep("Schema Discovery", 'active');
            setProgress(2);
        } else if (msg.includes("Found") && msg.includes("total tables")) {
            updateStep("Schema Discovery", 'completed');
            setProgress(3);
        } else if (msg.includes("PostgresSink connected")) {
            updateStep("Ingestion started", 'active');
            setProgress(4);
        } else if (msg.includes("PostgresSink closed")) {
            setProgress(p => Math.min(p + 1, totalSteps - 2));
        } else if (msg.includes("Metadata ingestion complete")) {
            updateStep("Ingestion started", 'completed');
            updateStep("Ingestion completed", 'completed');
            updateStep("PII Detection Scan", 'active');
            setProgress(totalSteps - 1);
        } else if (msg.includes("Ingestion job completed")) {
            setIsComplete(true);
            setIsThinking(false);
            updateStep("PII Detection Scan", 'completed');
            updateStep("Metadata Execution Summary", 'completed');
            setSteps(prev => prev.map(s => ({ ...s, status: 'completed' })));
            setProgress(totalSteps);
        }
    };

    const updateStep = (label: string, status: Step['status']) => {
        setSteps(prev => prev.map(s => s.label === label ? { ...s, status } : s));
    };

    const onCloseReset = (viewIngestedDataset: boolean = false) => {
        onClose(viewIngestedDataset)
        setStreamStatus("connecting")
        setIsSourceAiSummaryLoading(false)
        setSourceAiSummary(null)
        setAddDsConfig({})
    } 

    if (!isOpen) return null;

    return (
        <>
            {/* Overlay */}
            <div
                className="fixed inset-0 backdrop-blur-[1px] z-[60] transition-opacity duration-300"
                onClick={() => onCloseReset(false)}
            />

            {/* Sidebar Container */}
            <div 
                ref={mainScrollRef}
                className={`fixed inset-y-0 right-0 w-[400px] bg-white shadow-2xl z-[70] transform transition-transform duration-500 ease-out flex flex-col ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
            >

                {/* Header */}
                <div className="bg-indigo-600 p-4 text-white relative flex-shrink-0">
                    <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-2xl bg-white/20 flex items-center justify-center backdrop-blur-md">
                                <Zap className="w-4 h-4 text-white fill-white" />
                            </div>
                            <div>
                                <h2 className="text-base font-semibold font-sans">AI Ingestion Agent</h2>
                                <p className="text-xs text-indigo-100 opacity-80">Data pipeline overview</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="bg-white/10 hover:bg-white/20 p-1 rounded-xl transition-colors cursor-pointer">
                                <Bell className="w-4 h-4" />
                            </div>
                            <div className="bg-white/10 hover:bg-white/20 p-1 rounded-xl transition-colors cursor-pointer">
                                <History className="w-4 h-4" />
                            </div>
                            <div onClick={() => onCloseReset(false)} className="bg-white/10 hover:bg-white/20 p-1 rounded-xl transition-colors cursor-pointer">
                                <X className="w-4 h-4" />
                            </div>
                        </div>
                    </div>

                    <div className="mt-2">
                        <div className="flex items-center justify-between">
                            <div className={`inline-flex items-center gap-1.5 border text-white px-2 py-0.5 rounded-full text-xs font-medium shadow-lg ${isThinking ? 'bg-orange-500/90 border-orange-400' : 'bg-green-500 border-green-400'}`}>
                                <span className={`w-1.5 h-1.5 bg-white rounded-full ${isThinking ? 'animate-pulse' : ''}`} />
                                {isThinking ? 'Thinking' : 'Completed'}
                            </div>
                            <button className="text-xs font-medium text-white/70 hover:text-white transition-colors underline underline-offset-4">Override</button>
                        </div>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-5">
                    {/* Notification Toast (Inside Sidebar top) */}
                    {showNotification && (
                        <div className="bg-white border-2 border-indigo-100 rounded-2xl p-4 shadow-xl flex items-start gap-4 animate-in slide-in-from-top-4 duration-500">
                            <div className="w-10 h-10 rounded-full bg-gray-50 flex items-center justify-center border border-gray-100">
                                <div className="p-1 rounded bg-indigo-50 border border-indigo-100">
                                    <Zap className="w-5 h-5 text-indigo-600 fill-indigo-600" />
                                </div>
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-bold text-gray-900">Ingestion started</p>
                                <p className="text-xs text-gray-500 truncate">"{sourceName}" · {steps.length} steps identified</p>
                            </div>
                        </div>
                    )}

                    {/* Summary Info */}
                    <div className="bg-indigo-50/50 border border-indigo-100 rounded-2xl p-4 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                            <Zap className="w-12 h-12 text-indigo-600" />
                        </div>
                        <h3 className="text-xs font-bold text-indigo-600 uppercase tracking-wider mb-3">AI Agent Summary</h3>
                        <div className="space-y-2.5">
                            <div className="flex items-center gap-2">
                                <div className="w-4 h-4 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
                                    <Check className="w-2.5 h-2.5 text-green-600 stroke-[3]" />
                                </div>
                                <span className="text-xs font-medium text-gray-700">Connecting to {sourceName}...</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className={`w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 ${isComplete ? 'bg-green-100' : 'border border-indigo-400 border-t-transparent animate-spin'}`}>
                                    {isComplete && <Check className="w-2.5 h-2.5 text-green-600 stroke-[3]" />}
                                </div>
                                <span className="text-xs font-medium text-gray-700">Fetching dataset info...</span>
                            </div>
                        </div>
                    </div>

                    {/* Central Animation Placeholder */}
                    <div className="flex flex-col items-center justify-center p-2">
                        <div className="w-20 h-20 rounded-full bg-indigo-100 flex items-center justify-center mb-4 relative">
                            {!isComplete && (
                                <div className="absolute inset-x-0 bottom-[-5px] flex justify-center gap-1.5 opacity-40">
                                    <span className="w-1.5 h-1.5 bg-indigo-600 rounded-full animate-bounce delay-0" />
                                    <span className="w-1.5 h-1.5 bg-indigo-600 rounded-full animate-bounce delay-150" />
                                    <span className="w-1.5 h-1.5 bg-indigo-600 rounded-full animate-bounce delay-300" />
                                </div>
                            )}
                            {isComplete ? (
                                <div className="w-12 h-12 rounded-full bg-green-500 flex items-center justify-center animate-in zoom-in duration-500">
                                    <Check className="w-7 h-7 text-white stroke-[3]" />
                                </div>
                            ) : (
                                <Zap className="w-10 h-10 text-indigo-600 fill-indigo-100" />
                            )}
                        </div>
                        <h4 className="text-lg font-bold text-gray-800 tracking-tight">
                            {isComplete ? 'Ingestion Complete' : 'Schema Discovery'}
                        </h4>
                    </div>

                    {/* Pipeline Progress */}
                    <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
                        <div className="p-4 bg-gray-50/50 border-b border-gray-100 flex items-center justify-between">
                            <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest">Pipeline Progress</h3>
                            <span className="text-[10px] font-bold text-indigo-600">{progress}/{totalSteps} steps</span>
                        </div>
                        <div className="p-4">
                            <div className="w-full bg-gray-200 rounded-full h-2 mb-4 overflow-hidden">
                                <div
                                    className="bg-indigo-600 h-full transition-all duration-1000 ease-in-out"
                                    style={{ width: `${(progress / totalSteps) * 100}%` }}
                                />
                            </div>

                            <div className="flex items-center gap-2 mb-4">
                                <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${isComplete ? 'bg-green-100 text-green-700' : 'bg-indigo-100 text-indigo-700'}`}>
                                    {isComplete ? <Check className="w-2.5 h-2.5 stroke-[3]" /> : <Loader2 className="w-2.5 h-2.5 animate-spin" />}
                                    {isComplete ? 'Execution Complete' : 'Live Activity'}
                                </div>
                                <span className="text-xs font-bold text-gray-700">
                                    {isComplete ? 'All processes finished' : 'Streaming raw logs...'}
                                </span>
                            </div>

                            {/* Raw Log Viewer */}
                            <div
                                ref={scrollRef}
                                className="bg-gray-900 rounded-xl p-4 font-mono text-[10px] leading-relaxed h-[350px] overflow-y-auto custom-scrollbar-dark shadow-inner border border-gray-800"
                            >
                                {logs.length === 0 ? (
                                    <div className="text-gray-500 italic">Waiting for connection...</div>
                                ) : (
                                    logs.map((log, i) => (
                                        <div key={i} className="mb-1.5 flex gap-3 group">
                                            <span className="text-gray-600 shrink-0 select-none">
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

                    {/* Require Apporval for PII Scan Actions */}
                    {(streamStatus === "completed" && addDsConfig?.piiApproval && !isSourceAiSummaryLoading && !sourceAiSummary) ? <div className='w-full flex justify-between items-center gap-2 transition-all'>
                        <div>
                            <Button onClick={() => onCloseReset(false)} variant="outline" className='disabled:opacity-50'>
                                <ArrowRight />
                                Complete, skip PII
                            </Button>
                       </div>
                       <div>
                            <Button onClick={handleBatchApis} className='disabled:opacity-50'>
                                <ShieldCheckIcon />
                                Complete with PII Scan
                            </Button>
                       </div>
                    </div> : null}
                    
                    {/* {} */}
                    {(isSourceAiSummaryLoading || sourceAiSummary?.ai_summary) &&
                    <div className='bg-gray-50 border border-gray-200 px-4 py-2 rounded-lg transition-all space-y-3'>
                        <div className='text-indigo-600 flex items-center gap-2'>
                            {isSourceAiSummaryLoading ? <Loader2 size={14} className='animate-spin' />  : <RiRobot2Fill size={14} />}
                            {isSourceAiSummaryLoading ? <span className='text-xs font-medium'>PII Detection In-Progress</span> : <span className='text-xs font-medium'>Summary</span> }
                        </div>
                        {(sourceAiSummary?.ai_summary) && 
                        <div className='space-y-3 flex flex-col items-center'>
                            <p className='text-gray-600 leading-relaxed text-xs'>{sourceAiSummary?.ai_summary}</p>
                            <Button 
                                variant="primary" 
                                className='text-white w-full gap-2 flex justify-center items-center' 
                                onClick={() => {
                                    onCloseReset(true)
                                }}
                            >
                                <Database size={14} />
                                View Ingested Dataset
                                <ArrowRight size={14} />
                            </Button>
                        </div>
                        }
                    </div>}
                </div>

                {/* Footer Placeholder (Removed) */}
                <div className="p-6 pt-0" />

                {/* Custom styling for scrollbar */}
                <style jsx>{`
                    .custom-scrollbar::-webkit-scrollbar {
                        width: 4px;
                    }
                    .custom-scrollbar::-webkit-scrollbar-track {
                        background: transparent;
                    }
                    .custom-scrollbar::-webkit-scrollbar-thumb {
                        background: #e2e8f0;
                        border-radius: 10px;
                    }
                    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
                        background: #cbd5e1;
                    }
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
        </>
    );
};

export default IngestionSidebar;
