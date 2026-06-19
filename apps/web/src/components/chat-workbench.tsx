"use client";

import {
  AlertTriangle,
  BarChart3,
  ChevronDown,
  FileText,
  GripVertical,
  Library,
  LogOut,
  Menu,
  MessageCircle,
  PanelRight,
  Settings,
} from "lucide-react";
import { type CSSProperties, type FormEvent, type PointerEvent as ReactPointerEvent, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";
import { ChatThread } from "@/components/chat-thread";
import { CitationsPanel } from "@/components/citations-panel";
import { DocumentUpload } from "@/components/document-upload";
import { MessageComposer } from "@/components/message-composer";
import { ReasoningPanel } from "@/components/reasoning-panel";
import { UsagePanel } from "@/components/usage-panel";
import { WorkspaceSidebar } from "@/components/workspace-sidebar";
import { streamChat } from "@/lib/api/chat-stream";
import {
  createChat,
  createWorkspace,
  deleteChat,
  deleteWorkspace,
  getUsage,
  listChats,
  listDocuments,
  listMessages,
  listWorkspaces,
  updateChat,
  updateWorkspace,
  uploadDocument,
} from "@/lib/api/workspace-data";
import type {
  ChatMessage,
  ChatAttachment,
  ChatSession,
  FileAttachment,
  Citation,
  StreamStatus,
  UsageSummary,
  Workspace,
  WorkspaceDocument,
} from "@/lib/types";
import { createClient } from "@/lib/supabase/client";
import { type User } from "@supabase/supabase-js";

type SupportTabsProps = {
  statuses: StreamStatus[];
  isStreaming: boolean;
  hasAnswerStarted: boolean;
  hasError: boolean;
  citations: Citation[];
  documents: WorkspaceDocument[];
  disabled: boolean;
  isUploading: boolean;
  usage: UsageSummary[];
  onFilesSelected: (files: File[]) => void;
  onRefreshDocuments: () => void;
};

function SupportTabs({
  statuses,
  isStreaming,
  hasAnswerStarted,
  hasError,
  citations,
  documents,
  disabled,
  isUploading,
  usage,
  onFilesSelected,
  onRefreshDocuments,
}: SupportTabsProps) {
  return (
    <Tabs defaultValue="activity" className="flex h-full min-h-0 flex-col">
      <TabsList className="grid w-full shrink-0 grid-cols-4 bg-[#f3f3f3]">
        <TabsTrigger value="activity">Activity</TabsTrigger>
        <TabsTrigger value="sources" className="gap-1.5">
          <Library className="h-3.5 w-3.5" aria-hidden />
          <span className="hidden sm:inline xl:inline">Sources</span>
        </TabsTrigger>
        <TabsTrigger value="docs" className="gap-1.5">
          <FileText className="h-3.5 w-3.5" aria-hidden />
          <span className="hidden sm:inline xl:inline">Docs</span>
        </TabsTrigger>
        <TabsTrigger value="usage" className="gap-1.5">
          <BarChart3 className="h-3.5 w-3.5" aria-hidden />
          <span className="hidden sm:inline xl:inline">Usage</span>
        </TabsTrigger>
      </TabsList>
      <TabsContent value="activity" className="min-h-0 flex-1">
        <ReasoningPanel
          statuses={statuses}
          isStreaming={isStreaming}
          hasAnswerStarted={hasAnswerStarted}
          hasError={hasError}
        />
      </TabsContent>
      <TabsContent value="sources" className="min-h-0 flex-1">
        <CitationsPanel citations={citations} />
      </TabsContent>
      <TabsContent value="docs" className="min-h-0 flex-1">
        <DocumentUpload
          documents={documents}
          disabled={disabled}
          isUploading={isUploading}
          onFilesSelected={onFilesSelected}
          onRefresh={onRefreshDocuments}
        />
      </TabsContent>
      <TabsContent value="usage" className="min-h-0 flex-1">
        <UsagePanel usage={usage} />
      </TabsContent>
    </Tabs>
  );
}

export function ChatWorkbench() {
  const { toast } = useToast();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user);
    });
  }, []);

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [visibleSessions, setVisibleSessions] = useState<ChatSession[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState("");
  const [activeChatId, setActiveChatId] = useState("");
  const [pendingWebSearch, setPendingWebSearch] = useState<{ message: string; options: { advancedSearch: boolean; forceWeb: boolean } } | null>(null);
  const [dialogForceWeb, setDialogForceWeb] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [statuses, setStatuses] = useState<StreamStatus[]>([]);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [documents, setDocuments] = useState<WorkspaceDocument[]>([]);
  const [usage, setUsage] = useState<UsageSummary[]>([]);
  const [streamingAnswer, setStreamingAnswer] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [supportPanelWidth, setSupportPanelWidth] = useState(360);
  const [createDialog, setCreateDialog] = useState<"workspace" | "chat" | null>(null);
  const [manageDialog, setManageDialog] = useState<
    | { action: "edit" | "delete"; type: "workspace"; item: Workspace }
    | { action: "edit" | "delete"; type: "chat"; item: ChatSession }
    | null
  >(null);
  const [isProfileDialogOpen, setIsProfileDialogOpen] = useState(false);
  const [profileDialogView, setProfileDialogView] = useState<"menu" | "settings">("menu");
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const [isMobileToolsOpen, setIsMobileToolsOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [manageName, setManageName] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [isManaging, setIsManaging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const documentIdsRef = useRef<string[]>([]);
  const documentPollTimeoutMs = 45_000;

  const activeWorkspace = workspaces.find((workspace) => workspace.id === activeWorkspaceId);
  const activeSession =
    visibleSessions.find((session) => session.id === activeChatId) ?? visibleSessions[0];
  const visibleMessages = activeSession
    ? messages.filter((message) => message.chatId === activeSession.id)
    : [];

  function reportError(title: string, fallback: string, cause: unknown) {
    const message = cause instanceof Error ? cause.message : fallback;
    setError(message);
    toast({ title, description: message, variant: "destructive" });
  }

  useEffect(() => {
    let isMounted = true;

    async function loadInitialData() {
      setIsLoading(true);
      setError(null);

      try {
        const nextWorkspaces = await listWorkspaces();
        if (!isMounted) {
          return;
        }

        setWorkspaces(nextWorkspaces);
        const firstWorkspaceId = nextWorkspaces[0]?.id ?? "";
        setActiveWorkspaceId(firstWorkspaceId);

        if (!firstWorkspaceId) {
          setVisibleSessions([]);
          setMessages([]);
          setDocuments([]);
          setUsage([]);
          return;
        }

        const [nextChats, nextDocuments, nextUsage] = await Promise.all([
          listChats(firstWorkspaceId),
          listDocuments(firstWorkspaceId),
          getUsage(),
        ]);

        if (!isMounted) {
          return;
        }

        setVisibleSessions(nextChats);
        setDocuments(nextDocuments);
        documentIdsRef.current = nextDocuments.map((document) => document.id);
        setUsage(nextUsage);
        const firstChatId = nextChats[0]?.id ?? "";
        setActiveChatId(firstChatId);
        setMessages(firstChatId ? await listMessages(firstWorkspaceId, firstChatId) : []);
      } catch (loadError) {
        if (isMounted) {
          reportError("Could not load workspace data", "Unable to load workspace data.", loadError);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadInitialData();

    return () => {
      isMounted = false;
    };
  }, []);

  async function selectWorkspace(workspaceId: string) {
    setActiveWorkspaceId(workspaceId);
    setActiveChatId("");
    setVisibleSessions([]);
    setMessages([]);
    setDocuments([]);
    setCitations([]);
    setStatuses([]);
    setStreamingAnswer("");
    setError(null);

    try {
      const [nextChats, nextDocuments] = await Promise.all([
        listChats(workspaceId),
        listDocuments(workspaceId),
      ]);
      const nextChatId = nextChats[0]?.id ?? "";
      setVisibleSessions(nextChats);
      setDocuments(nextDocuments);
      documentIdsRef.current = nextDocuments.map((document) => document.id);
      setActiveChatId(nextChatId);
      setMessages(nextChatId ? await listMessages(workspaceId, nextChatId) : []);
    } catch (loadError) {
      reportError("Could not load workspace", "Unable to load workspace.", loadError);
    }
  }

  async function selectChat(chatId: string) {
    if (!activeWorkspace) {
      return;
    }

    setActiveChatId(chatId);
    setStreamingAnswer("");
    setCitations([]);
    setStatuses([]);
    setError(null);

    try {
      setMessages(await listMessages(activeWorkspace.id, chatId));
    } catch (loadError) {
      reportError("Could not load chat", "Unable to load chat.", loadError);
    }
  }

  function openCreateWorkspaceDialog() {
    setCreateName("New workspace");
    setCreateDialog("workspace");
  }

  function openCreateChatDialog() {
    setCreateName("New chat");
    setCreateDialog("chat");
  }

  function openEditWorkspaceDialog(workspace: Workspace) {
    setManageName(workspace.name);
    setManageDialog({ action: "edit", type: "workspace", item: workspace });
  }

  function openDeleteWorkspaceDialog(workspace: Workspace) {
    setManageName(workspace.name);
    setManageDialog({ action: "delete", type: "workspace", item: workspace });
  }

  function openEditChatDialog(session: ChatSession) {
    setManageName(session.title);
    setManageDialog({ action: "edit", type: "chat", item: session });
  }

  function openDeleteChatDialog(session: ChatSession) {
    setManageName(session.title);
    setManageDialog({ action: "delete", type: "chat", item: session });
  }

  async function handleCreateWorkspace(name: string) {
    setError(null);
    try {
      const workspace = await createWorkspace(name);
      setWorkspaces((currentWorkspaces) => [workspace, ...currentWorkspaces]);
      await selectWorkspace(workspace.id);
      toast({
        title: "Workspace created",
        description: `${workspace.name} is ready for chats and documents.`,
      });
    } catch (createError) {
      reportError("Could not create workspace", "Unable to create workspace.", createError);
    }
  }

  async function handleCreateChat(title: string) {
    if (!activeWorkspace) {
      return;
    }

    setError(null);

    try {
      const chat = await createChat(activeWorkspace.id, title);
      setVisibleSessions((currentSessions) => [chat, ...currentSessions]);
      setActiveChatId(chat.id);
      setMessages([]);
      setStatuses([]);
      setCitations([]);
      setStreamingAnswer("");
      toast({
        title: "Chat created",
        description: `${chat.title} was added to ${activeWorkspace.name}.`,
      });
    } catch (createError) {
      reportError("Could not create chat", "Unable to create chat.", createError);
    }
  }

  async function handleCreateSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedName = createName.trim();

    if (!trimmedName || !createDialog) {
      return;
    }

    setIsCreating(true);

    try {
      if (createDialog === "workspace") {
        await handleCreateWorkspace(trimmedName);
      } else {
        await handleCreateChat(trimmedName);
      }
      setCreateDialog(null);
      setCreateName("");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleManageSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!manageDialog) {
      return;
    }

    const trimmedName = manageName.trim();
    if (manageDialog.action === "edit" && !trimmedName) {
      return;
    }

    setIsManaging(true);

    try {
      if (manageDialog.type === "workspace") {
        if (manageDialog.action === "edit") {
          const updatedWorkspace = await updateWorkspace(manageDialog.item.id, trimmedName);
          setWorkspaces((currentWorkspaces) =>
            currentWorkspaces.map((workspace) =>
              workspace.id === updatedWorkspace.id ? updatedWorkspace : workspace,
            ),
          );
          toast({ title: "Workspace renamed", description: `${updatedWorkspace.name} was updated.` });
        } else {
          await deleteWorkspace(manageDialog.item.id);
          const nextWorkspaces = workspaces.filter((workspace) => workspace.id !== manageDialog.item.id);
          setWorkspaces(nextWorkspaces);
          const nextWorkspaceId = nextWorkspaces[0]?.id ?? "";
          if (nextWorkspaceId) {
            await selectWorkspace(nextWorkspaceId);
          } else {
            setActiveWorkspaceId("");
            setActiveChatId("");
            setVisibleSessions([]);
            setMessages([]);
            setDocuments([]);
            setCitations([]);
            setStatuses([]);
          }
          toast({ title: "Workspace deleted", description: `${manageDialog.item.name} was removed.` });
        }
      } else if (activeWorkspace) {
        if (manageDialog.action === "edit") {
          const updatedChat = await updateChat(activeWorkspace.id, manageDialog.item.id, trimmedName);
          setVisibleSessions((currentSessions) =>
            currentSessions.map((session) =>
              session.id === updatedChat.id ? { ...session, ...updatedChat } : session,
            ),
          );
          toast({ title: "Chat renamed", description: `${updatedChat.title} was updated.` });
        } else {
          await deleteChat(activeWorkspace.id, manageDialog.item.id);
          const nextSessions = visibleSessions.filter((session) => session.id !== manageDialog.item.id);
          setVisibleSessions(nextSessions);
          const nextChatId = nextSessions[0]?.id ?? "";
          setActiveChatId(nextChatId);
          setMessages(nextChatId ? await listMessages(activeWorkspace.id, nextChatId) : []);
          setCitations([]);
          setStatuses([]);
          setStreamingAnswer("");
          toast({ title: "Chat deleted", description: `${manageDialog.item.title} was removed.` });
        }
      }

      setManageDialog(null);
      setManageName("");
    } catch (manageError) {
      reportError(
        "Could not update workspace",
        "The requested workspace or chat action failed.",
        manageError,
      );
    } finally {
      setIsManaging(false);
    }
  }

  async function refreshDocuments() {
    if (!activeWorkspace) {
      return;
    }

    try {
      const nextDocuments = await listDocuments(activeWorkspace.id);
      setDocuments(nextDocuments);
      documentIdsRef.current = nextDocuments.map((document) => document.id);
    } catch (loadError) {
      reportError("Could not load documents", "Unable to load documents.", loadError);
    }
  }

  useEffect(() => {
    const hasProcessing = documents.some(
      (doc) => doc.status === "uploaded" || doc.status === "processing"
    );
    if (!hasProcessing) {
      return;
    }

    const interval = setInterval(() => {
      refreshDocuments();
    }, 2000);

    return () => clearInterval(interval);
  }, [documents, activeWorkspaceId]);

  async function handleUploadDocuments(files: File[]) {
    if (!activeWorkspace) {
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      await Promise.all(files.map((file) => uploadDocument(activeWorkspace.id, file)));
      await refreshDocuments();
      appendStatus("status", `${files.length} document upload queued for ingestion.`);
      toast({
        title: "Documents queued",
        description: `${files.length} upload${files.length === 1 ? "" : "s"} sent for ingestion.`,
      });
    } catch (uploadError) {
      reportError("Could not upload documents", "Unable to upload documents.", uploadError);
    } finally {
      setIsUploading(false);
    }
  }

  function appendStatus(kind: StreamStatus["kind"], content: string) {
    setStatuses((currentStatuses) => [
      ...currentStatuses,
      {
        id: crypto.randomUUID(),
        kind,
        content,
        createdAt: new Date().toISOString(),
      },
    ]);
  }

  function resizeSupportPanel(nextWidth: number) {
    setSupportPanelWidth(Math.min(560, Math.max(300, nextWidth)));
  }

  function startSupportPanelResize(event: ReactPointerEvent<HTMLDivElement>) {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = supportPanelWidth;

    function handlePointerMove(moveEvent: PointerEvent) {
      resizeSupportPanel(startWidth - (moveEvent.clientX - startX));
    }

    function handlePointerUp() {
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    }

    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
  }

  async function prepareComposerAttachments(
    attachments: FileAttachment[],
    onUpdate: (attachmentId: string, patch: Partial<FileAttachment>) => void,
  ) {
    if (!activeWorkspace) {
      attachments.forEach((attachment) =>
        onUpdate(attachment.id, { status: "failed", error: "Create or select a workspace first." }),
      );
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      attachments.forEach((attachment) => onUpdate(attachment.id, { status: "uploading" }));
      const uploadResults = await Promise.all(
        attachments.map((attachment) => uploadDocument(activeWorkspace.id, attachment.file)),
      );
      const uploaded = attachments
        .map((attachment, index) => {
          const result = uploadResults[index];
          if (!result.id) {
            onUpdate(attachment.id, {
              status: "failed",
              error: result.error ?? "Upload failed.",
            });
            return null;
          }
          onUpdate(attachment.id, {
            status: "processing",
            documentId: result.id,
            error: null,
          });
          return { attachmentId: attachment.id, documentId: result.id };
        })
        .filter((item): item is { attachmentId: string; documentId: string } => Boolean(item));

      if (uploaded.length === 0) {
        return;
      }

      appendStatus("status", `${uploaded.length} document${uploaded.length === 1 ? "" : "s"} queued for ingestion.`);
      const deadline = Date.now() + documentPollTimeoutMs;

      while (Date.now() < deadline) {
        const nextDocuments = await listDocuments(activeWorkspace.id);
        setDocuments(nextDocuments);
        documentIdsRef.current = nextDocuments.map((document) => document.id);

        let allSettled = true;
        uploaded.forEach(({ attachmentId, documentId }) => {
          const document = nextDocuments.find((item) => item.id === documentId);
          if (!document || (document.status !== "ready" && document.status !== "failed")) {
            allSettled = false;
            onUpdate(attachmentId, { status: "processing" });
            return;
          }
          onUpdate(attachmentId, {
            status: document.status === "ready" ? "ready" : "failed",
            error: document.error,
          });
        });

        if (allSettled) {
          const selectedDocuments = nextDocuments.filter((document) =>
            uploaded.some((item) => item.documentId === document.id),
          );
          const failedCount = selectedDocuments.filter((document) => document.status === "failed").length;
          if (failedCount > 0) {
            appendStatus(
              "status",
              `${failedCount} document${failedCount === 1 ? "" : "s"} failed during ingestion. Remove failed files before sending.`,
            );
            toast({
              title: "Document ingestion failed",
              description: "Remove the failed attachment or upload it again before chatting.",
              variant: "destructive",
            });
            return;
          }

          appendStatus("status", "Uploaded documents are ready for chat.");
          toast({
            title: "Documents ready",
            description: "You can now ask questions using the attached files.",
          });
          return;
        }

        await new Promise((resolve) => setTimeout(resolve, 2000));
      }

      uploaded.forEach(({ attachmentId }) =>
        onUpdate(attachmentId, {
          status: "failed",
          error: "Document processing timed out. Try again after it appears ready in Docs.",
        }),
      );
      toast({
        title: "Document still processing",
        description: "The document is not ready yet. Try again once it appears as ready in Docs.",
        variant: "destructive",
      });
    } catch (uploadError) {
      attachments.forEach((attachment) =>
        onUpdate(attachment.id, {
          status: "failed",
          error: uploadError instanceof Error ? uploadError.message : "Upload failed.",
        }),
      );
      reportError("Could not prepare attachment", "Unable to upload or process one or more attachments.", uploadError);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleSubmit(message: string, attachments: FileAttachment[] = [], options: { advancedSearch: boolean; forceWeb: boolean; skipWebPrompt?: boolean } = { advancedSearch: false, forceWeb: false }) {
    if (!activeWorkspace || !activeSession) {
        return;
    }

    const readyAttachments = attachments.filter(
      (attachment) => attachment.status === "ready" && attachment.documentId,
    );
    const pendingAttachments: ChatAttachment[] = readyAttachments.map((attachment) => ({
      id: attachment.id,
      name: attachment.name,
      size: attachment.size,
      type: attachment.type,
      status: "ready",
      documentId: attachment.documentId,
    }));
    let userMessageId = "";

    // Only add a new message bubble to the UI if we aren't resubmitting from a prompt
    if (!options.skipWebPrompt && !pendingWebSearch) {
      userMessageId = crypto.randomUUID();
      const userMessage: ChatMessage = {
        id: userMessageId,
        chatId: activeSession.id,
        role: "user",
        content: message,
        attachments: pendingAttachments,
        createdAt: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((currentMessages) => [...currentMessages, userMessage]);
    }
    
    setVisibleSessions((currentSessions) =>
      currentSessions.map((session) =>
        session.id === activeSession.id
          ? {
              ...session,
              summary: message,
              status: "active",
              updatedAt: "Now",
            }
          : session,
      ),
    );
    setStatuses([]);
    setCitations([]);
    setStreamingAnswer("");
    setError(null);
    setIsStreaming(true);
    setPendingWebSearch(null); // clear any pending prompt
    let finalAnswer = "";
    let finalCitations: Citation[] = [];

    let uploadedDocIds: string[] = readyAttachments.length > 0
      ? readyAttachments.map((attachment) => attachment.documentId as string)
      : documents
      .filter((document) => document.status === "ready")
      .map((document) => document.id);

    if (attachments.length > 0 && uploadedDocIds.length === 0) {
      setIsStreaming(false);
      appendStatus("status", "No uploaded documents are ready yet.");
      return;
    }

    try {
      await streamChat(
        {
          workspace_id: activeWorkspace.id,
          chat_id: activeSession.id,
          message,
          document_ids: uploadedDocIds,
          advanced_search: options.advancedSearch,
          force_web: options.forceWeb,
          skip_web_prompt: options.skipWebPrompt,
        },
        {
          onEvent: (event) => {
            if (event.type === "action_required") {
              setPendingWebSearch({ message, options });
              setIsStreaming(false);
              return; // Stop processing further for this stream
            }

            if (event.type === "status") {
              appendStatus("status", event.content);
            }

            if (event.type === "reasoning_summary") {
              appendStatus("reasoning_summary", event.content);
            }

            if (event.type === "answer_delta") {
              finalAnswer += event.content;
              setStreamingAnswer(finalAnswer);
            }

            if (event.type === "citations") {
              finalCitations = event.content;
              setCitations(event.content);
            }

            if (event.type === "error") {
              setError(event.content);
            }
          },
        },
      );
    } catch (streamError) {
      appendStatus("status", "Backend stream unavailable.");
      reportError("Chat stream failed", "Chat stream failed.", streamError);
    } finally {
      setMessages((currentMessages) =>
        finalAnswer
          ? [
              ...currentMessages,
              {
                id: crypto.randomUUID(),
                chatId: activeSession.id,
                role: "assistant",
                content: finalAnswer,
                citations: finalCitations,
                createdAt: new Date().toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                }),
              },
            ]
          : currentMessages,
      );
      if (finalAnswer) {
        setVisibleSessions((currentSessions) =>
          currentSessions.map((session) =>
            session.id === activeSession.id
              ? {
                  ...session,
                  summary: finalAnswer,
                  status: "active",
                  updatedAt: "Now",
                }
              : session,
          ),
        );
        getUsage().then(setUsage).catch(() => undefined);
      }
      setIsStreaming(false);
      setStreamingAnswer("");
    }
  }

  return (
    <>
    <main className="grid h-dvh min-h-0 grid-rows-[56px_minmax(0,1fr)] overflow-hidden bg-[#f4f4f4] text-foreground sm:grid-rows-[64px_minmax(0,1fr)]">
      <header className="flex min-w-0 items-center justify-between gap-2 border-b border-[#ededed] bg-[#f4f4f4] px-3 sm:gap-4 sm:px-5">
        <div className="flex min-w-0 items-center gap-3">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="-ml-1 h-10 w-10 shrink-0 md:hidden"
            aria-label="Open workspace navigation"
            aria-expanded={isMobileNavOpen}
            onClick={() => setIsMobileNavOpen(true)}
          >
            <Menu className="h-5 w-5" aria-hidden />
          </Button>
          <a href="/" aria-label="Workspace home" className="mr-1 flex min-w-0 items-center gap-2">
            <img src="/logo.svg" alt="Workspace Logo" className="h-8 w-8 shrink-0 object-contain" />
            <span className="truncate text-[16px] font-bold tracking-tight max-[380px]:hidden">Workspace</span>
          </a>
          <span className="hidden text-muted-foreground sm:inline">/</span>
          <Button variant="ghost" className="hidden h-9 min-w-0 gap-1 px-1 text-[15px] font-semibold sm:inline-flex">
            {activeWorkspace?.name ?? "Workspace"}
            <ChevronDown className="h-4 w-4 text-muted-foreground" aria-hidden />
          </Button>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-9 w-9 rounded-full bg-[#efefef] text-sm font-semibold hover:bg-[#e5e5e5] overflow-hidden"
            aria-label="Open user profile"
            onClick={() => setIsProfileDialogOpen(true)}
          >
            {user?.user_metadata?.avatar_url ? (
              <img src={user.user_metadata.avatar_url} alt={user?.user_metadata?.full_name || user?.email} className="w-full h-full object-cover" />
            ) : (
              (user?.user_metadata?.full_name || user?.email || "U").charAt(0).toUpperCase()
            )}
          </Button>
        </div>
      </header>

      <div className="grid min-h-0 grid-cols-1 md:grid-cols-[300px_minmax(0,1fr)] lg:grid-cols-[320px_minmax(0,1fr)]">
        <div className="hidden min-h-0 md:block">
          <WorkspaceSidebar
            workspaces={workspaces}
            activeWorkspaceId={activeWorkspaceId}
            sessions={visibleSessions}
            activeChatId={activeSession?.id ?? ""}
            isLoading={isLoading}
            onSelectWorkspace={selectWorkspace}
            onSelectChat={selectChat}
            onCreateWorkspace={openCreateWorkspaceDialog}
            onCreateChat={openCreateChatDialog}
            onEditWorkspace={openEditWorkspaceDialog}
            onDeleteWorkspace={openDeleteWorkspaceDialog}
            onEditChat={openEditChatDialog}
            onDeleteChat={openDeleteChatDialog}
          />
        </div>

        <Card className="m-0 grid h-full min-h-0 min-w-0 overflow-hidden rounded-none border-[#e6e6e6] bg-white shadow-none md:rounded-tl-xl">
          <section className="grid h-full min-h-0 min-w-0 grid-rows-[64px_minmax(0,1fr)] sm:grid-rows-[70px_minmax(0,1fr)]">
            <header className="flex min-w-0 items-center justify-between gap-3 border-b border-[#eeeeee] px-3 sm:px-5">
              <div className="flex min-w-0 items-center gap-3 sm:gap-4">
                <div className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#f1f1f1] sm:flex">
                  <MessageCircle className="h-5 w-5" aria-hidden />
                </div>
                <div className="min-w-0">
                  <h2 className="truncate text-[17px] font-semibold tracking-[-0.01em] sm:text-[21px]">
                    {activeSession?.title ?? "New workspace chat"}
                  </h2>
                  <p className="truncate text-[12px] text-muted-foreground sm:text-[13px]">
                    {activeWorkspace?.name} - memory, web retrieval, document citations
                  </p>
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-2 text-[13px] text-muted-foreground">
                <div className="hidden items-center gap-2 xl:flex">
                  <Badge variant="secondary">Active</Badge>
                  <Badge variant="outline">Private workspace</Badge>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  className="h-9 w-9 xl:hidden"
                  aria-label="Open activity and sources"
                  onClick={() => setIsMobileToolsOpen(true)}
                >
                  <PanelRight className="h-4 w-4" aria-hidden />
                </Button>
              </div>
            </header>

            <div
              className="grid h-full min-h-0 grid-cols-[minmax(0,1fr)] overflow-hidden xl:grid-cols-[minmax(0,1fr)_var(--support-panel-width)]"
              style={{ "--support-panel-width": `${supportPanelWidth}px` } as CSSProperties}
            >
              <div className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden">
                {error ? (
                  <Card className="mx-3 mt-3 flex items-start gap-3 border-[#f0d8b8] bg-[#fff8ed] p-3 text-sm shadow-none sm:mx-6 sm:mt-4">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[#a15c00]" aria-hidden />
                    <p className="leading-6 text-muted-foreground">{error}</p>
                  </Card>
                ) : null}
                {isLoading ? (
                  <div className="grid flex-1 place-items-center p-6 text-center">
                    <div>
                      <p className="text-[18px] font-semibold">Loading workspace</p>
                      <p className="mt-2 text-sm text-muted-foreground">
                        Fetching workspaces, chats, and documents from the API.
                      </p>
                    </div>
                  </div>
                ) : activeWorkspace && activeSession ? (
                  <>
                    <ChatThread
                      messages={visibleMessages}
                      streamingAnswer={streamingAnswer}
                      isStreaming={isStreaming}
                    />
                    <MessageComposer
                      disabled={isStreaming}
                      onSubmit={handleSubmit}
                      onPrepareAttachments={prepareComposerAttachments}
                    />
                  </>
                ) : (
                  <div className="grid flex-1 place-items-center p-6 text-center">
                    <div>
                      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-[#eeeeee]">
                        <MessageCircle className="h-6 w-6" aria-hidden />
                      </div>
                      <p className="mt-4 text-[18px] font-semibold">
                        {activeWorkspace ? "Create a chat" : "Create a workspace"}
                      </p>
                      <p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
                        {activeWorkspace
                          ? "Chats live inside the selected workspace and share its documents, memory, and usage context."
                          : "Workspaces group chats, documents, sources, and usage in one place."}
                      </p>
                      <Button
                        type="button"
                        className="mt-4"
                        onClick={activeWorkspace ? openCreateChatDialog : openCreateWorkspaceDialog}
                      >
                        {activeWorkspace ? "New chat" : "New workspace"}
                      </Button>
                    </div>
                  </div>
                )}
              </div>

              <aside className="relative hidden h-full min-h-0 min-w-0 overflow-hidden border-l border-[#eeeeee] bg-white p-4 xl:block 2xl:p-5">
                <div
                  role="separator"
                  aria-label="Resize activity panel"
                  aria-orientation="vertical"
                  aria-valuemin={300}
                  aria-valuemax={560}
                  aria-valuenow={supportPanelWidth}
                  tabIndex={0}
                  onPointerDown={startSupportPanelResize}
                  onKeyDown={(event) => {
                    if (event.key === "ArrowLeft") {
                      event.preventDefault();
                      resizeSupportPanel(supportPanelWidth + 24);
                    }
                    if (event.key === "ArrowRight") {
                      event.preventDefault();
                      resizeSupportPanel(supportPanelWidth - 24);
                    }
                  }}
                  className="absolute inset-y-0 left-0 z-10 flex w-4 -translate-x-1/2 cursor-col-resize items-center justify-center outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="flex h-12 w-5 items-center justify-center rounded-full border border-[#dedede] bg-white text-muted-foreground shadow-sm transition-colors hover:bg-[#f5f5f5]">
                    <GripVertical className="h-4 w-4" aria-hidden />
                  </span>
                </div>
                <SupportTabs
                  statuses={statuses}
                  isStreaming={isStreaming}
                  hasAnswerStarted={streamingAnswer.length > 0}
                  hasError={Boolean(error)}
                  citations={citations}
                  documents={documents}
                  disabled={!activeWorkspace}
                  isUploading={isUploading}
                  usage={usage}
                  onFilesSelected={handleUploadDocuments}
                  onRefreshDocuments={refreshDocuments}
                />
              </aside>
            </div>
          </section>
        </Card>
      </div>
    </main>
    <Dialog open={isMobileNavOpen} onOpenChange={setIsMobileNavOpen}>
      <DialogContent className="left-0 top-0 h-dvh w-full max-w-[380px] translate-x-0 translate-y-0 gap-0 rounded-none border-r border-[#e0e0e0] p-0 shadow-2xl max-[420px]:max-w-none [&>button]:right-3 [&>button]:top-3 [&>button]:z-20 [&>button]:rounded-full [&>button]:bg-white/90 [&>button]:p-2 [&>button]:shadow-sm">
        <DialogHeader className="sr-only">
          <DialogTitle>Workspace navigation</DialogTitle>
          <DialogDescription>Select a workspace or chat.</DialogDescription>
        </DialogHeader>
        <WorkspaceSidebar
          className="border-r-0 [&>div:first-child]:pt-12"
          workspaces={workspaces}
          activeWorkspaceId={activeWorkspaceId}
          sessions={visibleSessions}
          activeChatId={activeSession?.id ?? ""}
          isLoading={isLoading}
          onSelectWorkspace={(workspaceId) => {
            setIsMobileNavOpen(false);
            selectWorkspace(workspaceId);
          }}
          onSelectChat={(chatId) => {
            setIsMobileNavOpen(false);
            selectChat(chatId);
          }}
          onCreateWorkspace={() => {
            setIsMobileNavOpen(false);
            openCreateWorkspaceDialog();
          }}
          onCreateChat={() => {
            setIsMobileNavOpen(false);
            openCreateChatDialog();
          }}
          onEditWorkspace={(workspace) => {
            setIsMobileNavOpen(false);
            openEditWorkspaceDialog(workspace);
          }}
          onDeleteWorkspace={(workspace) => {
            setIsMobileNavOpen(false);
            openDeleteWorkspaceDialog(workspace);
          }}
          onEditChat={(session) => {
            setIsMobileNavOpen(false);
            openEditChatDialog(session);
          }}
          onDeleteChat={(session) => {
            setIsMobileNavOpen(false);
            openDeleteChatDialog(session);
          }}
        />
      </DialogContent>
    </Dialog>
    <Dialog open={isMobileToolsOpen} onOpenChange={setIsMobileToolsOpen}>
      <DialogContent className="left-auto right-0 top-0 h-dvh w-[min(420px,calc(100vw-1rem))] max-w-none translate-x-0 translate-y-0 gap-0 rounded-none p-3 sm:p-4">
        <DialogHeader className="sr-only">
          <DialogTitle>Activity and sources</DialogTitle>
          <DialogDescription>Review reasoning status, sources, documents, and usage.</DialogDescription>
        </DialogHeader>
        <SupportTabs
          statuses={statuses}
          isStreaming={isStreaming}
          hasAnswerStarted={streamingAnswer.length > 0}
          hasError={Boolean(error)}
          citations={citations}
          documents={documents}
          disabled={!activeWorkspace}
          isUploading={isUploading}
          usage={usage}
          onFilesSelected={handleUploadDocuments}
          onRefreshDocuments={refreshDocuments}
        />
      </DialogContent>
    </Dialog>
    <Dialog
      open={createDialog !== null}
      onOpenChange={(open) => {
        if (!open && !isCreating) {
          setCreateDialog(null);
          setCreateName("");
        }
      }}
    >
      <DialogContent>
        <form onSubmit={handleCreateSubmit} className="space-y-5">
          <DialogHeader>
            <DialogTitle>
              {createDialog === "workspace" ? "Create workspace" : "Create chat"}
            </DialogTitle>
            <DialogDescription>
              {createDialog === "workspace"
                ? "Workspaces contain chats, uploaded documents, sources, and usage."
                : `Add a chat inside ${activeWorkspace?.name ?? "the current workspace"}.`}
            </DialogDescription>
          </DialogHeader>
          <Input
            value={createName}
            onChange={(event) => setCreateName(event.target.value)}
            placeholder={createDialog === "workspace" ? "Workspace name" : "Chat title"}
            autoFocus
            disabled={isCreating}
          />
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setCreateDialog(null);
                setCreateName("");
              }}
              disabled={isCreating}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isCreating || createName.trim().length === 0}>
              {isCreating ? "Creating" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
    <Dialog
      open={manageDialog !== null}
      onOpenChange={(open) => {
        if (!open && !isManaging) {
          setManageDialog(null);
          setManageName("");
        }
      }}
    >
      <DialogContent>
        <form onSubmit={handleManageSubmit} className="space-y-5">
          <DialogHeader>
            <DialogTitle>
              {manageDialog?.action === "edit"
                ? manageDialog.type === "workspace"
                  ? "Rename workspace"
                  : "Rename chat"
                : manageDialog?.type === "workspace"
                  ? "Delete workspace"
                  : "Delete chat"}
            </DialogTitle>
            <DialogDescription>
              {manageDialog?.action === "edit"
                ? "Update the name shown in the sidebar."
                : manageDialog?.type === "workspace"
                  ? "This removes the workspace and its chats from the app."
                  : "This removes the chat and its messages from the current workspace."}
            </DialogDescription>
          </DialogHeader>
          {manageDialog?.action === "edit" ? (
            <Input
              value={manageName}
              onChange={(event) => setManageName(event.target.value)}
              placeholder={manageDialog.type === "workspace" ? "Workspace name" : "Chat title"}
              autoFocus
              disabled={isManaging}
            />
          ) : (
            <div className="rounded-md border border-[#f0d8d8] bg-[#fff8f8] p-3 text-sm leading-6 text-muted-foreground">
              Delete <span className="font-medium text-foreground">{manageName}</span>?
            </div>
          )}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setManageDialog(null);
                setManageName("");
              }}
              disabled={isManaging}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant={manageDialog?.action === "delete" ? "destructive" : "default"}
              disabled={isManaging || (manageDialog?.action === "edit" && manageName.trim().length === 0)}
            >
              {isManaging
                ? "Working"
                : manageDialog?.action === "delete"
                  ? "Delete"
                  : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
    <Dialog
      open={isProfileDialogOpen}
      onOpenChange={(open) => {
        setIsProfileDialogOpen(open);
        if (!open) {
          setProfileDialogView("menu");
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{profileDialogView === "settings" ? "Settings" : "Profile"}</DialogTitle>
          <DialogDescription>
            Manage workspace actions and account access.
          </DialogDescription>
        </DialogHeader>
        {profileDialogView === "settings" ? (
          <div className="space-y-3">
            <div className="rounded-md border border-[#eeeeee] bg-[#f8f8f8] p-3">
              <p className="text-sm font-medium">{activeWorkspace?.name ?? "Workspace"}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {activeSession?.title ?? "No chat selected"}
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              className="w-full justify-start"
              onClick={() => {
                setIsProfileDialogOpen(false);
                openCreateWorkspaceDialog();
              }}
            >
              New workspace
            </Button>
            <Button
              type="button"
              variant="outline"
              className="w-full justify-start"
              disabled={!activeWorkspace}
              onClick={() => {
                setIsProfileDialogOpen(false);
                openCreateChatDialog();
              }}
            >
              New chat
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="w-full justify-start"
              onClick={() => setProfileDialogView("menu")}
            >
              Back
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {user && (
              <div className="flex items-center gap-3 p-3 rounded-md border border-[#eeeeee] bg-[#f8f8f8] mb-4">
                {user?.user_metadata?.avatar_url ? (
                  <img src={user.user_metadata.avatar_url} alt="Profile" className="w-10 h-10 rounded-full object-cover" />
                ) : (
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#efefef] font-semibold text-muted-foreground">
                    {(user?.user_metadata?.full_name || user?.email || "U").charAt(0).toUpperCase()}
                  </div>
                )}
                <div className="flex flex-col min-w-0">
                  <span className="text-sm font-medium truncate">{user.user_metadata?.full_name || "User"}</span>
                  <span className="text-xs text-muted-foreground truncate">{user.email}</span>
                </div>
              </div>
            )}
            <Button
              type="button"
              variant="outline"
              className="w-full justify-start"
              onClick={() => setProfileDialogView("settings")}
            >
              <Settings className="h-4 w-4" aria-hidden />
              Settings
            </Button>
            <form action="/auth/logout" method="post">
              <Button type="submit" variant="outline" className="w-full justify-start">
                <LogOut className="h-4 w-4" aria-hidden />
                Log out
              </Button>
            </form>
          </div>
        )}
      </DialogContent>
    </Dialog>
    <Dialog
      open={pendingWebSearch !== null}
      onOpenChange={(open) => {
        if (!open) setPendingWebSearch(null);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Live Information Required</DialogTitle>
          <DialogDescription>
            Your question appears to require live web search for accurate results. Would you like to enable Web Search?
          </DialogDescription>
        </DialogHeader>
        
        <div className="flex items-center justify-between py-4">
          <span className="text-sm font-medium">Web Search</span>
          <button
            type="button"
            role="switch"
            aria-checked={dialogForceWeb}
            onClick={() => setDialogForceWeb(!dialogForceWeb)}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${dialogForceWeb ? "bg-[#111]" : "bg-neutral-200"}`}
          >
            <span
              data-state={dialogForceWeb ? "checked" : "unchecked"}
              className={`pointer-events-none block h-5 w-5 rounded-full bg-white shadow-lg ring-0 transition-transform ${dialogForceWeb ? "translate-x-5" : "translate-x-0"}`}
            />
          </button>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              if (pendingWebSearch) {
                handleSubmit(pendingWebSearch.message, [], {
                  ...pendingWebSearch.options,
                  skipWebPrompt: true, // skip the prompt this time
                  forceWeb: false, // force web off since they skipped
                });
              }
            }}
          >
            Skip & Guess
          </Button>
          <Button
            type="button"
            onClick={() => {
              if (pendingWebSearch) {
                handleSubmit(pendingWebSearch.message, [], {
                  ...pendingWebSearch.options,
                  skipWebPrompt: true, // we already prompted
                  forceWeb: dialogForceWeb,
                });
              }
            }}
          >
            Submit
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    </>
  );
}
