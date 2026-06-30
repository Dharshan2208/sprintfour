import { AnimatePresence, motion } from "framer-motion";
import { Detection } from "../lib/types";
import { AlertTriangle, ShieldAlert, X } from "lucide-react";

interface ExportValidationModalProps {
  open: boolean;
  onClose: () => void;
  detections: Detection[];
}

export function ExportValidationModal({
  open,
  onClose,
  detections,
}: ExportValidationModalProps) {
  const unresolved = detections.filter((d) => d.status === "unreviewed");
  const lowConfidence = detections.filter(
    (d) => d.status === "unreviewed" && d.confidence < 0.6,
  );
  const missed = detections.filter((d) => d.status === "missed");

  const hasRisk = unresolved.length > 0 || lowConfidence.length > 0 || missed.length > 0;

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 z-40 bg-black/60"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center px-4"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
          >
            <div className="w-full max-w-lg rounded-xl border border-[var(--border-subtle)] bg-[rgba(5,7,14,0.98)] p-4 shadow-2xl">
              <header className="mb-3 flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-500/20 text-amber-200">
                    <ShieldAlert className="h-4 w-4" />
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-xs font-medium uppercase tracking-[0.16em] text-amber-200">
                      Safety validation
                    </span>
                    <p className="text-xs text-[var(--muted-foreground)]">
                      Final check before export. Confirm you&apos;re comfortable with residual
                      risk.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-md border border-[var(--border-subtle)] bg-black/40 p-1 text-[var(--muted-foreground)] hover:bg-black/60"
                >
                  <X className="h-3 w-3" />
                </button>
              </header>

              <div className="space-y-3 text-[11px] text-[var(--muted-foreground)]">
                {hasRisk ? (
                  <>
                    <RiskRow
                      label="Unreviewed detections"
                      count={unresolved.length}
                      tone="destructive"
                      description="AI has proposed redactions that have not been explicitly approved or rejected."
                    />
                    <RiskRow
                      label="Low-confidence detections"
                      count={lowConfidence.length}
                      tone="warning"
                      description="Model is uncertain · these are the most likely places for mistakes."
                    />
                    <RiskRow
                      label="Manually marked misses"
                      count={missed.length}
                      tone="info"
                      description="You identified areas the AI missed. Confirm similar patterns elsewhere are covered."
                    />
                    <p className="mt-2 text-[11px] leading-relaxed text-slate-200">
                      Exporting now means you accept this level of residual risk. If you&apos;re
                      unsure, prioritize a quick pass over critical and low-confidence items
                      before proceeding.
                    </p>
                  </>
                ) : (
                  <div className="flex items-center gap-3 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-[11px] text-emerald-50">
                    <AlertTriangle className="h-4 w-4" />
                    <div>
                      <p className="font-medium">No blocking risks detected</p>
                      <p className="text-[11px] text-emerald-100/80">
                        All model suggestions reviewed and no manual misses recorded. A brief
                        final skim is still recommended for highly sensitive documents.
                      </p>
                    </div>
                  </div>
                )}
              </div>

              <footer className="mt-4 flex items-center justify-between text-[10px] text-[var(--muted-foreground)]">
                <div className="flex flex-col gap-0.5">
                  <span>Exporting does not bypass policy review or legal sign-off.</span>
                  <span>
                    This check is designed to slow down only the highest-risk mistakes, not your
                    entire workflow.
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={onClose}
                    className="rounded-md border border-[var(--border-subtle)] bg-black/40 px-3 py-1.5 text-[10px] text-slate-100 hover:bg-black/60"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="rounded-md border border-emerald-500/70 bg-emerald-500/20 px-3 py-1.5 text-[10px] font-medium text-emerald-50 hover:bg-emerald-500/30"
                  >
                    Acknowledge risk & export
                  </button>
                </div>
              </footer>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function RiskRow({
  label,
  description,
  count,
  tone,
}: {
  label: string;
  description: string;
  count: number;
  tone: "destructive" | "warning" | "info";
}) {
  const color =
    tone === "destructive"
      ? "text-rose-200"
      : tone === "warning"
        ? "text-amber-200"
        : "text-sky-200";

  const border =
    tone === "destructive"
      ? "border-rose-500/50"
      : tone === "warning"
        ? "border-amber-500/50"
        : "border-sky-500/50";

  return (
    <div
      className={`flex items-start justify-between gap-3 rounded-lg border bg-black/30 px-3 py-2 ${border}`}
    >
      <div>
        <div className={`flex items-center gap-2 text-[11px] font-medium ${color}`}>
          <AlertTriangle className="h-3 w-3" />
          <span>{label}</span>
          <span className="rounded-full bg-black/50 px-1.5 py-0.5 font-mono text-[9px] text-slate-100">
            {count}
          </span>
        </div>
        <p className="mt-0.5 text-[10px] text-[var(--muted-foreground)]">{description}</p>
      </div>
    </div>
  );
}

