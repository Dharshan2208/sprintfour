"use client";

import type { FilterKey } from "../../lib/types";
import { cn } from "../../lib/utils";

const FILTERS: Array<{ key: FilterKey; label: string }> = [
  { key: "all", label: "All" },
  { key: "critical", label: "Critical" },
  { key: "needs_review", label: "Needs review" },
  { key: "low_confidence", label: "Low confidence" },
  { key: "manual", label: "Manual" },
  { key: "approved", label: "Approved" },
  { key: "false_positive", label: "False positive" },
];

interface FilterPanelProps {
  activeFilter: FilterKey;
  counts: Partial<Record<FilterKey, number>>;
  onChange: (filter: FilterKey) => void;
}

export function FilterPanel({ activeFilter, counts, onChange }: FilterPanelProps) {
  return (
    <div className="flex flex-wrap gap-1">
      {FILTERS.map(({ key, label }) => (
        <button
          key={key}
          type="button"
          onClick={() => onChange(key)}
          className={cn(
            "rounded-full border px-2 py-0.5 text-[10px] transition",
            activeFilter === key
              ? "border-sky-500/50 bg-sky-500/10 text-sky-100"
              : "border-[var(--border-subtle)] text-[var(--muted-foreground)] hover:bg-[var(--muted)]",
          )}
        >
          {label}
          {counts[key] !== undefined && (
            <span className="ml-1 font-mono text-[9px]">{counts[key]}</span>
          )}
        </button>
      ))}
    </div>
  );
}
