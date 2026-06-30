"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Plus, X } from "lucide-react";
import { cn } from "../../lib/utils";

const QUICK_TYPES = [
  { type: "PERSON", label: "Person name", color: "ros" },
  { type: "PHONE", label: "Phone number", color: "sky" },
  { type: "EMAIL", label: "Email address", color: "sky" },
  { type: "AADHAAR", label: "Aadhaar", color: "red" },
  { type: "PAN", label: "PAN card", color: "red" },
  { type: "ADDRESS", label: "Address", color: "amber" },
  { type: "ORGANIZATION", label: "Organization", color: "amber" },
  { type: "CREDIT_CARD", label: "Credit card", color: "red" },
  { type: "DATE_OF_BIRTH", label: "DOB", color: "amber" },
  { type: "URL", label: "URL", color: "slat" },
];

interface AddMissedPiiPopoverProps {
  selectedText: string;
  anchorRect: DOMRect | null;
  onAdd: (entityType: string) => void;
  onClose: () => void;
}

export function AddMissedPiiPopover({
  selectedText,
  anchorRect,
  onAdd,
  onClose,
}: AddMissedPiiPopoverProps) {
  const [customType, setCustomType] = useState("");
  const [showCustom, setShowCustom] = useState(false);

  if (!selectedText || !anchorRect) return null;

  // Position above or below the selection
  const top = anchorRect.top - 8;
  const left = Math.min(
    anchorRect.left,
    window.innerWidth - 320,
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 4, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 4, scale: 0.96 }}
      className="fixed z-50 w-72 rounded-xl border border-[var(--border-subtle)] bg-[rgba(6,8,16,0.98)] p-3 shadow-2xl"
      style={{ top: top - 4, left: Math.max(8, left) }}
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <div>
          <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-rose-200">
            Missed PII detected
          </p>
          <p className="mt-0.5 line-clamp-2 font-mono text-[11px] text-slate-100">
            &ldquo;{selectedText.length > 60 ? selectedText.slice(0, 60) + "…" : selectedText}&rdquo;
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="shrink-0 rounded border border-[var(--border-subtle)] p-0.5 text-[var(--muted-foreground)]"
        >
          <X className="h-3 w-3" />
        </button>
      </div>

      <p className="mb-1.5 text-[9px] uppercase tracking-[0.14em] text-[var(--muted-foreground)]">
        Quick select type
      </p>
      <div className="flex flex-wrap gap-1">
        {QUICK_TYPES.map(({ type, label, color }) => (
          <button
            key={type}
            type="button"
            onClick={() => onAdd(type)}
            className={cn(
              "rounded-md border px-1.5 py-0.5 text-[9px] transition hover:opacity-80",
              color === "ros" && "border-rose-500/40 bg-rose-500/10 text-rose-100",
              color === "sky" && "border-sky-500/40 bg-sky-500/10 text-sky-100",
              color === "red" && "border-red-500/40 bg-red-500/10 text-red-100",
              color === "amber" && "border-amber-500/40 bg-amber-500/10 text-amber-100",
              color === "slat" && "border-slate-500/40 bg-slate-500/10 text-slate-100",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="mt-2">
        {showCustom ? (
          <div className="flex items-center gap-1">
            <input
              value={customType}
              onChange={(e) => setCustomType(e.target.value.toUpperCase())}
              placeholder="CUSTOM_TYPE"
              className="w-full rounded border border-[var(--border-subtle)] bg-black/30 px-1.5 py-0.5 text-[10px] font-mono outline-none"
            />
            <button
              type="button"
              onClick={() => {
                if (customType.trim()) onAdd(customType.trim());
              }}
              disabled={!customType.trim()}
              className="rounded border border-emerald-500/50 bg-emerald-500/10 px-1.5 py-0.5 text-[9px] text-emerald-100 disabled:opacity-40"
            >
              Add
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setShowCustom(true)}
            className="inline-flex items-center gap-1 text-[9px] text-[var(--muted-foreground)] hover:text-slate-100"
          >
            <Plus className="h-2.5 w-2.5" />
            Custom type
          </button>
        )}
      </div>
    </motion.div>
  );
}
