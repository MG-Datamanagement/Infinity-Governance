import { chatApiClient } from "@/lib/api-clients/chatApiClient";
import { dashboardApiClient } from "@/lib/api-clients/dashboardApiClient";
import {
  ChatRequest,
  ChatResponse,
  HistoryResponse,
  SessionDetailResponse,
  NewChatbotResponse,
} from "@/types";

export const chatApiServices = {
  async sendMessage(
    request: ChatRequest,
    agentNames: string,
    datasetNames: string,
  ): Promise<ChatResponse> {
    console.log(request, agentNames, datasetNames);
    return chatApiClient.post<ChatResponse>(
      `/chat/${agentNames}/${datasetNames}`,
      request,
    );
  },

  async sendNewChatbotMessage(
    query: string,
    sessionId: string | null,
    agentNames: string,
    tableNames: string,
    reasoning: "on" | "off" = "on",
    memory: "on" | "off" = "on",
  ): Promise<NewChatbotResponse> {
    return dashboardApiClient.post<NewChatbotResponse>(
      "/chatbot",
      {
        query,
        session_id: sessionId || "1001", // Fallback for testing if null
        reasoning,
        memory,
      },
      {
        params: {
          agent_names: agentNames,
          table_names: tableNames,
        },
      },
    );
  },

  async getHistory(): Promise<HistoryResponse> {
    return chatApiClient.get<HistoryResponse>("/history");
  },

  async getSessionDetail(sessionId: string): Promise<SessionDetailResponse> {
    return chatApiClient.get<SessionDetailResponse>(`/history/${sessionId}`);
  },
};
