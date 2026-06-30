"use client";

import type { RiskReport } from "../../lib/types";
import { cn, formatRiskScore } from "../../lib/utils";
import { AlertTriangle, ShieldAlert } from "lucide-react";

interface RiskPanelProps {
  report: RiskReport | null;
}

export function RiskPanel({ report }: RiskPanelProps) {
  if (!report) {
    return (
      <div className="rounded-lg border border-[var(--border-subtle)] bg-black/20 px-3 py-2 text-[10px] text-[var(--muted-foreground)]">
        Risk assessment loading…
      </div>
    );
  }

  const risk = formatRiskScore(report.overall_score);
  const progress = report.review_progress;

  return (
    <div className="space-y-2 rounded-lg border border-[var(--border-subtle)] bg-black/20 px-3 py-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-[10px] text-slate-200">
          <ShieldAlert className="h-3.5 w-3.5 text-amber-300" />
          <span>Risk</span>
        </div>
        <span
          className={cn(
            "rounded-full px-2 py-0.5 font-mono text-[10px]",
            risk.pct >= 70 ? "bg-amber-500/10 text-amber-100" : "bg-emerald-500/10 text-emerald-100",
          )}
        >
          {risk.pct} · {risk.label}
        </span>
      </div>

      <div>
        <div className="mb-1 flex justify-between text-[9px] text-[var(--muted-foreground)]">
          <span>Review progress</span>
          <span>{Math.round(progress.review_percentage)}%</span>
        </div>
        <div className="h-1.5 rounded-full bg-black/40">
          <div
            className="h-full rounded-full bg-emerald-400/80 transition-all"
            style={{ width: `${progress.review_percentage}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-[10px]">
        <Metric label="Critical" value={report.critical_items.length} tone="danger" />
        <Metric label="Pending" value={progress.pending_count} tone="warning" />
        <Metric
          label="Export"
          value={report.export_ready ? "Ready" : "Blocked"}
          tone={report.export_ready ? "success" : "warning"}
        />
        <Metric label="Reviewed" value={`${progress.reviewed_count}/${progress.total_items}`} />
      </div>

      {report.warnings[0] && (
        <p className="flex items-start gap-1.5 text-[10px] text-amber-100/90">
          <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
          <span>{report.warnings[0]}</span>
        </p>
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string | number;
  tone?: "danger" | "warning" | "success";
}) {
  const toneClass =
    tone === "danger"
      ? "text-rose-200"
      : tone === "warning"
        ? "text-amber-200"
        : tone === "success"
          ? "text-emerald-200"
          : "text-slate-200";

  return (
    <div className="rounded-md border border-[var(--border-subtle)] bg-black/20 px-2 py-1.5">
      <div className="text-[9px] uppercase tracking-[0.14em] text-[var(--muted-foreground)]">
        {label}
      </div>
      <div className={cn("font-mono text-[11px]", toneClass)}>{value}</div>
    </div>
  );
}
