import type { FilterKey, ReviewEntity, ReviewState } from "./types";
import { isPendingReview } from "./mappers";

export function cn(...classes: Array<string | undefined | false | null>) {
  return classes.filter(Boolean).join(" ");
}

export function formatConfidence(conf: number) {
  return `${Math.round(conf * 100)}%`;
}

export function formatPriority(priority: ReviewEntity["priority"]) {
  return priority.charAt(0).toUpperCase() + priority.slice(1);
}

export function formatReviewState(state: ReviewState) {
  switch (state) {
    case "pending":
    case "system_generated":
    case "unreviewed":
      return "Needs review";
    case "approved":
      return "Approved";
    case "rejected":
      return "Rejected";
    case "modified":
      return "Modified";
    case "manually_added":
      return "Manual";
    case "exported":
      return "Exported";
    default:
      return state;
  }
}

export function formatRiskScore(score: number) {
  const pct = Math.round(score * 100);
  if (pct >= 85) return { label: "Severe", pct };
  if (pct >= 70) return { label: "High", pct };
  if (pct >= 50) return { label: "Elevated", pct };
  return { label: "Moderate", pct };
}

export function matchesFilter(entity: ReviewEntity, filter: FilterKey) {
  switch (filter) {
    case "all":
      return true;
    case "critical":
      return entity.priority === "critical" || entity.isManual;
    case "needs_review":
      return isPendingReview(entity.reviewState);
    case "approved":
      return entity.reviewState === "approved" || entity.reviewState === "modified";
    case "rejected":
      return entity.reviewState === "rejected";
    case "manual":
      return entity.isManual;
    case "low_confidence":
      return entity.isLowConfidence && isPendingReview(entity.reviewState);
    case "missed":
      return entity.isManual;
    case "false_positive":
      return entity.isFalsePositive;
    default:
      return true;
  }
}

export function matchesSearch(entity: ReviewEntity, query: string) {
  if (!query.trim()) return true;
  const haystack =
    `${entity.entity} ${entity.entityType} ${entity.reason} ${entity.sources.join(" ")} ${entity.reviewState} ${entity.page}`.toLowerCase();
  return haystack.includes(query.trim().toLowerCase());
}

export function downloadTextFile(filename: string, content: string, mimeType = "text/plain") {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function downloadJsonFile(filename: string, payload: unknown) {
  downloadTextFile(filename, JSON.stringify(payload, null, 2), "application/json");
}
