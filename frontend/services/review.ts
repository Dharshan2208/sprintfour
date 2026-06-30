import { apiGet, apiPost } from "./api-client";
import type { AuditEvent, ReviewItem } from "../lib/types";

export async function getReviewItems(
  documentId: string,
  detections: Record<string, unknown>[],
) {
  return apiPost<{
    document_id: string;
    total_items: number;
    items: ReviewItem[];
  }>("/review/items", { document_id: documentId, detections });
}

export async function approveDetection(
  documentId: string,
  detectionId: string,
  actor: string,
  reason?: string,
) {
  return apiPost<ReviewItem>("/review/approve", {
    document_id: documentId,
    detection_id: detectionId,
    actor,
    reason,
  });
}

export async function rejectDetection(
  documentId: string,
  detectionId: string,
  actor: string,
  reason?: string,
) {
  return apiPost<ReviewItem>("/review/reject", {
    document_id: documentId,
    detection_id: detectionId,
    actor,
    reason,
  });
}

export async function editDetection(
  documentId: string,
  detectionId: string,
  actor: string,
  updates: {
    entity?: string;
    entity_type?: string;
    confidence?: number;
    reason_text?: string;
    start_offset?: number;
    end_offset?: number;
    page?: number;
    line?: number;
    reason?: string;
  },
) {
  return apiPost<ReviewItem>("/review/edit", {
    document_id: documentId,
    detection_id: detectionId,
    actor,
    ...updates,
  });
}

export async function addDetection(
  documentId: string,
  payload: {
    entity: string;
    entity_type: string;
    actor: string;
    reason?: string;
    confidence?: number;
    start_offset: number;
    end_offset: number;
    page: number;
    line: number;
  },
) {
  return apiPost<ReviewItem>("/review/add", {
    document_id: documentId,
    ...payload,
  });
}

export async function deleteDetection(
  documentId: string,
  detectionId: string,
  actor: string,
  reason?: string,
) {
  return apiPost<ReviewItem>("/review/delete", {
    document_id: documentId,
    detection_id: detectionId,
    actor,
    reason,
  });
}

export async function undoReview(documentId: string, actor: string) {
  return apiPost<{
    document_id: string;
    undone?: boolean;
    undone_action?: string;
    detection_id?: string;
  }>("/review/undo", { document_id: documentId, actor });
}

export async function redoReview(documentId: string, actor: string) {
  return apiPost<{
    document_id: string;
    redone?: boolean;
    redone_action?: string;
    detection_id?: string;
  }>("/review/redo", { document_id: documentId, actor });
}

// ── Batch operations (for quick correction) ────────────────────────

export async function batchApprove(
  documentId: string,
  detectionIds: string[],
  actor: string,
  reason?: string,
) {
  return apiPost<{
    document_id: string;
    processed_count: number;
    items: ReviewItem[];
  }>("/review/batch-approve", {
    document_id: documentId,
    detection_ids: detectionIds,
    actor,
    reason,
  });
}

export async function batchReject(
  documentId: string,
  detectionIds: string[],
  actor: string,
  reason?: string,
) {
  return apiPost<{
    document_id: string;
    processed_count: number;
    items: ReviewItem[];
  }>("/review/batch-reject", {
    document_id: documentId,
    detection_ids: detectionIds,
    actor,
    reason,
  });
}

export async function getReviewHistory(documentId: string, limit?: number) {
  const query = limit ? `?limit=${limit}` : "";
  return apiGet<{
    document_id: string;
    total_events: number;
    events: AuditEvent[];
  }>(`/review/history/${documentId}${query}`);
}
