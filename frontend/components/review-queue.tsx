import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Detection } from "../lib/types";
import { cn, formatConfidence, formatSeverity } from "../lib/utils";
import {
  Check,
  X,
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  Search,
  Circle,
  ShieldAlert,
} from "lucide-react";

interface ReviewQueueProps {
  items: Detection[];
  activeId: string | null;
  onSelect: (d: Detection) => void;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onMarkMissed: (id: string) => void;
  stats: {
    total: number;
    reviewed: number;
    unreviewed: number;
    unresolvedRisk: number;
    lowConfidence: number;
    criticalOpen: number;
  };
}

export function ReviewQueue({
  items,
  activeId,
  onSelect,
  onApprove,
  onReject,
  onMarkMissed,
  stats,
}: ReviewQueueProps) {
  const [query, setQuery] = useState("");
  const activeRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!activeRef.current) return;
    activeRef.current.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [activeId]);

  const search = query.trim().toLowerCase();
  const visibleItems = search
    ? items.filter((d) => {
        const haystack =
          `${d.text} ${d.kind} ${d.explanation} ${d.source} ${d.status}`.toLowerCase();
        return haystack.includes(search);
      })
    : items;

  const critical = visibleItems.filter(
    (d) => (d.severity === "critical" || d.status === "missed") && d.status !== "approved",
  );
  const needsReview = visibleItems.filter(
    (d) => d.status === "unreviewed" && d.severity !== "critical",
  );
  const reviewed = visibleItems.filter((d) => d.status !== "unreviewed" && d.status !== "missed");
  const completionPct = Math.round((stats.reviewed / Math.max(stats.total, 1)) * 100);

  return (
    <aside className="flex h-full flex-col rounded-xl border border-[var(--border-subtle)] bg-[rgba(9,11,20,0.98)]">
      <div className="sticky top-0 z-10 border-b border-[var(--border-subtle)] bg-[rgba(9,11,20,0.98)]">
        <header className="flex items-center justify-between gap-2 px-4 py-2.5">
          <div className="flex flex-col gap-0.5">
            <span className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
              Review queue
            </span>
            <span className="text-[11px] text-[var(--muted-foreground)]">
              Triage unresolved risk before obvious model matches.
            </span>
          </div>
          <div className="flex flex-col items-end text-[10px] text-[var(--muted-foreground)]">
            <span className="font-mono tabular-nums">
              {stats.reviewed}/{stats.total} reviewed
            </span>
            <span className="text-[10px]">Arrow keys navigate</span>
          </div>
        </header>

        <div className="px-3 pb-2">
          <div className="mb-2 rounded-md border border-amber-500/30 bg-amber-500/10 px-2.5 py-1.5">
            <div className="mb-1 flex items-center justify-between text-[10px]">
              <div className="flex items-center gap-1.5 text-amber-100">
                <ShieldAlert className="h-3.5 w-3.5" />
                <span>Unresolved risk</span>
              </div>
              <span className="font-mono text-amber-50">{stats.unresolvedRisk}</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-black/40">
              <motion.div
                className="h-full rounded-full bg-emerald-400/80"
                initial={false}
                animate={{ width: `${completionPct}%` }}
                transition={{ duration: 0.2 }}
              />
            </div>
            <div className="mt-1 flex justify-between text-[9px] text-[var(--muted-foreground)]">
              <span>{completionPct}% complete</span>
              <span>{stats.criticalOpen} critical open</span>
            </div>
          </div>

          <label className="flex items-center gap-2 rounded-md border border-[var(--border-subtle)] bg-[var(--muted)]/70 px-2 py-1.5 text-[11px] text-[var(--muted-foreground)]">
            <Search className="h-3.5 w-3.5" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search entity, type, source"
              className="w-full bg-transparent outline-none placeholder:text-[var(--muted-foreground)]"
            />
          </label>
        </div>
      </div>

      <div className="scrollbar-thin flex-1 space-y-4 overflow-auto px-3 py-3">
        <SectionLabel
          label="Critical risks"
          count={critical.length}
          tone="destructive"
          description="Missed entities and high-impact risk signals."
        />
        <div className="space-y-2">
          {critical.length === 0 && (
            <EmptyHint label="No unresolved critical issues. Focus on uncertainty next." />
          )}
          {critical.map((d) => (
            <div key={d.id} ref={d.id === activeId ? activeRef : undefined}>
              <QueueItem
                detection={d}
                isActive={d.id === activeId}
                onSelect={() => onSelect(d)}
                onApprove={() => onApprove(d.id)}
                onReject={() => onReject(d.id)}
                onMarkMissed={() => onMarkMissed(d.id)}
              />
            </div>
          ))}
        </div>

        <SectionLabel
          label="Needs review"
          count={needsReview.length}
          tone="warning"
          description="Low-confidence or contextual items where human judgment matters."
        />
        <div className="space-y-2">
          {needsReview.length === 0 && (
            <EmptyHint label="All model flags reviewed. Scan for missed PII before export." />
          )}
          {needsReview.map((d) => (
            <div key={d.id} ref={d.id === activeId ? activeRef : undefined}>
              <QueueItem
                detection={d}
                isActive={d.id === activeId}
                onSelect={() => onSelect(d)}
                onApprove={() => onApprove(d.id)}
                onReject={() => onReject(d.id)}
                onMarkMissed={() => onMarkMissed(d.id)}
              />
            </div>
          ))}
        </div>

        <SectionLabel
          label="Reviewed"
          count={reviewed.length}
          tone="muted"
          description="Approved redactions, false positives, and manual misses."
        />
        <div className="space-y-1.5">
          {reviewed.length === 0 && (
            <EmptyHint label="Nothing reviewed yet. Start with critical items above." />
          )}
          {reviewed.map((d) => (
            <ReviewedRow key={d.id} detection={d} isActive={d.id === activeId} />
          ))}
        </div>
      </div>

      <footer className="border-t border-[var(--border-subtle)] px-3 py-2 text-[10px] text-[var(--muted-foreground)]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <kbd className="rounded border border-[var(--border-subtle)] bg-black/30 px-1.5 py-0.5 font-mono text-[9px]">
              ↑
            </kbd>
            <span>Previous</span>
            <kbd className="ml-2 rounded border border-[var(--border-subtle)] bg-black/30 px-1.5 py-0.5 font-mono text-[9px]">
              ↓
            </kbd>
            <span>Next</span>
            <kbd className="ml-2 rounded border border-[var(--border-subtle)] bg-black/30 px-1.5 py-0.5 font-mono text-[9px]">
              Enter
            </kbd>
            <span>Approve</span>
            <kbd className="ml-2 rounded border border-[var(--border-subtle)] bg-black/30 px-1.5 py-0.5 font-mono text-[9px]">
              Del
            </kbd>
            <span>Reject</span>
          </div>
          <div className="flex items-center gap-1 text-[9px]">
            <ArrowUp className="h-3 w-3" />
            <ArrowDown className="h-3 w-3" />
            <span>Space = details</span>
          </div>
        </div>
      </footer>
    </aside>
  );
}

function SectionLabel({
  label,
  description,
  count,
  tone,
}: {
  label: string;
  description: string;
  count: number;
  tone: "destructive" | "warning" | "muted";
}) {
  const color =
    tone === "destructive"
      ? "text-rose-300"
      : tone === "warning"
        ? "text-amber-300"
        : "text-slate-300";

  const dot =
    tone === "destructive"
      ? "text-rose-400"
      : tone === "warning"
        ? "text-amber-400"
        : "text-slate-500";

  return (
    <div className="flex items-start justify-between text-[11px]">
      <div>
        <div className={cn("flex items-center gap-1.5 font-medium", color)}>
          <Circle className={cn("h-2 w-2", dot)} />
          <span>{label}</span>
          <span className="rounded-full bg-black/40 px-1.5 py-0.5 font-mono text-[9px] text-slate-200">
            {count}
          </span>
        </div>
        <p className="mt-0.5 text-[10px] text-[var(--muted-foreground)]">{description}</p>
      </div>
    </div>
  );
}

function QueueItem({
  detection,
  isActive,
  onSelect,
  onApprove,
  onReject,
  onMarkMissed,
}: {
  detection: Detection;
  isActive: boolean;
  onSelect: () => void;
  onApprove: () => void;
  onReject: () => void;
  onMarkMissed: () => void;
}) {
  return (
    <AnimatePresence initial={false}>
      <motion.article
        layout
        transition={{ duration: 0.16 }}
        className={cn(
          "group rounded-lg border px-3 py-2 text-xs transition",
          "border-[var(--border-subtle)] bg-[rgba(10,12,20,0.9)] hover:-translate-y-[1px] hover:border-sky-500/60 hover:bg-sky-500/5",
          isActive &&
            "border-sky-400/80 bg-sky-500/10 shadow-[0_0_0_1px_rgba(56,189,248,0.5),0_0_24px_rgba(56,189,248,0.18)]",
        )}
      >
        <button
          type="button"
          onClick={onSelect}
          className="flex w-full flex-col items-start gap-1 text-left"
        >
          <div className="flex w-full items-start justify-between gap-2">
            <p className="line-clamp-2 font-mono text-[11px] text-slate-100">{detection.text}</p>
            <SeverityPill detection={detection} />
          </div>
          <p className="line-clamp-2 text-[11px] text-[var(--muted-foreground)]">
            {detection.explanation}
          </p>
        </button>

        <div className="mt-2 flex items-center justify-between text-[10px] text-[var(--muted-foreground)]">
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-black/40 px-1.5 py-0.5 font-mono text-[9px]">
              {formatConfidence(detection.confidence)}
            </span>
            <span className="uppercase tracking-[0.16em]">{detection.kind.toUpperCase()}</span>
          </div>
          <span>{detection.source}</span>
        </div>

        <div className="mt-2 flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <ActionChip label="Approve" hint="Enter" tone="success" icon={Check} onClick={onApprove} />
            <ActionChip label="Reject" hint="Del" tone="muted" icon={X} onClick={onReject} />
            <ActionChip
              label="Missed"
              hint="M"
              tone="warning"
              icon={AlertTriangle}
              onClick={onMarkMissed}
            />
          </div>
          <span className="text-[9px] text-[var(--muted-foreground)]">Space: inspect</span>
        </div>
      </motion.article>
    </AnimatePresence>
  );
}

function SeverityPill({ detection }: { detection: Detection }) {
  const label = formatSeverity(detection.severity);
  const base = "rounded-full px-1.5 py-0.5 text-[10px] font-medium";

  if (detection.severity === "critical") {
    return (
      <span className={cn(base, "bg-rose-500/20 text-rose-100 ring-1 ring-rose-500/50")}>
        {label}
      </span>
    );
  }

  if (detection.severity === "high") {
    return (
      <span className={cn(base, "bg-amber-500/20 text-amber-100 ring-1 ring-amber-500/40")}>
        {label}
      </span>
    );
  }

  if (detection.severity === "medium") {
    return (
      <span className={cn(base, "bg-sky-500/15 text-sky-100 ring-1 ring-sky-500/40")}>
        {label}
      </span>
    );
  }

  return (
    <span className={cn(base, "bg-slate-700/40 text-slate-200 ring-1 ring-slate-500/40")}>
      {label}
    </span>
  );
}

function ActionChip({
  label,
  hint,
  tone,
  icon: Icon,
  onClick,
}: {
  label: string;
  hint: string;
  tone: "success" | "warning" | "muted";
  icon: typeof Check;
  onClick: () => void;
}) {
  const base =
    "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-0";

  const toneClasses =
    tone === "success"
      ? "border-emerald-500/60 bg-emerald-500/10 text-emerald-100 hover:bg-emerald-500/20 focus-visible:ring-emerald-500/70"
      : tone === "warning"
        ? "border-amber-500/60 bg-amber-500/10 text-amber-100 hover:bg-amber-500/20 focus-visible:ring-amber-500/70"
        : "border-slate-600/80 bg-slate-800/70 text-slate-100 hover:bg-slate-700/80 focus-visible:ring-slate-400/80";

  return (
    <button type="button" onClick={onClick} className={cn(base, toneClasses)}>
      <Icon className="h-3 w-3" />
      <span>{label}</span>
      <kbd className="rounded bg-black/40 px-1 py-0.5 font-mono text-[9px]">
        {hint}
      </kbd>
    </button>
  );
}

function ReviewedRow({ detection, isActive }: { detection: Detection; isActive: boolean }) {
  return (
    <div
      className={cn(
        "flex items-center justify-between rounded-md border px-2 py-1.5 text-[10px]",
        "border-[var(--border-subtle)] bg-[rgba(12,14,22,0.9)]",
        isActive && "border-sky-400/70 bg-sky-500/10",
      )}
    >
      <div className="flex flex-1 flex-col">
        <span className="line-clamp-1 font-mono text-[10px] text-slate-100">
          {detection.text}
        </span>
        <span className="mt-0.5 text-[9px] text-[var(--muted-foreground)]">
          {detection.status === "approved"
            ? "Approved redaction"
            : detection.status === "rejected"
              ? "False positive"
              : "Manually added miss"}
        </span>
      </div>
      <div className="ml-2 flex flex-col items-end text-[9px] text-[var(--muted-foreground)]">
        <span className="font-mono">{formatConfidence(detection.confidence)}</span>
        <span className="uppercase tracking-[0.16em]">
          {detection.kind.toUpperCase()}
        </span>
      </div>
    </div>
  );
}

function EmptyHint({ label }: { label: string }) {
  return (
    <div className="rounded-md border border-dashed border-[var(--border-subtle)] bg-[var(--muted)]/40 px-2 py-1.5 text-[10px] text-[var(--muted-foreground)]">
      {label}
    </div>
  );
}

