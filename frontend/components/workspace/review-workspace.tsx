"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { AppLayout } from "../../components/layout/app-layout";
import { Toolbar } from "../../components/layout/toolbar";
import { DocumentNavigator } from "../../components/document/document-navigator";
import { DocumentViewer } from "../../components/document/document-viewer";
import { AddMissedPiiPopover } from "../../components/document/add-missed-pii-popover";
import { ReviewQueue } from "../../components/review/review-queue";
import { EntityDrawer } from "../../components/entity-drawer";
import { UndoSnackbar } from "../../components/undo-snackbar";
import { ValidationModal } from "../../components/modals/validation-modal";
import { ExportModal } from "../../components/modals/export-modal";
import { useKeyboardShortcuts } from "../../hooks/use-keyboard-shortcuts";
import { useReviewActions } from "../../hooks/use-review-actions";
import {
  getNextUnresolvedEntity,
  getPreviousUnresolvedEntity,
  loadWorkspaceData,
} from "../../hooks/use-workspace-data";
import { computeReviewStats } from "../../lib/mappers";
import { validateExport, runExport } from "../../services/export";
import { getReviewHistory } from "../../services/review";
import { useDetectionStore } from "../../stores/detection-store";
import { useDocumentStore } from "../../stores/document-store";
import { useHistoryStore } from "../../stores/ui-store";
import { useReviewStore } from "../../stores/review-store";
import { useRiskStore } from "../../stores/risk-store";
import { useUIStore } from "../../stores/ui-store";
import type { CorrectionMode, TextSelectionRange, ValidationResult } from "../../lib/types";

export function ReviewWorkspace() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const documentId = params.id;

  // ── Document state ──
  const document = useDocumentStore((state) => state.document);
  const documentLoading = useDocumentStore((state) => state.isLoading);
  const documentError = useDocumentStore((state) => state.error);
  const entities = useReviewStore((state) => state.entities);
  const snackbar = useReviewStore((state) => state.snackbar);
  const isMutating = useReviewStore((state) => state.isMutating);
  const riskReport = useRiskStore((state) => state.report);
  const auditEvents = useHistoryStore((state) => state.events);

  // ── UI state ──
  const activeEntityId = useUIStore((state) => state.activeEntityId);
  const hoveredEntityId = useUIStore((state) => state.hoveredEntityId);
  const drawerOpen = useUIStore((state) => state.drawerOpen);
  const searchQuery = useUIStore((state) => state.searchQuery);
  const activeFilter = useUIStore((state) => state.activeFilter);
  const selectedPage = useUIStore((state) => state.selectedPage);
  const validationModalOpen = useUIStore((state) => state.validationModalOpen);
  const exportModalOpen = useUIStore((state) => state.exportModalOpen);
  const settings = useUIStore((state) => state.settings);

  // ── Correction experience state ──
  const correctionMode = useUIStore((state) => state.correctionMode);
  const batchSelectedIds = useUIStore((state) => state.batchSelectedIds);
  const selectionRange = useUIStore((state) => state.selectionRange);
  const showAddPiiPopover = useUIStore((state) => state.showAddPiiPopover);
  const addPiiAnchorRect = useUIStore((state) => state.addPiiAnchorRect);

  // ── UI actions ──
  const setActiveEntityId = useUIStore((state) => state.setActiveEntityId);
  const setHoveredEntityId = useUIStore((state) => state.setHoveredEntityId);
  const setDrawerOpen = useUIStore((state) => state.setDrawerOpen);
  const setSearchQuery = useUIStore((state) => state.setSearchQuery);
  const setActiveFilter = useUIStore((state) => state.setActiveFilter);
  const setSelectedPage = useUIStore((state) => state.setSelectedPage);
  const setValidationModalOpen = useUIStore((state) => state.setValidationModalOpen);
  const setExportModalOpen = useUIStore((state) => state.setExportModalOpen);
  const setCorrectionMode = useUIStore((state) => state.setCorrectionMode);
  const toggleBatchSelection = useUIStore((state) => state.toggleBatchSelection);
  const clearBatchSelection = useUIStore((state) => state.clearBatchSelection);
  const setSelectionRange = useUIStore((state) => state.setSelectionRange);
  const setShowAddPiiPopover = useUIStore((state) => state.setShowAddPiiPopover);
  const clearSnackbar = useReviewStore((state) => state.clearSnackbar);

  const resetWorkspace = useCallback(() => {
    useDocumentStore.getState().reset();
    useDetectionStore.getState().reset();
    useReviewStore.getState().reset();
    useRiskStore.getState().reset();
    useHistoryStore.getState().reset();
    useUIStore.getState().resetWorkspaceUi();
  }, []);

  const [bootError, setBootError] = useState<string | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const searchInputRef = useRef<HTMLInputElement | null>(null);

  const {
    approve,
    reject,
    edit,
    add,
    remove,
    undo,
    redo,
    batchApprove: batchApproveAction,
    batchReject: batchRejectAction,
    getDetectionPayload,
  } = useReviewActions(documentId);

  useEffect(() => {
    resetWorkspace();
    loadWorkspaceData(documentId)
      .then(async ({ entities: loadedEntities }) => {
        const history = await getReviewHistory(documentId);
        useHistoryStore.getState().setEvents(history.events);
        if (!useUIStore.getState().activeEntityId && loadedEntities[0]) {
          setActiveEntityId(loadedEntities[0].id);
        }
      })
      .catch((error) => {
        setBootError(error instanceof Error ? error.message : "Failed to load workspace");
      });

    return () => resetWorkspace();
  }, [documentId, resetWorkspace, setActiveEntityId]);

  const activeEntity = useMemo(
    () => entities.find((entity) => entity.id === activeEntityId) ?? null,
    [entities, activeEntityId],
  );

  const stats = useMemo(() => computeReviewStats(entities), [entities]);
  const fullyReviewed = stats.unreviewed === 0;

  const navigateList = useCallback(
    (offset: number) => {
      const index = entities.findIndex((entity) => entity.id === activeEntityId);
      if (index < 0) {
        setActiveEntityId(entities[0]?.id ?? null);
        return;
      }
      const next = entities[(index + offset + entities.length) % entities.length];
      setActiveEntityId(next?.id ?? null);
    },
    [activeEntityId, entities, setActiveEntityId],
  );

  const openValidation = useCallback(async () => {
    setValidationModalOpen(true);
    setValidationLoading(true);
    try {
      const result = await validateExport(documentId, getDetectionPayload(), {
        requireFullReview: settings.requireFullReview,
      });
      setValidation(result);
    } finally {
      setValidationLoading(false);
    }
  }, [documentId, getDetectionPayload, setValidationModalOpen, settings.requireFullReview]);

  // ── Correction mode handlers ──

  const handleCorrectionModeChange = useCallback((mode: CorrectionMode) => {
    setCorrectionMode(mode);
    clearBatchSelection();
    setSelectionRange(null);
    setShowAddPiiPopover(false);
  }, [setCorrectionMode, clearBatchSelection, setSelectionRange, setShowAddPiiPopover]);

  const handleTextSelection = useCallback((range: TextSelectionRange | null) => {
    setSelectionRange(range);
    if (range) {
      // Show the add PII popover near the selection
      const selection = window.getSelection();
      if (selection && !selection.isCollapsed) {
        const rect = selection.getRangeAt(0).getBoundingClientRect();
        setShowAddPiiPopover(true, rect);
      }
    } else {
      setShowAddPiiPopover(false);
    }
  }, [setSelectionRange, setShowAddPiiPopover]);

  const handleAddMissedPii = useCallback(async (entityType: string) => {
    if (!selectionRange || !document) return;
    try {
      await add({
        entity: selectionRange.text,
        entity_type: entityType,
        start_offset: selectionRange.startOffset,
        end_offset: selectionRange.endOffset,
        page: selectionRange.page,
        line: selectionRange.line,
        reason: `Manually added missed ${entityType} during correction review`,
      });
      setShowAddPiiPopover(false);
      setSelectionRange(null);
    } catch (err) {
      // Error handled by the hook
    }
  }, [selectionRange, document, add, setShowAddPiiPopover, setSelectionRange]);

  const handleBatchApprove = useCallback(() => {
    const ids = Array.from(batchSelectedIds);
    if (ids.length > 0) {
      batchApproveAction(ids);
      clearBatchSelection();
    }
  }, [batchSelectedIds, batchApproveAction, clearBatchSelection]);

  const handleBatchReject = useCallback(() => {
    const ids = Array.from(batchSelectedIds);
    if (ids.length > 0) {
      batchRejectAction(ids);
      clearBatchSelection();
    }
  }, [batchSelectedIds, batchRejectAction, clearBatchSelection]);

  useKeyboardShortcuts({
    enabled: !!document,
    onApprove: () => activeEntity && approve(activeEntity.id),
    onReject: () => activeEntity && reject(activeEntity.id),
    onEdit: () => activeEntity && setDrawerOpen(true),
    onAdd: () => setDrawerOpen(true),
    onNext: () => navigateList(1),
    onPrevious: () => navigateList(-1),
    onNextUnresolved: () => {
      const next = getNextUnresolvedEntity(entities, activeEntityId);
      if (next) setActiveEntityId(next.id);
    },
    onPreviousUnresolved: () => {
      const prev = getPreviousUnresolvedEntity(entities, activeEntityId);
      if (prev) setActiveEntityId(prev.id);
    },
    onNextOccurrence: () => navigateList(1),
    onPreviousOccurrence: () => navigateList(-1),
    onToggleDetails: () => {
      if (activeEntity) setDrawerOpen(!drawerOpen);
    },
    onExport: () => void openValidation(),
    onSearch: () => searchInputRef.current?.focus(),
    onUndo: () => void undo(),
    onRedo: () => void redo(),
    onCloseSurface: () => {
      setDrawerOpen(false);
      setValidationModalOpen(false);
      setExportModalOpen(false);
      setShowAddPiiPopover(false);
    },
  });

  if (bootError || documentError) {
    return (
      <AppLayout>
        <ErrorState message={bootError ?? documentError ?? "Unknown error"} />
      </AppLayout>
    );
  }

  if (documentLoading || !document) {
    return (
      <AppLayout>
        <LoadState />
      </AppLayout>
    );
  }

  return (
    <AppLayout
      documentId={documentId}
      statusBar={{
        filename: document.metadata.filename,
        stats,
        riskScore: riskReport?.overall_score,
        exportReady: riskReport?.export_ready,
        isMutating,
      }}
    >
      <Toolbar
        hasActive={!!activeEntity}
        onApprove={() => activeEntity && approve(activeEntity.id)}
        onReject={() => activeEntity && reject(activeEntity.id)}
        onEdit={() => setDrawerOpen(true)}
        onAdd={() => setDrawerOpen(true)}
        onUndo={() => void undo()}
        onRedo={() => void redo()}
        onExport={() => void openValidation()}
      />

      <div className="grid min-h-0 flex-1 gap-3 p-3 lg:grid-cols-[minmax(0,1.6fr)_minmax(340px,1fr)]">
        <div className="flex min-h-0 flex-col gap-2">
          <DocumentNavigator
            pages={document.pages}
            selectedPage={selectedPage}
            onSelectPage={setSelectedPage}
          />
          <DocumentViewer
            text={document.text}
            pages={document.pages}
            entities={entities}
            activeId={activeEntityId}
            hoveredId={hoveredEntityId}
            correctionMode={correctionMode}
            selectedPage={selectedPage}
            onSelect={(entity) => {
              setActiveEntityId(entity.id);
              setDrawerOpen(true);
            }}
            onHover={setHoveredEntityId}
            onTextSelection={handleTextSelection}
            onAddMissedPiiFromSelection={() => {
              if (selectionRange) {
                // Show the popover - will be handled by the popover component
              }
            }}
          />
        </div>

        <div className="flex min-h-0 flex-col">
          <ReviewQueue
            entities={entities}
            activeId={activeEntityId}
            hoveredId={hoveredEntityId}
            searchQuery={searchQuery}
            activeFilter={activeFilter}
            riskReport={riskReport}
            correctionMode={correctionMode}
            batchSelectedIds={batchSelectedIds}
            hasSelection={!!selectionRange}
            onSearchChange={setSearchQuery}
            onFilterChange={setActiveFilter}
            onSelect={(entity) => setActiveEntityId(entity.id)}
            onApprove={approve}
            onReject={reject}
            onHover={setHoveredEntityId}
            searchInputRef={searchInputRef}
            onCorrectionModeChange={handleCorrectionModeChange}
            onToggleBatch={toggleBatchSelection}
            onBatchApprove={handleBatchApprove}
            onBatchReject={handleBatchReject}
            onClearBatch={clearBatchSelection}
            onAddMissedPii={() => {
              if (selectionRange) {
                setShowAddPiiPopover(true, addPiiAnchorRect);
              }
            }}
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
                  <span>All entities reviewed. Run validation before export.</span>
                </div>
                <button
                  type="button"
                  onClick={() => void openValidation()}
                  className="rounded-md border border-emerald-500/60 bg-emerald-500/20 px-2.5 py-1 text-[10px]"
                >
                  Validate
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Add Missed PII Popover — appears when text is selected in the document */}
      <AnimatePresence>
        {showAddPiiPopover && selectionRange && (
          <AddMissedPiiPopover
            selectedText={selectionRange.text}
            anchorRect={addPiiAnchorRect}
            onAdd={handleAddMissedPii}
            onClose={() => setShowAddPiiPopover(false)}
          />
        )}
      </AnimatePresence>

      <EntityDrawer
        entity={activeEntity}
        documentText={document.text}
        auditEvents={auditEvents}
        open={drawerOpen && !!activeEntity}
        onClose={() => setDrawerOpen(false)}
        onApprove={() => activeEntity && approve(activeEntity.id)}
        onReject={() => activeEntity && reject(activeEntity.id)}
        onDelete={() => activeEntity && remove(activeEntity.id)}
      />

      <ValidationModal
        open={validationModalOpen}
        validation={validation}
        riskReport={riskReport}
        isLoading={validationLoading}
        onClose={() => setValidationModalOpen(false)}
        onContinue={() => {
          setValidationModalOpen(false);
          setExportModalOpen(true);
        }}
      />

      <ExportModal
        open={exportModalOpen}
        defaultFormat={settings.defaultExportFormat}
        isExporting={exporting}
        onClose={() => setExportModalOpen(false)}
        filename={document.metadata.filename}
        onExport={async (format) => {
          setExporting(true);
          try {
            const result = await runExport({
              document_id: documentId,
              text: document.text,
              detections: getDetectionPayload(),
              format,
              exported_by: settings.actorName,
              risk_report: (riskReport ?? undefined) as Record<string, unknown> | undefined,
              review_history: auditEvents as unknown as Record<string, unknown>[],
            });
            if (!result.redacted_text && !result.json_report) return null;
            return result;
          } finally {
            setExporting(false);
          }
        }}
      />

      <UndoSnackbar
        message={snackbar?.message ?? null}
        onUndo={snackbar?.action === "undo" ? () => void undo() : undefined}
        onDismiss={clearSnackbar}
      />
    </AppLayout>
  );
}

function LoadState() {
  return (
    <div className="grid flex-1 place-items-center">
      <div className="flex items-center gap-3 text-[12px] text-[var(--muted-foreground)]">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Loading document, running detection, and building risk queue…</span>
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="grid flex-1 place-items-center">
      <div className="flex max-w-md flex-col items-center gap-2 text-center">
        <AlertCircle className="h-5 w-5 text-rose-300" />
        <p className="text-sm text-rose-100">Workspace failed to load</p>
        <p className="text-xs text-[var(--muted-foreground)]">{message}</p>
      </div>
    </div>
  );
}
