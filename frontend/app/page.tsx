"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
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
  const [mode] = useState<"ready" | "loading" | "error">("ready");

  useKeyboardShortcuts({
    onPrimaryAction: () => active && updateStatus(active.id, "approved"),
    onReject: () => active && updateStatus(active.id, "rejected"),
    onNext: keyboardHandlers.next,
    onPrevious: keyboardHandlers.previous,
    onToggleDetails: () => active && setDetailOpen((v) => !v),
    onCloseSurface: () => {
      if (detailOpen) setDetailOpen(false);
      if (exportOpen) setExportOpen(false);
    },
  });

  const handleSelect = (d: (typeof items)[number]) => {
    setActiveId(d.id);
  };
  const fullyReviewed = useMemo(() => stats.unreviewed === 0, [stats.unreviewed]);

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-[#050509] to-[#05060a]">
      <TopNav remaining={stats.unreviewed} onExport={() => setExportOpen(true)} />
      <main className="flex flex-1 flex-col gap-3 px-3 pb-4 pt-3 md:px-4">
        {mode === "loading" ? (
          <LoadState />
        ) : mode === "error" ? (
          <ErrorState />
        ) : (
          <section className="grid flex-1 gap-3 md:grid-cols-[minmax(0,2fr)_minmax(340px,1fr)]">
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
              <AnimatePresence>
                {fullyReviewed && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 8 }}
                    className="mt-2 flex items-center justify-between rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-[11px] text-emerald-50"
                  >
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4" />
                      <span>All issues reviewed. Run final safety validation before export.</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setExportOpen(true)}
                      className="rounded-md border border-emerald-500/60 bg-emerald-500/20 px-2.5 py-1 text-[10px] font-medium text-emerald-50 hover:bg-emerald-500/25"
                    >
                      Validate
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </section>
        )}
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

function LoadState() {
  return (
    <div className="grid flex-1 place-items-center rounded-xl border border-[var(--border-subtle)] bg-[rgba(9,11,20,0.8)]">
      <div className="flex items-center gap-3 text-[12px] text-[var(--muted-foreground)]">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Analyzing detections and building risk-prioritized queue...</span>
      </div>
    </div>
  );
}

function ErrorState() {
  return (
    <div className="grid flex-1 place-items-center rounded-xl border border-rose-500/30 bg-rose-500/5">
      <div className="flex max-w-md flex-col items-center gap-2 text-center">
        <AlertCircle className="h-5 w-5 text-rose-300" />
        <p className="text-sm text-rose-100">Detection analysis failed</p>
        <p className="text-xs text-[var(--muted-foreground)]">
          Unable to load AI findings. Retry analysis before continuing review.
        </p>
      </div>
    </div>
  );
}
