import { apiPost } from "./api-client";
import type { ValidationResult } from "../lib/types";

export async function validateExport(
  documentId: string,
  detections: Record<string, unknown>[],
  options?: {
    reviewStates?: Record<string, string>;
    requireFullReview?: boolean;
  },
) {
  return apiPost<ValidationResult>("/export/validate", {
    document_id: documentId,
    detections,
    review_states: options?.reviewStates,
    require_full_review: options?.requireFullReview ?? false,
  });
}

export async function runExport(payload: {
  document_id: string;
  text: string;
  detections: Record<string, unknown>[];
  review_states?: Record<string, string>;
  format: "txt" | "pdf" | "json";
  exported_by: string;
  review_history?: Record<string, unknown>[];
  risk_report?: Record<string, unknown>;
}) {
  return apiPost<{
    document_id: string;
    export_format: string;
    redaction_count: number;
    export_duration_ms: number;
    exported_at: string;
    redacted_text?: string;
    json_report?: Record<string, unknown>;
    redaction_operations?: Array<{
      detection_id: string;
      entity_type: string;
      strategy: string;
    }>;
    exported?: boolean;
    validation_result?: ValidationResult;
  }>("/export/run", payload);
}
