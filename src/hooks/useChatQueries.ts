import { useQuery, useMutation } from "@tanstack/react-query";
import { chatApiServices } from "@/services/chatApiServices";
import { ChatRequest } from "@/types";

export const useChatHistory = () => {
  return useQuery({
    queryKey: ["chat-history"],
    queryFn: chatApiServices.getHistory,
  });
};

export const useSessionDetail = (sessionId: string) => {
  return useQuery({
    queryKey: ["chat-session-detail", sessionId],
    queryFn: () => chatApiServices.getSessionDetail(sessionId),
    enabled: !!sessionId,
  });
};

export const useSendMessage = (
  request: ChatRequest,
  agentNames: string,
  datasetNames: string,
) => {
  return useMutation({
    mutationFn: () =>
      chatApiServices.sendMessage(request, agentNames, datasetNames),
  });
};
