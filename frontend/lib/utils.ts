import { Detection } from "./types";

export function cn(...classes: Array<string | undefined | false | null>) {
  return classes.filter(Boolean).join(" ");
}

export function formatConfidence(conf: number) {
  return `${Math.round(conf * 100)}%`;
}

export function formatSeverity(severity: Detection["severity"]) {
  switch (severity) {
    case "critical":
      return "Critical";
    case "high":
      return "High";
    case "medium":
      return "Medium";
    case "low":
      return "Low";
  }
}

export function formatStatus(status: Detection["status"]) {
  switch (status) {
    case "unreviewed":
      return "Unreviewed";
    case "approved":
      return "Approved";
    case "rejected":
      return "Rejected";
    case "missed":
      return "Marked Missed";
  }
}

export function sortDetectionsForQueue(detections: Detection[]): Detection[] {
  const weightBySeverity: Record<Detection["severity"], number> = {
    critical: 4,
    high: 3,
    medium: 2,
    low: 1,
  };

  const weightByStatus: Record<Detection["status"], number> = {
    unreviewed: 3,
    missed: 2,
    approved: 1,
    rejected: 0,
  };

  return [...detections].sort((a, b) => {
    const aScore =
      weightBySeverity[a.severity] * 10 +
      weightByStatus[a.status] * 5 +
      a.confidence;
    const bScore =
      weightBySeverity[b.severity] * 10 +
      weightByStatus[b.status] * 5 +
      b.confidence;
    return bScore - aScore;
  });
}

