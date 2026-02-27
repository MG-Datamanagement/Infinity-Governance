import { IconType } from "react-icons/lib";

// Core Types
export interface Message {
  role: "human" | "ai";
  content: string;
  created_at: string;
  error: boolean;
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

// Enhanced API Response Types
export interface ToolDetail {
  tool: string;
  args: Record<string, any>;
  result_preview: string;
  source_label: string;
  source_type: string;
}

export interface ReasoningTool {
  label: string;
  icon: string;
  raw: string;
}

export interface ReasoningSource {
  label: string;
  icon: string;
  type: string;
}

export interface Source {
  label: string;
  type: string;
  pill: string;
  icon: string;
}

export interface ChatResponse {
  answer: string;
  reasoning?: string[];
  reasoning_summary?: string;
  reasoning_tools?: ReasoningTool[];
  reasoning_sources?: ReasoningSource[];
  sources?: Source[];
  tools_detail?: ToolDetail[];
  tools_used?: string[];
  agents_used?: string[];
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
  showAIPreferences: boolean;
  aiPreferences: AIPreferences;
}

export interface AIPreferences {
  multiAgentOrchestration: boolean;
  deepAnalysis: boolean;
  autoRemediation: boolean;
}

