"""
Detection Update Service — applies review actions to detections.

This service is the **single source of truth** for computing the current
review state of a detection.  It works by:

1. Looking up the current state from :class:`InMemoryReviewStore`.
2. Determining the new state based on the action type.
3. Persisting the new state.
4. Returning both the previous and new states so callers can record
   audit events.

This service knows nothing about audit, history, or validation — those
are handled by :class:`ReviewService`.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.exceptions import ReviewNotFoundException
from app.domain.models.review import ReviewActionType, ReviewState
from app.store.review_store import review_store

logger = logging.getLogger(settings.APP_NAME)


class DetectionUpdateService:
    """
    Manages review state transitions for detections.

    Usage::

        updater = DetectionUpdateService()
        prev_state, new_state = updater.apply_action(
            action_type=ReviewActionType.APPROVE,
            document_id="doc-123",
            detection_id="det-456",
        )
    """

    # ── Action → State Mapping ──────────────────────────────────────
    # Maps each action type to its resulting review state.

    _ACTION_TO_STATE: Dict[ReviewActionType, ReviewState] = {
        ReviewActionType.APPROVE: ReviewState.APPROVED,
        ReviewActionType.REJECT: ReviewState.REJECTED,
        ReviewActionType.EDIT: ReviewState.MODIFIED,
        ReviewActionType.ADD: ReviewState.MANUALLY_ADDED,
        ReviewActionType.DELETE: ReviewState.REJECTED,
        # Undo/redo will set the state explicitly based on the stored
        # previous state, not from this mapping.
    }

    # ── Public API ──────────────────────────────────────────────────

    def apply_action(
        self,
        action_type: ReviewActionType,
        document_id: str,
        detection_id: str,
    ) -> Tuple[Optional[ReviewState], ReviewState]:
        """
        Apply a review action and return ``(previous_state, new_state)``.

        Parameters
        ----------
        action_type : ReviewActionType
            The action being applied.
        document_id : str
            The document the detection belongs to.
        detection_id : str
            The detection being acted upon.

        Returns
        -------
        tuple of (Optional[ReviewState], ReviewState)
            ``(previous_state, new_state)`` — the state before and after
            the action.  ``previous_state`` may be ``None`` for new
            detections.

        Raises
        ------
        ReviewNotFoundException
            If the detection does not exist for non-ADD actions.
        """
        # ── ADD is special: it creates a new review item ──
        if action_type == ReviewActionType.ADD:
            new_state = ReviewState.MANUALLY_ADDED
            review_store.set_state(document_id, detection_id, new_state)
            return None, new_state

        # ── For all other actions, get the current state ──
        current_state = review_store.get_state(document_id, detection_id)
        if current_state is None:
            # The detection hasn't been tracked in review yet — this is
            # likely a detection from the pipeline that hasn't been
            # reviewed before.  Default to PENDING.
            current_state = ReviewState.PENDING

        # ── Determine new state ──
        if action_type == ReviewActionType.UNDO:
            # Undo restores the previous state (set externally by
            # HistoryService).  For now, just keep the current state.
            # The actual state will be set by the undo handler.
            new_state = current_state
        elif action_type == ReviewActionType.REDO:
            new_state = current_state
        else:
            new_state = self._ACTION_TO_STATE.get(action_type, current_state)

        # ── Persist ──
        review_store.set_state(document_id, detection_id, new_state)

        logger.debug(
            "Detection review state updated",
            extra={
                "document_id": document_id,
                "detection_id": detection_id,
                "previous_state": current_state.value if current_state else None,
                "new_state": new_state.value,
                "action": action_type.value,
            },
        )

        return current_state, new_state

    def set_state_directly(
        self,
        document_id: str,
        detection_id: str,
        state: ReviewState,
    ) -> None:
        """
        Directly set the review state for a detection.

        This is used by :class:`HistoryService` during undo/redo to
        restore a previous state without going through the action →
        state mapping.

        Use with care — this bypasses normal validation.
        """
        review_store.set_state(document_id, detection_id, state)

    def get_state(
        self, document_id: str, detection_id: str,
    ) -> Optional[ReviewState]:
        """
        Get the current review state for a detection.
        Returns ``None`` if the detection is not tracked.
        """
        return review_store.get_state(document_id, detection_id)

    def get_all_states(
        self, document_id: str,
    ) -> Dict[str, ReviewState]:
        """
        Get all review states for a document.

        Returns a dict mapping detection_id → ReviewState.
        """
        return review_store.get_all_states(document_id)

    def remove_detection(self, document_id: str, detection_id: str) -> None:
        """
        Remove a detection from review tracking entirely.

        Used when a detection is fully deleted (not just rejected).
        """
        review_store.remove_state(document_id, detection_id)
