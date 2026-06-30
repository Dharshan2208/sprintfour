"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Clock3, Flag, FileText, ShieldAlert } from "lucide-react";
import type { AuditEvent, ReviewEntity } from "../lib/types";
import { cn, formatConfidence, formatPriority, formatReviewState } from "../lib/utils";

interface EntityDrawerProps {
  entity: ReviewEntity | null;
  documentText: string;
  auditEvents: AuditEvent[];
  open: boolean;
  onClose: () => void;
  onApprove: () => void;
  onReject: () => void;
  onDelete: () => void;
}

export function EntityDrawer({
  entity,
  documentText,
  auditEvents,
  open,
  onClose,
  onApprove,
  onReject,
  onDelete,
}: EntityDrawerProps) {
  const entityEvents = entity
    ? auditEvents.filter((event) => event.detection_id === entity.id)
    : [];

  return (
    <AnimatePresence>
      {open && entity && (
        <>
          <motion.div
            className="fixed inset-0 z-30 bg-black/40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            className="fixed inset-y-0 right-0 z-40 w-full max-w-md border-l border-[var(--border-subtle)] bg-[rgba(6,8,16,0.98)] px-4 py-4 shadow-xl"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 260, damping: 30 }}
            aria-label="Entity details"
          >
            <header className="mb-3 flex items-start justify-between gap-2">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
                  Entity details
                </p>
                <p className="font-mono text-xs text-slate-50">{entity.entity}</p>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border border-[var(--border-subtle)] bg-black/40 px-2 py-1 text-[10px] text-[var(--muted-foreground)]"
              >
                Esc
              </button>
            </header>

            <div className="space-y-3 text-[11px]">
              <InfoGrid entity={entity} />
              <Section title="Why flagged" icon={Flag}>
                <p className="leading-relaxed text-slate-200">{entity.reason}</p>
              </Section>
              <Section title="Context" icon={FileText}>
                <ContextSnippet entity={entity} documentText={documentText} />
              </Section>
              <Section title="Audit history" icon={Clock3}>
                <div className="space-y-1.5">
                  {entityEvents.length === 0 ? (
                    <p className="text-[var(--muted-foreground)]">No audit entries yet.</p>
                  ) : (
                    entityEvents.map((event) => (
                      <div
                        key={event.event_id}
                        className="rounded border border-[var(--border-subtle)] bg-black/30 px-2 py-1.5"
                      >
                        <div className="flex justify-between gap-2">
                          <span className="text-slate-100">{event.action.action_type}</span>
                          <span className="font-mono text-[9px] text-[var(--muted-foreground)]">
                            {new Date(event.event_timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <p className="text-[10px] text-[var(--muted-foreground)]">
                          {event.previous_review_state ?? "—"} → {event.new_review_state}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </Section>
              <Section title="Quick actions" icon={ShieldAlert}>
                <div className="flex flex-wrap gap-2">
                  <ActionButton label="Approve" onClick={onApprove} />
                  <ActionButton label="Reject" onClick={onReject} />
                  <ActionButton label="Delete" onClick={onDelete} tone="danger" />
                </div>
              </Section>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

function InfoGrid({ entity }: { entity: ReviewEntity }) {
  return (
    <div className="grid grid-cols-2 gap-2 rounded-md border border-[var(--border-subtle)] bg-[var(--muted)]/50 px-2.5 py-2">
      <InfoRow label="Type" value={entity.entityType} />
      <InfoRow label="Confidence" value={formatConfidence(entity.confidence)} />
      <InfoRow label="Status" value={formatReviewState(entity.reviewState)} />
      <InfoRow label="Priority" value={formatPriority(entity.priority)} />
      <InfoRow label="Source" value={entity.sources.join(", ") || "—"} />
      <InfoRow label="Page" value={String(entity.page || "—")} />
    </div>
  );
}

function Section({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: typeof Flag;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-md border border-[var(--border-subtle)] bg-[rgba(8,10,18,0.9)] px-2.5 py-2">
      <div className="mb-1.5 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.16em] text-slate-200">
        <Icon className="h-3 w-3" />
        <span>{title}</span>
      </div>
      {children}
    </section>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[9px] uppercase tracking-[0.14em] text-[var(--muted-foreground)]">{label}</div>
      <div className="text-[11px] text-slate-100">{value}</div>
    </div>
  );
}

function ContextSnippet({
  entity,
  documentText,
}: {
  entity: ReviewEntity;
  documentText: string;
}) {
  const radius = 60;
  const start = Math.max(0, entity.startOffset - radius);
  const end = Math.min(documentText.length, entity.endOffset + radius);
  const before = documentText.slice(start, entity.startOffset);
  const target = documentText.slice(entity.startOffset, entity.endOffset);
  const after = documentText.slice(entity.endOffset, end);

  return (
    <p className="font-mono text-[11px] leading-relaxed text-slate-100">
      {start > 0 && <span className="text-slate-500/80">…</span>}
      <span className="text-slate-400">{before}</span>
      <mark className="rounded-[3px] bg-amber-500/30 px-0.5 text-slate-900">{target}</mark>
      <span className="text-slate-400">{after}</span>
      {end < documentText.length && <span className="text-slate-500/80">…</span>}
    </p>
  );
}

function ActionButton({
  label,
  onClick,
  tone,
}: {
  label: string;
  onClick: () => void;
  tone?: "danger";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-md border px-2.5 py-1 text-[10px]",
        tone === "danger"
          ? "border-rose-500/50 bg-rose-500/10 text-rose-100"
          : "border-[var(--border-subtle)] bg-black/30 text-slate-100 hover:bg-black/50",
      )}
    >
      {label}
    </button>
  );
}
