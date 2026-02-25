import React, { useState, useRef, useEffect } from "react";
import { Message, Source, ReasoningTool, ToolDetail } from "../types";
import { RiRobot2Line } from "react-icons/ri";
import { FiUser } from "react-icons/fi";
import { FiEdit2 } from "react-icons/fi";
import { LuReply } from "react-icons/lu";
import { MdOutlineContentCopy } from "react-icons/md";
import { AiOutlineDislike } from "react-icons/ai";
import { AiOutlineLike } from "react-icons/ai";
import { IoRefreshSharp } from "react-icons/io5";
import { cn } from "@/lib/utils";

// interface ChatMessageProps {
//   message: Message;
//   reasoning?: string[];
//   sources?: string[];
//   suggestions?: string[];
//   onSuggestionClick?: (suggestion: string) => void;
//   showReasoningToggle?: boolean;
//   onEditMessage?: (newContent: string) => void;
//   isLatestHumanMessage?: boolean;
// }

// export const ChatMessage: React.FC<ChatMessageProps> = ({
//   message,
//   reasoning,
//   sources,
//   suggestions,
//   onSuggestionClick,
//   showReasoningToggle,
//   onEditMessage,
//   isLatestHumanMessage,
// }) => {
//   const [showReasoning, setShowReasoning] = useState(false);
//   const [isEditing, setIsEditing] = useState(false);
//   const [editedContent, setEditedContent] = useState(message.content);
//   const textareaRef = useRef<HTMLTextAreaElement>(null);

//   useEffect(() => {
//     if (isEditing && textareaRef.current) {
//       textareaRef.current.style.height = "auto";
//       textareaRef.current.style.height =
//         textareaRef.current.scrollHeight + "px";
//       textareaRef.current.focus();
//       // Move cursor to end
//       const length = textareaRef.current.value.length;
//       textareaRef.current.setSelectionRange(length, length);
//     }
//   }, [isEditing]);

//   useEffect(() => {
//     if (isEditing && textareaRef.current) {
//       textareaRef.current.style.height = "auto";
//       textareaRef.current.style.height =
//         textareaRef.current.scrollHeight + "px";
//     }
//   }, [editedContent]);

//   const handleEdit = () => {
//     setIsEditing(true);
//     setEditedContent(message.content);
//   };

//   const handleSave = () => {
//     if (editedContent.trim() && onEditMessage) {
//       onEditMessage(editedContent.trim());
//       setIsEditing(false);
//     }
//   };

//   const handleCancel = () => {
//     setIsEditing(false);
//     setEditedContent(message.content);
//   };

//   const handleKeyDown = (e: React.KeyboardEvent) => {
//     if (e.key === "Enter" && !e.shiftKey) {
//       e.preventDefault();
//       handleSave();
//     } else if (e.key === "Escape") {
//       handleCancel();
//     }
//   };

//   return (
//     <div
//       className={`flex gap-2 my-4 ${message.role === "human" ? "justify-end" : "items-start"}`}
//     >
//       {message.role === "ai" && (
//         <div className="w-9 h-9 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center flex-shrink-0">
//           <RiRobot2Line size={16} />
//         </div>
//       )}

//       <div className={cn(message.role === "human" ? "w-auto" :  " flex-1 max-w-[600px]")}>
//         {message.role === "human" ? (
//           <div className="relative group">
//             {isEditing ? (
//               <div className="bg-indigo-600 text-white px-4 py-3 rounded-2xl rounded-br-md">
//                 <textarea
//                   ref={textareaRef}
//                   value={editedContent}
//                   onChange={(e) => setEditedContent(e.target.value)}
//                   onKeyDown={handleKeyDown}
//                   className="w-full bg-transparent border border-white/30 rounded-lg px-3 py-2 text-[15px] leading-relaxed resize-none outline-none focus:border-white/60"
//                   rows={1}
//                 />
//                 <div className="flex justify-end gap-2 mt-3">
//                   <button
//                     onClick={handleCancel}
//                     className="px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-white/10 transition-colors"
//                   >
//                     Cancel
//                   </button>
//                   <button
//                     onClick={handleSave}
//                     className="px-4 py-1.5 bg-white text-indigo-600 rounded-lg text-sm font-medium hover:bg-white/90 transition-colors"
//                     disabled={!editedContent.trim()}
//                   >
//                     Save
//                   </button>
//                 </div>
//               </div>
//             ) : (
//               <>
//                 <div className="bg-indigo-600 text-white px-3 py-2 rounded-2xl rounded-br-sm">
//                   <div className="text-[15px] leading-relaxed whitespace-pre-wrap">
//                     {message.content}
//                   </div>
//                 </div>
//                 {isLatestHumanMessage && onEditMessage && (
//                   <button
//                     onClick={handleEdit}
//                     className="absolute -bottom-6 right-0 text-sm text-gray-500 hover:text-indigo-600 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1"
//                   >
//                     <FiEdit2 size={16} />
//                     <span>Edit</span>
//                   </button>
//                 )}
//               </>
//             )}
//           </div>
//         ) : (
//           <>
//             <div className="text-sm leading-relaxed whitespace-pre-wrap border border-gray-300 rounded-2xl rounded-bl-sm px-3 py-2 shadow-sm">
//               {message.content}
//             </div>

//             {showReasoningToggle && reasoning && reasoning.length > 0 && (
//               <div className="mt-4 bg-gray-50 rounded-lg overflow-hidden">
//                 <button
//                   className="w-full flex items-center gap-2 px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
//                   onClick={() => setShowReasoning(!showReasoning)}
//                 >
//                   <span>{showReasoning ? "▼" : "▶"}</span>
//                   <span>💡</span>
//                   <span>Show Reasoning</span>
//                 </button>

//                 {showReasoning && (
//                   <div className="px-4 pb-4">
//                     <div className="text-[13px] text-gray-600 mb-2">
//                       Reasoning: {reasoning[0]}
//                     </div>
//                     <div className="flex gap-2 flex-wrap">
//                       <span className="bg-white border border-gray-300 px-3 py-1.5 rounded-md text-xs text-gray-700">
//                         🔧 Tool: Snowflake Connector
//                       </span>
//                       <span className="bg-white border border-gray-300 px-3 py-1.5 rounded-md text-xs text-gray-700">
//                         📚 Source: Governance Policy v2
//                       </span>
//                     </div>
//                   </div>
//                 )}
//               </div>
//             )}

//             {sources && sources.length > 0 && (
//               <div className="mt-3 flex gap-2 flex-wrap">
//                 {sources.map((source, idx) => (
//                   <span
//                     key={idx}
//                     className="bg-gray-100 px-3 py-1.5 rounded-md text-xs text-gray-700"
//                   >
//                     📄 {source}
//                   </span>
//                 ))}
//               </div>
//             )}

//             <div className="flex gap-2 mt-3">
//               <button
//                 className=" px-2.5 rounded-md py-1.5 text-sm hover:bg-gray-50 hover:border-indigo-600 transition-all"
//                 title="Like"
//               >
//                 <AiOutlineLike size={16} />
//               </button>
//               <button
//                 className=" px-2.5 rounded-md py-1.5 text-sm hover:bg-gray-50 hover:border-indigo-600 transition-all"
//                 title="Dislike"
//               >
//                 <AiOutlineDislike size={16} />
//               </button>
//               <button
//                 className=" px-2.5 rounded-md py-1.5 text-sm hover:bg-gray-50 hover:border-indigo-600 transition-all"
//                 title="Copy"
//               >
//                 <MdOutlineContentCopy size={16} />
//               </button>
//               <button
//                 className=" px-2.5 rounded-md py-1.5 text-sm hover:bg-gray-50 hover:border-indigo-600 transition-all"
//                 title="Retry"
//               >
//                 <IoRefreshSharp size={16} />
//               </button>
//             </div>

//             {suggestions && suggestions.length > 0 && (
//               <div className="mt-4 flex flex-col gap-2">
//                 {suggestions.map((suggestion, idx) => (
//                   <button
//                     key={idx}
//                     className="bg-white border border-gray-300 rounded-lg px-4 py-3 text-left text-sm text-gray-700 hover:border-indigo-600 hover:bg-indigo-50 transition-all"
//                     onClick={() => onSuggestionClick?.(suggestion)}
//                   >
//                     {suggestion} →
//                   </button>
//                 ))}
//               </div>
//             )}
//           </>
//         )}
//       </div>

//       {message.role === "human" && (
//         <div className="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
//           <FiUser size={16} />
//         </div>
//       )}
//     </div>
//   );
// };

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
      className={`flex gap-4 mb-6 ${message.role === "human" ? "justify-end" : "items-start"}`}
    >
      {message.role === "ai" && (
        <div className="w-9 h-9 rounded-full bg-indigo-50 flex items-center justify-center flex-shrink-0">
          <span className="text-lg">🤖</span>
        </div>
      )}

      <div className="flex-1 max-w-[700px]">
        {message.role === "human" ? (
          <div className="relative group">
            {isEditing ? (
              <div className="bg-indigo-600 text-white px-4 py-3 rounded-2xl rounded-br-md">
                <textarea
                  ref={textareaRef}
                  value={editedContent}
                  onChange={(e) => setEditedContent(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="w-full bg-transparent border border-white/30 rounded-lg px-3 py-2 text-[15px] leading-relaxed resize-none outline-none focus:border-white/60"
                  rows={1}
                />
                <div className="flex justify-end gap-2 mt-3">
                  <button
                    onClick={handleCancel}
                    className="px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-white/10 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    className="px-4 py-1.5 bg-white text-indigo-600 rounded-lg text-sm font-medium hover:bg-white/90 transition-colors"
                    disabled={!editedContent.trim()}
                  >
                    Save
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="bg-indigo-600 text-white px-4 py-3 rounded-2xl rounded-br-md">
                  <div className="text-[15px] leading-relaxed whitespace-pre-wrap">
                    {message.content}
                  </div>
                </div>
                {isLatestHumanMessage && onEditMessage && (
                  <button
                    onClick={handleEdit}
                    className="absolute -bottom-6 right-0 text-sm text-gray-500 hover:text-indigo-600 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1"
                  >
                    <span>✏️</span>
                    <span>Edit</span>
                  </button>
                )}
              </>
            )}
          </div>
        ) : (
          <>
            <div className="text-[15px] leading-relaxed text-gray-800 whitespace-pre-wrap">
              {message.content}
            </div>

            {showReasoningToggle && (reasoningSummary || reasoningTools) && (
              <div className="mt-4 bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
                <button
                  className="w-full flex items-center gap-2 px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
                  onClick={() => setShowReasoning(!showReasoning)}
                >
                  <span className="text-gray-400">
                    {showReasoning ? "▼" : "▶"}
                  </span>
                  <span className="text-base">💡</span>
                  <span>Show Reasoning</span>
                </button>

                {showReasoning && (
                  <div className="px-4 pb-4 border-t border-gray-200 pt-3">
                    {reasoningSummary && (
                      <div className="mb-3">
                        <div className="text-sm font-semibold text-gray-900 mb-2">
                          Reasoning:
                        </div>
                        <div className="text-[13px] text-gray-600 leading-relaxed">
                          {reasoningSummary}
                        </div>
                      </div>
                    )}

                    {reasoningTools && reasoningTools.length > 0 && (
                      <div className="flex gap-2 flex-wrap">
                        {reasoningTools.map((tool, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center gap-1.5 bg-indigo-50 text-indigo-700 border border-indigo-200 px-3 py-1.5 rounded-md text-xs font-medium"
                          >
                            <span className="text-sm">🔧</span>
                            <span>Tool: {tool.label}</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {sources && sources.length > 0 && (
              <div className="mt-3 flex gap-2 flex-wrap">
                {sources.map((source, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1.5 bg-gray-100 border border-gray-200 px-3 py-1.5 rounded-md text-xs text-gray-700"
                  >
                    <span className="text-sm">📄</span>
                    <span className="font-medium">{source.label}</span>
                    <span className="text-gray-400">·</span>
                    <span className="text-gray-600">{source.type}</span>
                  </span>
                ))}
              </div>
            )}

            <div className="flex gap-2 mt-3">
              <button
                className="border border-gray-300 rounded-md px-2.5 py-1.5 text-sm hover:bg-gray-50 hover:border-indigo-600 transition-all"
                title="Like"
                aria-label="Like"
              >
                👍
              </button>
              <button
                className="border border-gray-300 rounded-md px-2.5 py-1.5 text-sm hover:bg-gray-50 hover:border-indigo-600 transition-all"
                title="Dislike"
                aria-label="Dislike"
              >
                👎
              </button>
              <button
                className="border border-gray-300 rounded-md px-2.5 py-1.5 text-sm hover:bg-gray-50 hover:border-indigo-600 transition-all"
                title="Copy"
                aria-label="Copy message"
              >
                📋
              </button>
              <button
                className="border border-gray-300 rounded-md px-2.5 py-1.5 text-sm hover:bg-gray-50 hover:border-indigo-600 transition-all"
                title="Retry"
                aria-label="Retry"
              >
                ↻
              </button>
            </div>

            {suggestions && suggestions.length > 0 && (
              <div className="mt-4 flex flex-col gap-2">
                {suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    className="bg-white border border-gray-300 rounded-lg px-4 py-3 text-left text-sm text-gray-700 hover:border-indigo-600 hover:bg-indigo-50 transition-all flex items-center justify-between group"
                    onClick={() => onSuggestionClick?.(suggestion)}
                  >
                    <span>{suggestion}</span>
                    <span className="text-gray-400 group-hover:text-indigo-600 transition-colors">
                      →
                    </span>
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {message.role === "human" && (
        <div className="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
          <span className="text-lg">👤</span>
        </div>
      )}
    </div>
  );
};
