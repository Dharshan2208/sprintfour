import type { DocumentListEntry } from "./types";

const STORAGE_KEY = "sentinel-document-registry";

export function loadDocumentRegistry(): DocumentListEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as DocumentListEntry[];
  } catch {
    return [];
  }
}

export function saveDocumentRegistry(entries: DocumentListEntry[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

export function upsertDocumentEntry(entry: DocumentListEntry) {
  const existing = loadDocumentRegistry();
  const index = existing.findIndex((item) => item.documentId === entry.documentId);
  if (index >= 0) {
    existing[index] = { ...existing[index], ...entry };
  } else {
    existing.unshift(entry);
  }
  saveDocumentRegistry(existing);
  return existing;
}

export function getDocumentEntry(documentId: string) {
  return loadDocumentRegistry().find((item) => item.documentId === documentId);
}

export function updateDocumentEntry(
  documentId: string,
  patch: Partial<DocumentListEntry>,
) {
  const existing = loadDocumentRegistry();
  const index = existing.findIndex((item) => item.documentId === documentId);
  if (index < 0) return existing;
  existing[index] = { ...existing[index], ...patch };
  saveDocumentRegistry(existing);
  return existing;
}
