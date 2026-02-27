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

const USE_MOCK_DATA = false;

export const chatApiServices = {
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    return chatApiClient.post<ChatResponse>("/chat", request);
  },

  async getHistory(): Promise<HistoryResponse> {
    return chatApiClient.get<HistoryResponse>("/history");
  },

  async getSessionDetail(sessionId: string): Promise<SessionDetailResponse> {
    return chatApiClient.get<SessionDetailResponse>(`/history/${sessionId}`);
  },
};
