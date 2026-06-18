"use client";

import * as React from "react";
import * as ToastPrimitive from "@radix-ui/react-toast";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

type Toast = {
  id: string;
  title: string;
  description?: string;
  variant?: "default" | "destructive";
};

type ToastContextValue = {
  toast: (toast: Omit<Toast, "id">) => void;
};

const ToastContext = React.createContext<ToastContextValue | null>(null);

export function useToast() {
  const context = React.useContext(ToastContext);

  if (!context) {
    throw new Error("useToast must be used inside ToastProvider.");
  }

  return context;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const toast = React.useCallback((nextToast: Omit<Toast, "id">) => {
    const id = crypto.randomUUID();
    setToasts((currentToasts) => [...currentToasts, { ...nextToast, id }]);
  }, []);

  function removeToast(id: string) {
    setToasts((currentToasts) => currentToasts.filter((toastItem) => toastItem.id !== id));
  }

  return (
    <ToastContext.Provider value={{ toast }}>
      <ToastPrimitive.Provider swipeDirection="right">
        {children}
        {toasts.map((toastItem) => (
          <ToastPrimitive.Root
            key={toastItem.id}
            className={cn(
              "grid w-full max-w-sm grid-cols-[1fr_auto] items-start gap-3 rounded-md border bg-card p-4 text-card-foreground shadow-lg",
              toastItem.variant === "destructive" && "border-destructive/40 bg-[#fff8f8]",
            )}
            duration={4500}
            onOpenChange={(open) => {
              if (!open) {
                removeToast(toastItem.id);
              }
            }}
          >
            <div className="space-y-1">
              <ToastPrimitive.Title className="text-sm font-semibold">
                {toastItem.title}
              </ToastPrimitive.Title>
              {toastItem.description ? (
                <ToastPrimitive.Description className="text-sm leading-5 text-muted-foreground">
                  {toastItem.description}
                </ToastPrimitive.Description>
              ) : null}
            </div>
            <ToastPrimitive.Close className="rounded-sm opacity-70 transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring">
              <X className="h-4 w-4" aria-hidden />
              <span className="sr-only">Close</span>
            </ToastPrimitive.Close>
          </ToastPrimitive.Root>
        ))}
        <ToastPrimitive.Viewport className="fixed bottom-4 right-4 z-[100] flex w-[calc(100%-2rem)] max-w-sm flex-col gap-2 outline-none" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  );
}
