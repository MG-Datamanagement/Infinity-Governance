import { SettingsIcon } from "lucide-react";
import React from "react";
import { MdOutlineAutoAwesome } from "react-icons/md";
import { GoLightBulb } from "react-icons/go";
import { LuBrainCircuit } from "react-icons/lu";
import { BsArrowsAngleExpand } from "react-icons/bs";
import { RiCollapseDiagonalLine } from "react-icons/ri";
import { LuSparkles } from "react-icons/lu";
import { AIPreferences } from "@/types";
import { SlEnergy } from "react-icons/sl";
import { GrConfigure } from "react-icons/gr";
import { TbZoomScan } from "react-icons/tb";
import { GoWorkflow } from "react-icons/go";

interface ChatHeaderProps {
  memoryEnabled: boolean;
  reasoningEnabled: boolean;
  onToggleMemory: () => void;
  onToggleReasoning: () => void;
  onSettingsClick: () => void;
  onExpandClick: () => void;
  showAIPreferences: boolean;
  aiPreferences: AIPreferences;
  onToggleAIPreferences: () => void;
  onTogglePreference: (
    key: "multiAgentOrchestration" | "deepAnalysis" | "autoRemediation",
  ) => void;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  memoryEnabled,
  reasoningEnabled,
  onToggleMemory,
  onToggleReasoning,
  onSettingsClick,
  onExpandClick,
  onToggleAIPreferences,
  onTogglePreference,
  showAIPreferences,
  aiPreferences,
}) => {
  return (
    <>
      <div className="flex justify-between items-center px-4 py-2.5 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div>
            <LuSparkles size={18} className="text-indigo-600" />
          </div>
          <span className="text-sm font-semibold text-gray-900">
            Chat Assistant
          </span>
          <span className="bg-gray-200/50 text-gray-700 px-2 py-0.5 rounded-xl text-[10px] font-medium">
            Beta
          </span>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex justify-around items-center p-1 bg-gray-100 rounded-md">
            <div>
              <button
                className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-semibold transition-all ${
                  memoryEnabled
                    ? "bg-white text-indigo-600"
                    : "text-gray-500 hover:text-gray-950"
                }`}
                onClick={onToggleMemory}
              >
                <div>
                  <LuBrainCircuit size={12} />
                </div>
                <span className="text-[10px] font-medium">
                  Memory {memoryEnabled ? "On" : "Off"}
                </span>
              </button>
            </div>
            <div className="text-gray-300/60 mx-1.5">|</div>
            <div>
              <button
                className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium transition-all ${
                  reasoningEnabled
                    ? "bg-white text-indigo-600"
                    : "text-gray-500 hover:text-gray-950"
                }`}
                onClick={onToggleReasoning}
              >
                <div>
                  <GoLightBulb size={12} />
                </div>
                <span className="text-[10px] font-medium">
                  Reasoning {reasoningEnabled ? "On" : "Off"}
                </span>
              </button>
            </div>
          </div>

          <div>
            <button
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
              onClick={onToggleAIPreferences}
              title="AI Preferences"
            >
              <SettingsIcon size={16} className="text-gray-500" />
            </button>
          </div>

          <div>
            <button
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
              onClick={onExpandClick}
            >
              <RiCollapseDiagonalLine size={16} className="text-gray-500" />
            </button>
          </div>
        </div>
      </div>

      {/* {showAIPreferences && (
        <div className="px-4 py-2.5 border-b border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <SlEnergy size={14} className="text-indigo-600" />

              <span className="text-xs font-medium text-gray-900">
                AI Workflow Preferences
              </span>
            </div>
            <span className="text-[10px] text-gray-500">
              Enable advanced features (higher token usage)
            </span>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => onTogglePreference("multiAgentOrchestration")}
              className={`flex items-center gap-2 px-2 py-1 rounded-lg text-[10px] font-medium transition-all ${
                aiPreferences.multiAgentOrchestration
                  ? "bg-indigo-50 text-indigo-700 border border-indigo-300"
                  : "bg-white hover:text-gray-600 border border-gray-200 text-gray-400"
              }`}
            >
              <GoWorkflow size={12} />
              <span>Multi-Agent Orchestration</span>
              {aiPreferences.multiAgentOrchestration && (
                <span className="text-indigo-600">✓</span>
              )}
            </button>

            <button
              onClick={() => onTogglePreference("deepAnalysis")}
              className={`flex items-center gap-2 px-2 py-1 rounded-lg text-[10px] font-medium transition-all ${
                aiPreferences.deepAnalysis
                  ? "bg-teal-50 text-teal-700 border border-teal-300"
                  : "bg-white hover:text-gray-600 border border-gray-200 text-gray-400"
              }`}
            >
              <TbZoomScan size={12} />
              <span>Deep Analysis</span>
              {aiPreferences.deepAnalysis && (
                <span className="text-teal-600">✓</span>
              )}
            </button>

            <button
              onClick={() => onTogglePreference("autoRemediation")}
              className={`flex items-center gap-2 px-2 py-1 rounded-lg text-[10px] font-medium transition-all ${
                aiPreferences.autoRemediation
                  ? "bg-orange-50 text-orange-700 border border-orange-300"
                  : "bg-white hover:text-gray-600 border border-gray-200 text-gray-400"
              }`}
            >
              <GrConfigure size={12} />
              <span>Auto-Remediation</span>
              {aiPreferences.autoRemediation && (
                <span className="text-orange-600">✓</span>
              )}
            </button>
          </div>
        </div>
      )} */}
    </>
  );
};
