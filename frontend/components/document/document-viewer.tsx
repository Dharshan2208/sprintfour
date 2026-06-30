"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import type { CorrectionMode, DocumentPage, ReviewEntity, TextSelectionRange } from "../../lib/types";
import { cn } from "../../lib/utils";
import { EntityHighlight } from "./entity-highlight";

interface DocumentViewerProps {
  text: string;
  pages: DocumentPage[];
  entities: ReviewEntity[];
  activeId: string | null;
  hoveredId: string | null;
  correctionMode: CorrectionMode;
  onSelect: (entity: ReviewEntity) => void;
  onHover: (entityId: string | null) => void;
  selectedPage: number | null;
  // ── Text selection for adding missed PII ──
  onTextSelection?: (range: TextSelectionRange | null) => void;
  onAddMissedPiiFromSelection?: () => void;
}

export function DocumentViewer({
  text,
  pages,
  entities,
  activeId,
  hoveredId,
  correctionMode,
  onSelect,
  onHover,
  selectedPage,
  onTextSelection,
  onAddMissedPiiFromSelection,
}: DocumentViewerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const activeRef = useRef<HTMLSpanElement | null>(null);
  const textContainerRef = useRef<HTMLDivElement | null>(null);

  const activeEntity = useMemo(
    () => entities.find((entity) => entity.id === activeId) ?? null,
    [entities, activeId],
  );

  useEffect(() => {
    if (!activeRef.current) return;
    activeRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [activeId]);

  // ── Text selection handler for adding missed PII ──
  const handleMouseUp = useCallback(() => {
    if (!onTextSelection) return;
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || !selection.toString().trim()) {
      onTextSelection(null);
      return;
    }

    const selectedText = selection.toString().trim();
    if (!selectedText || selectedText.length < 1) {
      onTextSelection(null);
      return;
    }

    // Find the closest text offset using the DOM Range
    const range = selection.getRangeAt(0);
    const startContainer = range.startContainer;
    const endContainer = range.endContainer;

    // Find page number from the closest parent section
    let node: Node | null = startContainer;
    let foundPage = 1;
    while (node) {
      if (node instanceof HTMLElement && node.dataset?.page) {
        foundPage = parseInt(node.dataset.page, 10);
        break;
      }
      node = node.parentNode;
    }

    // Calculate approximate offset - find the first character of the selection
    // We use the fact that the text content is placed in the DOM
    const fullText = textContainerRef.current?.textContent ?? "";
    const textStartOffset = fullText.indexOf(selectedText);
    if (textStartOffset === -1) {
      // Can't find exact position - use approximate
      onTextSelection(null);
      return;
    }

    onTextSelection({
      startOffset: textStartOffset,
      endOffset: textStartOffset + selectedText.length,
      text: selectedText,
      page: foundPage,
      line: 0,
    });
  }, [onTextSelection]);

  const handleKeyUp = useCallback((e: React.KeyboardEvent) => {
    // Allow adding missed PII with Ctrl+Shift+M when text is selected
    if (e.key === "M" && (e.ctrlKey || e.metaKey) && e.shiftKey) {
      onAddMissedPiiFromSelection?.();
    }
  }, [onAddMissedPiiFromSelection]);

  const visiblePages = selectedPage
    ? pages.filter((page) => page.page_number === selectedPage)
    : pages;

  return (
    <section
      aria-label="Document"
      className={cn(
        "flex h-full min-h-0 flex-col rounded-xl border border-[var(--border-subtle)] bg-[rgba(9,11,20,0.96)]",
        correctionMode === "spot_missed" && "ring-1 ring-rose-500/30",
        correctionMode === "review_false_positives" && "ring-1 ring-amber-500/30",
        correctionMode === "diff" && "ring-1 ring-violet-500/30",
      )}
    >
      <header className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-2.5">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
            Document
          </p>
          <p className="text-[11px] text-[var(--muted-foreground)]">
            {correctionMode === "spot_missed"
              ? "Select text to mark as missed PII · click highlighted to reject false positives"
              : correctionMode === "review_false_positives"
                ? "False positives are struck through · click to select and reject"
                : correctionMode === "diff"
                  ? "🟡 Tool flagged · 🔴 Missed by tool · ⚪ Correct"
                  : "Inline entities · scroll syncs with review queue"}
          </p>
        </div>
        {activeEntity && (
          <div className="text-[10px] text-[var(--muted-foreground)]">
            Page {activeEntity.page || "—"} · Line {activeEntity.line || "—"}
          </div>
        )}
      </header>

      <div
        ref={containerRef}
        tabIndex={0}
        className="scrollbar-thin flex-1 overflow-auto px-8 py-6 text-sm leading-relaxed outline-none"
        onMouseUp={handleMouseUp}
        onKeyUp={handleKeyUp}
      >
        <div ref={textContainerRef}>
          {visiblePages.length > 0
            ? visiblePages.map((page) => (
                <section key={page.page_number} className="mb-8" data-page={page.page_number}>
                  <div className="mb-3 text-[10px] uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
                    Page {page.page_number}
                  </div>
                  <p className="max-w-3xl whitespace-pre-wrap text-[14px] leading-7 tracking-[0.003em] text-slate-100/90">
                    {renderSegment(
                      page.text,
                      page.start_offset,
                      entities.filter(
                        (entity) =>
                          entity.endOffset > page.start_offset &&
                          entity.startOffset < page.end_offset,
                      ),
                      activeId,
                      hoveredId,
                      onSelect,
                      onHover,
                      activeRef,
                      correctionMode,
                    )}
                  </p>
                </section>
              ))
            : (
                <p className="max-w-3xl whitespace-pre-wrap text-[14px] leading-7 text-slate-100/90">
                  {renderSegment(text, 0, entities, activeId, hoveredId, onSelect, onHover, activeRef, correctionMode)}
                </p>
              )}
        </div>
      </div>
    </section>
  );
}

function renderSegment(
  segmentText: string,
  segmentOffset: number,
  entities: ReviewEntity[],
  activeId: string | null,
  hoveredId: string | null,
  onSelect: (entity: ReviewEntity) => void,
  onHover: (entityId: string | null) => void,
  activeRef: React.RefObject<HTMLSpanElement | null>,
  correctionMode: CorrectionMode = "off",
) {
  const localEntities = entities
    .map((entity) => ({
      entity,
      start: entity.startOffset - segmentOffset,
      end: entity.endOffset - segmentOffset,
    }))
    .filter((item) => item.end > 0 && item.start < segmentText.length)
    .sort((a, b) => a.start - b.start);

  if (!localEntities.length) return segmentText;

  const parts: React.ReactNode[] = [];
  let cursor = 0;

  for (const { entity, start, end } of localEntities) {
    const clampedStart = Math.max(0, start);
    const clampedEnd = Math.min(segmentText.length, end);
    if (clampedStart > cursor) {
      const gapText = segmentText.slice(cursor, clampedStart);
      // In "spot_missed" mode, highlight gaps that might contain missed PII
      if (correctionMode === "spot_missed" && gapText.trim().length > 2) {
        parts.push(
          <span className="rounded-sm bg-rose-500/5 px-0.5 text-rose-100/90 ring-1 ring-rose-500/20">
            {gapText}
          </span>,
        );
      } else {
        parts.push(gapText);
      }
    }

    const spanText = segmentText.slice(clampedStart, clampedEnd);
    const isActive = entity.id === activeId;

    parts.push(
      <span key={entity.id} ref={isActive ? activeRef : undefined}>
        <EntityHighlight
          entity={entity}
          text={spanText}
          isActive={isActive}
          isHovered={entity.id === hoveredId}
          correctionMode={correctionMode}
          onSelect={() => onSelect(entity)}
          onHover={(hovered) => onHover(hovered ? entity.id : null)}
        />
      </span>,
    );
    cursor = clampedEnd;
  }

  if (cursor < segmentText.length) {
    const remainingText = segmentText.slice(cursor);
    if (correctionMode === "spot_missed" && remainingText.trim().length > 2) {
      parts.push(
        <span className="rounded-sm bg-rose-500/5 px-0.5 text-rose-100/90 ring-1 ring-rose-500/20">
          {remainingText}
        </span>,
      );
    } else {
      parts.push(remainingText);
    }
  }

  return parts;
}
