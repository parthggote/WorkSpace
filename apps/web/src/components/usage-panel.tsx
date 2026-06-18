import { BarChart3 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import type { UsageSummary } from "@/lib/types";

type UsagePanelProps = {
  usage: UsageSummary[];
};

export function UsagePanel({ usage }: UsagePanelProps) {
  const totalTokens = usage.reduce((sum, row) => sum + row.totalTokens, 0);
  const totalCost = usage.reduce((sum, row) => sum + row.estimatedCostUsd, 0);

  return (
    <Card className="flex h-full min-h-0 flex-col overflow-hidden shadow-none border-none">
      <CardHeader className="flex-row items-center gap-2 space-y-0 py-3">
        <BarChart3 className="h-4 w-4 text-primary" aria-hidden />
        <CardTitle>Usage</CardTitle>
      </CardHeader>
      <Separator />
      <CardContent className="space-y-3 pt-4 flex-1 min-h-0 flex flex-col overflow-hidden">
        <div className="grid grid-cols-2 gap-2 shrink-0">
          <div className="rounded-md bg-muted p-3">
            <p className="text-xs text-muted-foreground">Tokens</p>
            <p className="mt-1 font-mono text-sm">{totalTokens.toLocaleString()}</p>
          </div>
          <div className="rounded-md bg-muted p-3">
            <p className="text-xs text-muted-foreground">Cost</p>
            <p className="mt-1 font-mono text-sm">${totalCost.toFixed(4)}</p>
          </div>
        </div>

        <ScrollArea className="min-h-0 flex-1 pr-1">
          <div className="space-y-2">
            {usage.length > 0 ? (
              usage.map((row) => (
                <div
                  key={row.workspaceId}
                  className="rounded-md border border-border bg-background p-3"
                >
                  <p className="truncate text-sm font-medium">{row.workspaceName}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {row.totalTokens.toLocaleString()} tokens - ${row.estimatedCostUsd.toFixed(4)}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-sm leading-6 text-muted-foreground">
                Usage will appear after streamed responses are logged.
              </p>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
