import { useCallback, useMemo, useState } from "react";
import { Detection } from "../lib/types";
import { sortDetectionsForQueue } from "../lib/utils";

export function useDetectionSelection(initialDetections: Detection[]) {
  const [items, setItems] = useState<Detection[]>(sortDetectionsForQueue(initialDetections));
  const [activeId, setActiveId] = useState<string | null>(initialDetections[0]?.id ?? null);

  const active = useMemo(
    () => items.find((d) => d.id === activeId) ?? null,
    [items, activeId],
  );

  const updateStatus = useCallback(
    (id: string, status: Detection["status"]) => {
      setItems((prev) =>
        sortDetectionsForQueue(
          prev.map((d) =>
            d.id === id
              ? {
                  ...d,
                  status,
                  updatedAt: new Date().toISOString(),
                }
              : d,
          ),
        ),
      );
    },
    [],
  );

  const goToOffset = useCallback(
    (offset: number, reviewOnly = true) => {
      if (!items.length) return;
      const candidates = reviewOnly
        ? items.filter((d) => d.status === "unreviewed" || d.status === "missed")
        : items;
      if (!candidates.length) return;

      const index = candidates.findIndex((d) => d.id === activeId);
      const next =
        index === -1
          ? candidates[0]
          : candidates[(index + offset + candidates.length) % candidates.length];
      setActiveId(next.id);
    },
    [items, activeId],
  );

  const keyboardHandlers = useMemo(
    () => ({
      approve: () => active && updateStatus(active.id, "approved"),
      reject: () => active && updateStatus(active.id, "rejected"),
      markMissed: () => active && updateStatus(active.id, "missed"),
      next: () => goToOffset(1),
      previous: () => goToOffset(-1),
      setActiveId,
    }),
    [active, updateStatus, goToOffset],
  );

  const stats = useMemo(
    () => ({
      total: items.length,
      reviewed: items.filter((d) => d.status !== "unreviewed").length,
      unreviewed: items.filter((d) => d.status === "unreviewed").length,
      unresolvedRisk: items.filter(
        (d) => d.status === "unreviewed" || d.status === "missed",
      ).length,
      lowConfidence: items.filter(
        (d) => (d.status === "unreviewed" || d.status === "missed") && d.confidence < 0.65,
      ).length,
      criticalOpen: items.filter(
        (d) =>
          (d.status === "unreviewed" || d.status === "missed") &&
          (d.severity === "critical" || d.confidence < 0.4),
      ).length,
    }),
    [items],
  );

  return { items, active, setActiveId, updateStatus, keyboardHandlers, stats };
}

