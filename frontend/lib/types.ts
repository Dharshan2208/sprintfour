export type DetectionSeverity = "critical" | "high" | "medium" | "low";

export type DetectionStatus =
  | "unreviewed"
  | "approved"
  | "rejected"
  | "missed";

export type DetectionKind =
  | "name"
  | "email"
  | "phone"
  | "address"
  | "id"
  | "financial"
  | "other";

export interface Detection {
  id: string;
  kind: DetectionKind;
  severity: DetectionSeverity;
  confidence: number; // 0 - 1
  status: DetectionStatus;
  text: string;
  explanation: string;
  source: "model" | "rule" | "pattern" | "manual";
  start: number;
  end: number;
  paragraphIndex: number;
  createdAt: string;
  updatedAt?: string;
  auditTrail?: {
    at: string;
    action: "approved" | "rejected" | "marked_missed" | "auto_flagged";
    by: "system" | "reviewer";
    note?: string;
  }[];
}

export interface DocumentMetadata {
  id: string;
  title: string;
  riskScore: number; // 0 - 100
  totalDetections: number;
  unreviewedCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface ReviewStats {
  total: number;
  reviewed: number;
  criticalRemaining: number;
  pendingLowConfidence: number;
}

