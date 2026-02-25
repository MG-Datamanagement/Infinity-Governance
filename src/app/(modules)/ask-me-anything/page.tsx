"use client";
import React, { useState, useEffect, useRef } from "react";
import { Sidebar } from "./components/Sidebar";
import { ChatHeader } from "./components/ChatHeader";
import { ChatMessage } from "./components/ChatMessage";
import { ChatInput } from "./components/ChatInput";
import { WelcomeScreen } from "./components/WelcomeScreen";
import { AgentModal, DatasetModal } from "./components/Modals";
import { chatAPI } from "./api";
import { MOCK_AGENTS, MOCK_DATASETS } from "./mockData";
import {
  Message,
  ChatSession,
  UIState,
  ReasoningTool,
  Source,
  ToolDetail,
} from "./types";

// const ChatBot: React.FC = () => {
//   // UI State
//   const [uiState, setUIState] = useState<UIState>({
//     isSidebarCollapsed: false,
//     memoryEnabled: true,
//     reasoningEnabled: true,
//     showAgentModal: false,
//     showDatasetModal: false,
//     showReasoningPanel: false,
//     selectedAgents: [],
//     selectedDatasets: [],
//   });

//   // Chat State
//   const [messages, setMessages] = useState<Message[]>([]);
//   const [sessions, setSessions] = useState<ChatSession[]>([]);
//   const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
//   const [isLoading, setIsLoading] = useState(false);
//   const [searchQuery, setSearchQuery] = useState("");
//   const [agentSearchQuery, setAgentSearchQuery] = useState("");
//   const [datasetSearchQuery, setDatasetSearchQuery] = useState("");

//   // Response state - track responses for each message
//   const [messageResponses, setMessageResponses] = useState<
//     Map<
//       number,
//       {
//         reasoning?: string[];
//         sources?: string[];
//         suggestions?: string[];
//       }
//     >
//   >(new Map());

//   const messagesEndRef = useRef<HTMLDivElement>(null);

//   // Load history on mount
//   useEffect(() => {
//     loadHistory();
//   }, []);

//   // Auto-scroll to bottom
//   useEffect(() => {
//     messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
//   }, [messages]);

//   const loadHistory = async () => {
//     try {
//       const history = await chatAPI.getHistory();
//       setSessions(history.sessions);
//     } catch (error) {
//       console.error("Failed to load history:", error);
//     }
//   };

//   const handleSendMessage = async (content: string) => {
//     const userMessage: Message = {
//       role: "human",
//       content,
//       created_at: new Date().toISOString(),
//     };

//     setMessages((prev) => [...prev, userMessage]);
//     setIsLoading(true);

//     try {
//       const response = await chatAPI.sendMessage({
//         message: content,
//         session_id: currentSessionId,
//         memory: uiState.memoryEnabled,
//         reasoning: uiState.reasoningEnabled,
//       });

//       const aiMessage: Message = {
//         role: "ai",
//         content: response.answer,
//         created_at: response.timestamp,
//       };

//       setMessages((prev) => [...prev, aiMessage]);

//       // Store response data for the AI message
//       setMessageResponses((prev) => {
//         const newMap = new Map(prev);
//         newMap.set(messages.length + 1, {
//           reasoning: response.reasoning,
//           sources: response.sources,
//           suggestions: response.suggestions,
//         });
//         return newMap;
//       });

//       if (!currentSessionId) {
//         setCurrentSessionId(response.session_id);
//         loadHistory();
//       }
//     } catch (error) {
//       console.error("Failed to send message:", error);
//       const errorMessage: Message = {
//         role: "ai",
//         content: "Sorry, I encountered an error processing your request.",
//         created_at: new Date().toISOString(),
//       };
//       setMessages((prev) => [...prev, errorMessage]);
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   const handleEditMessage = async (
//     messageIndex: number,
//     newContent: string,
//   ) => {
//     // Remove all messages after the edited message
//     const updatedMessages = messages.slice(0, messageIndex + 1);

//     // Update the edited message content
//     updatedMessages[messageIndex] = {
//       ...updatedMessages[messageIndex],
//       content: newContent,
//     };

//     setMessages(updatedMessages);

//     // Clear responses after this message
//     setMessageResponses((prev) => {
//       const newMap = new Map(prev);
//       // Remove all responses after the edited message
//       Array.from(newMap.keys()).forEach((key) => {
//         if (key > messageIndex) {
//           newMap.delete(key);
//         }
//       });
//       return newMap;
//     });

//     // Resend the edited message
//     await handleSendMessage(newContent);
//   };

//   const handleNewChat = () => {
//     setMessages([]);
//     setCurrentSessionId(null);
//     setMessageResponses(new Map());
//     setUIState((prev) => ({
//       ...prev,
//       selectedAgents: [],
//       selectedDatasets: [],
//     }));
//   };

//   const handleSelectSession = async (sessionId: string) => {
//     try {
//       const sessionDetail = await chatAPI.getSessionDetail(sessionId);
//       setMessages(sessionDetail.messages);
//       setCurrentSessionId(sessionId);
//       setMessageResponses(new Map());
//     } catch (error) {
//       console.error("Failed to load session:", error);
//     }
//   };

//   const handleToggleAgent = (agentId: string) => {
//     setUIState((prev) => ({
//       ...prev,
//       selectedAgents: prev.selectedAgents.includes(agentId)
//         ? prev.selectedAgents.filter((id) => id !== agentId)
//         : [...prev.selectedAgents, agentId],
//     }));
//   };

//   const handleToggleDataset = (datasetId: string) => {
//     setUIState((prev) => ({
//       ...prev,
//       selectedDatasets: prev.selectedDatasets.includes(datasetId)
//         ? prev.selectedDatasets.filter((id) => id !== datasetId)
//         : [...prev.selectedDatasets, datasetId],
//     }));
//   };

//   const showWelcome = messages.length === 0 && !isLoading;

//   // Find the index of the last human message
//   const lastHumanMessageIndex = messages.reduce((lastIndex, msg, index) => {
//     return msg.role === "human" ? index : lastIndex;
//   }, -1);

//   return (
//     <div className="flex h-[calc(100vh-58px)] bg-gray-50">
//       <Sidebar
//         isCollapsed={uiState.isSidebarCollapsed}
//         sessions={sessions}
//         currentSessionId={currentSessionId}
//         onToggle={() =>
//           setUIState((prev) => ({
//             ...prev,
//             isSidebarCollapsed: !prev.isSidebarCollapsed,
//           }))
//         }
//         onNewChat={handleNewChat}
//         onSelectSession={handleSelectSession}
//         searchQuery={searchQuery}
//         onSearchChange={setSearchQuery}
//       />

//       <div className="flex-1 flex flex-col bg-white">
//         <ChatHeader
//           memoryEnabled={uiState.memoryEnabled}
//           reasoningEnabled={uiState.reasoningEnabled}
//           onToggleMemory={() =>
//             setUIState((prev) => ({
//               ...prev,
//               memoryEnabled: !prev.memoryEnabled,
//             }))
//           }
//           onToggleReasoning={() =>
//             setUIState((prev) => ({
//               ...prev,
//               reasoningEnabled: !prev.reasoningEnabled,
//             }))
//           }
//           onSettingsClick={() => console.log("Settings clicked")}
//           onExpandClick={() => console.log("Expand clicked")}
//         />

//         <div className="flex-1 overflow-y-auto px-6 py-4">
//           {showWelcome ? (
//             <WelcomeScreen onPromptClick={handleSendMessage} />
//           ) : (
//             <div className="mx-auto pb-6">
//               {messages.map((message, idx) => {
//                 const responseData = messageResponses.get(idx);
//                 const isLatestHumanMessage =
//                   message.role === "human" && idx === lastHumanMessageIndex;

//                 return (
//                   <ChatMessage
//                     key={idx}
//                     message={message}
//                     reasoning={responseData?.reasoning}
//                     sources={responseData?.sources}
//                     suggestions={responseData?.suggestions}
//                     onSuggestionClick={handleSendMessage}
//                     showReasoningToggle={message.role === "ai"}
//                     onEditMessage={
//                       isLatestHumanMessage
//                         ? (newContent) => handleEditMessage(idx, newContent)
//                         : undefined
//                     }
//                     isLatestHumanMessage={isLatestHumanMessage}
//                   />
//                 );
//               })}
//               {isLoading && (
//                 <div className="flex gap-4 mb-6 items-start">
//                   <div className="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
//                     <span className="text-lg">🤖</span>
//                   </div>
//                   <div className="flex-1 max-w-[700px]">
//                     <div className="flex gap-1.5 py-3">
//                       <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]"></span>
//                       <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:200ms]"></span>
//                       <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:400ms]"></span>
//                     </div>
//                   </div>
//                 </div>
//               )}
//               <div ref={messagesEndRef} />
//             </div>
//           )}
//         </div>

//         <ChatInput
//           onSend={handleSendMessage}
//           disabled={isLoading}
//           selectedAgents={uiState.selectedAgents}
//           selectedDatasets={uiState.selectedDatasets}
//           onOpenAgentModal={() =>
//             setUIState((prev) => ({ ...prev, showAgentModal: true }))
//           }
//           onOpenDatasetModal={() =>
//             setUIState((prev) => ({ ...prev, showDatasetModal: true }))
//           }
//           onRemoveAgent={(id) => handleToggleAgent(id)}
//           onRemoveDataset={(id) => handleToggleDataset(id)}
//           isDatasetModalOpen={uiState?.showDatasetModal}
//           isAgentModalOpen={uiState?.showAgentModal}
//         />
//       </div>

//       <AgentModal
//         isOpen={uiState.showAgentModal}
//         agents={MOCK_AGENTS}
//         selectedAgents={uiState.selectedAgents}
//         onClose={() =>
//           setUIState((prev) => ({ ...prev, showAgentModal: false }))
//         }
//         onToggleAgent={handleToggleAgent}
//         searchQuery={agentSearchQuery}
//         onSearchChange={setAgentSearchQuery}
//       />

//       <DatasetModal
//         isOpen={uiState.showDatasetModal}
//         datasets={MOCK_DATASETS}
//         selectedDatasets={uiState.selectedDatasets}
//         onClose={() =>
//           setUIState((prev) => ({ ...prev, showDatasetModal: false }))
//         }
//         onToggleDataset={handleToggleDataset}
//         searchQuery={datasetSearchQuery}
//         onSearchChange={setDatasetSearchQuery}
//       />
//     </div>
//   );
// };

// export default ChatBot;

export const AskMeAnything: React.FC = () => {
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
  });

  // Chat State
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [agentSearchQuery, setAgentSearchQuery] = useState("");
  const [datasetSearchQuery, setDatasetSearchQuery] = useState("");

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
    try {
      const history = await chatAPI.getHistory();
      setSessions(history.sessions);
    } catch (error) {
      console.error("Failed to load history:", error);
    }
  };

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      role: "human",
      content,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await chatAPI.sendMessage({
        message: content,
        session_id: currentSessionId,
        memory: uiState.memoryEnabled,
        reasoning: uiState.reasoningEnabled,
      });

      const aiMessage: Message = {
        role: "ai",
        content: response.answer,
        created_at: response.timestamp,
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
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
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
    try {
      const sessionDetail = await chatAPI.getSessionDetail(sessionId);
      setMessages(sessionDetail.messages);
      setCurrentSessionId(sessionId);
      setMessageResponses(new Map());
    } catch (error) {
      console.error("Failed to load session:", error);
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

  const showWelcome = messages.length === 0 && !isLoading;

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
        />

        <div className="flex-1 overflow-y-auto px-6 py-6">
          {showWelcome ? (
            <WelcomeScreen onPromptClick={handleSendMessage} />
          ) : (
            <div className="max-w-[900px] mx-auto pb-6">
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
                  />
                );
              })}
              {isLoading && (
                <div className="flex gap-4 mb-6 items-start">
                  <div className="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
                    <span className="text-lg">🤖</span>
                  </div>
                  <div className="flex-1 max-w-[700px]">
                    <div className="flex gap-1.5 py-3">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]"></span>
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:200ms]"></span>
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:400ms]"></span>
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
          disabled={isLoading}
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

export default AskMeAnything;
