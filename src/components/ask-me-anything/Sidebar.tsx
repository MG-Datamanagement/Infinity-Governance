import React, { useRef } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Search,
  Plus,
  Plug,
  History,
  MessageSquarePlusIcon,
  Trash2Icon,
  Loader2,
} from "lucide-react";
import { cn } from "../../lib/utils";
import { ChatSession } from "@/types";
import { IoRefreshSharp } from "react-icons/io5";

interface SidebarProps {
  isCollapsed: boolean;
  sessions: ChatSession[];
  currentSessionId: string | null;
  onToggle: () => void;
  onNewChat: () => void;
  onSelectSession: (sessionId: string) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onRetryFetchHistroy: () => void;
  isHistoryLoading: boolean;
  isChatLoading: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isCollapsed,
  sessions,
  currentSessionId,
  onToggle,
  onNewChat,
  onSelectSession,
  searchQuery,
  onSearchChange,
  onRetryFetchHistroy,
  isHistoryLoading,
  isChatLoading,
}) => {
  const filteredSessions = sessions.filter((session) =>
    session.title.toLowerCase().includes(searchQuery.toLowerCase()),
  );
  const chatHistorySeacrhRef = useRef<HTMLInputElement>(null);

  return (
    <aside
      className={cn(
        "bg-white border-r border-gray-200 flex flex-col gap-1 transition-all duration-300 relative",
        isCollapsed ? "w-[52px]" : "w-60",
      )}
    >
      {/* Toggle Button */}
      <button
        onClick={onToggle}
        className={cn(
          "absolute w-6 h-6 bg-white border border-gray-200 rounded-full flex items-center justify-center hover:bg-gray-50 z-20",
          isCollapsed ? "top-12 left-11" : "top-12 left-[230px]",
        )}
      >
        {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>

      {/* New Chat */}
      <div className={cn(isCollapsed ? "px-2 py-1.5" : "p-3")}>
        <button
          onClick={onNewChat}
          className={cn(
            "w-full bg-indigo-600 text-white rounded-md p-2.5 text-sm font-semibold flex items-center justify-center gap-2 hover:bg-indigo-700 transition-colors",
            "p-2",
          )}
          title={isCollapsed ? "New Chat" : ""}
        >
          <div>
            <MessageSquarePlusIcon size={16} />
          </div>
          {!isCollapsed && <span>New Chat</span>}
        </button>
      </div>

      {/* Search */}
      <div className={cn(isCollapsed ? "px-2 py-1.5" : "px-3 py-1")}>
        <button
          onClick={(event) => {
            event?.preventDefault();
            if (isCollapsed) {
              onToggle();
              chatHistorySeacrhRef.current &&
                chatHistorySeacrhRef.current.focus();
            }
          }}
          className={cn(
            "w-full flex justify-center items-center rounded-md text-sm outline-none focus:border-indigo-600",
            "border border-gray-300",
            "px-3 py-2",
          )}
        >
          <div>
            <Search size={16} className="text-gray-500 font-bold" />
          </div>
          {!isCollapsed && (
            <input
              type="text"
              ref={chatHistorySeacrhRef}
              placeholder="Search chats..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="border-none outline-none shadow-none px-2 w-full"
            />
          )}
        </button>
      </div>

      {/* History */}
      <div
        className={cn(
          "flex-1 overflow-y-auto space-y-1",
          isCollapsed ? "px-2 py-1.5" : "p-2",
        )}
      >
        <div>
          {!filteredSessions.length && !isHistoryLoading ? (
            <button
              title="Refetch History"
              onClick={(event) => {
                event?.stopPropagation();
                onRetryFetchHistroy();
              }}
              className={cn(
                "w-full flex justify-between items-center",
                isCollapsed
                  ? "border border-gray-300 rounded-md p-2 hover:text-indigo-600"
                  : "border-none p-1",
              )}
            >
              {!isCollapsed && (
                <div className="text-xs font-semibold text-gray-500 tracking-wide">
                  History
                </div>
              )}
              <IoRefreshSharp size={16} className="text-gray-600 font-bold" />
            </button>
          ) : (
            <button
              title="Chat History"
              onClick={(event) => {
                event?.stopPropagation();
                isCollapsed && onToggle();
              }}
              className={cn(
                "w-full flex justify-between items-center",
                isCollapsed
                  ? "border border-gray-300 rounded-md p-2 focus:border-indigo-600"
                  : "border-none p-1",
              )}
            >
              {!isCollapsed && (
                <div className="text-xs font-semibold text-gray-500 tracking-wide">
                  History
                </div>
              )}
              {isHistoryLoading ? (
                <Loader2 size={16} className="text-gray-500 animate-spin" />
              ) : (
                <History size={16} className="text-gray-500 font-bold" />
              )}
            </button>
          )}
        </div>

        {!isCollapsed ? (
          <div className="space-y-1">
            {filteredSessions.map((session) => (
              <button
                key={session.id}
                onClick={() => onSelectSession(session.id)}
                title={isCollapsed ? session.title : ""}
                className={cn(
                  "w-full flex items-center rounded-md px-3 py-2 text-left text-sm transition-colors truncate",
                  currentSessionId === session.id
                    ? "bg-indigo-50 text-indigo-600"
                    : "hover:bg-gray-100",
                  isCollapsed && "justify-center",
                  "group",
                )}
              >
                <div className="flex justify-between items-center w-full">
                  {!isCollapsed && (
                    <span className="text-[13px] text-gray-700 truncate max-w-52 shrink-1">
                      {session.title}
                    </span>
                  )}
                  {!isCollapsed && (
                    <button
                      onClick={(event) => event.stopPropagation()}
                      className="hidden group-hover:block rounded-sm"
                    >
                      <Trash2Icon
                        size={14}
                        className="text-gray-600 hover:text-red-600"
                      />
                    </button>
                  )}
                  {/* {isChatLoading &&
                    !isCollapsed &&
                    currentSessionId !== session.id && (
                      <button
                        onClick={(event) => event.stopPropagation()}
                        className="rounded-sm"
                      >
                        <Loader2
                          size={16}
                          className="text-indigo-600 animate-spin"
                        />
                      </button>
                    )} */}
                </div>
              </button>
            ))}
          </div>
        ) : null}
      </div>

      {/* Footer */}
      <div className="border-t border-gray-200 p-3">
        <div
          className={cn(
            "flex items-center gap-2 text-xs text-gray-500",
            isCollapsed && "justify-center",
          )}
          title={isCollapsed ? "Connected to 8 sources" : ""}
        >
          <Plug size={14} />
          {isCollapsed ? 8 : <span>Connected to 8 sources</span>}
        </div>
      </div>
    </aside>
  );
};
