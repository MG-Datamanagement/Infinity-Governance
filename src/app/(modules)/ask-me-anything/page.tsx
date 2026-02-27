"use client";
import React, { useState, useEffect, useRef } from "react";
import { Sidebar } from "./components/Sidebar";
import { ChatHeader } from "./components/ChatHeader";
import { ChatMessage } from "./components/ChatMessage";
import { ChatInput } from "./components/ChatInput";
import { WelcomeScreen } from "./components/WelcomeScreen";
import { AgentModal, DatasetModal } from "./components/Modals";
import {
  Message,
  ChatSession,
  UIState,
  ReasoningTool,
  Source,
  ToolDetail,
} from "../../../types";
import { RiRobot2Line } from "react-icons/ri";
import { cn } from "@/lib/utils";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { LoadingFallback } from "@/components/Fallbacks";
import { chatApiServices } from "@/services/chatApiServices";
import { MOCK_AGENTS, MOCK_DATASETS } from "@/services/mock/chatMockApiService";

const AskMeAnything: React.FC = () => {
  // UI State
  const [uiState, setUIState] = useState<UIState>({
    isSidebarCollapsed: false,
    memoryEnabled: true,
    reasoningEnabled: true,
    showAgentModal: false,
    showDatasetModal: false,
    showReasoningPanel: false,
    selectedAgents: [],
    selectedDatasets: [],
    showAIPreferences: false,
    aiPreferences: {
      multiAgentOrchestration: false,
      deepAnalysis: false,
      autoRemediation: false,
    },
  });

  // Chat State
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isThinking, setIsThinking] = useState<boolean>(false);
  const [isHistoryLoading, setIsHistoryLoading] = useState<boolean>(false);
  const [isSessionLoading, setIsSessionLoading] = useState<boolean>(false);
  const [replyTo, setReplyTo] = useState<null | string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [agentSearchQuery, setAgentSearchQuery] = useState<string>("");
  const [datasetSearchQuery, setDatasetSearchQuery] = useState<string>("");

  // Response state - track enhanced responses for each message
  const [messageResponses, setMessageResponses] = useState<
    Map<
      number,
      {
        reasoning?: string[];
        reasoningSummary?: string;
        reasoningTools?: ReasoningTool[];
        sources?: Source[];
        toolsDetail?: ToolDetail[];
        suggestions?: string[];
      }
    >
  >(new Map());

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load history on mount
  useEffect(() => {
    loadHistory();
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadHistory = async () => {
    setIsHistoryLoading(true);
    try {
      const history = await chatApiServices.getHistory();
      setSessions(history.sessions);
    } catch (error) {
      console.error("Failed to load history:", error);
    } finally {
      setIsHistoryLoading(false);
    }
  };

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      role: "human",
      content,
      created_at: new Date().toISOString(),
      error: false,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsThinking(true);

    try {
      const response = await chatApiServices.sendMessage({
        message: content,
        session_id: currentSessionId,
        memory: uiState.memoryEnabled,
        reasoning: uiState.reasoningEnabled,
      });

      const aiMessage: Message = {
        role: "ai",
        content: response.answer,
        created_at: response.timestamp,
        error: false,
      };

      setMessages((prev) => [...prev, aiMessage]);

      // Store enhanced response data for the AI message
      setMessageResponses((prev) => {
        const newMap = new Map(prev);
        newMap.set(messages.length + 1, {
          reasoning: response.reasoning,
          reasoningSummary: response.reasoning_summary,
          reasoningTools: response.reasoning_tools,
          sources: response.sources,
          toolsDetail: response.tools_detail,
          suggestions: response.suggestions,
        });
        return newMap;
      });

      if (!currentSessionId) {
        setCurrentSessionId(response.session_id);
        loadHistory();
      }
    } catch (error) {
      console.error("Failed to send message:", error);
      const errorMessage: Message = {
        role: "ai",
        content: "Sorry, I encountered an error processing your request.",
        created_at: new Date().toISOString(),
        error: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsThinking(false);
    }
  };

  const handleEditMessage = async (
    messageIndex: number,
    newContent: string,
  ) => {
    // Remove all messages after the edited message
    const updatedMessages = messages.slice(0, messageIndex + 1);

    // Update the edited message content
    updatedMessages[messageIndex] = {
      ...updatedMessages[messageIndex],
      content: newContent,
    };

    setMessages(updatedMessages);

    // Clear responses after this message
    setMessageResponses((prev) => {
      const newMap = new Map(prev);
      // Remove all responses after the edited message
      Array.from(newMap.keys()).forEach((key) => {
        if (key > messageIndex) {
          newMap.delete(key);
        }
      });
      return newMap;
    });

    // Resend the edited message
    await handleSendMessage(newContent);
  };

  const handleNewChat = () => {
    setMessages([]);
    setCurrentSessionId(null);
    setMessageResponses(new Map());
    setUIState((prev) => ({
      ...prev,
      selectedAgents: [],
      selectedDatasets: [],
    }));
  };

  const handleSelectSession = async (sessionId: string) => {
    setIsSessionLoading(true);
    try {
      const sessionDetail = await chatApiServices.getSessionDetail(sessionId);
      setMessages(sessionDetail.messages);
      setCurrentSessionId(sessionId);
      setMessageResponses(new Map());
    } catch (error) {
      console.error("Failed to load session:", error);
    } finally {
      setIsSessionLoading(false);
    }
  };

  const handleToggleAgent = (agentId: string) => {
    setUIState((prev) => ({
      ...prev,
      selectedAgents: prev.selectedAgents.includes(agentId)
        ? prev.selectedAgents.filter((id) => id !== agentId)
        : [...prev.selectedAgents, agentId],
    }));
  };

  const handleToggleDataset = (datasetId: string) => {
    setUIState((prev) => ({
      ...prev,
      selectedDatasets: prev.selectedDatasets.includes(datasetId)
        ? prev.selectedDatasets.filter((id) => id !== datasetId)
        : [...prev.selectedDatasets, datasetId],
    }));
  };

  const handleToggleAIPreferences = () => {
    setUIState((prev) => ({
      ...prev,
      showAIPreferences: !prev.showAIPreferences,
    }));
  };

  const handleTogglePreference = (
    key: "multiAgentOrchestration" | "deepAnalysis" | "autoRemediation",
  ) => {
    setUIState((prev) => ({
      ...prev,
      aiPreferences: {
        ...prev.aiPreferences,
        [key]: !prev.aiPreferences[key],
      },
    }));
  };

  const showWelcome = messages.length === 0 && !isThinking;

  // Find the index of the last human message
  const lastHumanMessageIndex = messages.reduce((lastIndex, msg, index) => {
    return msg.role === "human" ? index : lastIndex;
  }, -1);

  return (
    <div className="flex h-[calc(100vh-58px)] bg-gray-50">
      <Sidebar
        isCollapsed={uiState.isSidebarCollapsed}
        sessions={sessions}
        currentSessionId={currentSessionId}
        onToggle={() =>
          setUIState((prev) => ({
            ...prev,
            isSidebarCollapsed: !prev.isSidebarCollapsed,
          }))
        }
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        isHistoryLoading={isHistoryLoading}
        onRetryFetchHistroy={loadHistory}
        isChatLoading={isSessionLoading}
      />

      <div className="flex-1 flex flex-col bg-white">
        <ChatHeader
          memoryEnabled={uiState.memoryEnabled}
          reasoningEnabled={uiState.reasoningEnabled}
          onToggleMemory={() =>
            setUIState((prev) => ({
              ...prev,
              memoryEnabled: !prev.memoryEnabled,
            }))
          }
          onToggleReasoning={() =>
            setUIState((prev) => ({
              ...prev,
              reasoningEnabled: !prev.reasoningEnabled,
            }))
          }
          onSettingsClick={() => console.log("Settings clicked")}
          onExpandClick={() => console.log("Expand clicked")}
          showAIPreferences={uiState.showAIPreferences}
          aiPreferences={uiState.aiPreferences}
          onToggleAIPreferences={handleToggleAIPreferences}
          onTogglePreference={handleTogglePreference}
        />

        <div className="flex-1 overflow-y-auto px-6 py-6">
          {showWelcome ? (
            <WelcomeScreen onPromptClick={handleSendMessage} />
          ) : (
            <div className="max-w-[900px]">
              {messages.map((message, idx) => {
                const responseData = messageResponses.get(idx);
                const isLatestHumanMessage =
                  message.role === "human" && idx === lastHumanMessageIndex;

                return (
                  <ChatMessage
                    key={idx}
                    message={message}
                    reasoning={responseData?.reasoning}
                    reasoningSummary={responseData?.reasoningSummary}
                    reasoningTools={responseData?.reasoningTools}
                    sources={responseData?.sources}
                    toolsDetail={responseData?.toolsDetail}
                    suggestions={responseData?.suggestions}
                    onSuggestionClick={handleSendMessage}
                    showReasoningToggle={message.role === "ai"}
                    onEditMessage={
                      isLatestHumanMessage
                        ? (newContent) => handleEditMessage(idx, newContent)
                        : undefined
                    }
                    isLatestHumanMessage={isLatestHumanMessage}
                    handleReplyTo={(replyTo: null | string) =>
                      setReplyTo(replyTo)
                    }
                  />
                );
              })}
              {isThinking && (
                <div className="flex gap-4 items-start">
                  <div className="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
                    <RiRobot2Line size={16} />
                  </div>
                  <div
                    className={cn(
                      "flex-1 max-w-[200px]",
                      "text-sm leading-relaxed whitespace-pre-wrap border border-gray-300 rounded-2xl rounded-bl-sm px-3 py-2 shadow-sm",
                    )}
                  >
                    <div className="flex items-center gap-1">
                      <span className="w-1 h-1 bg-indigo-400 rounded-full animate-bounce [animation-delay:0ms]"></span>
                      <span className="w-1 h-1 bg-indigo-400 rounded-full animate-bounce [animation-delay:100ms]"></span>
                      <span className="w-1 h-1 bg-indigo-400 rounded-full animate-bounce [animation-delay:400ms]"></span>
                      <span className="text-gray-600 font-normal text-sm mx-2">
                        Thinking...
                      </span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <ChatInput
          onSend={handleSendMessage}
          disabled={isThinking}
          selectedAgents={uiState.selectedAgents}
          selectedDatasets={uiState.selectedDatasets}
          onOpenAgentModal={() =>
            setUIState((prev) => ({ ...prev, showAgentModal: true }))
          }
          onOpenDatasetModal={() =>
            setUIState((prev) => ({ ...prev, showDatasetModal: true }))
          }
          onRemoveAgent={(id) => handleToggleAgent(id)}
          onRemoveDataset={(id) => handleToggleDataset(id)}
          isAgentModalOpen={uiState.showAgentModal}
          isDatasetModalOpen={uiState.showDatasetModal}
          replyTo={replyTo}
          handleReplyTo={(replyTo: null | string) => setReplyTo(replyTo)}
        />
      </div>

      <AgentModal
        isOpen={uiState.showAgentModal}
        agents={MOCK_AGENTS}
        selectedAgents={uiState.selectedAgents}
        onClose={() =>
          setUIState((prev) => ({ ...prev, showAgentModal: false }))
        }
        onToggleAgent={handleToggleAgent}
        searchQuery={agentSearchQuery}
        onSearchChange={setAgentSearchQuery}
      />

      <DatasetModal
        isOpen={uiState.showDatasetModal}
        datasets={MOCK_DATASETS}
        selectedDatasets={uiState.selectedDatasets}
        onClose={() =>
          setUIState((prev) => ({ ...prev, showDatasetModal: false }))
        }
        onToggleDataset={handleToggleDataset}
        searchQuery={datasetSearchQuery}
        onSearchChange={setDatasetSearchQuery}
      />
    </div>
  );
};

export default function AskMeAnythingPage() {
  return (
    <ErrorBoundary fallback={<LoadingFallback />}>
      <AskMeAnything />
    </ErrorBoundary>
  );
}
