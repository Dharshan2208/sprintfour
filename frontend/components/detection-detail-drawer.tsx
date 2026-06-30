import { motion, AnimatePresence } from "framer-motion";
import { Detection } from "../lib/types";
import { cn, formatConfidence, formatSeverity, formatStatus } from "../lib/utils";
import { documentParagraphs } from "../lib/mock-data";
import { Info, Clock, Flag, FileText } from "lucide-react";

interface DetectionDetailDrawerProps {
  detection: Detection | null;
  open: boolean;
  onClose: () => void;
}

export function DetectionDetailDrawer({
  detection,
  open,
  onClose,
}: DetectionDetailDrawerProps) {
  return (
    <AnimatePresence>
      {open && detection && (
        <>
          <motion.div
            className="fixed inset-0 z-30 bg-black/40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            className="fixed inset-y-0 right-0 z-40 w-full max-w-md border-l border-[var(--border-subtle)] bg-[rgba(6,8,16,0.98)] px-4 py-4 shadow-xl backdrop-blur-md"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 260, damping: 30 }}
            aria-label="Detection details"
          >
            <header className="mb-3 flex items-start justify-between gap-2">
              <div className="flex flex-col gap-1">
                <span className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
                  Detection details
                </span>
                <p className="font-mono text-xs text-slate-50">{detection.text}</p>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border border-[var(--border-subtle)] bg-black/40 px-2 py-1 text-[10px] text-[var(--muted-foreground)] hover:bg-black/60"
              >
                Esc to close
              </button>
            </header>

            <div className="space-y-3 text-[11px] text-[var(--muted-foreground)]">
              <section className="grid grid-cols-2 gap-2 rounded-md border border-[var(--border-subtle)] bg-[var(--muted)]/50 px-2.5 py-2">
                <InfoRow
                  label="Severity"
                  value={formatSeverity(detection.severity)}
                  strong
                />
                <InfoRow label="Confidence" value={formatConfidence(detection.confidence)} />
                <InfoRow
                  label="Status"
                  value={formatStatus(detection.status)}
                  muted={detection.status === "unreviewed"}
                />
                <InfoRow
                  label="Source"
                  value={detection.source === "model" ? "Model" : detection.source}
                />
              </section>

              <section className="rounded-md border border-[var(--border-subtle)] bg-[rgba(8,10,18,0.9)] px-2.5 py-2">
                <div className="mb-1.5 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.16em] text-slate-200">
                  <Flag className="h-3 w-3 text-sky-300" />
                  <span>Why this was flagged</span>
                </div>
                <p className="text-[11px] leading-relaxed text-slate-200">
                  {detection.explanation}
                </p>
              </section>

              <section className="rounded-md border border-[var(--border-subtle)] bg-[rgba(8,10,18,0.9)] px-2.5 py-2">
                <div className="mb-1.5 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.16em] text-slate-200">
                  <FileText className="h-3 w-3 text-amber-300" />
                  <span>Surrounding context</span>
                </div>
                <ContextSnippet detection={detection} />
              </section>

              <section className="rounded-md border border-[var(--border-subtle)] bg-[rgba(8,10,18,0.9)] px-2.5 py-2">
                <div className="mb-1.5 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.16em] text-slate-200">
                  <Clock className="h-3 w-3 text-slate-300" />
                  <span>Audit trail</span>
                </div>
                <p className="mb-1 text-[10px] text-[var(--muted-foreground)]">
                  Decisions are logged for downstream audit and safety review.
                </p>
                <div className="space-y-1.5">
                  {detection.auditTrail?.map((entry, idx) => (
                    <div
                      key={`${entry.at}-${idx}`}
                      className="flex items-start justify-between gap-2 rounded border border-[var(--border-subtle)]/70 bg-black/40 px-2 py-1.5"
                    >
                      <div className="flex flex-col gap-0.5">
                        <span className="text-[10px] text-slate-100">
                          {entry.action === "auto_flagged"
                            ? "AI model flag"
                            : entry.action === "approved"
                              ? "Approved"
                              : entry.action === "rejected"
                                ? "Rejected"
                                : "Marked as missed"}
                        </span>
                        {entry.note && (
                          <span className="text-[10px] text-[var(--muted-foreground)]">
                            {entry.note}
                          </span>
                        )}
                      </div>
                      <span className="whitespace-nowrap text-[9px] font-mono text-[var(--muted-foreground)]">
                        {new Date(entry.at).toLocaleTimeString(undefined, {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>
                  )) ?? (
                    <div className="rounded border border-dashed border-[var(--border-subtle)] px-2 py-1.5 text-[10px] text-[var(--muted-foreground)]">
                      No audit entries yet. Actions taken here will appear for future safety
                      review.
                    </div>
                  )}
                </div>
              </section>

              <section className="rounded-md border border-[var(--border-subtle)] bg-[rgba(8,10,18,0.9)] px-2.5 py-2">
                <div className="mb-1.5 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.16em] text-slate-200">
                  <Info className="h-3 w-3 text-emerald-300" />
                  <span>Recommended reviewer posture</span>
                </div>
                <p className="text-[11px] leading-relaxed text-slate-200">
                  Treat the model as a helpful but fallible assistant. Confirm that redaction
                  is consistent with your policy and scan nearby context for missed PII before
                  approving.
                </p>
              </section>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

function InfoRow({
  label,
  value,
  strong,
  muted,
}: {
  label: string;
  value: string;
  strong?: boolean;
  muted?: boolean;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[9px] uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
        {label}
      </span>
      <span
        className={cn(
          "text-[11px]",
          strong && "font-medium text-slate-50",
          muted && "text-amber-300",
        )}
      >
        {value}
      </span>
    </div>
  );
}

function ContextSnippet({ detection }: { detection: Detection }) {
  const paragraph = documentParagraphs[detection.paragraphIndex] ?? "";
  const contextRadius = 60;
  const start = Math.max(0, detection.start - contextRadius);
  const end = Math.min(paragraph.length, detection.end + contextRadius);

  const before = paragraph.slice(start, detection.start);
  const target = paragraph.slice(detection.start, detection.end);
  const after = paragraph.slice(detection.end, end);

  return (
    <p className="font-mono text-[11px] leading-relaxed text-slate-100">
      {start > 0 && <span className="text-slate-500/80">…</span>}
      <span className="text-slate-400">{before}</span>
      <mark className="rounded-[3px] bg-amber-500/30 px-0.5 text-slate-900">
        {target}
      </mark>
      <span className="text-slate-400">{after}</span>
      {end < paragraph.length && <span className="text-slate-500/80">…</span>}
    </p>
  );
}

