import { apiPost } from "./api-client";
import type { DetectionRunResponse } from "../lib/types";

export async function runDetection(documentId: string) {
  return apiPost<DetectionRunResponse>("/detection/run", { document_id: documentId });
}
