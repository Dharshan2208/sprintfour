import { create } from "zustand";
import type { BackendDetection } from "../lib/types";

interface DetectionStore {
  detections: BackendDetection[];
  processingTimeMs: number | null;
  isLoading: boolean;
  error: string | null;
  setDetections: (detections: BackendDetection[], processingTimeMs?: number) => void;
  upsertDetection: (detection: BackendDetection) => void;
  removeDetection: (detectionId: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useDetectionStore = create<DetectionStore>((set) => ({
  detections: [],
  processingTimeMs: null,
  isLoading: false,
  error: null,
  setDetections: (detections, processingTimeMs) =>
    set({ detections, processingTimeMs: processingTimeMs ?? null, error: null }),
  upsertDetection: (detection) =>
    set((state) => {
      const index = state.detections.findIndex((item) => item.id === detection.id);
      if (index < 0) return { detections: [...state.detections, detection] };
      const next = [...state.detections];
      next[index] = detection;
      return { detections: next };
    }),
  removeDetection: (detectionId) =>
    set((state) => ({
      detections: state.detections.filter((item) => item.id !== detectionId),
    })),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  reset: () =>
    set({ detections: [], processingTimeMs: null, isLoading: false, error: null }),
}));
