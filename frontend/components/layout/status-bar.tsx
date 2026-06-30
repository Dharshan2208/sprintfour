"use client";

import type { ReviewStats } from "../../lib/types";
import { cn, formatRiskScore } from "../../lib/utils";

interface StatusBarProps {
  filename?: string;
  stats: ReviewStats;
  riskScore?: number;
  exportReady?: boolean;
  isMutating?: boolean;
}

export function StatusBar({
  filename,
  stats,
  riskScore,
  exportReady,
  isMutating,
}: StatusBarProps) {
  const risk = riskScore === undefined ? null : formatRiskScore(riskScore);

  return (
    <footer className="flex h-9 items-center justify-between border-t border-[var(--border-subtle)] bg-[rgba(8,10,18,0.98)] px-4 text-[10px] text-[var(--muted-foreground)]">
      <div className="flex items-center gap-3">
        {filename && <span className="truncate text-slate-200">{filename}</span>}
        <span>
          {stats.reviewed}/{stats.total} reviewed
        </span>
        <span>{stats.criticalCompletion}% critical done</span>
        {stats.manualAdditions > 0 && <span>{stats.manualAdditions} manual</span>}
      </div>
      <div className="flex items-center gap-3">
        {risk && (
          <span
            className={cn(
              "rounded-full px-2 py-0.5 font-mono",
              risk.pct >= 70
                ? "bg-amber-500/10 text-amber-100"
                : "bg-emerald-500/10 text-emerald-100",
            )}
          >
            Risk {risk.pct}
          </span>
        )}
        <span className={exportReady ? "text-emerald-200" : "text-amber-200"}>
          Export {exportReady ? "ready" : "blocked"}
        </span>
        {isMutating && <span className="text-sky-200">Saving…</span>}
      </div>
    </footer>
  );
}
