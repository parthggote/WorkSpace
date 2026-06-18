import type { ChatStreamEvent, ChatStreamRequest } from "@/lib/types";
import { getAuthToken } from "@/lib/api/auth-token";

const DEMO_USER_ID = "00000000-0000-0000-0000-000000000001";

type StreamChatOptions = {
  apiUrl?: string;
  token?: string;
  signal?: AbortSignal;
  onEvent: (event: ChatStreamEvent) => void;
};

export function parseSseChunk(chunk: string): ChatStreamEvent[] {
  return chunk
    .split(/\n\n|\r\n\r\n/)
    .map((eventBlock) => {
      const dataLines = eventBlock
        .split(/\r?\n/)
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.replace(/^data:\s?/, ""));

      if (dataLines.length === 0) {
        return null;
      }

      try {
        return JSON.parse(dataLines.join("\n")) as ChatStreamEvent;
      } catch {
        return {
          type: "error",
          content: "Received a streaming event that could not be parsed.",
        } satisfies ChatStreamEvent;
      }
    })
    .filter((event): event is ChatStreamEvent => event !== null);
}

export async function streamChat(
  payload: ChatStreamRequest,
  { apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000", token, signal, onEvent }: StreamChatOptions,
) {
  if (!apiUrl) {
    throw new Error("NEXT_PUBLIC_API_URL is required to stream chat responses.");
  }

  const authToken = await getAuthToken(token);

  const response = await fetch(`${apiUrl.replace(/\/$/, "")}/api/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : { "x-demo-user-id": DEMO_USER_ID }),
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Chat stream failed with ${response.status}.`);
  }

  if (!response.body) {
    throw new Error("Chat stream response did not include a readable body.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const boundary = Math.max(buffer.lastIndexOf("\n\n"), buffer.lastIndexOf("\r\n\r\n"));

    if (boundary === -1) {
      continue;
    }

    const complete = buffer.slice(0, boundary);
    buffer = buffer.slice(boundary).trimStart();
    parseSseChunk(complete).forEach(onEvent);
  }

  if (buffer.trim()) {
    parseSseChunk(buffer).forEach(onEvent);
  }
}
