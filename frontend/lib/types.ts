// ── API envelope ──────────────────────────────────────────────────

export interface ApiMeta {
  request_id: string;
  timestamp: string;
}

export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
  meta: ApiMeta;
}

// ── Backend-aligned types ─────────────────────────────────────────

export type ReviewState =
  | "pending"
  | "approved"
  | "rejected"
  | "modified"
  | "manually_added"
  | "system_generated"
  | "unreviewed"
  | "exported";

export type PriorityLevel = "critical" | "high" | "medium" | "low";

export interface BackendDetection {
  id: string;
  entity: string;
  entity_type: string;
  confidence: number;
  reason: string;
  sources: string[];
  start_offset: number;
  end_offset: number;
  page: number;
  line: number;
  status: string;
  review_state: string;
}

export interface DocumentPage {
  page_number: number;
  text: string;
  start_offset: number;
  end_offset: number;
  paragraphs: DocumentParagraph[];
}

export interface DocumentParagraph {
  paragraph_number: number;
  text: string;
  start_offset: number;
  end_offset: number;
  lines: DocumentLine[];
}

export interface DocumentLine {
  text: string;
  line_number: number;
  start_offset: number;
  end_offset: number;
}

export interface DocumentRecord {
  document_id: string;
  text: string;
  metadata: {
    filename: string;
    file_size: number;
    mime_type: string;
    extension: string;
    upload_timestamp: string;
    processing_status: string;
  };
  page_count: number;
  character_count: number;
  text_preview: string;
  pages: DocumentPage[];
  processing_status: string;
}

export interface UploadResponse {
  document_id: string;
  metadata: DocumentRecord["metadata"];
  page_count: number;
  character_count: number;
  text_preview: string;
  processing_status: string;
}

export interface DetectionRunResponse {
  document_id: string;
  processing_time_ms: number;
  summary: {
    total_count: number;
    per_type: Record<string, number>;
    per_source: Record<string, number>;
    high_confidence_count: number;
    medium_confidence_count: number;
    low_confidence_count: number;
  };
  detections: BackendDetection[];
}

export interface ReviewItem {
  detection_id: string;
  entity: string;
  entity_type: string;
  confidence: number;
  reason: string;
  sources: string[];
  start_offset: number;
  end_offset: number;
  page: number;
  line: number;
  review_state: ReviewState;
}

export interface PriorityItem {
  detection_id: string;
  entity_type: string;
  entity: string;
  confidence: number;
  review_state: string;
  priority: PriorityLevel;
  reason: string;
}

export interface ReviewProgress {
  total_items: number;
  reviewed_count: number;
  pending_count: number;
  approval_rate: number;
  review_percentage: number;
}

export interface RiskReport {
  document_id: string;
  overall_score: number;
  export_ready: boolean;
  export_ready_threshold: number;
  review_progress: ReviewProgress;
  priority_items: PriorityItem[];
  critical_items: PriorityItem[];
  warnings: string[];
  recommendations: string[];
  analyzed_at: string;
}

export interface ValidationIssue {
  severity: string;
  code: string;
  message: string;
  detection_id: string | null;
}

export interface ValidationResult {
  document_id: string;
  is_valid: boolean;
  issues: ValidationIssue[];
}

export interface AuditEvent {
  event_id: string;
  document_id: string;
  detection_id: string;
  previous_review_state: string | null;
  new_review_state: string;
  action: {
    action_type: string;
    detection_id: string;
    document_id: string;
    actor: string;
    reason: string | null;
    timestamp: string;
    previous_state: string | null;
    new_state: string;
  };
  event_timestamp: string;
}

// ── View model (UI) ─────────────────────────────────────────────────

export type QueueSection =
  | "critical"
  | "high_risk"
  | "low_confidence"
  | "false_positive"
  | "reviewed";

export type FilterKey =
  | "all"
  | "critical"
  | "needs_review"
  | "approved"
  | "rejected"
  | "manual"
  | "low_confidence"
  | "missed"
  | "false_positive";

export interface ReviewEntity {
  id: string;
  entity: string;
  entityType: string;
  confidence: number;
  reason: string;
  sources: string[];
  startOffset: number;
  endOffset: number;
  page: number;
  line: number;
  reviewState: ReviewState;
  priority: PriorityLevel;
  priorityReason: string;
  queueSection: QueueSection;
  isManual: boolean;
  isFalsePositive: boolean;
  isLowConfidence: boolean;
}

export interface DocumentListEntry {
  documentId: string;
  filename: string;
  uploadedAt: string;
  pageCount: number;
  detectionCount: number;
  reviewPercentage: number;
  overallRisk: number;
  exportReady: boolean;
}

export interface ReviewStats {
  total: number;
  reviewed: number;
  unreviewed: number;
  criticalOpen: number;
  lowConfidence: number;
  manualAdditions: number;
  criticalCompletion: number;
}

export interface UserSettings {
  actorName: string;
  requireFullReview: boolean;
  defaultExportFormat: "txt" | "pdf" | "json";
  showKeyboardHints: boolean;
}

/** Types for the AI correction workflow (Problem 3) */

export type CorrectionMode = "off" | "spot_missed" | "review_false_positives" | "diff";

export interface MissedPiiSuggestion {
  id: string;
  text: string;
  startOffset: number;
  endOffset: number;
  suggestedType: string;
  confidence: number;
  reason: string;
}

export interface TextSelectionRange {
  startOffset: number;
  endOffset: number;
  text: string;
  page: number;
  line: number;
}
