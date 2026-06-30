"use client";

import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, ShieldAlert, X } from "lucide-react";
import type { RiskReport, ValidationResult } from "../../lib/types";

interface ValidationModalProps {
  open: boolean;
  validation: ValidationResult | null;
  riskReport: RiskReport | null;
  isLoading: boolean;
  onClose: () => void;
  onContinue: () => void;
}

export function ValidationModal({
  open,
  validation,
  riskReport,
  isLoading,
  onClose,
  onContinue,
}: ValidationModalProps) {
  const blocking = validation?.issues.filter((issue) => issue.severity === "error") ?? [];
  const warnings = validation?.issues.filter((issue) => issue.severity !== "error") ?? [];
  const canContinue = validation?.is_valid === true;

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
                  <div>
                    <p className="text-xs font-medium uppercase tracking-[0.16em] text-amber-200">
                      Export validation
                    </p>
                    <p className="text-xs text-[var(--muted-foreground)]">
                      Backend validation before export is allowed.
                    </p>
                  </div>
                </div>
                <button type="button" onClick={onClose} className="rounded-md border border-[var(--border-subtle)] p-1">
                  <X className="h-3 w-3" />
                </button>
              </header>

              {isLoading ? (
                <p className="text-sm text-[var(--muted-foreground)]">Running validation…</p>
              ) : (
                <div className="space-y-3 text-[11px]">
                  {riskReport && (
                    <div className="rounded-lg border border-[var(--border-subtle)] bg-black/30 px-3 py-2">
                      <div className="flex justify-between">
                        <span>Risk summary</span>
                        <span className="font-mono text-slate-100">
                          {Math.round(riskReport.overall_score * 100)}
                        </span>
                      </div>
                      <p className="mt-1 text-[var(--muted-foreground)]">
                        {riskReport.export_ready ? "Export readiness threshold met." : "Risk remains above export threshold."}
                      </p>
                    </div>
                  )}

                  {blocking.map((issue) => (
                    <IssueRow key={`${issue.code}-${issue.detection_id}`} issue={issue} tone="error" />
                  ))}
                  {warnings.map((issue) => (
                    <IssueRow key={`${issue.code}-${issue.detection_id}`} issue={issue} tone="warning" />
                  ))}

                  {canContinue ? (
                    <div className="flex items-center gap-2 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-emerald-50">
                      <AlertTriangle className="h-4 w-4" />
                      <span>Safe to export based on current review state.</span>
                    </div>
                  ) : (
                    <p className="text-rose-100">Resolve blocking issues before exporting.</p>
                  )}
                </div>
              )}

              <footer className="mt-4 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-md border border-[var(--border-subtle)] px-3 py-1.5 text-[10px]"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={!canContinue || isLoading}
                  onClick={onContinue}
                  className="rounded-md border border-emerald-500/70 bg-emerald-500/20 px-3 py-1.5 text-[10px] font-medium text-emerald-50 disabled:opacity-40"
                >
                  Continue to export
                </button>
              </footer>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function IssueRow({
  issue,
  tone,
}: {
  issue: ValidationResult["issues"][number];
  tone: "error" | "warning";
}) {
  return (
    <div
      className={`rounded-lg border px-3 py-2 ${
        tone === "error" ? "border-rose-500/40 bg-rose-500/10" : "border-amber-500/40 bg-amber-500/10"
      }`}
    >
      <p className="font-medium text-slate-100">{issue.message}</p>
      <p className="text-[10px] text-[var(--muted-foreground)]">
        {issue.code}
        {issue.detection_id ? ` · ${issue.detection_id}` : ""}
      </p>
    </div>
  );
}
