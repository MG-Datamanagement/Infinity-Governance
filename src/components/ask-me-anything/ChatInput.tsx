import React, { useState, useRef, useEffect } from "react";
import { TbTableSpark } from "react-icons/tb";
import { RiRobot2Line } from "react-icons/ri";
import { FiSend } from "react-icons/fi";
import { cn } from "@/lib/utils";
import { IoClose } from "react-icons/io5";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  selectedAgents: string[];
  selectedDatasets: string[];
  onOpenAgentModal: () => void;
  onOpenDatasetModal: () => void;
  onRemoveAgent: (agentId: string) => void;
  onRemoveDataset: (datasetId: string) => void;
  placeholder?: string;
  isDatasetModalOpen: boolean;
  isAgentModalOpen: boolean;
  replyTo: null | string;
  handleReplyTo: (replyTo: null | string) => void;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  disabled,
  selectedAgents,
  selectedDatasets,
  onOpenAgentModal,
  onOpenDatasetModal,
  onRemoveAgent,
  onRemoveDataset,
  isAgentModalOpen,
  isDatasetModalOpen,
  placeholder = "Ask Me Anything...!",
  replyTo,
  handleReplyTo,
}) => {
  const [message, setMessage] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        textareaRef.current.scrollHeight + "px";
    }
  }, [message]);

  const handleSubmit = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-gray-200 px-6 py-2 mx-auto w-full">
      {replyTo && (
        <div className="w-full flex justify-between items-center gap-1 bg-gray-50 border-t border-l border-r rounded-tl-xl rounded-tr-xl p-2 border-gray-200 transition-all">
          <span className="line-clamp-1 text-xs text-slate-500">
            Replying to: {replyTo}
          </span>
          <button
            className="opacity-60 hover:opacity-100 transition-opacity"
            onClick={() => handleReplyTo(null)}
          >
            <IoClose size={14} />
          </button>
        </div>
      )}

      {(selectedDatasets.length > 0 || selectedAgents.length > 0) && (
        <div
          className={cn(
            "flex gap-1 flex-wrap bg-gray-50 transition-all p-2 border-t border-l border-r border-gray-200",
            replyTo
              ? "rounded-tl-none rounded-tr-none"
              : "rounded-tl-xl rounded-tr-xl",
          )}
        >
          {selectedDatasets.map((datasetId) => (
            <span
              key={datasetId}
              className="flex items-center bg-indigo-50 border border-indigo-200 text-indigo-600 rounded-3xl px-1.5 py-1 gap-1.5"
            >
              <TbTableSpark size={10} />
              <span className="text-[10px] font-semibold">{datasetId}</span>
              <button
                onClick={() => onRemoveDataset(datasetId)}
                className="opacity-60 hover:opacity-100 transition-opacity"
              >
                <IoClose size={10} />
              </button>
            </span>
          ))}
          {selectedAgents.map((agentId) => (
            <span
              key={agentId}
              className="flex items-center bg-purple-50 border border-purple-200 text-purple-600 rounded-3xl px-1.5 py-1 gap-1.5"
            >
              <RiRobot2Line size={10} />
              <span className="text-[10px] font-semibold">{agentId}</span>
              <button
                onClick={() => onRemoveAgent(agentId)}
                className="opacity-60 hover:opacity-100 transition-opacity"
              >
                <IoClose size={10} />
              </button>
            </span>
          ))}
        </div>
      )}

      <div
        className={cn(
          "flex items-center gap-2 border border-gray-300 rounded-xl p-2 focus-within:border-indigo-600 transition-all",
          selectedDatasets.length > 0 || selectedAgents.length > 0 || replyTo
            ? "rounded-tl-none rounded-tr-none"
            : "",
        )}
      >
        {/* <button
          className={cn(
            "p-2 rounded-md hover:bg-gray-200 transition-colors flex-shrink-0",
            isDatasetModalOpen ? "bg-indigo-100 text-indigo-600 font-bold" : "",
          )}
          onClick={onOpenDatasetModal}
          title="Add datasets to context"
        >
          <TbTableSpark size={16} />
        </button> */}

        <button
          className={cn(
            "p-2 rounded-md hover:bg-gray-200 transition-colors flex-shrink-0",
            isAgentModalOpen ? "bg-purple-100 text-purple-600 font-bold" : "",
          )}
          onClick={onOpenAgentModal}
          title="Call agents"
        >
          <RiRobot2Line size={16} />
        </button>

        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="flex-1 bg-transparent border-none outline-none resize-none text-sm p-1 max-h-[200px] leading-relaxed"
        />

        <button
          className={cn(
            "text-white rounded-lg p-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0",
            !message.trim() ? "bg-gray-300" : "bg-indigo-600",
          )}
          onClick={handleSubmit}
          disabled={disabled || !message.trim()}
        >
          <FiSend size={16} />
        </button>
      </div>

      <div className="text-center text-xs/3 text-gray-300 my-1.5">
        AI can make mistakes. Please review generated insights.
      </div>
    </div>
  );
};
