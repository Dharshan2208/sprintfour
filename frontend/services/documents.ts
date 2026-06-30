import { apiGet, apiUpload } from "./api-client";
import type { DocumentRecord, UploadResponse } from "../lib/types";

export async function uploadDocument(file: File) {
  return apiUpload<UploadResponse>("/documents/upload", file);
}

export async function getDocument(documentId: string) {
  return apiGet<DocumentRecord>(`/documents/${documentId}`);
}
