import { describe, expect, it } from "vitest";
import {
  mapChatSession,
  mapChatMessage,
  mapWorkspace,
  summarizeWorkspaceState,
} from "./workspace-data";

describe("workspace-data mappers", () => {
  it("maps backend workspace and chat rows into UI state without seeded dummy fields", () => {
    expect(
      mapWorkspace({
        id: "ws-1",
        name: "Product",
        color: "#111111",
        icon: "P",
      }),
    ).toEqual({
      id: "ws-1",
      name: "Product",
      color: "#111111",
      icon: "P",
      description: "Workspace",
    });

    expect(
      mapChatSession({
        id: "chat-1",
        workspace_id: "ws-1",
        title: "Launch notes",
        updated_at: "2026-06-18T04:30:00.000Z",
      }),
    ).toEqual({
      id: "chat-1",
      workspaceId: "ws-1",
      title: "Launch notes",
      summary: "No messages yet",
      updatedAt: "Jun 18, 10:00",
      status: "idle",
    });
  });

  it("maps backend messages and derives the latest chat summary from real content", () => {
    const messages = [
      mapChatMessage(
        {
          id: "msg-1",
          role: "user",
          content: "Can we ship this release with pricing copy unresolved?",
          created_at: "2026-06-18T05:00:00.000Z",
        },
        "chat-1",
      ),
    ];

    expect(messages[0]).toEqual({
      id: "msg-1",
      chatId: "chat-1",
      role: "user",
      content: "Can we ship this release with pricing copy unresolved?",
      createdAt: "10:30",
    });

    expect(summarizeWorkspaceState([], messages)).toEqual({
      chatCount: 0,
      messageCount: 1,
      latestSummary: "Can we ship this release with pricing copy unresolved?",
    });
  });
});
