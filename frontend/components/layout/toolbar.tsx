"use client";

import {
  Check,
  Download,
  Pencil,
  Plus,
  Redo2,
  Undo2,
  X,
} from "lucide-react";
import { cn } from "../../lib/utils";

interface ToolbarProps {
  hasActive: boolean;
  onApprove: () => void;
  onReject: () => void;
  onEdit: () => void;
  onAdd: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onExport: () => void;
}

export function Toolbar({
  hasActive,
  onApprove,
  onReject,
  onEdit,
  onAdd,
  onUndo,
  onRedo,
  onExport,
}: ToolbarProps) {
  return (
    <header className="flex h-11 items-center justify-between border-b border-[var(--border-subtle)] bg-[rgba(8,10,18,0.98)] px-4">
      <div className="flex items-center gap-1.5">
        <ToolbarButton
          label="Approve"
          hint="Enter"
          icon={Check}
          onClick={onApprove}
          disabled={!hasActive}
          tone="success"
        />
        <ToolbarButton
          label="Reject"
          hint="Del"
          icon={X}
          onClick={onReject}
          disabled={!hasActive}
        />
        <ToolbarButton
          label="Edit"
          hint="E"
          icon={Pencil}
          onClick={onEdit}
          disabled={!hasActive}
        />
        <ToolbarButton label="Add" hint="A" icon={Plus} onClick={onAdd} />
        <ToolbarButton label="Undo" hint="⌘Z" icon={Undo2} onClick={onUndo} />
        <ToolbarButton label="Redo" hint="⌘⇧Z" icon={Redo2} onClick={onRedo} />
      </div>
      <button
        type="button"
        onClick={onExport}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-md border border-emerald-500/50 bg-emerald-500/10 px-3 py-1.5 text-[11px] font-medium text-emerald-100",
          "hover:bg-emerald-500/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/80",
        )}
      >
        <Download className="h-3.5 w-3.5" />
        Export
        <kbd className="rounded bg-black/40 px-1 py-0.5 font-mono text-[9px]">⌘E</kbd>
      </button>
    </header>
  );
}

function ToolbarButton({
  label,
  hint,
  icon: Icon,
  onClick,
  disabled,
  tone,
}: {
  label: string;
  hint: string;
  icon: typeof Check;
  onClick: () => void;
  disabled?: boolean;
  tone?: "success";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] transition disabled:opacity-40",
        tone === "success"
          ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-100 hover:bg-emerald-500/20"
          : "border-[var(--border-subtle)] bg-black/20 text-slate-200 hover:bg-black/40",
      )}
    >
      <Icon className="h-3 w-3" />
      <span>{label}</span>
      <kbd className="rounded bg-black/40 px-1 py-0.5 font-mono text-[9px]">{hint}</kbd>
    </button>
  );
}
