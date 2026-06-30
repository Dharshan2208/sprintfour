import { useCallback } from "react";
import { updateDocumentEntry } from "../lib/document-registry";
import { detectionToApiPayload } from "../lib/mappers";
import {
  addDetection,
  approveDetection,
  batchApprove,
  batchReject,
  deleteDetection,
  editDetection,
  redoReview,
  rejectDetection,
  undoReview,
} from "../services/review";
import { useDetectionStore } from "../stores/detection-store";
import { useReviewStore } from "../stores/review-store";
import { useUIStore } from "../stores/ui-store";
import {
  getNextUnresolvedEntity,
  refreshRiskAndReview,
} from "./use-workspace-data";

export function useReviewActions(documentId: string) {
  const actor = useUIStore((state) => state.settings.actorName);
  const setMutating = useReviewStore((state) => state.setMutating);
  const showSnackbar = useReviewStore((state) => state.showSnackbar);
  const setActiveEntityId = useUIStore((state) => state.setActiveEntityId);

  const afterMutation = useCallback(
    async (message: string, options?: { advance?: boolean; currentId?: string }) => {
      const detections = useDetectionStore.getState().detections;
      const { entities, riskReport, stats } = await refreshRiskAndReview(
        documentId,
        detections,
      );

      updateDocumentEntry(documentId, {
        detectionCount: stats.total,
        reviewPercentage: Math.round(riskReport.review_progress.review_percentage),
        overallRisk: Math.round(riskReport.overall_score * 100),
        exportReady: riskReport.export_ready,
      });

      if (options?.advance) {
        const next = getNextUnresolvedEntity(entities, options.currentId ?? null);
        if (next) setActiveEntityId(next.id);
      }

      showSnackbar(message, "undo");
      return entities;
    },
    [documentId, setActiveEntityId, showSnackbar],
  );

  const approve = useCallback(
    async (detectionId: string) => {
      setMutating(true);
      try {
        await approveDetection(documentId, detectionId, actor);
        await afterMutation("Detection approved", { advance: true, currentId: detectionId });
      } finally {
        setMutating(false);
      }
    },
    [actor, afterMutation, documentId, setMutating],
  );

  const reject = useCallback(
    async (detectionId: string) => {
      setMutating(true);
      try {
        await rejectDetection(documentId, detectionId, actor);
        await afterMutation("Detection rejected", { advance: true, currentId: detectionId });
      } finally {
        setMutating(false);
      }
    },
    [actor, afterMutation, documentId, setMutating],
  );

  const edit = useCallback(
    async (
      detectionId: string,
      updates: {
        entity?: string;
        entity_type?: string;
        confidence?: number;
        reason_text?: string;
        start_offset?: number;
        end_offset?: number;
        page?: number;
        line?: number;
      },
    ) => {
      setMutating(true);
      try {
        await editDetection(documentId, detectionId, actor, updates);
        await afterMutation("Detection updated");
      } finally {
        setMutating(false);
      }
    },
    [actor, afterMutation, documentId, setMutating],
  );

  const add = useCallback(
    async (payload: {
      entity: string;
      entity_type: string;
      start_offset: number;
      end_offset: number;
      page: number;
      line: number;
      reason?: string;
    }) => {
      setMutating(true);
      try {
        const created = await addDetection(documentId, { ...payload, actor });
        const detections = useDetectionStore.getState().detections;
        useDetectionStore.getState().upsertDetection({
          id: created.detection_id,
          entity: created.entity,
          entity_type: created.entity_type,
          confidence: created.confidence,
          reason: created.reason,
          sources: created.sources,
          start_offset: created.start_offset,
          end_offset: created.end_offset,
          page: created.page,
          line: created.line,
          status: "pending_review",
          review_state: created.review_state,
        });
        await afterMutation("Manual detection added");
        setActiveEntityId(created.detection_id);
      } finally {
        setMutating(false);
      }
    },
    [actor, afterMutation, documentId, setActiveEntityId, setMutating],
  );

  const remove = useCallback(
    async (detectionId: string) => {
      setMutating(true);
      try {
        await deleteDetection(documentId, detectionId, actor);
        useDetectionStore.getState().removeDetection(detectionId);
        await afterMutation("Detection deleted");
      } finally {
        setMutating(false);
      }
    },
    [actor, afterMutation, documentId, setMutating],
  );

  const undo = useCallback(async () => {
    setMutating(true);
    try {
      await undoReview(documentId, actor);
      await afterMutation("Action undone");
    } finally {
      setMutating(false);
    }
  }, [actor, afterMutation, documentId, setMutating]);

  const redo = useCallback(async () => {
    setMutating(true);
    try {
      await redoReview(documentId, actor);
      await afterMutation("Action redone");
    } finally {
      setMutating(false);
    }
  }, [actor, afterMutation, documentId, setMutating]);

  const batchApproveAction = useCallback(
    async (detectionIds: string[]) => {
      setMutating(true);
      try {
        await batchApprove(documentId, detectionIds, actor, "Batch approved");
        await afterMutation(`${detectionIds.length} detections approved`);
      } finally {
        setMutating(false);
      }
    },
    [actor, afterMutation, documentId, setMutating],
  );

  const batchRejectAction = useCallback(
    async (detectionIds: string[]) => {
      setMutating(true);
      try {
        await batchReject(documentId, detectionIds, actor, "Batch rejected as false positives");
        await afterMutation(`${detectionIds.length} detections rejected`);
      } finally {
        setMutating(false);
      }
    },
    [actor, afterMutation, documentId, setMutating],
  );

  const getDetectionPayload = useCallback(() => {
    return useDetectionStore.getState().detections.map(detectionToApiPayload);
  }, []);

  return {
    approve,
    reject,
    edit,
    add,
    remove,
    undo,
    redo,
    batchApprove: batchApproveAction,
    batchReject: batchRejectAction,
    getDetectionPayload,
  };
}
