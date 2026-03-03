"use client";

import React, { useState, useMemo } from "react";
import {Connector, connectors} from "@/services/mock";
import SearchInput from "@/components/ui/SearchInput";
import ConnectorCard from "@/app/(data-connectors)/components/ConnectorCard";


const DataConnectorsPage: React.FC = () => {
    const [search, setSearch] = useState("");

    const filtered = useMemo(() => {
        if (!search.trim()) return connectors;
        const q = search.toLowerCase();
        return connectors.filter(
            (c) =>
                c.name.toLowerCase().includes(q) ||
                c.description.toLowerCase().includes(q)
        );
    }, [search]);

    const handleConnectorClick = (connector: Connector) => {
        // Handle connector selection — navigate or open modal
        console.log("Selected connector:", connector.id);
    };

    return (
        <div className="min-h-screen bg-gray-50 font-sans">
            <main className="max-w-7xl mx-auto px-8 py-8">

                {/* Breadcrumb */}
                <nav className="flex items-center gap-1.5 text-sm text-gray-400 mb-6">
                    <a href="/" className="hover:text-gray-600 transition-colors">
                        Home
                    </a>
                    <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 5l7 7-7 7"
                        />
                    </svg>
                    <span className="text-gray-600 font-medium">Data Connectors</span>
                </nav>

                {/* Page Header */}
                <div className="flex items-start justify-between mb-8">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
                            Connect Data Source
                        </h1>
                        <p className="text-gray-400 mt-1 text-sm">
                            Configure connectors to import metadata from your data
                            infrastructure
                        </p>
                    </div>

                    <div className="flex items-center gap-3">
                        <SearchInput
                            value={search}
                            onChange={setSearch}
                            placeholder="Search data sources..."
                        />
                        <button className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors duration-150 whitespace-nowrap">
                            <svg
                                className="w-4 h-4"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M12 4v16m8-8H4"
                                />
                            </svg>
                            Create source
                        </button>
                    </div>
                </div>

                {/* Connectors Grid */}
                {filtered.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {filtered.map((connector) => (
                            <ConnectorCard
                                key={connector.id}
                                connector={connector}
                                onClick={handleConnectorClick}
                            />
                        ))}
                    </div>
                ) : (
                    /* Empty state */
                    <div className="flex flex-col items-center justify-center py-24 text-gray-400">
                        <svg
                            className="w-12 h-12 mb-3 text-gray-300"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={1.5}
                                d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z"
                            />
                        </svg>
                        <p className="font-medium text-gray-500">No connectors found</p>
                        <p className="text-sm mt-1">
                            Try a different search term
                        </p>
                    </div>
                )}
            </main>
        </div>
    );
};

export default DataConnectorsPage;