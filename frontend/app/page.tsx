/* eslint-disable react/jsx-key */
"use client";

import { useState } from "react";
import { TopNav } from "../components/top-nav";
import { DocumentViewer } from "../components/document-viewer";
import { ReviewQueue } from "../components/review-queue";
import { DetectionDetailDrawer } from "../components/detection-detail-drawer";
import { ExportValidationModal } from "../components/export-validation-modal";
import { detections } from "../lib/mock-data";
import { useDetectionSelection } from "../hooks/use-detection-selection";
import { useKeyboardShortcuts } from "../hooks/use-keyboard-shortcuts";

export default function Home() {
  const { items, active, setActiveId, updateStatus, keyboardHandlers, stats } =
    useDetectionSelection(detections);
  const [detailOpen, setDetailOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);

  useKeyboardShortcuts({
    onApprove: () => active && updateStatus(active.id, "approved"),
    onReject: () => active && updateStatus(active.id, "rejected"),
    onMarkMissed: () => active && updateStatus(active.id, "missed"),
    onNext: keyboardHandlers.next,
  });

  const handleSelect = (d: (typeof items)[number]) => {
    setActiveId(d.id);
    setDetailOpen(true);
  };

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-[#050509] to-[#05060a]">
      <TopNav />
      <main className="flex flex-1 flex-col gap-3 px-3 pb-4 pt-3 md:px-4">
        <section className="grid flex-1 gap-3 md:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
          <DocumentViewer
            detections={items}
            activeId={active?.id ?? null}
            onSelect={handleSelect}
          />
          <div className="flex h-full flex-col">
            <ReviewQueue
              items={items}
              activeId={active?.id ?? null}
              onSelect={handleSelect}
              onApprove={(id) => updateStatus(id, "approved")}
              onReject={(id) => updateStatus(id, "rejected")}
              onMarkMissed={(id) => updateStatus(id, "missed")}
              stats={stats}
            />
            <div className="mt-2 flex items-center justify-between rounded-lg border border-[var(--border-subtle)] bg-[var(--muted)]/50 px-3 py-2 text-[10px] text-[var(--muted-foreground)]">
              <div className="flex items-center gap-2">
                <span className="rounded bg-black/40 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.16em] text-slate-200">
                  Keyboard-first
                </span>
                <span>Keep hands on the keyboard; mouse is optional.</span>
              </div>
              <button
                type="button"
                onClick={() => setExportOpen(true)}
                className="rounded-md border border-emerald-500/60 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-medium text-emerald-50 hover:bg-emerald-500/25"
              >
                Run safety validation
              </button>
            </div>
          </div>
        </section>
      </main>

      <DetectionDetailDrawer
        detection={active ?? null}
        open={detailOpen && !!active}
        onClose={() => setDetailOpen(false)}
      />

      <ExportValidationModal
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        detections={items}
      />
    </div>
  );
}
