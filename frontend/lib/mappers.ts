import type {
  BackendDetection,
  PriorityItem,
  QueueSection,
  ReviewEntity,
  ReviewItem,
  ReviewState,
} from "./types";

const LOW_CONFIDENCE_THRESHOLD = 0.7;

const PENDING_STATES: ReviewState[] = ["pending", "system_generated", "unreviewed"];

export function isPendingReview(state: string): boolean {
  return PENDING_STATES.includes(state as ReviewState);
}

export function mergeDetectionWithReview(
  detection: BackendDetection,
  reviewItem?: ReviewItem,
  priorityItem?: PriorityItem,
): ReviewEntity {
  const reviewState = (reviewItem?.review_state ??
    detection.review_state ??
    "pending") as ReviewState;
  const priority = priorityItem?.priority ?? inferPriority(detection, reviewState);
  const priorityReason = priorityItem?.reason ?? detection.reason;

  return {
    id: detection.id,
    entity: reviewItem?.entity ?? detection.entity,
    entityType: reviewItem?.entity_type ?? detection.entity_type,
    confidence: reviewItem?.confidence ?? detection.confidence,
    reason: reviewItem?.reason ?? detection.reason,
    sources: reviewItem?.sources ?? detection.sources,
    startOffset: reviewItem?.start_offset ?? detection.start_offset,
    endOffset: reviewItem?.end_offset ?? detection.end_offset,
    page: reviewItem?.page ?? detection.page,
    line: reviewItem?.line ?? detection.line,
    reviewState,
    priority,
    priorityReason,
    queueSection: classifyQueueSection(reviewState, priority, detection.confidence),
    isManual: reviewState === "manually_added",
    isFalsePositive: reviewState === "rejected",
    isLowConfidence: detection.confidence < LOW_CONFIDENCE_THRESHOLD,
  };
}

function inferPriority(
  detection: BackendDetection,
  reviewState: ReviewState,
): PriorityItem["priority"] {
  if (reviewState === "rejected" || reviewState === "approved" || reviewState === "exported") {
    return "low";
  }
  if (reviewState === "manually_added") return "critical";
  if (detection.confidence < LOW_CONFIDENCE_THRESHOLD) return "medium";
  return "high";
}

function classifyQueueSection(
  reviewState: ReviewState,
  priority: PriorityItem["priority"],
  confidence: number,
): QueueSection {
  if (reviewState === "rejected") return "false_positive";
  if (
    reviewState === "approved" ||
    reviewState === "modified" ||
    reviewState === "exported"
  ) {
    return "reviewed";
  }
  if (reviewState === "manually_added" || priority === "critical") return "critical";
  if (confidence < LOW_CONFIDENCE_THRESHOLD && isPendingReview(reviewState)) {
    return "low_confidence";
  }
  if (priority === "high" || priority === "medium") return "high_risk";
  return "low_confidence";
}

export function sortByPriority(items: ReviewEntity[]): ReviewEntity[] {
  const sectionWeight: Record<QueueSection, number> = {
    critical: 5,
    high_risk: 4,
    low_confidence: 3,
    false_positive: 1,
    reviewed: 0,
  };
  const priorityWeight: Record<PriorityItem["priority"], number> = {
    critical: 4,
    high: 3,
    medium: 2,
    low: 1,
  };

  return [...items].sort((a, b) => {
    const sectionDiff = sectionWeight[b.queueSection] - sectionWeight[a.queueSection];
    if (sectionDiff !== 0) return sectionDiff;
    const priorityDiff = priorityWeight[b.priority] - priorityWeight[a.priority];
    if (priorityDiff !== 0) return priorityDiff;
    return b.confidence - a.confidence;
  });
}

export function computeReviewStats(items: ReviewEntity[]) {
  const total = items.length;
  const reviewed = items.filter((item) => !isPendingReview(item.reviewState)).length;
  const unreviewed = total - reviewed;
  const criticalOpen = items.filter(
    (item) =>
      isPendingReview(item.reviewState) &&
      (item.priority === "critical" || item.isManual),
  ).length;
  const lowConfidence = items.filter(
    (item) => isPendingReview(item.reviewState) && item.isLowConfidence,
  ).length;
  const manualAdditions = items.filter((item) => item.isManual).length;
  const criticalTotal = items.filter(
    (item) => item.priority === "critical" || item.isManual,
  ).length;
  const criticalReviewed = items.filter(
    (item) =>
      (item.priority === "critical" || item.isManual) &&
      !isPendingReview(item.reviewState),
  ).length;
  const criticalCompletion =
    criticalTotal === 0 ? 100 : Math.round((criticalReviewed / criticalTotal) * 100);

  return {
    total,
    reviewed,
    unreviewed,
    criticalOpen,
    lowConfidence,
    manualAdditions,
    criticalCompletion,
  };
}

export function detectionToApiPayload(detection: BackendDetection) {
  return {
    id: detection.id,
    entity: detection.entity,
    entity_type: detection.entity_type,
    confidence: detection.confidence,
    reason: detection.reason,
    sources: detection.sources,
    start_offset: detection.start_offset,
    end_offset: detection.end_offset,
    page: detection.page,
    line: detection.line,
  };
}

export function entityToApiPayload(entity: ReviewEntity) {
  return {
    id: entity.id,
    entity: entity.entity,
    entity_type: entity.entityType,
    confidence: entity.confidence,
    reason: entity.reason,
    sources: entity.sources,
    start_offset: entity.startOffset,
    end_offset: entity.endOffset,
    page: entity.page,
    line: entity.line,
  };
}
