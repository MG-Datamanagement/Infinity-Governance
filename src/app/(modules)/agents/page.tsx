"use client";

import React, { useState, useMemo } from 'react';
import {
    Bot,
    Plus,
    Search,
    Filter,
    List,
    LayoutGrid,
    CheckCircle2,
    PauseCircle,
    XCircle,
    X,
    ChevronRight,
    ChevronLeft,
    Home as HomeIcon,
    BrainCircuit,
    User2,
    Clock,
    Upload,
    Settings
} from 'lucide-react';

const initialAgents = [
    {
        id: 1,
        name: "Data Quality Agent",
        type: "Data Validation",
        description: "Automatically scans new datasets for anomalies and schema drifts based on defined rules.",
        useCaseBadge: "BYO Agent",
        status: "Active",
        owner: "Data Engineering",
        models: ["Anomaly Detection v2"],
        lastUpdated: "Mar 6, 2026"
    },
    {
        id: 2,
        name: "Classification Agent",
        type: "Metadata Tagging",
        description: "Platform-managed agent that auto-tags columns with PII and classification metadata.",
        useCaseBadge: "Platform Agent",
        status: "Active",
        owner: "Governance Team",
        models: ["PII Classifier v4", "Llama-3-70b-Instruct"],
        lastUpdated: "Mar 5, 2026"
    },
    {
        id: 3,
        name: "Compliance Monitor",
        type: "Policy Enforcement",
        description: "Monitors data access patterns for potential compliance violations.",
        useCaseBadge: "BYO Agent",
        status: "Paused",
        owner: "Legal Team",
        models: ["Policy Evaluator v1"],
        lastUpdated: "Feb 20, 2026"
    },
    {
        id: 4,
        name: "Support Router Agent",
        type: "Workflow Automation",
        description: "Reads incoming tickets and routes them to the appropriate support tier.",
        useCaseBadge: "BYO Agent",
        status: "Active",
        owner: "CX Team",
        models: ["Support Ticket Classifier v3"],
        lastUpdated: "Jan 15, 2026"
    },
    {
        id: 5,
        name: "Sync Agent",
        type: "Data Sync",
        description: "Validates synchronization jobs across distributed data systems for integrity constraints.",
        useCaseBadge: "Platform Agent",
        status: "Error",
        owner: "DevOps",
        models: ["Sync Validator v1"],
        lastUpdated: "Feb 10, 2026"
    }
];

export default function AgentsPage() {
    const [searchQuery, setSearchQuery] = useState("");
    const [statusFilter, setStatusFilter] = useState("All Statuses");
    const [typeFilter, setTypeFilter] = useState("All Types");
    const [viewMode, setViewMode] = useState<"list" | "grid">("list");
    const [isRegisterModalOpen, setIsRegisterModalOpen] = useState(false);
    const [selectedAgentType, setSelectedAgentType] = useState<"byo" | "managed" | null>(null);
    const [modalStep, setModalStep] = useState<1 | 2>(1);

    const [agents, setAgents] = useState(initialAgents);
    const [newAgentName, setNewAgentName] = useState("");
    const [newAgentOwner, setNewAgentOwner] = useState("");
    const [newAgentDesc, setNewAgentDesc] = useState("");

    const handleOpenModal = () => {
        setIsRegisterModalOpen(true);
        setModalStep(1);
        setSelectedAgentType(null);
    };

    const handleCloseModal = () => {
        setIsRegisterModalOpen(false);
        setTimeout(() => {
            setModalStep(1);
            setSelectedAgentType(null);
            setNewAgentName("");
            setNewAgentOwner("");
            setNewAgentDesc("");
        }, 200);
    };

    const handleRegister = () => {
        if (!newAgentName.trim() || !newAgentOwner.trim()) return;

        const newAgent = {
            id: Date.now(),
            name: newAgentName,
            type: "Custom",
            description: newAgentDesc,
            useCaseBadge: selectedAgentType === 'byo' ? "BYO Agent" : "Platform Agent",
            status: "Active",
            owner: newAgentOwner,
            models: ["General Endpoint v1"],
            lastUpdated: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
        };

        setAgents([newAgent, ...agents]);
        handleCloseModal();
    };

    // Filter integration
    const filteredAgents = useMemo(() => {
        return agents.filter(agent => {
            // Search matching (name or usecase text)
            const matchesSearch =
                agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                agent.type.toLowerCase().includes(searchQuery.toLowerCase()) ||
                agent.useCaseBadge.toLowerCase().includes(searchQuery.toLowerCase());

            // Status matching
            const matchesStatus =
                statusFilter === "All Statuses" ||
                agent.status === statusFilter;

            // Type matching
            const matchesType =
                typeFilter === "All Types" ||
                agent.useCaseBadge === typeFilter;

            return matchesSearch && matchesStatus && matchesType;
        });
    }, [searchQuery, statusFilter, typeFilter]);

    return (
        <div className="max-w-[1600px] mx-auto p-6 md:p-8 space-y-6 bg-white min-h-screen text-gray-900">

            {/* Breadcrumb */}
            <div className="flex items-center text-sm text-gray-500 gap-2">
                <HomeIcon size={14} />
                <span>Home</span>
                <ChevronRight size={14} className="text-gray-400" />
                <span>Governance</span>
                <ChevronRight size={14} className="text-gray-400" />
                <span className="font-semibold text-gray-900">Agents</span>
            </div>

            {/* Header section */}
            <div className="flex items-start justify-between">
                <div className="space-y-1">
                    <div className="flex items-center gap-2">
                        <Bot size={28} className="text-indigo-600" />
                        <h1 className="text-2xl font-bold text-gray-900">AI Agents</h1>
                    </div>
                    <p className="text-gray-500 text-sm">
                        Manage, govern, and monitor autonomous AI agents operating on your data platform.
                    </p>
                </div>
                <button
                    onClick={handleOpenModal}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                >
                    <Plus size={16} />
                    Register Agent
                </button>
            </div>

            {/* Search and Filters box */}
            <div className="bg-white border text-gray-900 border-gray-200 rounded-xl p-4 space-y-4 shadow-sm">
                <div className="relative">
                    <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                        <Search size={18} className="text-gray-400" />
                    </div>
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full bg-white pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all placeholder:text-gray-400"
                        placeholder="Search agents by name or use case..."
                    />
                </div>

                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                            <Filter size={16} />
                            Filters:
                        </div>

                        {/* Statuses Filter Dropdown */}
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm hover:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 bg-white text-gray-700 cursor-pointer appearance-none outline-none transition-all pr-8 relative"
                            style={{
                                backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`,
                                backgroundPosition: `right 0.25rem center`,
                                backgroundRepeat: `no-repeat`,
                                backgroundSize: `1.5em 1.5em`
                            }}
                        >
                            <option value="All Statuses">All Statuses</option>
                            <option value="Active">Active</option>
                            <option value="Paused">Paused</option>
                            <option value="Error">Error</option>
                        </select>

                        {/* Types Filter Dropdown */}
                        <select
                            value={typeFilter}
                            onChange={(e) => setTypeFilter(e.target.value)}
                            className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm hover:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 bg-white text-gray-700 cursor-pointer appearance-none outline-none transition-all pr-8 relative"
                            style={{
                                backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`,
                                backgroundPosition: `right 0.25rem center`,
                                backgroundRepeat: `no-repeat`,
                                backgroundSize: `1.5em 1.5em`
                            }}
                        >
                            <option value="All Types">All Types</option>
                            <option value="BYO Agent">BYO Agent</option>
                            <option value="Platform Agent">Platform Agent</option>
                        </select>

                        {(searchQuery !== "" || statusFilter !== "All Statuses" || typeFilter !== "All Types") && (
                            <button
                                onClick={() => {
                                    setSearchQuery("");
                                    setStatusFilter("All Statuses");
                                    setTypeFilter("All Types");
                                }}
                                className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors ml-1"
                            >
                                <X size={14} className="text-gray-400" />
                                Clear Filters
                            </button>
                        )}
                    </div>

                    <div className="flex items-center border border-gray-200 rounded-lg p-0.5 bg-gray-50">
                        <button
                            onClick={() => setViewMode("list")}
                            className={`p-1.5 rounded-md transition-colors ${viewMode === 'list' ? 'bg-white shadow-sm text-gray-700' : 'text-gray-400 hover:bg-gray-100'}`}
                        >
                            <List size={16} />
                        </button>
                        <button
                            onClick={() => setViewMode("grid")}
                            className={`p-1.5 rounded-md transition-colors ${viewMode === 'grid' ? 'bg-white shadow-sm text-gray-700' : 'text-gray-400 hover:bg-gray-100'}`}
                        >
                            <LayoutGrid size={16} />
                        </button>
                    </div>
                </div>
            </div>

            {/* Content Area */}
            {viewMode === "list" ? (
                <div className="border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead>
                                <tr className="border-b border-gray-200 text-gray-500 text-xs font-semibold uppercase tracking-wider bg-gray-50/50">
                                    <th className="px-6 py-4 font-semibold">Agent Name</th>
                                    <th className="px-6 py-4 font-semibold">Type / Use Case</th>
                                    <th className="px-6 py-4 font-semibold">Status</th>
                                    <th className="px-6 py-4 font-semibold">Owner</th>
                                    <th className="px-6 py-4 font-semibold">Models Used</th>
                                    <th className="px-6 py-4 font-semibold">Last Updated</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {filteredAgents.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                                            No agents found matching your filters.
                                        </td>
                                    </tr>
                                ) : (
                                    filteredAgents.map((agent) => (
                                        <tr key={agent.id} className="hover:bg-gray-50/50 transition-colors">
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 rounded-md bg-indigo-50 flex items-center justify-center flex-shrink-0 border border-indigo-100">
                                                        <Bot size={16} className="text-indigo-600" />
                                                    </div>
                                                    <span className="font-semibold text-gray-900">{agent.name}</span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex flex-col gap-1 items-start">
                                                    <span className="font-medium text-gray-900">{agent.type}</span>
                                                    <span className="text-[11px] font-medium px-2 py-0.5 rounded border border-gray-200 bg-gray-50 text-gray-600">
                                                        {agent.useCaseBadge}
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${agent.status === 'Active' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' :
                                                    agent.status === 'Error' ? 'bg-red-50 text-red-700 border-red-100' :
                                                        'bg-amber-50 text-amber-700 border-amber-100'
                                                    }`}>
                                                    {agent.status === 'Active' ? (
                                                        <CheckCircle2 size={12} className="text-emerald-500" />
                                                    ) : agent.status === 'Error' ? (
                                                        <XCircle size={12} className="text-red-500" />
                                                    ) : (
                                                        <PauseCircle size={12} className="text-amber-500" />
                                                    )}
                                                    {agent.status}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-gray-500">
                                                {agent.owner}
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex flex-wrap gap-2">
                                                    {agent.models.map((model, idx) => (
                                                        <span key={idx} className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium bg-indigo-50/50 text-indigo-700 border border-indigo-100">
                                                            <BrainCircuit size={12} className="text-indigo-500" />
                                                            {model}
                                                        </span>
                                                    ))}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-gray-500 text-sm whitespace-nowrap">
                                                {agent.lastUpdated}
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            ) : (
                /* Grid View */
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {filteredAgents.length === 0 ? (
                        <div className="col-span-1 md:col-span-2 p-8 text-center border border-gray-200 rounded-xl bg-white text-gray-500 shadow-sm">
                            No agents found matching your filters.
                        </div>
                    ) : (
                        filteredAgents.map((agent) => (
                            <div key={agent.id} className="bg-white border text-gray-900 border-gray-200 rounded-xl p-5 md:p-6 shadow-sm flex flex-col border-l-[3px] border-l-indigo-500 hover:shadow-md transition-shadow">
                                {/* Card Header */}
                                <div className="flex justify-between items-start mb-4">
                                    <div className="flex gap-4">
                                        <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center flex-shrink-0 border border-indigo-100">
                                            <Bot size={20} className="text-indigo-600" />
                                        </div>
                                        <div>
                                            <h3 className="font-semibold text-lg text-gray-900 leading-tight">{agent.name}</h3>
                                            <p className="text-sm font-medium text-gray-500">{agent.type}</p>
                                        </div>
                                    </div>
                                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${agent.status === 'Active' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' :
                                        agent.status === 'Error' ? 'bg-red-50 text-red-700 border-red-100' :
                                            'bg-amber-50 text-amber-700 border-amber-100'
                                        }`}>
                                        {agent.status === 'Active' ? (
                                            <CheckCircle2 size={12} className="text-emerald-500" />
                                        ) : agent.status === 'Error' ? (
                                            <XCircle size={12} className="text-red-500" />
                                        ) : (
                                            <PauseCircle size={12} className="text-amber-500" />
                                        )}
                                        {agent.status}
                                    </span>
                                </div>

                                {/* Description */}
                                <p className="text-gray-500 text-[13px] leading-relaxed mb-6">
                                    {agent.description}
                                </p>

                                {/* Meta section */}
                                <div className="mt-auto space-y-4">
                                    <div className="flex items-center flex-wrap gap-x-5 gap-y-3">
                                        <span className="text-[11px] font-medium px-2 py-0.5 rounded border border-gray-200 bg-gray-50 text-gray-600">
                                            {agent.useCaseBadge}
                                        </span>
                                        <div className="flex items-center gap-1.5 text-xs text-gray-500">
                                            <User2 size={14} className="text-gray-400" />
                                            {agent.owner}
                                        </div>
                                        <div className="flex items-center gap-1.5 text-xs text-gray-500">
                                            <Clock size={14} className="text-gray-400" />
                                            Updated {agent.lastUpdated}
                                        </div>
                                    </div>

                                    {/* Models Separator */}
                                    <div className="border-t border-gray-100 pt-3 flex flex-wrap gap-2">
                                        {agent.models.map((model, idx) => (
                                            <span key={idx} className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium bg-indigo-50/50 text-indigo-600 border border-indigo-100">
                                                <BrainCircuit size={12} className="text-indigo-400" />
                                                {model}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}

            {/* Register Agent Modal */}
            {isRegisterModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50 backdrop-blur-sm">
                    <div className="bg-white rounded-2xl w-full max-w-3xl shadow-xl overflow-hidden flex flex-col">
                        {/* Modal Header */}
                        <div className="p-6 pb-4 border-b border-gray-100 flex justify-between items-start">
                            <div>
                                <div className="flex items-center gap-2 mb-1 text-indigo-700">
                                    <Bot size={20} />
                                    <h2 className="text-[20px] font-semibold text-gray-900">Register New Agent</h2>
                                </div>
                                <p className="text-gray-500 text-[15px]">
                                    {modalStep === 1 ? "Select how this agent is managed." : "Provide basic metadata for the agent."}
                                </p>
                            </div>
                            <button
                                onClick={handleCloseModal}
                                className="p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
                            >
                                <X size={20} />
                            </button>
                        </div>

                        {modalStep === 1 ? (
                            <>
                                {/* Modal Body - Agent Type Selection */}
                                <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-5">
                                    {/* BYO Agent Card */}
                                    <div
                                        onClick={() => setSelectedAgentType("byo")}
                                        className={`p-6 rounded-xl border-2 cursor-pointer transition-all ${selectedAgentType === 'byo'
                                            ? 'border-indigo-500 bg-indigo-50/20'
                                            : 'border-gray-100 hover:border-indigo-200 hover:shadow-sm'
                                            }`}
                                    >
                                        <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-xl flex items-center justify-center mb-5">
                                            <Upload size={24} />
                                        </div>
                                        <h3 className="text-[18px] font-semibold text-gray-900 mb-2">Bring Your Own Agent</h3>
                                        <p className="text-gray-500 text-[14.5px] leading-relaxed">
                                            Register an external agent built with LangChain, AutoGen, or custom code. You manage the execution.
                                        </p>
                                    </div>

                                    {/* Managed Agent Card */}
                                    <div
                                        onClick={() => setSelectedAgentType("managed")}
                                        className={`p-6 rounded-xl border-2 cursor-pointer transition-all ${selectedAgentType === 'managed'
                                            ? 'border-indigo-500 bg-indigo-50/20'
                                            : 'border-gray-100 hover:border-indigo-200 hover:shadow-sm'
                                            }`}
                                    >
                                        <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-xl flex items-center justify-center mb-5">
                                            <Settings size={24} />
                                        </div>
                                        <h3 className="text-[18px] font-semibold text-gray-900 mb-2">Managed Platform Agent</h3>
                                        <p className="text-gray-500 text-[14.5px] leading-relaxed">
                                            Deploy a pre-built agent template managed entirely within the platform infrastructure.
                                        </p>
                                    </div>
                                </div>

                                {/* Modal Footer */}
                                <div className="p-6 pt-4 border-t border-gray-100 flex justify-end gap-3 mt-4">
                                    <button
                                        onClick={handleCloseModal}
                                        className="px-5 py-2.5 rounded-lg text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 transition-colors"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        disabled={!selectedAgentType}
                                        onClick={() => setModalStep(2)}
                                        className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-colors ${selectedAgentType
                                            ? 'bg-indigo-400 hover:bg-indigo-500 text-white cursor-pointer'
                                            : 'bg-indigo-300 text-white/90 cursor-not-allowed opacity-70'
                                            }`}
                                    >
                                        Next <ChevronRight size={16} />
                                    </button>
                                </div>
                            </>
                        ) : (
                            <>
                                {/* Step 2 - Form */}
                                <div className="p-6 space-y-6">
                                    {/* Selected Badge */}
                                    <div className="flex items-center gap-2.5 p-3.5 bg-indigo-50/50 rounded-xl border border-indigo-100/50">
                                        <span className="text-[12.5px] font-semibold px-3 py-1 rounded-full bg-indigo-200/50 text-indigo-700">
                                            {selectedAgentType === 'byo' ? 'BYO Agent' : 'Platform Agent'}
                                        </span>
                                        <span className="text-[14.5px] text-indigo-600">Selected. Provide basic details to register.</span>
                                    </div>

                                    {/* Input Fields */}
                                    <div className="space-y-5">
                                        <div className="space-y-1.5">
                                            <label className="text-[14px] font-semibold text-gray-900 block">Agent Name *</label>
                                            <input
                                                type="text"
                                                value={newAgentName}
                                                onChange={(e) => setNewAgentName(e.target.value)}
                                                placeholder="e.g. Data Quality Scanner"
                                                className="w-full px-3.5 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all placeholder:text-gray-400"
                                            />
                                        </div>
                                        <div className="space-y-1.5">
                                            <label className="text-[14px] font-semibold text-gray-900 block">Owner / Team *</label>
                                            <input
                                                type="text"
                                                value={newAgentOwner}
                                                onChange={(e) => setNewAgentOwner(e.target.value)}
                                                placeholder="e.g. Data Engineering"
                                                className="w-full px-3.5 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all placeholder:text-gray-400"
                                            />
                                        </div>
                                        <div className="space-y-1.5">
                                            <label className="text-[14px] font-semibold text-gray-900 block">Description</label>
                                            <textarea
                                                rows={3}
                                                value={newAgentDesc}
                                                onChange={(e) => setNewAgentDesc(e.target.value)}
                                                placeholder="Describe the agent's purpose and capabilities..."
                                                className="w-full px-3.5 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all placeholder:text-gray-400 resize-none"
                                            ></textarea>
                                        </div>
                                    </div>
                                </div>

                                {/* Step 2 Footer */}
                                <div className="p-6 pt-4 border-t border-gray-100 flex justify-between items-center mt-4">
                                    <button
                                        onClick={() => setModalStep(1)}
                                        className="flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-sm font-medium text-gray-700 bg-white border border-gray-200 hover:bg-gray-50 transition-colors"
                                    >
                                        <ChevronLeft size={16} /> Back
                                    </button>
                                    <div className="flex gap-3">
                                        <button
                                            onClick={handleCloseModal}
                                            className="px-5 py-2.5 rounded-lg text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 transition-colors"
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            onClick={handleRegister}
                                            disabled={!newAgentName.trim() || !newAgentOwner.trim()}
                                            className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-colors ${newAgentName.trim() && newAgentOwner.trim()
                                                    ? 'bg-indigo-600 hover:bg-indigo-700 text-white cursor-pointer'
                                                    : 'bg-indigo-300 text-white/90 cursor-not-allowed opacity-70'
                                                }`}
                                        >
                                            Register Agent
                                        </button>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
