import { IconType } from "react-icons/lib";

// Core Types
export interface Message {
  role: 'human' | 'ai';
  content: string;
  created_at: string;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  last_active: string;
  message_count: number;
}

export interface HistoryResponse {
  total_sessions: number;
  sessions: ChatSession[];
}

export interface SessionDetailResponse {
  session_id: string;
  title: string;
  created_at: string;
  last_active: string;
  message_count: number;
  messages: Message[];
}

export interface ChatRequest {
  message: string;
  session_id: string | null;
  memory: boolean;
  reasoning: boolean;
}

export interface ChatResponse {
  answer: string;
  reasoning?: string[];
  sources?: string[];
  suggestions?: string[];
  session_id: string;
  timestamp: string;
  memory_enabled: boolean;
  reasoning_enabled: boolean;
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  icon: string | IconType;
  alert?: string;
  tag?: string;
  disabled: boolean;
}

export interface Dataset {
  id: string;
  name: string;
  type: string;
  columns: number;
  rows: number;
  selected?: boolean;
}

// UI State Types
export interface UIState {
  isSidebarCollapsed: boolean;
  memoryEnabled: boolean;
  reasoningEnabled: boolean;
  showAgentModal: boolean;
  showDatasetModal: boolean;
  showReasoningPanel: boolean;
  selectedAgents: string[];
  selectedDatasets: string[];
}