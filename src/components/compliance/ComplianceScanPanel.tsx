"use client";

import { useEffect, useRef, useState } from "react";
import { X, CheckCircle2, Bot, ChevronDown, ChevronUp } from "lucide-react";
import { dashboardApiServices } from "@/services/dashboardApiServices";
import { cn } from "@/lib/utils";

type ScanSummary = {
    frameworks_scanned: number;
    issues_found: number;
    policies_checked: number;
    overall_score: number;
    issue_summary: string;
};

type ReasoningStep = { title: string; description: string };

interface Props {
    isOpen: boolean;
    onClose: () => void;
    onScanComplete?: () => void;
}

export function ComplianceScanPanel({ isOpen, onClose, onScanComplete }: Props) {
    const [phase, setPhase] = useState<"scanning" | "done">("scanning");
    const [loadingSteps, setLoadingSteps] = useState<string[]>([]);
    const [currentStepIdx, setCurrentStepIdx] = useState(0);
    const [summary, setSummary] = useState<ScanSummary | null>(null);
    const [reasoning, setReasoning] = useState<ReasoningStep[]>([]);
    const [reasoningOpen, setReasoningOpen] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // Reset and launch scan whenever panel opens
    useEffect(() => {
        if (!isOpen) return;
        setPhase("scanning");
        setCurrentStepIdx(0);
        setSummary(null);
        setReasoning([]);
        setReasoningOpen(false);
        setError(null);

        let steps: string[] = [];

        const run = async () => {
            try {
                // 1. Fetch loading steps first for accurate labels
                const loadingData = await dashboardApiServices.getComplianceLoadingSteps();
                steps = loadingData.reasoning_loads;
                setLoadingSteps(steps);

                // 2. Start cycling through steps every ~2s while the scan runs
                let idx = 0;
                timerRef.current = setInterval(() => {
                    idx = Math.min(idx + 1, steps.length - 1);
                    setCurrentStepIdx(idx);
                }, 2000);

                // 3. Fire the actual scan (may take a while)
                const result = await dashboardApiServices.runComplianceScan();

                // 4. Scan done
                if (timerRef.current) clearInterval(timerRef.current);
                setCurrentStepIdx(steps.length - 1);
                setSummary(result.summary);
                setReasoning(result.reasoning);
                setPhase("done");
                onScanComplete?.();
            } catch (err) {
                if (timerRef.current) clearInterval(timerRef.current);
                setError("Scan failed. Please try again.");
                setPhase("done");
            }
        };

        run();

        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
        };
    }, [isOpen]);

    if (!isOpen) return null;

    const total = loadingSteps.length || 7;
    const progress = total > 0 ? Math.round(((currentStepIdx + 1) / total) * 100) : 0;

    return (
        <>
            {/* Overlay */}
            <div
                className="fixed inset-0 bg-black/20 z-40"
                onClick={phase === "done" ? onClose : undefined}
            />

            {/* Panel */}
            <div className="fixed right-0 top-0 h-full w-[340px] bg-white shadow-2xl z-50 flex flex-col overflow-hidden">
                {/* Header */}
                <div className="bg-indigo-600 px-5 py-4 flex items-center justify-between shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-white/20 flex items-center justify-center">
                            <Bot size={20} className="text-white" />
                        </div>
                        <div>
                            <p className="text-sm font-bold text-white leading-tight">AI Compliance Agent</p>
                            <p className="text-[11px] text-indigo-200">
                                {phase === "scanning" ? "Compliance scan active" : "Scan complete"}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        {phase === "scanning" ? (
                            <span className="flex items-center gap-1.5 px-2.5 py-1 bg-orange-500 rounded-full text-[11px] font-bold text-white">
                                <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />
                                Thinking
                            </span>
                        ) : (
                            <button
                                onClick={onClose}
                                className="flex items-center gap-1.5 px-3 py-1 bg-white/20 hover:bg-white/30 rounded-full text-[11px] font-bold text-white transition-colors"
                            >
                                <CheckCircle2 size={13} />
                                Done
                            </button>
                        )}
                        <button
                            onClick={onClose}
                            className="text-white/70 hover:text-white transition-colors"
                        >
                            <X size={18} />
                        </button>
                    </div>
                </div>

                {/* Status strip */}
                {phase === "done" && !error && summary && (
                    <div className="bg-emerald-50 border-b border-emerald-100 px-5 py-3 flex items-start gap-2">
                        <CheckCircle2 size={16} className="text-emerald-500 mt-0.5 shrink-0" />
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                                <p className="text-xs font-bold text-emerald-700">Scan Complete</p>
                                <span className="px-2 py-0.5 bg-indigo-50 border border-indigo-100 rounded-full text-[10px] font-bold text-indigo-600">
                                    {summary.frameworks_scanned} frameworks
                                </span>
                                <span className="px-2 py-0.5 bg-indigo-50 border border-indigo-100 rounded-full text-[10px] font-bold text-indigo-600">
                                    {summary.policies_checked} policies
                                </span>
                            </div>
                            <p className="text-[11px] text-emerald-600 mt-0.5 leading-snug">
                                {summary.issue_summary}
                            </p>
                        </div>
                    </div>
                )}

                {/* Body */}
                <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
                    {/* Scanning animation */}
                    {phase === "scanning" && (
                        <div className="flex flex-col items-center gap-4 py-6">
                            <div className="relative w-16 h-16">
                                <div className="absolute inset-0 rounded-full bg-indigo-100 animate-ping opacity-40" />
                                <div className="relative w-16 h-16 rounded-full bg-indigo-50 border-2 border-indigo-200 flex items-center justify-center">
                                    <Bot size={28} className="text-indigo-500" />
                                </div>
                            </div>
                            {/* Dot loader */}
                            <div className="flex items-center gap-1.5">
                                {[0, 1, 2].map((i) => (
                                    <span
                                        key={i}
                                        className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce"
                                        style={{ animationDelay: `${i * 150}ms` }}
                                    />
                                ))}
                            </div>
                            <p className="text-sm font-medium text-gray-700 text-center">
                                {loadingSteps[currentStepIdx] || "Initializing compliance engine"}
                            </p>

                            {/* Progress bar */}
                            <div className="w-full">
                                <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                                    <div
                                        className="h-1.5 bg-indigo-500 rounded-full transition-all duration-700"
                                        style={{ width: `${progress}%` }}
                                    />
                                </div>
                                <p className="text-[10px] text-gray-400 mt-1 text-right">
                                    Step {currentStepIdx + 1} of {total}
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Error state */}
                    {error && (
                        <div className="rounded-xl bg-red-50 border border-red-100 p-4 text-sm text-red-600">
                            {error}
                        </div>
                    )}

                    {/* Reasoning steps accordion */}
                    {loadingSteps.length > 0 && (
                        <div className="border border-gray-200 rounded-xl overflow-hidden">
                            <button
                                onClick={() => setReasoningOpen((v) => !v)}
                                className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-sm font-semibold text-gray-700"
                            >
                                <span>
                                    Reasoning steps ({Math.min(currentStepIdx + 1, total)}/{total})
                                </span>
                                {reasoningOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                            </button>

                            {reasoningOpen && (
                                <div className="divide-y divide-gray-100">
                                    {(reasoning.length > 0 ? reasoning : loadingSteps.map((s) => ({ title: s, description: "" }))).map(
                                        (step, idx) => {
                                            const done = phase === "done" || idx < currentStepIdx;
                                            const active = phase === "scanning" && idx === currentStepIdx;
                                            return (
                                                <div
                                                    key={idx}
                                                    className={cn(
                                                        "flex items-start gap-3 px-4 py-3 text-xs transition-colors",
                                                        active ? "bg-indigo-50/60" : "bg-white"
                                                    )}
                                                >
                                                    <div
                                                        className={cn(
                                                            "w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5 text-[10px] font-bold",
                                                            done
                                                                ? "bg-emerald-100 text-emerald-600"
                                                                : active
                                                                    ? "bg-indigo-100 text-indigo-600"
                                                                    : "bg-gray-100 text-gray-400"
                                                        )}
                                                    >
                                                        {done ? "✓" : idx + 1}
                                                    </div>
                                                    <div>
                                                        <p className={cn("font-semibold", done ? "text-gray-700" : active ? "text-indigo-700" : "text-gray-400")}>
                                                            {"title" in step ? step.title : step}
                                                        </p>
                                                        {"description" in step && step.description && (
                                                            <p className="text-gray-400 mt-0.5">{step.description}</p>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        }
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Summary table */}
                    {phase === "done" && summary && (
                        <div className="border border-gray-200 rounded-xl overflow-hidden">
                            <div className="flex items-center gap-2 px-4 py-3 bg-gray-50 border-b border-gray-100">
                                <Bot size={14} className="text-indigo-500" />
                                <p className="text-xs font-bold text-gray-700">Summary</p>
                            </div>
                            <div className="divide-y divide-gray-100">
                                {[
                                    { label: "Frameworks scanned", value: summary.frameworks_scanned, color: "text-gray-900" },
                                    { label: "Issues found", value: summary.issues_found, color: summary.issues_found > 0 ? "text-red-600" : "text-emerald-600" },
                                    { label: "Policies checked", value: summary.policies_checked, color: "text-gray-900" },
                                    { label: "Overall score", value: `${summary.overall_score.toFixed(0)}%`, color: summary.overall_score >= 80 ? "text-emerald-600" : summary.overall_score >= 60 ? "text-orange-500" : "text-red-600" },
                                ].map((row) => (
                                    <div key={row.label} className="flex items-center justify-between px-4 py-3">
                                        <span className="text-xs text-gray-500">{row.label}</span>
                                        <span className={cn("text-xs font-bold", row.color)}>{row.value}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                {phase === "scanning" ? (
                    <div className="px-5 py-4 border-t border-gray-100 shrink-0">
                        <button
                            onClick={onClose}
                            className="w-full flex items-center justify-center gap-2 py-2.5 border border-red-200 rounded-xl text-xs font-bold text-red-500 hover:bg-red-50 transition-colors"
                        >
                            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                            Stop scan
                        </button>
                    </div>
                ) : (
                    <div className="px-5 py-4 border-t border-gray-100 shrink-0">
                        <button
                            onClick={onClose}
                            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold py-3 rounded-xl transition-colors"
                        >
                            View Full Report
                        </button>
                    </div>
                )}
            </div>
        </>
    );
}
