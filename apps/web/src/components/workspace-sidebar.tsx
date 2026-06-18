import { Clock3, MessageCircle, Pencil, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import type { ChatSession, Workspace } from "@/lib/types";

type WorkspaceSidebarProps = {
  className?: string;
  workspaces: Workspace[];
  activeWorkspaceId: string;
  sessions: ChatSession[];
  activeChatId: string;
  isLoading?: boolean;
  onSelectWorkspace: (workspaceId: string) => void;
  onSelectChat: (chatId: string) => void;
  onCreateWorkspace: () => void;
  onCreateChat: () => void;
  onEditWorkspace: (workspace: Workspace) => void;
  onDeleteWorkspace: (workspace: Workspace) => void;
  onEditChat: (session: ChatSession) => void;
  onDeleteChat: (session: ChatSession) => void;
};

export function WorkspaceSidebar({
  className,
  workspaces,
  activeWorkspaceId,
  sessions,
  activeChatId,
  isLoading,
  onSelectWorkspace,
  onSelectChat,
  onCreateWorkspace,
  onCreateChat,
  onEditWorkspace,
  onDeleteWorkspace,
  onEditChat,
  onDeleteChat,
}: WorkspaceSidebarProps) {
  const activeWorkspace = workspaces.find((workspace) => workspace.id === activeWorkspaceId);

  return (
    <aside className={cn("flex h-full min-h-0 w-full flex-col border-r border-[#e6e6e6] bg-[#f4f4f4]", className)}>
      <div className="border-b border-[#e6e6e6] px-3 py-3">
        <div className="flex items-center justify-between gap-2 px-1">
          <div className="min-w-0">
            <p className="text-[15px] font-semibold text-[#1f1f1f]">Workspaces</p>
            <p className="truncate text-[12px] text-muted-foreground">
              {activeWorkspace?.name ?? "No workspace selected"}
            </p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={onCreateWorkspace}
            disabled={isLoading}
            aria-label="Create workspace"
          >
            <Plus className="h-4 w-4" aria-hidden />
          </Button>
        </div>

        <div className="mt-3 grid grid-cols-1 gap-1">
          {workspaces.map((workspace) => {
            const isActive = workspace.id === activeWorkspaceId;

            return (
              <div
                key={workspace.id}
                className={cn(
                  "group flex items-center gap-1 rounded-md",
                  isActive && "bg-[#dedede] hover:bg-[#dedede]",
                )}
              >
                <button
                  type="button"
                  onClick={() => onSelectWorkspace(workspace.id)}
                  className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-2 py-2 text-left"
                >
                  <span
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold text-white"
                    style={{ backgroundColor: workspace.color }}
                  >
                    {workspace.icon.slice(0, 2)}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-[14px] font-medium">{workspace.name}</span>
                    <span className="block truncate text-[12px] text-muted-foreground">
                      {workspace.description}
                    </span>
                  </span>
                </button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 shrink-0 opacity-70 hover:opacity-100"
                  onClick={() => onEditWorkspace(workspace)}
                  aria-label={`Rename ${workspace.name}`}
                >
                  <Pencil className="h-3.5 w-3.5" aria-hidden />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 shrink-0 opacity-70 hover:opacity-100"
                  onClick={() => onDeleteWorkspace(workspace)}
                  aria-label={`Delete ${workspace.name}`}
                >
                  <Trash2 className="h-3.5 w-3.5" aria-hidden />
                </Button>
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex h-12 shrink-0 items-center justify-between px-4">
          <div>
            <p className="text-[15px] font-semibold text-[#1f1f1f]">Chats</p>
            <p className="text-[12px] text-muted-foreground">Inside this workspace</p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={onCreateChat}
            disabled={isLoading || !activeWorkspace}
            aria-label="Create chat"
          >
            <Plus className="h-4 w-4" aria-hidden />
          </Button>
        </div>

        <ScrollArea className="min-h-0 flex-1 px-2">
          <div className="space-y-1 pb-3">
            {sessions.length > 0 ? (
              sessions.map((session) => {
                const isActive = session.id === activeChatId;

                return (
                  <div
                    key={session.id}
                    className={cn(
                      "group flex items-start gap-1 rounded-md",
                      isActive && "bg-white shadow-sm hover:bg-white",
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => onSelectChat(session.id)}
                      className="flex min-w-0 flex-1 items-start gap-3 rounded-md px-3 py-3 text-left"
                    >
                      <MessageCircle className="h-4 w-4" aria-hidden />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[14px] font-medium">
                          {session.title}
                        </span>
                        <span className="block truncate text-[12px] text-muted-foreground">
                          {session.summary}
                        </span>
                        <span className="mt-1 flex items-center gap-1 text-[11px] text-muted-foreground">
                          <Clock3 className="h-3 w-3" aria-hidden />
                          {session.updatedAt}
                        </span>
                      </span>
                    </button>
                    <div className="flex shrink-0 pt-2">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 opacity-70 hover:opacity-100"
                        onClick={() => onEditChat(session)}
                        aria-label={`Rename ${session.title}`}
                      >
                        <Pencil className="h-3.5 w-3.5" aria-hidden />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 opacity-70 hover:opacity-100"
                        onClick={() => onDeleteChat(session)}
                        aria-label={`Delete ${session.title}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" aria-hidden />
                      </Button>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="mx-2 rounded-md border border-dashed border-[#d8d8d8] bg-white px-3 py-4 text-sm leading-6 text-muted-foreground">
                {activeWorkspace
                  ? "No chats yet. Create one to start using workspace memory."
                  : "Create a workspace before starting chats."}
              </div>
            )}
          </div>
        </ScrollArea>
      </div>
    </aside>
  );
}
