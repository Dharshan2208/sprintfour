import { create } from "zustand";
import type { DocumentRecord } from "../lib/types";

interface DocumentStore {
  document: DocumentRecord | null;
  isLoading: boolean;
  error: string | null;
  setDocument: (document: DocumentRecord | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useDocumentStore = create<DocumentStore>((set) => ({
  document: null,
  isLoading: false,
  error: null,
  setDocument: (document) => set({ document, error: null }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  reset: () => set({ document: null, isLoading: false, error: null }),
}));
