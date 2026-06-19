import { CheckCircle2, FileText, Loader2, MessageCircle, XCircle } from "lucide-react";
import { AnswerContent } from "@/components/answer-content";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import type { ChatAttachment, ChatMessage } from "@/lib/types";

type ChatThreadProps = {
  messages: ChatMessage[];
  streamingAnswer: string;
  isStreaming: boolean;
};

function AssistantSkeleton() {
  return (
    <div className="space-y-3" aria-label="Assistant response loading">
      <div className="h-3 w-11/12 animate-pulse rounded-full bg-[#e8e8e8]" />
      <div className="h-3 w-4/5 animate-pulse rounded-full bg-[#e8e8e8]" />
      <div className="h-3 w-2/3 animate-pulse rounded-full bg-[#e8e8e8]" />
    </div>
  );
}

function attachmentLabel(attachment: ChatAttachment) {
  if (attachment.status === "uploading") return "Uploading";
  if (attachment.status === "processing" || attachment.status === "queued") return "Processing";
  if (attachment.status === "ready") return "Ready";
  return "Failed";
}

function AttachmentStatusIcon({ attachment }: { attachment: ChatAttachment }) {
  if (attachment.status === "ready") {
    return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" aria-hidden />;
  }
  if (attachment.status === "failed") {
    return <XCircle className="h-3.5 w-3.5 text-destructive" aria-hidden />;
  }
  return <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" aria-hidden />;
}

function MessageAttachments({ attachments }: { attachments?: ChatAttachment[] }) {
  if (!attachments?.length) {
    return null;
  }

  return (
    <div className="mt-1 flex flex-wrap gap-2">
      {attachments.map((attachment) => (
        <div
          key={attachment.id}
          className={cn(
            "flex max-w-full items-center gap-2 rounded-lg border px-2.5 py-1.5 text-xs",
            attachment.status === "failed"
              ? "border-[#f0d0d0] bg-[#fff7f7]"
              : attachment.status === "ready"
                ? "border-[#d7eadc] bg-[#f7fff8]"
                : "border-[#e5e5e5] bg-[#fafafa]",
          )}
          title={attachment.error ?? attachment.name}
        >
          <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden />
          <span className="max-w-[140px] truncate font-medium text-[#202020] sm:max-w-[180px]">
            {attachment.name}
          </span>
          <span className="flex shrink-0 items-center gap-1 text-muted-foreground">
            <AttachmentStatusIcon attachment={attachment} />
            {attachmentLabel(attachment)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function ChatThread({ messages, streamingAnswer, isStreaming }: ChatThreadProps) {
  const hasPendingAssistant = isStreaming || Boolean(streamingAnswer);
  const isEmpty = messages.length === 0 && !hasPendingAssistant;

  return (
    <ScrollArea className="flex-1 bg-white">
      <div className={cn("min-h-full p-3 sm:p-6", isEmpty && "grid place-items-center")}>
        {isEmpty ? (
          <div className="flex flex-col items-center gap-4 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#eeeeee]">
              <MessageCircle className="h-6 w-6" aria-hidden />
            </div>
            <p className="text-[18px] font-semibold">Your conversation will appear here</p>
          </div>
        ) : (
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 sm:gap-5">
            {messages.map((message) => (
              <article
                key={message.id}
                className={cn(
                  "flex max-w-[94%] flex-col gap-2 rounded-xl border px-3 py-3 sm:max-w-[86%] sm:px-4",
                  message.role === "user"
                    ? "ml-auto border-[#e1e1e1] bg-[#f4f4f4]"
                    : "mr-auto border-transparent bg-white",
                )}
              >
                <div className="flex min-w-0 items-center justify-between gap-3">
                  <Badge variant={message.role === "user" ? "default" : "secondary"}>
                    {message.role === "user" ? "You" : "Assistant"}
                  </Badge>
                  <time className="shrink-0 font-mono text-[11px] text-muted-foreground">
                    {message.createdAt}
                  </time>
                </div>
                {message.role === "assistant" ? (
                  <>
                    <AnswerContent content={message.content} />
                    {message.citations && message.citations.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-2 border-t border-[#f0f0f0] pt-2">
                        {message.citations.map((citation, idx) => (
                          <a
                            key={citation.message_id || citation.locator || citation.url || String(idx)}
                            href={citation.url || "#"}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={cn(
                              "inline-flex max-w-full items-center gap-1 rounded-md border border-[#e8e8e8] bg-[#f9f9f9] px-2 py-1 text-[11px] text-[#555]",
                              citation.url ? "hover:bg-[#f0f0f0] transition-colors" : "cursor-default"
                            )}
                            onClick={(e) => !citation.url && e.preventDefault()}
                          >
                            <span className="font-semibold capitalize text-[#333]">{citation.source}</span>
                            <span className="max-w-[120px] truncate sm:max-w-[150px]">{citation.title}</span>
                          </a>
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <p className="whitespace-pre-wrap text-[14px] leading-6 text-[#202020]">
                      {message.content}
                    </p>
                    <MessageAttachments attachments={message.attachments} />
                  </>
                )}
              </article>
            ))}

            {hasPendingAssistant ? (
              <article className="mr-auto flex max-w-[94%] flex-col gap-3 rounded-xl border border-[#eeeeee] bg-white px-3 py-3 shadow-sm sm:max-w-[86%] sm:px-4">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
                  <Badge variant="secondary">Assistant</Badge>
                </div>
                {streamingAnswer ? <AnswerContent content={streamingAnswer} /> : <AssistantSkeleton />}
              </article>
            ) : null}
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
