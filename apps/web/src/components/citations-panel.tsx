import { ExternalLink, Library, Link2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import type { Citation } from "@/lib/types";

type CitationsPanelProps = {
  citations: Citation[];
};

export function CitationsPanel({ citations }: CitationsPanelProps) {
  return (
    <Card className="flex h-full min-h-0 flex-col overflow-hidden shadow-none border-none">
      <CardHeader className="flex-row items-center gap-2 space-y-0 py-3">
        <Library className="h-4 w-4 text-accent" aria-hidden />
        <CardTitle>Citations</CardTitle>
      </CardHeader>
      <Separator />
      <ScrollArea className="min-h-0 flex-1">
        <CardContent className="space-y-3 pt-4">
          {citations.length > 0 ? (
            citations.map((citation, idx) => (
              <Card key={citation.message_id || citation.locator || citation.url || String(idx)} className="bg-background shadow-none">
                <CardContent className="p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{citation.title}</p>
                      <div className="mt-1 flex flex-wrap items-center gap-2">
                        <Badge variant="outline" className="capitalize">
                          {citation.source.replace("-", " ")}
                        </Badge>
                        {citation.score ? (
                          <span className="text-xs text-muted-foreground">
                            {Math.round(citation.score * 100)}%
                          </span>
                        ) : null}
                      </div>
                    </div>
                    {citation.url ? (
                      <Button asChild variant="outline" size="icon" className="h-8 w-8 shrink-0">
                        <a href={citation.url} aria-label={`Open ${citation.title}`}>
                          <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                        </a>
                      </Button>
                    ) : (
                      <Button variant="outline" size="icon" className="h-8 w-8 shrink-0" disabled>
                        <Link2 className="h-3.5 w-3.5" aria-hidden />
                      </Button>
                    )}
                  </div>
                  {citation.excerpt && (
                    <p className="mt-3 text-xs leading-5 text-muted-foreground">{citation.excerpt}</p>
                  )}
                </CardContent>
              </Card>
            ))
          ) : (
            <p className="text-sm leading-6 text-muted-foreground">
              Memory, web, and document citations will appear here when sources are used.
            </p>
          )}
        </CardContent>
      </ScrollArea>
    </Card>
  );
}

