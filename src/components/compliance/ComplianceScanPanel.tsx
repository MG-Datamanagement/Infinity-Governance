"use client";

import { useEffect, useRef, useState, useCallback } from "react";
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

// ─── How long each step "plays" before advancing (ms) ───────────────────────
const STEP_DURATION = 1800;

export function ComplianceScanPanel({
  isOpen,
  onClose,
  onScanComplete,
}: Props) {
  const [phase, setPhase] = useState<"scanning" | "completing" | "done">(
    "scanning",
  );
  const [loadingSteps, setLoadingSteps] = useState<string[]>([]);
  const [currentStepIdx, setCurrentStepIdx] = useState(-1); // -1 = not started yet
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [summary, setSummary] = useState<ScanSummary | null>(null);
  const [reasoning, setReasoning] = useState<ReasoningStep[]>([]);
  const [reasoningOpen, setReasoningOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pending result from API — held until animation catches up
  const pendingResult = useRef<{
    summary: ScanSummary;
    reasoning: ReasoningStep[];
  } | null>(null);
  const apiDone = useRef(false);
  const stepTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stepsContainerRef = useRef<HTMLDivElement | null>(null);

  const clearTimer = () => {
    if (stepTimerRef.current) {
      clearTimeout(stepTimerRef.current);
      stepTimerRef.current = null;
    }
  };

  // ── Advance one step at a time, wait STEP_DURATION between each ──────────
  const advanceStep = useCallback((idx: number, steps: string[]) => {
    if (idx >= steps.length) return;

    setCurrentStepIdx(idx);

    // After STEP_DURATION mark it complete and move to next
    stepTimerRef.current = setTimeout(() => {
      setCompletedSteps((prev) => new Set(prev).add(idx));

      const nextIdx = idx + 1;

      if (nextIdx < steps.length) {
        // More steps to show
        advanceStep(nextIdx, steps);
      } else {
        // All steps animated — if API already returned, show done
        if (apiDone.current && pendingResult.current) {
          const { summary: s, reasoning: r } = pendingResult.current;
          setSummary(s);
          setReasoning(r);
          setPhase("done");
        } else {
          // API still pending — enter "completing" (hold on last step)
          setPhase("completing");
        }
      }
    }, STEP_DURATION);
  }, []);

  // ── Reset & launch on open ────────────────────────────────────────────────
  useEffect(() => {
    if (!isOpen) return;

    // Reset everything
    clearTimer();
    setPhase("scanning");
    setCurrentStepIdx(-1);
    setCompletedSteps(new Set());
    setSummary(null);
    setReasoning([]);
    // setReasoningOpen(true);
    setError(null);
    pendingResult.current = null;
    apiDone.current = false;

    const run = async () => {
      try {
        // 1. Fetch step labels
        const loadingData =
          await dashboardApiServices.getComplianceLoadingSteps();
        const steps: string[] = loadingData.reasoning_loads;
        setLoadingSteps(steps);

        // 2. Kick off visual animation immediately (does NOT wait for scan)
        advanceStep(0, steps);

        // 3. Fire scan in parallel
        const result = await dashboardApiServices.runComplianceScan();
        apiDone.current = true;
        pendingResult.current = {
          summary: result.summary,
          reasoning: result.reasoning,
        };

        // 4. If animation already finished all steps, resolve now
        // (phase check handled by the useEffect below)
        await dashboardApiServices.runCompliance();
        onScanComplete?.();
      } catch {
        clearTimer();
        setError("Scan failed. Please try again.");
        setPhase("done");
      }
    };

    run();

    return () => clearTimer();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  // ── When phase hits "completing" AND api has returned, finalize ───────────
  useEffect(() => {
    if (phase === "completing" && apiDone.current && pendingResult.current) {
      const { summary: s, reasoning: r } = pendingResult.current;
      setSummary(s);
      setReasoning(r);
      setPhase("done");
    }
  }, [phase]);

  // ── Auto-scroll active step into view ────────────────────────────────────
  //   useEffect(() => {
  //     if (stepsContainerRef.current && currentStepIdx >= 0) {
  //       const el = stepsContainerRef.current.querySelector(
  //         `[data-step="${currentStepIdx}"]`,
  //       );
  //       el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  //     }
  //   }, [currentStepIdx]);

  if (!isOpen) return null;

  const total = loadingSteps.length || 7;
  const progressPct =
    currentStepIdx < 0 ? 0 : Math.round((completedSteps.size / total) * 100);

  const stepsToRender: ReasoningStep[] =
    reasoning.length > 0
      ? reasoning
      : loadingSteps.map((s) => ({ title: s, description: "" }));

  const isScanning = phase === "scanning" || phase === "completing";

  return (
    <>
      <style>{`
                @keyframes csp-slide-in {
                    from { transform: translateX(100%); opacity: 0; }
                    to   { transform: translateX(0);    opacity: 1; }
                }
                @keyframes csp-fade-up {
                    from { opacity: 0; transform: translateY(10px); }
                    to   { opacity: 1; transform: translateY(0);    }
                }
                @keyframes csp-shimmer {
                    0%   { background-position: -300% center; }
                    100% { background-position:  300% center; }
                }
                @keyframes csp-pulse-ring {
                    0%   { transform: scale(0.95); box-shadow: 0 0 0 0   rgba(99,102,241,0.5); }
                    70%  { transform: scale(1);    box-shadow: 0 0 0 8px rgba(99,102,241,0);   }
                    100% { transform: scale(0.95); box-shadow: 0 0 0 0   rgba(99,102,241,0);   }
                }
                @keyframes csp-spin { to { transform: rotate(360deg); } }
                @keyframes csp-dot {
                    0%, 80%, 100% { transform: scale(0.5); opacity: 0.3; }
                    40%           { transform: scale(1);   opacity: 1;   }
                }
                @keyframes csp-check-draw {
                    from { stroke-dashoffset: 20; }
                    to   { stroke-dashoffset: 0;  }
                }
                @keyframes csp-bar-grow {
                    from { width: 0%; }
                }

                .csp-panel         { animation: csp-slide-in 0.38s cubic-bezier(0.22,1,0.36,1) both; }
                .csp-fade-up       { animation: csp-fade-up  0.35s cubic-bezier(0.22,1,0.36,1) both; }
                .csp-shimmer-bar {
                    background: linear-gradient(90deg,
                        #6366f1 0%, #818cf8 35%, #c7d2fe 50%, #818cf8 65%, #6366f1 100%);
                    background-size: 300% 100%;
                    animation: csp-shimmer 1.8s linear infinite;
                }
                .csp-pulse-ring    { animation: csp-pulse-ring 1.6s ease-out infinite; }
                .csp-spin          { animation: csp-spin 0.9s linear infinite; }
                .csp-dot-1         { animation: csp-dot 1.3s ease-in-out 0s    infinite; }
                .csp-dot-2         { animation: csp-dot 1.3s ease-in-out 0.2s  infinite; }
                .csp-dot-3         { animation: csp-dot 1.3s ease-in-out 0.4s  infinite; }
                .csp-check path    { stroke-dasharray: 20; animation: csp-check-draw 0.3s ease-out forwards; }
                .csp-progress-bar  { animation: csp-bar-grow 0.6s ease-out both; }
            `}</style>

      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/25 z-40 backdrop-blur-[1px]"
        onClick={phase === "done" ? onClose : undefined}
      />

      {/* Panel */}
      <div className="csp-panel fixed right-0 top-0 h-full w-[360px] bg-white shadow-2xl z-50 flex flex-col overflow-hidden">
        {/* HEADER */}
        <div className="bg-indigo-600 px-5 py-4 flex items-center justify-between shrink-0 relative">
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background:
                "linear-gradient(135deg,rgba(255,255,255,0.08) 0%,transparent 55%)",
            }}
          />

          <div className="flex items-center gap-3 relative z-10">
            <div
              className={cn(
                "w-9 h-9 rounded-xl bg-white/20 flex items-center justify-center relative",
                isScanning && "csp-pulse-ring",
              )}
            >
              <Bot size={20} className="text-white" />
            </div>
            <div>
              <p className="text-sm font-bold text-white leading-tight">
                AI Compliance Agent
              </p>
              <p className="text-[11px] text-indigo-200 flex items-center gap-1.5 mt-0.5">
                {isScanning ? (
                  <>
                    <span className="w-1.5 h-1.5 rounded-full bg-orange-300 animate-pulse" />
                    Compliance scan active
                  </>
                ) : (
                  <>
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-300" />
                    Scan complete
                  </>
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 relative z-10">
            {isScanning ? (
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

          {/* Animated progress border at bottom of header */}
          <div className="absolute bottom-0 left-0 right-0 h-[3px] bg-white/10 overflow-hidden">
            {isScanning ? (
              <div
                key={progressPct}
                className="csp-progress-bar csp-shimmer-bar h-full rounded-full"
                style={{ width: `${Math.max(progressPct, 6)}%` }}
              />
            ) : (
              <div className="h-full bg-emerald-400 w-full transition-all duration-700" />
            )}
          </div>
        </div>

        {/* SUB-STRIP */}
        <div
          className={cn(
            "relative px-5 py-2.5 flex items-center justify-between shrink-0 transition-colors duration-500",

            isScanning
              ? "bg-indigo-50"
              : "bg-emerald-50 border-b border-emerald-100",
          )}
        >
          {isScanning ? (
            <>
              <p className="text-[11px] text-indigo-600 font-medium">
                AI-driven compliance scan active
              </p>
              <button className="text-[11px] text-indigo-500 font-bold hover:text-indigo-700 transition-colors">
                Override
              </button>
            </>
          ) : summary ? (
            <div className="flex items-start gap-2 w-full">
              <CheckCircle2
                size={15}
                className="text-emerald-500 mt-0.5 shrink-0"
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="text-xs font-bold text-emerald-700">
                    Scan Complete
                  </p>
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
          ) : null}

          {/* Animated progress border — bottom of sub-strip, scanning only */}
          {isScanning && (
            <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-indigo-100 overflow-hidden">
              <div
                key={progressPct}
                className="csp-progress-bar csp-shimmer-bar h-full"
                style={{ width: `${Math.max(progressPct, 6)}%` }}
              />
            </div>
          )}
        </div>

        {/* BODY */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4">
          {/* Scanning animation */}
          {isScanning && (
            <div className="flex flex-col items-center gap-3 py-4">
              <div className="relative w-14 h-14">
                <div className="absolute inset-0 rounded-full bg-indigo-100 animate-ping opacity-30" />
                <div className="relative w-14 h-14 rounded-full bg-indigo-50 border-2 border-indigo-200 flex items-center justify-center">
                  <Bot size={26} className="text-indigo-500" />
                </div>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-indigo-400 csp-dot-1" />
                <span className="w-2 h-2 rounded-full bg-indigo-400 csp-dot-2" />
                <span className="w-2 h-2 rounded-full bg-indigo-400 csp-dot-3" />
              </div>

              {/* key= forces remount → re-triggers fade-up on every step change */}
              <p
                key={currentStepIdx}
                className="csp-fade-up text-sm font-semibold text-gray-700 text-center px-4 min-h-[20px]"
              >
                {currentStepIdx >= 0
                  ? (loadingSteps[currentStepIdx] ?? "Initializing…")
                  : "Initializing compliance engine…"}
              </p>

              {/* <div className="w-full">
                <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                  <div
                    key={progressPct}
                    className="csp-progress-bar csp-shimmer-bar h-1.5 rounded-full"
                    style={{ width: `${Math.max(progressPct, 4)}%` }}
                  />
                </div>
                <div className="flex justify-between mt-1.5">
                  <p className="text-[10px] text-gray-400">
                    {currentStepIdx >= 0
                      ? `Step ${currentStepIdx + 1} of ${total}`
                      : "Starting…"}
                  </p>
                  <p className="text-[10px] text-indigo-400 font-medium">
                    {progressPct}%
                  </p>
                </div>
              </div> */}
            </div>
          )}

          {/* Error */}
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
                className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors"
              >
                <span className="flex items-center gap-2 text-sm font-semibold text-gray-700">
                  Reasoning steps
                  <span
                    className={cn(
                      "text-[10px] font-bold px-1.5 py-0.5 rounded-full transition-colors duration-300",
                      phase === "done"
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-indigo-100 text-indigo-700",
                    )}
                  >
                    {completedSteps.size}/{total}
                  </span>
                </span>
                {reasoningOpen ? (
                  <ChevronUp size={16} className="text-gray-500" />
                ) : (
                  <ChevronDown size={16} className="text-gray-500" />
                )}
              </button>

              {reasoningOpen && (
                <div
                  ref={stepsContainerRef}
                  className="divide-y divide-gray-100 max-h-72 overflow-y-auto"
                >
                  {stepsToRender.map((step, idx) => {
                    // Only render steps that the animation has reached
                    if (idx > currentStepIdx && phase !== "done") return null;

                    const isDone = completedSteps.has(idx) || phase === "done";
                    const isActive = !isDone && idx === currentStepIdx;

                    return (
                      <div
                        key={idx}
                        data-step={idx}
                        className={cn(
                          "csp-fade-up flex items-start gap-3 px-4 py-3 text-xs border-l-2 transition-colors duration-500",
                          isDone
                            ? "bg-white border-emerald-300"
                            : isActive
                              ? "bg-indigo-50/60 border-indigo-400"
                              : "bg-white border-transparent",
                        )}
                      >
                        {/* Indicator */}
                        <div
                          className={cn(
                            "w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5 transition-all duration-300",
                            isDone
                              ? "bg-emerald-100"
                              : isActive
                                ? "bg-indigo-100 ring-2 ring-indigo-200 ring-offset-1"
                                : "bg-gray-100",
                          )}
                        >
                          {isDone ? (
                            <svg
                              className="csp-check"
                              width="10"
                              height="10"
                              viewBox="0 0 10 10"
                              fill="none"
                            >
                              <path
                                d="M2 5l2.5 2.5L8 3"
                                stroke="#16a34a"
                                strokeWidth="1.6"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              />
                            </svg>
                          ) : isActive ? (
                            <svg
                              className="csp-spin"
                              width="10"
                              height="10"
                              viewBox="0 0 10 10"
                              fill="none"
                            >
                              <circle
                                cx="5"
                                cy="5"
                                r="3.5"
                                stroke="#c7d2fe"
                                strokeWidth="1.5"
                              />
                              <path
                                d="M5 1.5A3.5 3.5 0 018.5 5"
                                stroke="#6366f1"
                                strokeWidth="1.5"
                                strokeLinecap="round"
                              />
                            </svg>
                          ) : (
                            <span className="text-[9px] font-bold text-gray-400">
                              {idx + 1}
                            </span>
                          )}
                        </div>

                        {/* Text */}
                        <div className="flex-1 min-w-0">
                          <p
                            className={cn(
                              "font-semibold leading-snug transition-colors duration-300",
                              isDone
                                ? "text-gray-700"
                                : isActive
                                  ? "text-indigo-700"
                                  : "text-gray-400",
                            )}
                          >
                            {step.title}
                          </p>
                          {step.description && (
                            <p
                              className={cn(
                                "mt-0.5 leading-snug transition-colors duration-300",
                                isDone
                                  ? "text-gray-400"
                                  : isActive
                                    ? "text-indigo-400"
                                    : "text-gray-300",
                              )}
                            >
                              {step.description}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Summary — only shown after done */}
          {phase === "done" && summary && (
            <div className="csp-fade-up border border-gray-200 rounded-xl overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-3 bg-gray-50 border-b border-gray-100">
                <Bot size={14} className="text-indigo-500" />
                <p className="text-xs font-bold text-gray-700">Summary</p>
              </div>
              <div className="divide-y divide-gray-100">
                {[
                  {
                    label: "Frameworks scanned",
                    value: summary.frameworks_scanned,
                    color: "text-gray-900",
                  },
                  {
                    label: "Issues found",
                    value: summary.issues_found,
                    color:
                      summary.issues_found > 0
                        ? "text-red-600"
                        : "text-emerald-600",
                  },
                  {
                    label: "Policies checked",
                    value: summary.policies_checked,
                    color: "text-gray-900",
                  },
                  {
                    label: "Overall score",
                    value: `${summary.overall_score.toFixed(0)}%`,
                    color:
                      summary.overall_score >= 80
                        ? "text-emerald-600"
                        : summary.overall_score >= 60
                          ? "text-orange-500"
                          : "text-red-600",
                  },
                ].map((row, i) => (
                  <div
                    key={row.label}
                    className="csp-fade-up flex items-center justify-between px-4 py-3"
                    style={{ animationDelay: `${i * 100}ms` }}
                  >
                    <span className="text-xs text-gray-500">{row.label}</span>
                    <span
                      className={cn(
                        "text-xs font-bold tabular-nums",
                        row.color,
                      )}
                    >
                      {row.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* FOOTER */}
        {isScanning ? (
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
              className="w-full bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white text-sm font-bold py-3 rounded-xl transition-colors"
            >
              View Full Report
            </button>
          </div>
        )}
      </div>
    </>
  );
}
