"use client";

import { motion } from "framer-motion";
import { Check, Square, X } from "lucide-react";
import type { ReviewEntity } from "../../lib/types";
import { cn, formatConfidence, formatPriority, formatReviewState } from "../../lib/utils";

interface ReviewCardProps {
  entity: ReviewEntity;
  isActive: boolean;
  isHovered: boolean;
  batchSelected?: boolean;
  onSelect: () => void;
  onApprove: () => void;
  onReject: () => void;
  onHover: (hovered: boolean) => void;
  onToggleBatch?: () => void;
  compact?: boolean;
}

export function ReviewCard({
  entity,
  isActive,
  isHovered,
  batchSelected,
  onSelect,
  onApprove,
  onReject,
  onHover,
  onToggleBatch,
  compact = false,
}: ReviewCardProps) {
  if (compact) {
    return (
      <div className="flex items-center gap-1">
        {onToggleBatch && (
          <button
            type="button"
            onClick={onToggleBatch}
            className="shrink-0 rounded p-0.5 text-[var(--muted-foreground)] hover:text-slate-100"
          >
            <Square
              className={cn(
                "h-3 w-3",
                batchSelected && "fill-sky-500/40 text-sky-400",
              )}
            />
          </button>
        )}
        <button
          type="button"
          onClick={onSelect}
          onMouseEnter={() => onHover(true)}
          onMouseLeave={() => onHover(false)}
          className={cn(
            "flex w-full items-center justify-between rounded-md border px-2 py-1.5 text-left text-[10px]",
            "border-[var(--border-subtle)] bg-[rgba(12,14,22,0.9)]",
            batchSelected && "border-sky-500/50 bg-sky-500/8",
            (isActive || isHovered) && "border-sky-400/70 bg-sky-500/10",
          )}
        >
          <span className="line-clamp-1 font-mono text-slate-100">{entity.entity}</span>
          <span className="text-[var(--muted-foreground)]">{formatReviewState(entity.reviewState)}</span>
        </button>
      </div>
    );
  }

  return (
    <motion.article
      layout
      transition={{ duration: 0.16 }}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
      className={cn(
        "rounded-lg border px-3 py-2 text-xs transition",
        "border-[var(--border-subtle)] bg-[rgba(10,12,20,0.9)] hover:border-sky-500/50 hover:bg-sky-500/5",
        batchSelected && "border-sky-500/60 bg-sky-500/8 shadow-[0_0_0_1px_rgba(56,189,248,0.3)]",
        (isActive || isHovered) &&
          "border-sky-400/80 bg-sky-500/10 shadow-[0_0_0_1px_rgba(56,189,248,0.35)]",
      )}
    >
      <div className="flex items-start gap-2">
        {onToggleBatch && (
          <button
            type="button"
            onClick={onToggleBatch}
            className="mt-0.5 shrink-0 rounded p-0.5 text-[var(--muted-foreground)] hover:text-slate-100"
          >
            <Square
              className={cn(
                "h-3.5 w-3.5",
                batchSelected && "fill-sky-500/40 text-sky-400",
              )}
            />
          </button>
        )}
        <button type="button" onClick={onSelect} className="min-w-0 flex-1 text-left">
          <div className="flex items-start justify-between gap-2">
            <p className="line-clamp-2 font-mono text-[11px] text-slate-100">{entity.entity}</p>
            <span className="shrink-0 rounded-full bg-black/40 px-1.5 py-0.5 text-[9px] text-amber-100">
              {formatPriority(entity.priority)}
            </span>
          </div>
          <p className="mt-1 line-clamp-2 text-[11px] text-[var(--muted-foreground)]">
            {entity.reason}
          </p>
        </button>
      </div>

      <div className="mt-2 flex items-center justify-between text-[10px] text-[var(--muted-foreground)]">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-black/40 px-1.5 py-0.5 font-mono text-[9px]">
            {formatConfidence(entity.confidence)}
          </span>
          <span className="uppercase tracking-[0.14em]">{entity.entityType}</span>
        </div>
        <span>P{entity.page || "—"}</span>
      </div>

      <div className="mt-2 flex items-center gap-1.5">
        <ActionChip label="Approve" hint="Enter" icon={Check} onClick={onApprove} tone="success" />
        <ActionChip label="Reject" hint="Del" icon={X} onClick={onReject} />
      </div>
    </motion.article>
  );
}

function ActionChip({
  label,
  hint,
  icon: Icon,
  onClick,
  tone,
}: {
  label: string;
  hint: string;
  icon: typeof Check;
  onClick: () => void;
  tone?: "success";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px]",
        tone === "success"
          ? "border-emerald-500/60 bg-emerald-500/10 text-emerald-100 hover:bg-emerald-500/20"
          : "border-slate-600/80 bg-slate-800/70 text-slate-100 hover:bg-slate-700/80",
      )}
    >
      <Icon className="h-3 w-3" />
      <span>{label}</span>
      <kbd className="rounded bg-black/40 px-1 py-0.5 font-mono text-[9px]">{hint}</kbd>
    </button>
  );
}
