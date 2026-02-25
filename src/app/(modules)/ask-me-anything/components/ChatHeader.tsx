import { SettingsIcon } from "lucide-react";
import React from "react";
import { MdOutlineAutoAwesome } from "react-icons/md";
import { GoLightBulb } from "react-icons/go";
import { LuBrainCircuit } from "react-icons/lu";
import { BsArrowsAngleExpand } from "react-icons/bs";
import { RiCollapseDiagonalLine } from "react-icons/ri";

interface ChatHeaderProps {
  memoryEnabled: boolean;
  reasoningEnabled: boolean;
  onToggleMemory: () => void;
  onToggleReasoning: () => void;
  onSettingsClick: () => void;
  onExpandClick: () => void;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  memoryEnabled,
  reasoningEnabled,
  onToggleMemory,
  onToggleReasoning,
  onSettingsClick,
  onExpandClick,
}) => {
  return (
    <div className="flex justify-between items-center px-4 py-3.5 border-b border-gray-200">
      <div className="flex items-center gap-3">
        <div>
          <MdOutlineAutoAwesome size={16} />
        </div>
        <span className="text-md font-medium text-gray-900">
          Chat Assistant
        </span>
        <span className="bg-gray-200/50 text-gray-700 px-2 py-1 rounded-xl text-xs/3 font-medium">
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
                <LuBrainCircuit size={14} />
              </div>
              <span className="">Memory {memoryEnabled ? "On" : "Off"}</span>
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
                <GoLightBulb size={14} />
              </div>
              <span>Reasoning {reasoningEnabled ? "On" : "Off"}</span>
            </button>
          </div>
        </div>

        <div>
          <button
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            onClick={onSettingsClick}
          >
            <div>
              <SettingsIcon size={16} className="text-gray-500" />
            </div>
          </button>
        </div>

        <div>
          <button
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            onClick={onExpandClick}
          >
            <div>
              <RiCollapseDiagonalLine />
            </div>
          </button>
        </div>
      </div>
    </div>
  );
};
