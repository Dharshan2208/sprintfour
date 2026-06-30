"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { AppLayout } from "../../../components/layout/app-layout";
import { AuditTimeline } from "../../../components/audit-timeline";
import { getReviewHistory } from "../../../services/review";
import type { AuditEvent } from "../../../lib/types";

export default function HistoryPage() {
  const params = useParams<{ id: string }>();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getReviewHistory(params.id)
      .then((response) => setEvents(response.events))
      .catch((historyError) => {
        setError(historyError instanceof Error ? historyError.message : "Failed to load history");
      })
      .finally(() => setLoading(false));
  }, [params.id]);

  return (
    <AppLayout documentId={params.id}>
      <div className="flex min-h-0 flex-1 flex-col gap-4 p-6">
        <header>
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
            Audit history
          </p>
          <h1 className="mt-1 text-xl font-medium text-slate-50">Review event log</h1>
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">
            Immutable record of approve, reject, edit, add, delete, undo, and redo actions.
          </p>
        </header>

        {loading ? (
          <div className="flex items-center gap-2 text-sm text-[var(--muted-foreground)]">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading audit history…
          </div>
        ) : error ? (
          <p className="text-sm text-rose-300">{error}</p>
        ) : (
          <AuditTimeline events={events} />
        )}
      </div>
    </AppLayout>
  );
}
