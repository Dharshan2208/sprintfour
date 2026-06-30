"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import type { CorrectionMode, FilterKey, ReviewEntity } from "../../lib/types";
import { matchesFilter, matchesSearch } from "../../lib/utils";
import { CorrectionToolbar } from "./correction-toolbar";
import { FilterPanel } from "./filter-panel";
import { ReviewCard } from "./review-card";
import { RiskPanel } from "./risk-panel";
import { SearchBar } from "./search-bar";
import type { RiskReport } from "../../lib/types";

interface ReviewQueueProps {
  entities: ReviewEntity[];
  activeId: string | null;
  hoveredId: string | null;
  searchQuery: string;
  activeFilter: FilterKey;
  riskReport: RiskReport | null;
  // ── Correction experience (Problem 3) ──
  correctionMode: CorrectionMode;
  batchSelectedIds: Set<string>;
  hasSelection: boolean;
  onSearchChange: (value: string) => void;
  onFilterChange: (filter: FilterKey) => void;
  onSelect: (entity: ReviewEntity) => void;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onHover: (id: string | null) => void;
  searchInputRef?: React.RefObject<HTMLInputElement | null>;
  // ── Correction callbacks ──
  onCorrectionModeChange: (mode: CorrectionMode) => void;
  onToggleBatch: (id: string) => void;
  onBatchApprove: () => void;
  onBatchReject: () => void;
  onClearBatch: () => void;
  onAddMissedPii: () => void;
}

export function ReviewQueue({
  entities,
  activeId,
  hoveredId,
  searchQuery,
  activeFilter,
  riskReport,
  correctionMode,
  batchSelectedIds,
  hasSelection,
  onSearchChange,
  onFilterChange,
  onSelect,
  onApprove,
  onReject,
  onHover,
  searchInputRef,
  onCorrectionModeChange,
  onToggleBatch,
  onBatchApprove,
  onBatchReject,
  onClearBatch,
  onAddMissedPii,
}: ReviewQueueProps) {
  const activeRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [activeId]);

  const filtered = useMemo(
    () =>
      entities.filter(
        (entity) => matchesFilter(entity, activeFilter) && matchesSearch(entity, searchQuery),
      ),
    [entities, activeFilter, searchQuery],
  );

  const sections = useMemo(
    () => ({
      critical: filtered.filter((entity) => entity.queueSection === "critical"),
      highRisk: filtered.filter((entity) => entity.queueSection === "high_risk"),
      lowConfidence: filtered.filter((entity) => entity.queueSection === "low_confidence"),
      falsePositive: filtered.filter((entity) => entity.queueSection === "false_positive"),
      reviewed: filtered.filter((entity) => entity.queueSection === "reviewed"),
    }),
    [filtered],
  );

  const filterCounts = useMemo(() => {
    const counts: Partial<Record<FilterKey, number>> = { all: entities.length };
    for (const entity of entities) {
      (["critical", "needs_review", "low_confidence", "manual", "approved", "false_positive"] as FilterKey[]).forEach(
        (filter) => {
          if (matchesFilter(entity, filter)) {
            counts[filter] = (counts[filter] ?? 0) + 1;
          }
        },
      );
    }
    return counts;
  }, [entities]);

  // Correction-mode auto-filters
  useEffect(() => {
    if (correctionMode === "spot_missed") {
      onFilterChange("manual");
    } else if (correctionMode === "review_false_positives") {
      onFilterChange("false_positive");
    } else if (correctionMode === "diff") {
      // Show everything - no filter change
    }
  }, [correctionMode]);

  const handleSelectAll = useCallback(() => {
    const allSelected = filtered.every((entity) => batchSelectedIds.has(entity.id));
    if (allSelected) {
      // Deselect all
      for (const entity of filtered) {
        if (batchSelectedIds.has(entity.id)) {
          onToggleBatch(entity.id);
        }
      }
    } else {
      // Select all filtered entities not already selected
      for (const entity of filtered) {
        if (!batchSelectedIds.has(entity.id)) {
          onToggleBatch(entity.id);
        }
      }
    }
  }, [filtered, batchSelectedIds, onToggleBatch]);

  const sectionProps = useCallback(
    (entity: ReviewEntity) => ({
      entity,
      isActive: entity.id === activeId,
      isHovered: entity.id === hoveredId,
      batchSelected: batchSelectedIds.has(entity.id),
      onSelect: () => onSelect(entity),
      onApprove: () => onApprove(entity.id),
      onReject: () => onReject(entity.id),
      onHover: (hovered: boolean) => onHover(hovered ? entity.id : null),
      onToggleBatch: () => onToggleBatch(entity.id),
    }),
    [activeId, hoveredId, batchSelectedIds, onSelect, onApprove, onReject, onHover, onToggleBatch],
  );

  return (
    <aside className="flex h-full min-h-0 flex-col rounded-xl border border-[var(--border-subtle)] bg-[rgba(9,11,20,0.98)]">
      {/* Correction toolbar */}
      <CorrectionToolbar
        mode={correctionMode}
        onModeChange={onCorrectionModeChange}
        batchCount={batchSelectedIds.size}
        totalFiltered={filtered.length}
        onBatchApprove={onBatchApprove}
        onBatchReject={onBatchReject}
        onClearBatch={onClearBatch}
        onSelectAll={handleSelectAll}
        hasSelection={hasSelection}
        onAddMissedPii={onAddMissedPii}
      />

      <div className="border-b border-[var(--border-subtle)] px-3 py-3">
        <div className="mb-2">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
            Review queue
          </p>
          <p className="text-[11px] text-[var(--muted-foreground)]">
            {correctionMode !== "off"
              ? "Correction mode — fix what the tool got wrong"
              : "Prioritized by risk engine — not flat list order"}
          </p>
        </div>
        <RiskPanel report={riskReport} />
        <div className="mt-2 space-y-2">
          <SearchBar value={searchQuery} onChange={onSearchChange} inputRef={searchInputRef} />
          <FilterPanel
            activeFilter={activeFilter}
            counts={filterCounts}
            onChange={onFilterChange}
          />
        </div>
      </div>

      <div className="scrollbar-thin flex-1 space-y-4 overflow-auto px-3 py-3">
        <QueueSection title="Critical missed PII" count={sections.critical.length}>
          {sections.critical.map((entity) => (
            <div key={entity.id} ref={entity.id === activeId ? activeRef : undefined}>
              <ReviewCard {...sectionProps(entity)} />
            </div>
          ))}
        </QueueSection>

        <QueueSection title="High-risk unresolved" count={sections.highRisk.length}>
          {sections.highRisk.map((entity) => (
            <div key={entity.id} ref={entity.id === activeId ? activeRef : undefined}>
              <ReviewCard {...sectionProps(entity)} />
            </div>
          ))}
        </QueueSection>

        <QueueSection title="Low confidence" count={sections.lowConfidence.length}>
          {sections.lowConfidence.map((entity) => (
            <div key={entity.id} ref={entity.id === activeId ? activeRef : undefined}>
              <ReviewCard {...sectionProps(entity)} />
            </div>
          ))}
        </QueueSection>

        <QueueSection title="False positives" count={sections.falsePositive.length}>
          {sections.falsePositive.map((entity) => (
            <ReviewCard key={entity.id} {...sectionProps(entity)} compact />
          ))}
        </QueueSection>

        <QueueSection title="Reviewed" count={sections.reviewed.length}>
          {sections.reviewed.map((entity) => (
            <ReviewCard key={entity.id} {...sectionProps(entity)} compact />
          ))}
        </QueueSection>
      </div>
    </aside>
  );
}

function QueueSection({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between text-[11px]">
        <span className="font-medium text-slate-200">{title}</span>
        <span className="rounded-full bg-black/40 px-1.5 py-0.5 font-mono text-[9px]">{count}</span>
      </div>
      {count === 0 ? (
        <div className="rounded-md border border-dashed border-[var(--border-subtle)] px-2 py-1.5 text-[10px] text-[var(--muted-foreground)]">
          Nothing in this section.
        </div>
      ) : (
        <div className="space-y-2">{children}</div>
      )}
    </section>
  );
}
