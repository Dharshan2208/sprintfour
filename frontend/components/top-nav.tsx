import { ShieldCheck, FileText, Download } from "lucide-react";
import { documentMetadata, reviewStats } from "../lib/mock-data";
import { cn } from "../lib/utils";

export function TopNav() {
  const remaining = documentMetadata.unreviewedCount;

  return (
    <header className="flex h-14 items-center border-b border-[var(--border-subtle)] bg-[rgba(9,10,16,0.92)] px-4 backdrop-blur-sm">
      <div className="flex flex-1 items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/40">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div className="flex flex-col leading-tight">
            <span className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
              Sentinel
            </span>
            <span className="text-[11px] text-[var(--muted-foreground)]">
              Anonymization review workspace
            </span>
          </div>
        </div>

        <div className="mx-4 h-6 w-px bg-[var(--border-subtle)]" />

        <div className="hidden items-center gap-2 md:flex">
          <FileText className="h-4 w-4 text-sky-300/90" />
          <span className="truncate text-sm font-medium text-sky-50/90">
            {documentMetadata.title}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4 text-xs">
        <RiskBadge score={documentMetadata.riskScore} />

        <div className="hidden items-baseline gap-1 sm:flex">
          <span className="font-mono text-[11px] text-[var(--muted-foreground)]">
            Remaining
          </span>
          <span className="rounded-full bg-[var(--muted)] px-2 py-0.5 font-mono text-[11px]">
            {remaining}
          </span>
        </div>

        <div className="hidden items-center gap-2 border-l border-[var(--border-subtle)] pl-4 md:flex">
          <div className="flex flex-col text-[10px] leading-tight text-[var(--muted-foreground)]">
            <span className="font-medium uppercase tracking-[0.16em]">
              Shortcuts
            </span>
            <span>A = approve · R = reject · M = missed · Tab = next</span>
          </div>
        </div>

        <button
          className={cn(
            "inline-flex items-center gap-1 rounded-md border border-emerald-500/50 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-100 shadow-sm",
            "hover:bg-emerald-500/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/80 focus-visible:ring-offset-0",
          )}
        >
          <Download className="h-3.5 w-3.5" />
          <span>Export</span>
        </button>

        <div className="ml-2 flex h-7 w-7 items-center justify-center rounded-full bg-[var(--muted)] text-[11px] font-medium text-[var(--muted-foreground)]">
          JD
        </div>
      </div>
    </header>
  );
}

function RiskBadge({ score }: { score: number }) {
  const level =
    score >= 85 ? "Severe" : score >= 70 ? "High" : score >= 50 ? "Elevated" : "Moderate";

  const colorClasses =
    score >= 85
      ? "bg-rose-500/10 text-rose-200 ring-rose-500/40"
      : score >= 70
        ? "bg-amber-500/10 text-amber-200 ring-amber-500/40"
        : "bg-sky-500/10 text-sky-200 ring-sky-500/40";

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-3 py-1 text-[11px] font-medium ring-1",
        colorClasses,
      )}
      aria-label={`Document risk score ${score}, level ${level}`}
    >
      <span className="font-mono tabular-nums">{score}</span>
      <span className="uppercase tracking-[0.16em]">{level}</span>
    </div>
  );
}

