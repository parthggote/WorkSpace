"use client";

import { FileText, Globe, Paperclip, SendHorizontal, Sparkles, X } from "lucide-react";
import { type FormEvent, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { FileAttachment } from "@/lib/types";

type MessageComposerProps = {
  disabled?: boolean;
  onSubmit: (message: string, files: File[], options: { advancedSearch: boolean; forceWeb: boolean }) => void;
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileIcon(type: string) {
  return <FileText className="h-3.5 w-3.5 shrink-0" aria-hidden />;
}

export function MessageComposer({ disabled, onSubmit }: MessageComposerProps) {
  const [message, setMessage] = useState("");
  const [attachments, setAttachments] = useState<FileAttachment[]>([]);
  const [advancedSearch, setAdvancedSearch] = useState(false);
  const [forceWeb, setForceWeb] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleFiles(fileList: FileList | null) {
    const newFiles = Array.from(fileList ?? []);
    if (newFiles.length === 0) return;

    const newAttachments: FileAttachment[] = newFiles.map((file) => ({
      id: crypto.randomUUID(),
      file,
      name: file.name,
      size: file.size,
      type: file.type || file.name.split(".").pop() || "file",
    }));
    setAttachments((prev) => [...prev, ...newAttachments]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function removeAttachment(id: string) {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedMessage = message.trim();
    if ((!trimmedMessage && attachments.length === 0) || disabled) return;

    const files = attachments.map((a) => a.file);
    onSubmit(trimmedMessage || "Please analyze the attached documents.", files, {
      advancedSearch,
      forceWeb,
    });
    setMessage("");
    setAttachments([]);
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      const form = event.currentTarget.closest("form");
      if (form) form.requestSubmit();
    }
  }

  return (
    <form onSubmit={handleSubmit} className="shrink-0 border-t border-[#ededed] bg-white p-4">
      <div className="mx-auto max-w-3xl rounded-[22px] border border-[#e1e1e1] bg-white p-3 shadow-[0_2px_14px_rgba(0,0,0,0.04)] transition-shadow focus-within:shadow-[0_2px_20px_rgba(0,0,0,0.08)]">
        {/* Attached files */}
        {attachments.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-2 px-1">
            {attachments.map((attachment) => (
              <div
                key={attachment.id}
                className="group flex items-center gap-1.5 rounded-lg border border-[#e5e5e5] bg-[#f8f8f8] px-2.5 py-1.5 text-xs transition-colors hover:bg-[#f0f0f0]"
              >
                {getFileIcon(attachment.type)}
                <span className="max-w-[120px] truncate font-medium text-[#333]">
                  {attachment.name}
                </span>
                <span className="text-muted-foreground">{formatFileSize(attachment.size)}</span>
                <button
                  type="button"
                  onClick={() => removeAttachment(attachment.id)}
                  className="ml-0.5 rounded-full p-0.5 text-muted-foreground opacity-60 transition-opacity hover:bg-[#e0e0e0] hover:opacity-100"
                  aria-label={`Remove ${attachment.name}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Text area */}
        <Textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={3}
          placeholder={
            attachments.length > 0
              ? "Ask about the attached files or type a message..."
              : "Chat with your workspace..."
          }
          className="min-h-16 resize-none border-0 px-1 text-[15px] shadow-none focus-visible:ring-0"
        />

        {/* Bottom bar with actions */}
        <div className="mt-3 flex items-center justify-between">
          <div className="flex items-center gap-1">
            {/* Attach file button */}
            <TooltipProvider delayDuration={300}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-9 w-9 rounded-full text-muted-foreground hover:text-foreground"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={disabled}
                  >
                    <Paperclip className="h-[18px] w-[18px]" aria-hidden />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="top">Attach files (PDF, DOCX, TXT, MD, CSV)</TooltipContent>
              </Tooltip>
            </TooltipProvider>

            {/* Advanced search toggle */}
            <TooltipProvider delayDuration={300}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className={`h-9 w-9 rounded-full transition-all ${
                      advancedSearch
                        ? "bg-gradient-to-br from-violet-500/10 to-indigo-500/10 text-violet-600 shadow-[0_0_12px_rgba(139,92,246,0.25)]"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                    onClick={() => setAdvancedSearch((prev) => !prev)}
                    disabled={disabled}
                  >
                    <Sparkles className="h-[18px] w-[18px]" aria-hidden />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="top">
                  {advancedSearch ? "Advanced search ON" : "Enable advanced search (LangGraph)"}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>

            {/* Web search toggle */}
            <TooltipProvider delayDuration={300}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className={`h-9 w-9 rounded-full transition-all ${
                      forceWeb
                        ? "bg-gradient-to-br from-sky-500/10 to-cyan-500/10 text-sky-600 shadow-[0_0_12px_rgba(14,165,233,0.25)]"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                    onClick={() => setForceWeb((prev) => !prev)}
                    disabled={disabled}
                  >
                    <Globe className="h-[18px] w-[18px]" aria-hidden />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="top">
                  {forceWeb ? "Web search ON" : "Force web search"}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>

            {/* Active mode badges */}
            {(advancedSearch || forceWeb || attachments.length > 0) && (
              <div className="ml-2 flex items-center gap-1.5">
                {advancedSearch && (
                  <Badge variant="secondary" className="gap-1 bg-violet-50 text-violet-700 text-[11px] px-2 py-0.5">
                    <Sparkles className="h-3 w-3" /> Advanced
                  </Badge>
                )}
                {forceWeb && (
                  <Badge variant="secondary" className="gap-1 bg-sky-50 text-sky-700 text-[11px] px-2 py-0.5">
                    <Globe className="h-3 w-3" /> Web
                  </Badge>
                )}
                {attachments.length > 0 && (
                  <Badge variant="secondary" className="gap-1 bg-amber-50 text-amber-700 text-[11px] px-2 py-0.5">
                    <Paperclip className="h-3 w-3" /> {attachments.length} file{attachments.length !== 1 ? "s" : ""}
                  </Badge>
                )}
              </div>
            )}
          </div>

          {/* Send button */}
          <Button
            type="submit"
            disabled={disabled || (message.trim().length === 0 && attachments.length === 0)}
            aria-label="Send message"
            size="icon"
            className="h-10 w-10 rounded-full"
          >
            <SendHorizontal className="h-4 w-4" aria-hidden />
          </Button>
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.txt,.md,.csv,.json,.log"
        className="sr-only"
        onChange={(event) => handleFiles(event.target.files)}
        disabled={disabled}
      />
    </form>
  );
}
