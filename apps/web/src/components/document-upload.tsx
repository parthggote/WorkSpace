"use client";

import { FileUp, RefreshCcw } from "lucide-react";
import { useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import type { WorkspaceDocument } from "@/lib/types";

type DocumentUploadProps = {
  documents: WorkspaceDocument[];
  disabled?: boolean;
  isUploading?: boolean;
  onFilesSelected: (files: File[]) => void;
  onRefresh: () => void;
};

export function DocumentUpload({
  documents,
  disabled,
  isUploading,
  onFilesSelected,
  onRefresh,
}: DocumentUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedNames, setSelectedNames] = useState<string[]>([]);

  function handleFiles(selectedFiles: FileList | null) {
    const nextFiles = Array.from(selectedFiles ?? []);

    if (nextFiles.length === 0) {
      return;
    }

    setSelectedNames(nextFiles.map((file) => file.name));
    onFilesSelected(nextFiles);
  }

  return (
    <Card className="flex h-full min-h-0 flex-col overflow-hidden shadow-none border-none">
      <CardHeader className="flex-row items-center justify-between gap-3 space-y-0 py-3">
        <div>
          <CardTitle>Documents</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">Attach files for workspace retrieval.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button type="button" variant="ghost" size="icon" onClick={onRefresh} disabled={disabled}>
            <RefreshCcw className="h-4 w-4" aria-hidden />
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={() => inputRef.current?.click()}
            disabled={disabled || isUploading}
          >
            <FileUp className="h-4 w-4" aria-hidden />
            {isUploading ? "Uploading" : "Upload"}
          </Button>
        </div>
      </CardHeader>
      <Separator />
      <CardContent className="pt-4 flex-1 min-h-0 flex flex-col overflow-hidden">
        <input
          ref={inputRef}
          type="file"
          multiple
          className="sr-only"
          onChange={(event) => handleFiles(event.target.files)}
          disabled={disabled || isUploading}
        />

        <ScrollArea className="min-h-0 flex-1 pr-1">
          {documents.length > 0 ? (
            <ul className="space-y-2">
              {documents.map((document) => (
                <li
                  key={document.id}
                  className="flex items-center justify-between gap-2 rounded-md bg-muted px-2 py-1.5 text-xs"
                >
                  <span className="truncate">{document.filename}</span>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{document.fileType}</Badge>
                    <Badge variant={document.status === "failed" ? "outline" : "secondary"}>
                      {document.status}
                    </Badge>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="space-y-2 text-sm leading-6 text-muted-foreground">
              <p>Upload PDF, DOCX, Markdown, or text files to include them in workspace memory.</p>
              {selectedNames.length > 0 ? (
                <p>Last selected: {selectedNames.join(", ")}</p>
              ) : null}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
