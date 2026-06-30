import { create } from "zustand";
import type { AuditEvent, CorrectionMode, FilterKey, TextSelectionRange, UserSettings } from "../lib/types";

const DEFAULT_SETTINGS: UserSettings = {
  actorName: "reviewer",
  requireFullReview: false,
  defaultExportFormat: "txt",
  showKeyboardHints: true,
};

function loadSettings(): UserSettings {
  if (typeof window === "undefined") return DEFAULT_SETTINGS;
  try {
    const raw = localStorage.getItem("sentinel-settings");
    if (!raw) return DEFAULT_SETTINGS;
    return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

interface UIStore {
  activeEntityId: string | null;
  hoveredEntityId: string | null;
  drawerOpen: boolean;
  exportModalOpen: boolean;
  validationModalOpen: boolean;
  searchQuery: string;
  activeFilter: FilterKey;
  selectedPage: number | null;
  settings: UserSettings;
  // ── Correction experience (Problem 3) ──
  correctionMode: CorrectionMode;
  batchSelectedIds: Set<string>;
  selectionRange: TextSelectionRange | null;
  showAddPiiPopover: boolean;
  addPiiAnchorRect: DOMRect | null;
  setActiveEntityId: (id: string | null) => void;
  setHoveredEntityId: (id: string | null) => void;
  setDrawerOpen: (open: boolean) => void;
  setExportModalOpen: (open: boolean) => void;
  setValidationModalOpen: (open: boolean) => void;
  setSearchQuery: (query: string) => void;
  setActiveFilter: (filter: FilterKey) => void;
  setSelectedPage: (page: number | null) => void;
  updateSettings: (patch: Partial<UserSettings>) => void;
  resetWorkspaceUi: () => void;
  // ── Correction actions ──
  setCorrectionMode: (mode: CorrectionMode) => void;
  toggleBatchSelection: (id: string) => void;
  clearBatchSelection: () => void;
  setSelectionRange: (range: TextSelectionRange | null) => void;
  setShowAddPiiPopover: (show: boolean, anchorRect?: DOMRect | null) => void;
}

export const useUIStore = create<UIStore>((set, get) => ({
  activeEntityId: null,
  hoveredEntityId: null,
  drawerOpen: false,
  exportModalOpen: false,
  validationModalOpen: false,
  searchQuery: "",
  activeFilter: "all",
  selectedPage: null,
  settings: loadSettings(),
  // ── Correction experience initial state ──
  correctionMode: "off",
  batchSelectedIds: new Set<string>(),
  selectionRange: null,
  showAddPiiPopover: false,
  addPiiAnchorRect: null,
  setActiveEntityId: (activeEntityId) => set({ activeEntityId }),
  setHoveredEntityId: (hoveredEntityId) => set({ hoveredEntityId }),
  setDrawerOpen: (drawerOpen) => set({ drawerOpen }),
  setExportModalOpen: (exportModalOpen) => set({ exportModalOpen }),
  setValidationModalOpen: (validationModalOpen) => set({ validationModalOpen }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  setActiveFilter: (activeFilter) => set({ activeFilter }),
  setSelectedPage: (selectedPage) => set({ selectedPage }),
  updateSettings: (patch) => {
    const settings = { ...get().settings, ...patch };
    if (typeof window !== "undefined") {
      localStorage.setItem("sentinel-settings", JSON.stringify(settings));
    }
    set({ settings });
  },
  setCorrectionMode: (correctionMode) => set({ correctionMode }),
  toggleBatchSelection: (id) =>
    set((state) => {
      const next = new Set(state.batchSelectedIds);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return { batchSelectedIds: next };
    }),
  clearBatchSelection: () => set({ batchSelectedIds: new Set() }),
  setSelectionRange: (selectionRange) => set({ selectionRange }),
  setShowAddPiiPopover: (show, anchorRect = null) =>
    set({ showAddPiiPopover: show, addPiiAnchorRect: anchorRect }),
  resetWorkspaceUi: () =>
    set({
      activeEntityId: null,
      hoveredEntityId: null,
      drawerOpen: false,
      exportModalOpen: false,
      validationModalOpen: false,
      searchQuery: "",
      activeFilter: "all",
      selectedPage: null,
      correctionMode: "off",
      batchSelectedIds: new Set(),
      selectionRange: null,
      showAddPiiPopover: false,
      addPiiAnchorRect: null,
    }),
}));

interface HistoryStore {
  events: AuditEvent[];
  isLoading: boolean;
  setEvents: (events: AuditEvent[]) => void;
  setLoading: (loading: boolean) => void;
  reset: () => void;
}

export const useHistoryStore = create<HistoryStore>((set) => ({
  events: [],
  isLoading: false,
  setEvents: (events) => set({ events }),
  setLoading: (isLoading) => set({ isLoading }),
  reset: () => set({ events: [], isLoading: false }),
}));
