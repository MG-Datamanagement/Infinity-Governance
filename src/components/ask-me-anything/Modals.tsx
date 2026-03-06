import React from "react";
import { TbTableSpark } from "react-icons/tb";
import { RiRobot2Line } from "react-icons/ri";
import { IoClose } from "react-icons/io5";
import { Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { Agent, ChatDataset } from "@/types";

interface AgentModalProps {
  isOpen: boolean;
  agents: Agent[];
  selectedAgents: string[];
  onClose: () => void;
  onToggleAgent: (agentId: string) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
}

export const AgentModal: React.FC<AgentModalProps> = ({
  isOpen,
  agents,
  selectedAgents,
  onClose,
  onToggleAgent,
  searchQuery,
  onSearchChange,
}) => {
  if (!isOpen) return null;

  const filteredAgents = agents.filter(
    (agent) =>
      agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.description.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <div
      className="fixed inset-5 backdrop-blur-xs flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="w-[90%] max-w-[350px] max-h-[55vh] bg-white rounded-lg flex flex-col shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center px-4 py-2 rounded-tl-lg rounded-tr-lg bg-[#f1f5f9] border-b border-gray-200">
          <div className="flex items-center gap-2.5 text-sm font-medium">
            <RiRobot2Line size={18} className="text-[#a754f4] font-bold" />
            <span className="text-gray-700">Call Agents</span>
          </div>
          <button
            className="text-xl opacity-60 hover:opacity-100 transition-opacity"
            onClick={onClose}
          >
            <IoClose size={16} />
          </button>
        </div>

        <div className="px-3 py-2 border-b border-gray-200">
          <div className="flex items-center px-2 py-1 border border-gray-200 rounded-lg text-sm outline-none focus:border-indigo-600 transition-colors">
            <div>
              <Search size={16} className="text-gray-500 font-bold" />
            </div>
            <input
              type="text"
              placeholder="Search agents..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="px-2 py-1 text-xs outline-none shadow-none border-none"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-1">
          {filteredAgents.map((agent) => {
            const Icon = agent?.icon;

            return (
              <div
                key={agent.id}
                className={`flex items-start gap-3 px-2 py-1 mb-1 rounded-sm cursor-pointer transition-all ${
                  selectedAgents.includes(agent.id)
                    ? "bg-purple-50 border-pruple-600"
                    : "border-gray-300 hover:border-indigo-600 hover:bg-indigo-50"
                } ${agent?.disabled ? "opacity-30" : ""}`}
                onClick={() => !agent?.disabled && onToggleAgent(agent.id)}
              >
                <input
                  type="checkbox"
                  checked={selectedAgents.includes(agent.id)}
                  onChange={() => {}}
                  className={cn(
                    "my-auto",
                    selectedAgents.includes(agent.id) ? "accent-purple-600" : "",
                  )}
                  disabled={agent?.disabled}
                />
                <div className="my-auto">
                  <Icon size={16} />
                </div>
                <div className="flex-1 space-y-1">
                  <div
                    className={cn(
                      "text-xs font-medium text-gray-900",
                      selectedAgents.includes(agent.id)
                        ? "text-purple-600"
                        : "",
                    )}
                  >
                    {agent.name}
                  </div>
                  <div className="text-[10px] text-gray-600">
                    {agent.description}
                  </div>
                  {agent?.alert ? (
                    <div className="text-xs/3 text-orange-500">
                      {agent?.alert}
                    </div>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>

        <div className="px-4 py-2 border-t border-gray-200">
          <span className="text-xs text-gray-600">
            {selectedAgents.length} agents selected
          </span>
        </div>
      </div>
    </div>
  );
};

interface DatasetModalProps {
  isOpen: boolean;
  datasets: ChatDataset[];
  selectedDatasets: string[];
  onClose: () => void;
  onToggleDataset: (datasetId: string) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
}

export const DatasetModal: React.FC<DatasetModalProps> = ({
  isOpen,
  datasets,
  selectedDatasets,
  onClose,
  onToggleDataset,
  searchQuery,
  onSearchChange,
}) => {
  if (!isOpen) return null;

  const filteredDatasets = datasets.filter((dataset) =>
    dataset.name.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <div
      className="fixed inset-5 backdrop-blur-xs flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="w-[90%] max-w-[350px] max-h-[55vh] bg-white rounded-lg flex flex-col shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center px-4 py-2 rounded-tl-lg rounded-tr-lg bg-[#f1f5f9] border-b border-gray-200">
          <div className="flex items-center gap-2.5 text-sm font-medium">
            <TbTableSpark size={16} className="text-[#4e45e3] font-bold" />
            <span className="text-gray-700">Add Datasets</span>
          </div>
          <button
            className="text-xl opacity-60 hover:opacity-100 transition-opacity"
            onClick={onClose}
          >
            <IoClose size={16} />
          </button>
        </div>

        <div className="px-3 py-2 border-b border-gray-200">
          <div className="flex items-center px-2 py-1 border border-gray-200 rounded-lg text-sm outline-none focus:border-indigo-600 transition-colors">
            <div>
              <Search size={14} className="text-gray-500 font-bold" />
            </div>
            <input
              type="text"
              placeholder="Search datasets..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="px-2 py-1 text-xs outline-none shadow-none border-none"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-1">
          {filteredDatasets.map((dataset) => (
            <div
              key={dataset.id}
              className={`flex items-start gap-3 px-2 py-1 mb-1 rounded-sm cursor-pointer transition-all ${
                selectedDatasets.includes(dataset.id)
                  ? "bg-indigo-50 border-indigo-600"
                  : "border-gray-300 hover:border-indigo-600 hover:bg-indigo-50"
              }`}
              onClick={() => onToggleDataset(dataset.id)}
            >
              <input
                type="checkbox"
                checked={selectedDatasets.includes(dataset.id)}
                onChange={() => {}}
                className={cn(
                  "my-auto",
                  selectedDatasets.includes(dataset.id)
                    ? "accent-indigo-600"
                    : "",
                )}
              />
              <div className="flex-1 space-y-1">
                <div
                  className={cn(
                    "text-xs font-medium text-gray-900",
                    selectedDatasets.includes(dataset.id)
                      ? "text-indigo-600"
                      : "",
                  )}
                >
                  {dataset.name}
                </div>
                <div className="text-[10px] text-gray-600">
                  {dataset.type} • {dataset.columns} cols •{" "}
                  {dataset.rows.toLocaleString()} rows
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="px-4 py-2 border-t border-gray-200">
          <span className="text-xs text-gray-600">
            {selectedDatasets.length} datasets selected
          </span>
        </div>
      </div>
    </div>
  );
};
