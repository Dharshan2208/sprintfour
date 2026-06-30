import { apiPost } from "./api-client";
import type { RiskReport } from "../lib/types";

export async function assessRisk(
  documentId: string,
  detections: Record<string, unknown>[],
  reviewStates?: Record<string, string>,
) {
  return apiPost<RiskReport>("/risk/assess", {
    document_id: documentId,
    detections,
    review_states: reviewStates,
  });
}

export async function getRiskSummary(
  documentId: string,
  detections: Record<string, unknown>[],
) {
  return apiPost<{
    document_id: string;
    overall_score: number;
    export_ready: boolean;
    review_progress: RiskReport["review_progress"];
    critical_count: number;
    warnings: string[];
  }>("/risk/summary", { document_id: documentId, detections });
}
