import type {
  ChatMessage,
  ChatSession,
  UsageSummary,
  Workspace,
  WorkspaceDocument,
} from "@/lib/types";

import { getAuthToken } from "@/lib/api/auth-token";

const DEMO_USER_ID = "00000000-0000-0000-0000-000000000001";

type RequestOptions = {
  apiUrl?: string;
  token?: string;
};

type WorkspaceRow = {
  id: string;
  name: string;
  color?: string | null;
  icon?: string | null;
  description?: string | null;
};

type ChatRow = {
  id: string;
  workspace_id: string;
  title?: string | null;
  updated_at?: string | null;
};

type MessageRow = {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at?: string | null;
};

type DocumentRow = {
  id: string;
  filename: string;
  file_type?: string | null;
  status: string;
  error?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

type UsageRow = {
  workspace_id: string;
  workspace_name: string;
  total_tokens: number;
  estimated_cost_usd: number;
};

function baseUrl(apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000") {
  return apiUrl.replace(/\/$/, "");
}

function headers(token?: string) {
  return {
    Accept: "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : { "x-demo-user-id": DEMO_USER_ID }),
  };
}

async function requestJson<T>(path: string, options: RequestOptions & RequestInit = {}) {
  const { apiUrl, token, ...init } = options;
  const authToken = await getAuthToken(token);
  
  const response = await fetch(`${baseUrl(apiUrl)}/api${path}`, {
    ...init,
    headers: {
      ...headers(authToken),
      ...init.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API request failed with ${response.status}.`);
  }

  return (await response.json()) as T;
}

export function formatDateTime(value?: string | null) {
  if (!value) {
    return "No activity";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "No activity";
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatTime(value?: string | null) {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function mapWorkspace(row: WorkspaceRow): Workspace {
  return {
    id: row.id,
    name: row.name,
    color: row.color || "#111111",
    icon: row.icon || row.name.slice(0, 2).toUpperCase(),
    description: row.description || "Workspace",
  };
}

export function mapChatSession(row: ChatRow): ChatSession {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    title: row.title || "New chat",
    summary: "No messages yet",
    updatedAt: formatDateTime(row.updated_at),
    status: "idle",
  };
}

export function mapChatMessage(row: MessageRow, chatId: string): ChatMessage {
  return {
    id: row.id,
    chatId,
    role: row.role,
    content: row.content,
    createdAt: formatTime(row.created_at),
  };
}

export function mapDocument(row: DocumentRow): WorkspaceDocument {
  return {
    id: row.id,
    filename: row.filename,
    fileType: row.file_type || "file",
    status: row.status,
    error: row.error,
    createdAt: formatDateTime(row.created_at),
    updatedAt: formatDateTime(row.updated_at),
  };
}

export function mapUsage(row: UsageRow): UsageSummary {
  return {
    workspaceId: row.workspace_id,
    workspaceName: row.workspace_name,
    totalTokens: row.total_tokens,
    estimatedCostUsd: row.estimated_cost_usd,
  };
}

export function summarizeWorkspaceState(chats: ChatSession[], messages: ChatMessage[]) {
  return {
    chatCount: chats.length,
    messageCount: messages.length,
    latestSummary: messages.at(-1)?.content || "No messages yet",
  };
}

export async function listWorkspaces(options?: RequestOptions) {
  const rows = await requestJson<WorkspaceRow[]>("/workspaces", options);
  return rows.map(mapWorkspace);
}

export async function createWorkspace(name: string, options?: RequestOptions) {
  const row = await requestJson<WorkspaceRow>("/workspaces", {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name,
      color: "#111111",
      icon: name.slice(0, 2).toUpperCase(),
    }),
  });
  return mapWorkspace(row);
}

export async function updateWorkspace(workspaceId: string, name: string, options?: RequestOptions) {
  const row = await requestJson<WorkspaceRow>(`/workspaces/${workspaceId}`, {
    ...options,
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  return mapWorkspace(row);
}

export async function deleteWorkspace(workspaceId: string, options?: RequestOptions) {
  return requestJson<{ ok: boolean }>(`/workspaces/${workspaceId}`, {
    ...options,
    method: "DELETE",
  });
}

export async function listChats(workspaceId: string, options?: RequestOptions) {
  const rows = await requestJson<ChatRow[]>(`/workspaces/${workspaceId}/chats`, options);
  return rows.map(mapChatSession);
}

export async function createChat(workspaceId: string, title = "New chat", options?: RequestOptions) {
  const row = await requestJson<ChatRow>(`/workspaces/${workspaceId}/chats`, {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return mapChatSession(row);
}

export async function updateChat(workspaceId: string, chatId: string, title: string, options?: RequestOptions) {
  const row = await requestJson<ChatRow>(`/workspaces/${workspaceId}/chats/${chatId}`, {
    ...options,
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return mapChatSession(row);
}

export async function deleteChat(workspaceId: string, chatId: string, options?: RequestOptions) {
  return requestJson<{ ok: boolean }>(`/workspaces/${workspaceId}/chats/${chatId}`, {
    ...options,
    method: "DELETE",
  });
}

export async function listMessages(workspaceId: string, chatId: string, options?: RequestOptions) {
  const rows = await requestJson<MessageRow[]>(
    `/workspaces/${workspaceId}/chats/${chatId}/messages`,
    options,
  );
  return rows.map((row) => mapChatMessage(row, chatId));
}

export async function listDocuments(workspaceId: string, options?: RequestOptions) {
  const rows = await requestJson<DocumentRow[]>(`/workspaces/${workspaceId}/documents`, options);
  return rows.map(mapDocument);
}

export async function uploadDocument(workspaceId: string, file: File, options?: RequestOptions) {
  const formData = new FormData();
  formData.append("file", file);
  return requestJson<{ id?: string; status?: string; ok?: boolean; error?: string }>(
    `/workspaces/${workspaceId}/documents`,
    {
      ...options,
      method: "POST",
      body: formData,
    },
  );
}

export async function getUsage(options?: RequestOptions) {
  const rows = await requestJson<UsageRow[]>("/usage", options);
  return rows.map(mapUsage);
}
