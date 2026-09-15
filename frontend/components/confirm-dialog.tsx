"use client";

import { useEffect, useId, useRef } from "react";
import { AlertTriangle, HelpCircle } from "lucide-react";

import { Button, Spinner } from "@/components/ui";
import { cn } from "@/lib/utils";

type ConfirmDialogProps = {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  busy?: boolean;
  variant?: "default" | "destructive";
  onConfirm: () => void;
  onOpenChange: (open: boolean) => void;
};

export function ConfirmDialog({ open, title, description, confirmLabel, busy = false, variant = "default", onConfirm, onOpenChange }: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return <dialog
    ref={dialogRef}
    aria-describedby={descriptionId}
    aria-labelledby={titleId}
    className="w-[calc(100%-2rem)] max-w-md rounded-lg border bg-card p-0 text-card-foreground shadow-xl backdrop:bg-black/45"
    onCancel={(event) => { event.preventDefault(); if (!busy) onOpenChange(false); }}
    onClick={(event) => { if (event.target === event.currentTarget && !busy) onOpenChange(false); }}
  >
    <div className="p-6">
      <div className="flex items-start gap-3">
        <span className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-full", variant === "destructive" ? "bg-destructive/10 text-destructive" : "bg-primary/10 text-primary")}>
          {variant === "destructive" ? <AlertTriangle className="h-5 w-5" /> : <HelpCircle className="h-5 w-5" />}
        </span>
        <div className="min-w-0">
          <h2 id={titleId} className="text-base font-semibold">{title}</h2>
          <p id={descriptionId} className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
        </div>
      </div>
      <div className="mt-6 flex justify-end gap-2 border-t pt-4">
        <Button type="button" variant="outline" disabled={busy} onClick={() => onOpenChange(false)}>取消</Button>
        <Button type="button" variant={variant === "destructive" ? "destructive" : "default"} disabled={busy} onClick={onConfirm}>
          {busy && <Spinner className="mr-2" />}{confirmLabel}
        </Button>
      </div>
    </div>
  </dialog>;
}
