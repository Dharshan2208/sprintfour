"use client";

import { motion } from "framer-motion";
import {
  Crosshair,
  Eye,
  FileSearch,
  ScanSearch,
  X,
} from "lucide-react";
import type { CorrectionMode } from "../../lib/types";
import { cn } from "../../lib/utils";

interface CorrectionToolbarProps {
  mode: CorrectionMode;
  onModeChange: (mode: CorrectionMode) => void;
  batchCount: number;
  totalFiltered: number;
  onBatchApprove: () => void;
  onBatchReject: () => void;
  onClearBatch: () => void;
  onSelectAll: () => void;
  hasSelection: boolean;
  onAddMissedPii: () => void;
}

const MODES: Array<{
  key: CorrectionMode;
  label: string;
  icon: typeof Crosshair;
  hint: string;
}> = [
  { key: "off", label: "Review", icon: Eye, hint: "Standard review" },
  { key: "spot_missed", label: "Missed PII", icon: ScanSearch, hint: "Find what the tool missed" },
  { key: "review_false_positives", label: "False positives", icon: Crosshair, hint: "Fix over-redaction" },
  { key: "diff", label: "All mistakes", icon: FileSearch, hint: "Diff view" },
];

export function CorrectionToolbar({
  mode,
  onModeChange,
  batchCount,
  totalFiltered,
  onBatchApprove,
  onBatchReject,
  onClearBatch,
  onSelectAll,
  hasSelection,
  onAddMissedPii,
}: CorrectionToolbarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-[var(--border-subtle)] bg-[rgba(9,11,20,0.98)] px-3 py-2">
      <div className="flex items-center gap-1">
        <span className="mr-1 text-[10px] font-medium uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
          Mode
        </span>
        {MODES.map(({ key, label, icon: Icon, hint }) => (
          <button
            key={key}
            type="button"
            onClick={() => onModeChange(key)}
            title={hint}
            className={cn(
              "inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] transition",
              mode === key
                ? key === "off"
                  ? "border-sky-500/50 bg-sky-500/10 text-sky-100"
                  : key === "spot_missed"
                    ? "border-rose-500/50 bg-rose-500/10 text-rose-100"
                    : key === "review_false_positives"
                      ? "border-amber-500/50 bg-amber-500/10 text-amber-100"
                      : "border-violet-500/50 bg-violet-500/10 text-violet-100"
                : "border-[var(--border-subtle)] text-[var(--muted-foreground)] hover:bg-[var(--muted)]",
            )}
          >
            <Icon className="h-3 w-3" />
            <span>{label}</span>
          </button>
        ))}
      </div>

      <div className="ml-auto flex items-center gap-1.5">
        {/* Batch actions */}
        {batchCount > 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center gap-1.5 rounded-md border border-sky-500/30 bg-sky-500/8 px-2 py-1"
          >
            <span className="text-[10px] text-sky-100">{batchCount} / {totalFiltered} selected</span>
            <button
              type="button"
              onClick={onSelectAll}
              className="rounded px-1.5 py-0.5 text-[9px] font-medium text-sky-100 hover:bg-sky-500/20"
            >
              {batchCount < totalFiltered ? "Select all" : "Deselect all"}
            </button>
            <button
              type="button"
              onClick={onBatchApprove}
              className="rounded px-1.5 py-0.5 text-[9px] font-medium text-emerald-100 hover:bg-emerald-500/20"
            >
              Approve all
            </button>
            <button
              type="button"
              onClick={onBatchReject}
              className="rounded px-1.5 py-0.5 text-[9px] font-medium text-rose-100 hover:bg-rose-500/20"
            >
              Reject all
            </button>
            <button
              type="button"
              onClick={onClearBatch}
              className="rounded px-1 py-0.5 text-[9px] text-[var(--muted-foreground)] hover:bg-black/30"
            >
              <X className="h-2.5 w-2.5" />
            </button>
          </motion.div>
        )}

        {/* Add missed PII from text selection */}
        {hasSelection && (
          <motion.button
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            type="button"
            onClick={onAddMissedPii}
            className="inline-flex items-center gap-1 rounded-md border border-rose-500/50 bg-rose-500/10 px-2 py-1 text-[10px] font-medium text-rose-100"
          >
            <ScanSearch className="h-3 w-3" />
            Mark as missed PII
          </motion.button>
        )}
      </div>
    </div>
  );
}
