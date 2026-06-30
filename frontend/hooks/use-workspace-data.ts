import {
  computeReviewStats,
  detectionToApiPayload,
  mergeDetectionWithReview,
  sortByPriority,
} from "../lib/mappers";
import type { BackendDetection, ReviewEntity } from "../lib/types";
import { runDetection } from "../services/detection";
import { getDocument } from "../services/documents";
import { assessRisk } from "../services/risk";
import { getReviewItems } from "../services/review";
import { useDetectionStore } from "../stores/detection-store";
import { useDocumentStore } from "../stores/document-store";
import { useReviewStore } from "../stores/review-store";
import { useRiskStore } from "../stores/risk-store";

export async function loadWorkspaceData(documentId: string) {
  const documentStore = useDocumentStore.getState();
  const detectionStore = useDetectionStore.getState();
  const reviewStore = useReviewStore.getState();
  const riskStore = useRiskStore.getState();

  documentStore.setLoading(true);
  detectionStore.setLoading(true);
  riskStore.setLoading(true);

  try {
    const document = await getDocument(documentId);
    documentStore.setDocument(document);

    let detections: BackendDetection[] = detectionStore.detections;
    if (detections.length === 0) {
      const detectionResult = await runDetection(documentId);
      detections = detectionResult.detections;
      detectionStore.setDetections(detections, detectionResult.processing_time_ms);
    }

    const detectionPayload = detections.map(detectionToApiPayload);
    const reviewResponse = await getReviewItems(documentId, detectionPayload);
    reviewStore.setReviewItems(reviewResponse.items);

    const riskReport = await assessRisk(documentId, detectionPayload);
    riskStore.setReport(riskReport);

    const priorityMap = new Map(
      riskReport.priority_items.map((item) => [item.detection_id, item]),
    );
    const reviewMap = new Map(
      reviewResponse.items.map((item) => [item.detection_id, item]),
    );

    const entities = sortByPriority(
      detections.map((detection) =>
        mergeDetectionWithReview(
          detection,
          reviewMap.get(detection.id),
          priorityMap.get(detection.id),
        ),
      ),
    );

    reviewStore.setEntities(entities);

    return {
      document,
      entities,
      riskReport,
      stats: computeReviewStats(entities),
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to load workspace";
    documentStore.setError(message);
    detectionStore.setError(message);
    riskStore.setError(message);
    throw error;
  } finally {
    documentStore.setLoading(false);
    detectionStore.setLoading(false);
    riskStore.setLoading(false);
  }
}

export async function refreshRiskAndReview(documentId: string, detections: BackendDetection[]) {
  const reviewStore = useReviewStore.getState();
  const riskStore = useRiskStore.getState();
  const detectionPayload = detections.map(detectionToApiPayload);

  const [reviewResponse, riskReport] = await Promise.all([
    getReviewItems(documentId, detectionPayload),
    assessRisk(documentId, detectionPayload),
  ]);

  reviewStore.setReviewItems(reviewResponse.items);
  riskStore.setReport(riskReport);

  const priorityMap = new Map(
    riskReport.priority_items.map((item) => [item.detection_id, item]),
  );
  const reviewMap = new Map(
    reviewResponse.items.map((item) => [item.detection_id, item]),
  );

  const entities = sortByPriority(
    detections.map((detection) =>
      mergeDetectionWithReview(
        detection,
        reviewMap.get(detection.id),
        priorityMap.get(detection.id),
      ),
    ),
  );

  reviewStore.setEntities(entities);
  return { entities, riskReport, stats: computeReviewStats(entities) };
}

export function getNextUnresolvedEntity(
  entities: ReviewEntity[],
  currentId: string | null,
): ReviewEntity | null {
  const unresolved = entities.filter(
    (entity) =>
      entity.queueSection !== "reviewed" && entity.queueSection !== "false_positive",
  );
  if (!unresolved.length) return null;
  if (!currentId) return unresolved[0];
  const index = unresolved.findIndex((entity) => entity.id === currentId);
  if (index < 0) return unresolved[0];
  return unresolved[(index + 1) % unresolved.length] ?? null;
}

export function getPreviousUnresolvedEntity(
  entities: ReviewEntity[],
  currentId: string | null,
): ReviewEntity | null {
  const unresolved = entities.filter(
    (entity) =>
      entity.queueSection !== "reviewed" && entity.queueSection !== "false_positive",
  );
  if (!unresolved.length) return null;
  if (!currentId) return unresolved[unresolved.length - 1];
  const index = unresolved.findIndex((entity) => entity.id === currentId);
  if (index < 0) return unresolved[unresolved.length - 1];
  return unresolved[(index - 1 + unresolved.length) % unresolved.length] ?? null;
}
