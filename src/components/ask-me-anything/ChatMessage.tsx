import React, { useState, useRef, useEffect } from "react";
import { Message, Source, ReasoningTool, ToolDetail } from "@/types";
import { RiRobot2Line } from "react-icons/ri";
import { FiUser } from "react-icons/fi";
import { FiEdit2 } from "react-icons/fi";
import { LuReply } from "react-icons/lu";
import { MdOutlineContentCopy } from "react-icons/md";
import { AiOutlineDislike } from "react-icons/ai";
import { AiOutlineLike } from "react-icons/ai";
import { IoRefreshSharp } from "react-icons/io5";
import { cn } from "@/lib/utils";
import { GoLightBulb } from "react-icons/go";
import { FaChevronDown } from "react-icons/fa6";
import { FaChevronRight } from "react-icons/fa6";
import { FiBookOpen } from "react-icons/fi";
import { IoHardwareChipOutline } from "react-icons/io5";
import { FiDatabase } from "react-icons/fi";
import { GoArrowRight } from "react-icons/go";
import { GoDotFill } from "react-icons/go";

interface ChatMessageProps {
  message: Message;
  reasoning?: string[];
  reasoningSummary?: string;
  reasoningTools?: ReasoningTool[];
  sources?: Source[];
  toolsDetail?: ToolDetail[];
  suggestions?: string[];
  onSuggestionClick?: (suggestion: string) => void;
  showReasoningToggle?: boolean;
  onEditMessage?: (newContent: string) => void;
  isLatestHumanMessage?: boolean;
  handleReplyTo: (replyTo: null | string) => void;
  isThinking: boolean;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  reasoning,
  reasoningSummary,
  reasoningTools,
  sources,
  toolsDetail,
  suggestions,
  onSuggestionClick,
  showReasoningToggle,
  onEditMessage,
  isLatestHumanMessage,
  handleReplyTo,
  isThinking
}) => {
  const [showReasoning, setShowReasoning] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(message.content);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        textareaRef.current.scrollHeight + "px";
      textareaRef.current.focus();
      const length = textareaRef.current.value.length;
      textareaRef.current.setSelectionRange(length, length);
    }
  }, [isEditing]);

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        textareaRef.current.scrollHeight + "px";
    }
  }, [editedContent]);

  const handleEdit = () => {
    setIsEditing(true);
    setEditedContent(message.content);
  };

  const handleSave = () => {
    if (editedContent.trim() && onEditMessage) {
      onEditMessage(editedContent.trim());
      setIsEditing(false);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditedContent(message.content);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSave();
    } else if (e.key === "Escape") {
      handleCancel();
    }
  };

  return (
    <div
      className={`flex gap-2 mb-8 ${message.role === "human" ? "justify-end" : "items-start"}`}
    >
      {message.role === "ai" && (
        <div className="w-9 h-9 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center flex-shrink-0">
          <RiRobot2Line size={16} />
        </div>
      )}

      <div
        className={cn(
          message.role === "human" ? "w-auto" : " flex-1 max-w-[500px]",
        )}
      >
        {message.role === "human" ? (
          <div className="relative">
            {isEditing ? (
              <div className="bg-indigo-600 text-white p-2 rounded-2xl rounded-br-sm">
                <textarea
                  ref={textareaRef}
                  value={editedContent}
                  onChange={(e) => setEditedContent(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="w-full bg-transparent border border-white/30 rounded-lg p-1 text-sm leading-relaxed resize-none outline-none focus:border-white/60"
                  rows={1}
                />
                <div className="flex justify-end gap-2">
                  <button
                    onClick={handleCancel}
                    className="px-2.5 py-1 rounded-lg text-sm font-medium hover:bg-white/10 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    className="px-2.5 py-1 bg-white text-indigo-600 rounded-lg text-sm font-medium hover:bg-white/90 transition-colors"
                    disabled={!editedContent.trim()}
                  >
                    Save
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="bg-indigo-600 text-white px-3 py-2 rounded-2xl rounded-br-sm">
                  <div className="text-sm leading-relaxed whitespace-pre-wrap">
                    {message.content}
                  </div>

                  {message.edited && (
                    <div className="text-[10px] text-white/60 mt-1 italic">
                      Edited
                    </div>
                  )}
                </div>
                {isLatestHumanMessage && onEditMessage  && (
                  <button
                    onClick={handleEdit}
                    className="absolute -bottom-6 right-0 text-sm text-gray-500 hover:text-indigo-600 transition-all flex items-center gap-1"
                  >
                    <FiEdit2 size={14} />
                    <span>Edit</span>
                  </button>
                )}
              </>
            )}
          </div>
        ) : (
          <>
            <div className="text-sm leading-relaxed whitespace-pre-wrap border border-gray-300 rounded-2xl rounded-bl-sm px-3 py-2 shadow-sm">
              {message.content}
            </div>

            {showReasoningToggle && (reasoningSummary || reasoningTools) && (
              <div className="mt-2 bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
                <button
                  className="w-full flex items-center gap-2 px-2 py-1 text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
                  onClick={() => setShowReasoning(!showReasoning)}
                >
                  <span className="text-gray-400">
                    {showReasoning ? (
                      <FaChevronDown size={10} />
                    ) : (
                      <FaChevronRight size={10} />
                    )}
                  </span>
                  <GoLightBulb size={12} className="text-indigo-600" />
                  <span className="text-[10px]">Show Reasoning</span>
                </button>

                {showReasoning && (
                  <div className="px-3 py-2 border-t border-gray-200">
                    {reasoningSummary && (
                      <div className="mb-2">
                        <div className="text-[10px] font-medium text-gray-900">
                          Reasoning:{" "}
                          <span className="text-[10px] text-gray-500 leading-relaxed">
                            {reasoningSummary}
                          </span>
                        </div>
                      </div>
                    )}

                    {reasoningTools && reasoningTools.length > 0 && (
                      <div className="flex gap-2 flex-wrap">
                        {reasoningTools.map((tool, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center gap-0.5 bg-indigo-50 text-indigo-700 border border-indigo-200 px-1 py-0.5 rounded-md"
                          >
                            <IoHardwareChipOutline size={10} />
                            <span className="text-[10px]">
                              Tool: {tool.label}
                            </span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {sources && sources.length > 0 && (
              <div className="mt-2 flex gap-2 flex-wrap">
                {sources.map((source, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 bg-slate-50 border border-gray-200 px-2 py-1 rounded-md"
                  >
                    <FiDatabase size={10} />
                    <span className="text-gray-800 font-medium text-[10px]">
                      {source.label}
                    </span>
                    <GoDotFill size={5} className="text-gray-800 h-3" />

                    <span className="text-gray-500 text-[10px] ">
                      {source.type}
                    </span>
                  </span>
                ))}
              </div>
            )}

            <div className="flex gap-2 mt-2">
              <button
                className="rounded-md px-2.5 py-1.5 text-sm text-slate-600 hover:bg-gray-50 hover:border-indigo-600 transition-all"
                title="Like"
                aria-label="Like"
              >
                <AiOutlineLike size={16} />
              </button>
              <button
                className="rounded-md px-2.5 py-1.5 text-sm text-slate-600 hover:bg-gray-50 hover:border-indigo-600 transition-all"
                title="Dislike"
                aria-label="Dislike"
              >
                <AiOutlineDislike size={14} />
              </button>
              <button
                className="rounded-md px-2.5 py-1.5 text-sm text-slate-600 hover:bg-gray-50 hover:border-indigo-600 transition-all"
                title="Copy"
                aria-label="Copy message"
              >
                <MdOutlineContentCopy size={14} />
              </button>

              {message.error ? (
                <button
                  className="rounded-md px-2.5 py-1.5 text-sm text-slate-600 hover:bg-gray-50 hover:border-indigo-600 transition-all"
                  title="Retry"
                  aria-label="Retry"
                >
                  <IoRefreshSharp size={14} />
                </button>
              ) : (
                <button
                  className="rounded-md px-2.5 py-1.5 text-sm text-slate-600 hover:bg-gray-50 hover:border-indigo-600 transition-all"
                  title="Reply"
                  aria-label="Reply"
                  onClick={() =>
                    message.role === "ai" && handleReplyTo(message.content)
                  }
                >
                  <LuReply size={14} />
                </button>
              )}
            </div>

            {suggestions && suggestions.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    className="bg-white gap-1 border border-gray-300 rounded-2xl px-2 py-1 text-left text-xs text-indigo-600 hover:border-indigo-600 transition-all flex items-center justify-between group"
                    onClick={() => onSuggestionClick?.(suggestion)}
                  >
                    <span className="text-[10px] font-medium">
                      {suggestion}
                    </span>
                    <GoArrowRight size={12} />
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {message.role === "human" && (
        <div className="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
          <FiUser size={16} />
        </div>
      )}
    </div>
  );
};
