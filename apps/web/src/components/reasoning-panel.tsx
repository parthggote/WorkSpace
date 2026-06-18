import { Activity, CheckCircle2, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import type { StreamStatus } from "@/lib/types";

type ReasoningPanelProps = {
  statuses: StreamStatus[];
  isStreaming: boolean;
  hasAnswerStarted: boolean;
  hasError: boolean;
};

export function ReasoningPanel({
  statuses,
  isStreaming,
  hasAnswerStarted,
  hasError,
}: ReasoningPanelProps) {
  const panelStatus = hasError
    ? "Error"
    : isStreaming && hasAnswerStarted
      ? "Answering"
      : isStreaming
        ? "Working"
        : statuses.length > 0
          ? "Complete"
          : "Idle";

  return (
    <Card className="flex h-full min-h-0 flex-col overflow-hidden">
      <CardHeader className="flex-row items-center justify-between space-y-0 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <Activity className="h-4 w-4 shrink-0 text-primary" aria-hidden />
          <CardTitle className="truncate">Reasoning status</CardTitle>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Badge
            variant={isStreaming ? "accent" : "secondary"}
            className={hasError ? "bg-[#fff0f0] text-[#9f1d1d]" : undefined}
          >
            {panelStatus}
          </Badge>
          {isStreaming ? (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" aria-hidden />
          ) : (
            <CheckCircle2 className="h-4 w-4 text-primary" aria-hidden />
          )}
        </div>
      </CardHeader>
      <Separator />
      <ScrollArea className="min-h-0 flex-1">
        <CardContent className="space-y-2 p-3">
          {statuses.length > 0 ? (
            statuses.map((status, index) => (
              <div
                key={status.id}
                className={cn(
                  "rounded-lg border px-3 py-2.5",
                  status.kind === "reasoning_summary"
                    ? "border-[#d7e8ff] bg-[#f4f9ff]"
                    : "border-[#ebebeb] bg-[#f7f7f7]",
                )}
              >
                <div className="flex items-center justify-between gap-3">
                  <Badge variant={status.kind === "status" ? "secondary" : "accent"}>
                    {status.kind === "status" ? `Step ${index + 1}` : "Summary"}
                  </Badge>
                  <time className="font-mono text-[10px] text-muted-foreground">
                    {new Date(status.createdAt).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </time>
                </div>
                <p className="mt-2 text-[13px] leading-5 text-[#202020]">{status.content}</p>
              </div>
            ))
          ) : (
            <div className="rounded-lg border border-dashed border-[#dedede] p-3">
              <p className="text-[13px] leading-5 text-muted-foreground">
                Activity appears here while the assistant saves your message, checks memory,
                retrieves sources, and starts answering.
              </p>
            </div>
          )}
        </CardContent>
      </ScrollArea>
    </Card>
  );
}
