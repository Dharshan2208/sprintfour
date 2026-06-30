import { create } from "zustand";
import type { RiskReport } from "../lib/types";

interface RiskStore {
  report: RiskReport | null;
  isLoading: boolean;
  error: string | null;
  setReport: (report: RiskReport | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useRiskStore = create<RiskStore>((set) => ({
  report: null,
  isLoading: false,
  error: null,
  setReport: (report) => set({ report, error: null }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  reset: () => set({ report: null, isLoading: false, error: null }),
}));
