"use client";

import React, { useState } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────
interface EvidenceItem {
    name: string;
    value: string;
    icon?: "lock" | "clock" | "tag";
}

interface ViolationDetail {
    name: string;
    issue: string;
    confidence?: string;
    description?: string;
    actionLabel: string;
    actionVariant: "red" | "blue";
}

interface HumanApproval {
    body: string;
    actionNeeded: string;
}

interface AuditRule {
    id: number;
    title: string;
    description: string;
    status: "compliant" | "violation";
    actionBanner?: string;
    evidence?: EvidenceItem[];
    humanApproval?: HumanApproval;
    violationDetails?: ViolationDetail[];
}

interface ComplianceData {
    datasetName: string;
    score: number;
    scoreMax: number;
    criticalViolations: number;
    policiesChecked: number;
    policyName: string;
    protectedAssets: number;
    protectedLabel: string;
    rules: AuditRule[];
}

// ─── Mock compliance data per dataset ────────────────────────────────────────
const defaultCompliance: ComplianceData = {
    datasetName: "customers",
    score: 85,
    scoreMax: 100,
    criticalViolations: 1,
    policiesChecked: 3,
    policyName: "Standard Enterprise Policy v2.1",
    protectedAssets: 5,
    protectedLabel: "Columns encrypted or masked",
    rules: [
        {
            id: 1,
            title: "Rule 1: PII Encryption",
            description: "All columns tagged as PII must have encryption at rest enabled.",
            status: "compliant",
            evidence: [
                { name: "email", value: "Encrypted (AES-256)", icon: "lock" },
                { name: "phone", value: "Encrypted (AES-256)", icon: "lock" },
                { name: "ssn", value: "Encrypted (AES-256)", icon: "lock" },
            ],
        },
        {
            id: 2,
            title: "Rule 2: Financial Access Control",
            description: "Columns tagged as Financial must have Row-Level Security (RLS) policies attached.",
            status: "violation",
            actionBanner: "Action required — this violation needs your attention",
            humanApproval: {
                body: "This violation was not auto-remediated because applying Row-Level Security policies is a critical security action that can restrict data access for downstream users and applications. Automated remediation could break existing queries, dashboards, or ML pipelines that depend on unrestricted access to ltv_score.",
                actionNeeded: 'Action needed: Review the impact and click "Remediate" to have the AI agent apply the default RLS policy with your approval.',
            },
            violationDetails: [
                {
                    name: "ltv_score",
                    issue: "No RLS Policy Found",
                    actionLabel: "Apply Default RLS Policy",
                    actionVariant: "red",
                },
            ],
        },
        {
            id: 3,
            title: "Rule 3: Data Retention",
            description: "Regulated data must have a defined retention period.",
            status: "compliant",
            evidence: [
                { name: "ssn (HIPAA)", value: "Retention: 7 Years", icon: "clock" },
            ],
        },
        {
            id: 4,
            title: "Rule 4: AI Classification Quality",
            description: "All AI-assigned classification tags must meet a minimum confidence threshold of 80%.",
            status: "violation",
            actionBanner: "Action required — low-confidence classification needs review",
            violationDetails: [
                {
                    name: "ltv_score",
                    issue: '72% confidence — below 80% threshold',
                    confidence: "Financial",
                    description: "Decimal values resembling monetary calculations were detected, but no regulatory markers confirm this as regulated financial data. The tag may be incorrect.",
                    actionLabel: "Review & Approve Tag",
                    actionVariant: "red",
                },
            ],
        },
    ],
};

// ─── Sub-components ───────────────────────────────────────────────────────────

const EvidenceIcon: React.FC<{ icon?: EvidenceItem["icon"] }> = ({ icon }) => {
    if (icon === "lock")
        return (
            <svg className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
        );
    if (icon === "clock")
        return (
            <svg className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
        );
    return (
        <svg className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
        </svg>
    );
};

const CompliantRule: React.FC<{ rule: AuditRule }> = ({ rule }) => (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
        <div className="border-l-4 border-l-green-500 p-5">
            <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h3 className="text-sm font-semibold text-gray-900">{rule.title}</h3>
                </div>
                <span className="inline-block text-[10px] font-bold tracking-wide text-green-700 bg-green-50 border border-green-200 rounded-full px-2.5 py-0.5 flex-shrink-0">
                    COMPLIANT
                </span>
            </div>
            <p className="text-xs text-gray-500 mt-1 ml-7">{rule.description}</p>

            {rule.evidence && rule.evidence.length > 0 && (
                <div className="mt-4 ml-7">
                    <p className="text-[10px] font-semibold text-gray-400 tracking-widest uppercase mb-2">Evidence</p>
                    <div className="space-y-1.5">
                        {rule.evidence.map((e) => (
                            <div key={e.name} className="flex items-center justify-between">
                                <div className="flex items-center gap-1.5">
                                    <EvidenceIcon icon={e.icon} />
                                    <span className="text-xs text-gray-700">{e.name}</span>
                                </div>
                                <span className="text-xs font-medium text-green-600">{e.value}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    </div>
);

const ViolationRule: React.FC<{ rule: AuditRule }> = ({ rule }) => (
    <div className="border border-red-200 rounded-xl overflow-hidden">
        {/* Action banner */}
        {rule.actionBanner && (
            <div className="flex items-center gap-2 bg-red-50 px-4 py-2 border-b border-red-100">
                <span className="w-2 h-2 rounded-full bg-red-500 flex-shrink-0" />
                <span className="text-xs font-medium text-red-600">{rule.actionBanner}</span>
            </div>
        )}

        <div className="border-l-4 border-l-red-400 p-5">
            <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-red-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <h3 className="text-sm font-semibold text-gray-900">{rule.title}</h3>
                </div>
                <span className="inline-block text-[10px] font-bold tracking-wide text-red-600 bg-red-50 border border-red-200 rounded-full px-2.5 py-0.5 flex-shrink-0">
                    VIOLATION
                </span>
            </div>
            <p className="text-xs text-gray-500 mt-1 ml-7">{rule.description}</p>

            {/* Human Approval box */}
            {rule.humanApproval && (
                <div className="mt-4 ml-7 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                    <div className="flex items-center gap-1.5 mb-1.5">
                        <svg className="w-4 h-4 text-yellow-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                        <span className="text-xs font-semibold text-yellow-800">Human Approval Required</span>
                    </div>
                    <p className="text-xs text-yellow-800 leading-relaxed">
                        {rule.humanApproval.body.split(/(not auto-remediated|critical security action|ltv_score)/).map((part, i) =>
                            part === "not auto-remediated" ? <strong key={i}>not auto-remediated</strong>
                                : part === "critical security action" ? <strong key={i}>critical security action</strong>
                                    : part === "ltv_score" ? <code key={i} className="bg-yellow-100 px-1 rounded text-yellow-900 font-mono text-[11px]">ltv_score</code>
                                        : part
                        )}
                    </p>
                    <p className="text-xs text-yellow-800 mt-1.5 leading-relaxed">
                        <strong>Action needed:</strong>{" "}
                        {rule.humanApproval.actionNeeded.replace("Action needed: ", "")}
                    </p>
                </div>
            )}

            {/* Violation details */}
            {rule.violationDetails && rule.violationDetails.length > 0 && (
                <div className="mt-4 ml-7 border border-gray-200 rounded-lg overflow-hidden">
                    <div className="bg-gray-50 px-4 py-2 border-b border-gray-100">
                        <span className="text-[10px] font-semibold text-gray-500 tracking-widest uppercase">Violation Details</span>
                    </div>
                    {rule.violationDetails.map((vd) => (
                        <div key={vd.name} className="p-4">
                            <div className="flex items-center justify-between mb-1">
                                <div className="flex items-center gap-1.5">
                                    <svg className="w-3.5 h-3.5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                    </svg>
                                    {vd.confidence ? (
                                        <span className="text-xs text-gray-800">
                                            <code className="bg-red-50 border border-red-100 text-red-700 px-1.5 py-0.5 rounded font-mono text-[11px]">
                                                {vd.name}
                                            </code>{" "}
                                            tagged as &quot;{vd.confidence}&quot;
                                        </span>
                                    ) : (
                                        <span className="text-xs font-medium text-gray-800">{vd.name}</span>
                                    )}
                                </div>
                                <span className="text-xs font-semibold text-red-500">{vd.issue}</span>
                            </div>
                            {vd.description && (
                                <p className="text-xs text-gray-500 leading-relaxed mt-1 mb-3">{vd.description}</p>
                            )}
                            <div className="flex justify-end">
                                <button className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500 hover:bg-red-600 text-white text-xs font-semibold rounded-lg transition-colors">
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                    </svg>
                                    {vd.actionLabel}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    </div>
);

// ─── Main Modal ───────────────────────────────────────────────────────────────
interface ComplianceReportModalProps {
    datasetName?: string;
    onClose: () => void;
}

const ComplianceReportModal: React.FC<ComplianceReportModalProps> = ({
    datasetName,
    onClose,
}) => {
    const data: ComplianceData = {
        ...defaultCompliance,
        datasetName: datasetName ?? defaultCompliance.datasetName,
    };

    const scorePercent = (data.score / data.scoreMax) * 100;

    return (
        // Backdrop
        <div
            className="fixed inset-0 z-50 flex items-start justify-end bg-black/40 backdrop-blur-sm"
            onClick={onClose}
        >
            {/* Panel */}
            <div
                className="relative h-full w-full max-w-2xl bg-white shadow-2xl flex flex-col overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex-shrink-0 px-6 pt-6 pb-4 border-b border-gray-100">
                    <div className="flex items-start justify-between gap-3">
                        <div>
                            <h2 className="text-xl font-bold text-gray-900">Policy Enforcement &amp; Audit</h2>
                            <p className="text-sm text-gray-400 mt-0.5">
                                Automated compliance check for{" "}
                                <strong className="text-gray-700">{data.datasetName}</strong>
                            </p>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    {/* Action buttons */}
                    <div className="flex items-center gap-2 mt-4">
                        <button className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            View History
                        </button>
                        <button className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                            </svg>
                            Re-run Check
                        </button>
                        <button className="flex items-center gap-1.5 px-3 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors font-medium">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                            Remediate Violations
                        </button>
                    </div>
                </div>

                {/* Scrollable body */}
                <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

                    {/* Score cards */}
                    <div className="grid grid-cols-3 gap-3">
                        {/* Compliance Score */}
                        <div className="bg-white border border-gray-200 rounded-xl p-4">
                            <div className="flex items-start justify-between mb-1">
                                <p className="text-xs text-gray-400 font-medium">Compliance Score</p>
                                <div className="w-8 h-8 rounded-lg bg-yellow-50 flex items-center justify-center">
                                    <svg className="w-4 h-4 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                    </svg>
                                </div>
                            </div>
                            <p className="text-3xl font-extrabold text-gray-900 mb-2">
                                {data.score}/{data.scoreMax}
                            </p>
                            <div className="w-full bg-gray-100 rounded-full h-2 mb-2">
                                <div
                                    className="h-2 rounded-full bg-gradient-to-r from-yellow-400 to-orange-400"
                                    style={{ width: `${scorePercent}%` }}
                                />
                            </div>
                            {data.criticalViolations > 0 && (
                                <p className="text-xs font-medium text-orange-500">
                                    {data.criticalViolations} Critical Violation Detected
                                </p>
                            )}
                        </div>

                        {/* Policies Checked */}
                        <div className="bg-white border border-gray-200 rounded-xl p-4">
                            <div className="flex items-start justify-between mb-1">
                                <p className="text-xs text-gray-400 font-medium">Policies Checked</p>
                                <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center">
                                    <svg className="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                </div>
                            </div>
                            <p className="text-3xl font-extrabold text-gray-900 mb-1">{data.policiesChecked}</p>
                            <p className="text-xs text-gray-400">Against &ldquo;{data.policyName}&rdquo;</p>
                        </div>

                        {/* Protected Assets */}
                        <div className="bg-white border border-gray-200 rounded-xl p-4">
                            <div className="flex items-start justify-between mb-1">
                                <p className="text-xs text-gray-400 font-medium">Protected Assets</p>
                                <div className="w-8 h-8 rounded-lg bg-green-50 flex items-center justify-center">
                                    <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                    </svg>
                                </div>
                            </div>
                            <p className="text-3xl font-extrabold text-gray-900 mb-1">{data.protectedAssets}</p>
                            <p className="text-xs text-gray-400">{data.protectedLabel}</p>
                        </div>
                    </div>

                    {/* Audit results */}
                    <div>
                        <h3 className="text-sm font-bold text-gray-900 mb-3">Automated Audit Results</h3>
                        <div className="space-y-4">
                            {data.rules.map((rule) =>
                                rule.status === "compliant" ? (
                                    <CompliantRule key={rule.id} rule={rule} />
                                ) : (
                                    <ViolationRule key={rule.id} rule={rule} />
                                )
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ComplianceReportModal;
