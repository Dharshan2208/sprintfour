"use client";

import type { AuditEvent } from "../lib/types";

interface AuditTimelineProps {
  events: AuditEvent[];
}

export function AuditTimeline({ events }: AuditTimelineProps) {
  if (!events.length) {
    return (
      <div className="rounded-lg border border-dashed border-[var(--border-subtle)] px-4 py-6 text-sm text-[var(--muted-foreground)]">
        No audit events recorded for this document yet.
      </div>
    );
  }

  return (
    <ol className="space-y-3">
      {events.map((event) => (
        <li
          key={event.event_id}
          className="rounded-lg border border-[var(--border-subtle)] bg-[rgba(9,11,20,0.96)] px-4 py-3"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm text-slate-100">{event.action.action_type}</p>
              <p className="mt-1 text-[12px] text-[var(--muted-foreground)]">
                Detection {event.detection_id} · actor {event.action.actor}
              </p>
              <p className="mt-1 text-[12px] text-slate-300">
                {event.previous_review_state ?? "—"} → {event.new_review_state}
              </p>
            </div>
            <time className="whitespace-nowrap font-mono text-[11px] text-[var(--muted-foreground)]">
              {new Date(event.event_timestamp).toLocaleString()}
            </time>
          </div>
        </li>
      ))}
    </ol>
  );
}
