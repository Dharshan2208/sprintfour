import { create } from "zustand";
import type { ReviewEntity, ReviewItem } from "../lib/types";

interface ReviewStore {
  reviewItems: ReviewItem[];
  entities: ReviewEntity[];
  isMutating: boolean;
  snackbar: { message: string; action?: "undo" } | null;
  setReviewItems: (items: ReviewItem[]) => void;
  setEntities: (entities: ReviewEntity[]) => void;
  updateEntity: (entity: ReviewEntity) => void;
  setMutating: (mutating: boolean) => void;
  showSnackbar: (message: string, action?: "undo") => void;
  clearSnackbar: () => void;
  reset: () => void;
}

export const useReviewStore = create<ReviewStore>((set) => ({
  reviewItems: [],
  entities: [],
  isMutating: false,
  snackbar: null,
  setReviewItems: (reviewItems) => set({ reviewItems }),
  setEntities: (entities) => set({ entities }),
  updateEntity: (entity) =>
    set((state) => ({
      entities: state.entities.map((item) => (item.id === entity.id ? entity : item)),
    })),
  setMutating: (isMutating) => set({ isMutating }),
  showSnackbar: (message, action) => set({ snackbar: { message, action } }),
  clearSnackbar: () => set({ snackbar: null }),
  reset: () =>
    set({
      reviewItems: [],
      entities: [],
      isMutating: false,
      snackbar: null,
    }),
}));
