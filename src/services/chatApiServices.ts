import { chatApiClient } from "@/lib/api-clients/chatApiClient";
import {
  MOCK_CHAT_RESPONSE,
  MOCK_HISTORY,
  MOCK_SESSION_DETAIL,
} from "@/services/mock/chatMockApiService";
import {
  ChatRequest,
  ChatResponse,
  HistoryResponse,
  SessionDetailResponse,
} from "@/types";

export const chatApiServices = {
  async sendMessage(
    request: ChatRequest,
    agentNames: string,
    datasetNames: string,
  ): Promise<ChatResponse> {
    console.log(request, agentNames, datasetNames)
    return chatApiClient.post<ChatResponse>(
      `/chat/${agentNames}/${datasetNames}`,
      request,
    );
  },

  async getHistory(): Promise<HistoryResponse> {
    return chatApiClient.get<HistoryResponse>("/history");
  },

  async getSessionDetail(sessionId: string): Promise<SessionDetailResponse> {
    return chatApiClient.get<SessionDetailResponse>(`/history/${sessionId}`);
  },
};
