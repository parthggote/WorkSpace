export type Workspace = {
  id: string;
  name: string;
  color: string;
  icon: string;
  description: string;
};

export type ChatSession = {
  id: string;
  workspaceId: string;
  title: string;
  summary: string;
  updatedAt: string;
  status: "active" | "idle" | "archived";
};

export type ChatMessage = {
  id: string;
  chatId: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  citations?: Citation[];
};

export type Citation = {
  source: string;
  title: string;
  locator?: string | null;
  url?: string | null;
  chat_id?: string | null;
  message_id?: string | null;
  score?: number | null;
  excerpt?: string | null;
};

export type WorkspaceDocument = {
  id: string;
  filename: string;
  fileType: string;
  status: "uploaded" | "queued" | "processing" | "ready" | "failed" | string;
  error?: string | null;
  createdAt?: string;
  updatedAt?: string;
};

export type UsageSummary = {
  workspaceId: string;
  workspaceName: string;
  totalTokens: number;
  estimatedCostUsd: number;
};

export type StreamStatus = {
  id: string;
  kind: "status" | "reasoning_summary";
  content: string;
  createdAt: string;
};

export type ChatStreamRequest = {
  workspace_id: string;
  chat_id: string;
  message: string;
  document_ids?: string[];
  advanced_search?: boolean;
  force_web?: boolean;
  skip_web_prompt?: boolean;
};

export type FileAttachment = {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
};

export type ChatStreamEvent =
  | { type: "status"; content: string }
  | { type: "reasoning_summary"; content: string }
  | { type: "answer_delta"; content: string }
  | { type: "citations"; content: Citation[] }
  | { type: "action_required"; content: { action: string } }
  | { type: "error"; content: string }
  | { type: "done" };
