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

export const useSendMessage = () => {
  return useMutation({
    mutationFn: (request: ChatRequest) => chatApiServices.sendMessage(request),
  });
};
