import type { CorrectionMode, ReviewEntity } from "../../lib/types";
import { cn } from "../../lib/utils";

interface EntityHighlightProps {
  entity: ReviewEntity;
  text: string;
  isActive: boolean;
  isHovered: boolean;
  correctionMode?: CorrectionMode;
  onSelect: () => void;
  onHover: (hovered: boolean) => void;
}

export function EntityHighlight({
  entity,
  text,
  isActive,
  isHovered,
  correctionMode = "off",
  onSelect,
  onHover,
}: EntityHighlightProps) {
  const isFalsePositive = entity.isFalsePositive;
  const isApproved = entity.reviewState === "approved" || entity.reviewState === "modified";
  const isManual = entity.isManual;
  const isPending = entity.reviewState === "pending" || entity.reviewState === "system_generated" || entity.reviewState === "unreviewed";

  // In correction mode, add tooltip-like hints
  const title = correctionMode !== "off"
    ? isFalsePositive
      ? "False positive — click to see details"
      : isManual
        ? "Manually added (you marked this)"
        : isApproved
          ? `Approved ${entity.entityType}`
          : isPending
            ? `Unreviewed ${entity.entityType}`
            : `${entity.reviewState} ${entity.entityType}`
    : undefined;

  // In diff mode, show a legend indicator
  const showIndicator = correctionMode === "diff" && (isFalsePositive || isManual || isApproved || isPending);

  return (
    <button
      type="button"
      onClick={onSelect}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
      title={title}
      className={cn(
        "relative rounded-[3px] px-0.5 py-0.5 text-left underline-offset-2 transition",
        highlightClasses(entity, correctionMode),
        (isActive || isHovered) &&
          "ring-1 ring-sky-400/80 ring-offset-1 ring-offset-slate-950/40",
      )}
      aria-label={`${entity.entityType}: ${entity.entity}`}
    >
      {showIndicator && (
        <span className="absolute -left-0.5 -top-0.5 h-1.5 w-1.5 rounded-full"
          style={{
            backgroundColor: isFalsePositive ? "#fbbf24" : isManual ? "#38bdf8" : isApproved ? "#34d399" : "#f87171",
          }}
        />
      )}
      <span className="relative z-10">{text}</span>
    </button>
  );
}

function highlightClasses(entity: ReviewEntity, correctionMode: CorrectionMode) {
  const baseClasses = "underline-offset-2";

  if (entity.isFalsePositive) {
    // False positives: struck through, muted
    if (correctionMode === "review_false_positives" || correctionMode === "diff") {
      return "bg-amber-500/20 text-amber-100/80 line-through decoration-amber-400/60";
    }
    return "bg-slate-800/30 text-slate-400/70 line-through";
  }

  if (entity.isManual) {
    // Manually added (missed PII that user caught)
    if (correctionMode === "spot_missed" || correctionMode === "diff") {
      return "border border-cyan-400/80 bg-cyan-500/15 text-cyan-50";
    }
    return "border border-sky-400/90 bg-sky-500/12 text-sky-50";
  }

  if (entity.reviewState === "approved" || entity.reviewState === "modified") {
    // Approved redactions
    if (correctionMode === "diff") {
      return "bg-emerald-500/15 text-emerald-50/80";
    }
    return "bg-red-500/12 text-red-50/80";
  }

  if (entity.priority === "critical") {
    return "bg-red-500/24 text-red-100";
  }

  if (entity.isLowConfidence) {
    return "border-b border-dotted border-amber-400/80 bg-amber-500/12 text-amber-100";
  }

  if (entity.confidence >= 0.8) {
    return "bg-amber-500/16 text-amber-50";
  }

  return "border-b border-dotted border-amber-400/70 bg-amber-500/10 text-amber-100/90";
}
