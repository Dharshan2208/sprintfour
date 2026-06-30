"""
Review Service — orchestrates the human review lifecycle for detections.

This is the **primary entry point** for all human review operations.
It coordinates:

1. :class:`ReviewValidator`   — validates the action before execution
2. :class:`DetectionUpdateService` — applies the state change
3. :class:`AuditService`      — records the immutable audit event
4. :class:`HistoryService`    — records the action for undo/redo

The service does NOT contain business logic for validation, state
transitions, or audit — it delegates to the appropriate single-responsibility
service.

Usage::

    service = ReviewService()
    result = service.approve_detection(
        document_id="doc-123",
        detection_id="det-456",
        actor="user-abc",
        reason="Looks correct",
    )
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.domain.models.review import (
    ReviewAction,
    ReviewActionType,
    ReviewItem,
    ReviewState,
)
from app.services.audit_service import AuditService
from app.services.detection_update_service import DetectionUpdateService
from app.services.history_service import HistoryService
from app.services.review_validator import ReviewValidator
from app.store.review_store import review_store

logger = logging.getLogger(settings.APP_NAME)


class ReviewService:
    """
    Orchestrates human review operations on PII detections.

    Every public method follows the same pattern:
    1. Build a :class:`ReviewAction`.
    2. Validate it via :class:`ReviewValidator`.
    3. Apply it via :class:`DetectionUpdateService`.
    4. Record audit event via :class:`AuditService`.
    5. Push to :class:`HistoryService` for undo/redo.
    """

    def __init__(
        self,
        validator: Optional[ReviewValidator] = None,
        update_service: Optional[DetectionUpdateService] = None,
        audit_service: Optional[AuditService] = None,
        history_service: Optional[HistoryService] = None,
    ) -> None:
        self._validator = validator or ReviewValidator()
        self._update_service = update_service or DetectionUpdateService()
        self._audit_service = audit_service or AuditService()
        self._history_service = history_service or HistoryService()

    # ──────────────────────────────────────────────────────────────
    # Review Actions
    # ──────────────────────────────────────────────────────────────

    def approve_detection(
        self,
        document_id: str,
        detection_id: str,
        actor: str = "unknown",
        reason: Optional[str] = None,
    ) -> ReviewItem:
        """
        Approve a detection as correctly identified PII.

        Parameters
        ----------
        document_id : str
            The document the detection belongs to.
        detection_id : str
            The detection to approve.
        actor : str
            Who is performing the action.
        reason : str, optional
            Why the detection is being approved.

        Returns
        -------
        ReviewItem
            The updated review item reflecting the new state.
        """
        action = self._build_action(
            action_type=ReviewActionType.APPROVE,
            document_id=document_id,
            detection_id=detection_id,
            actor=actor,
            reason=reason,
        )

        # Validate, apply, record
        return self._execute_action(action, document_id)

    def reject_detection(
        self,
        document_id: str,
        detection_id: str,
        actor: str = "unknown",
        reason: Optional[str] = None,
    ) -> ReviewItem:
        """
        Reject a detection as a false positive.

        Parameters
        ----------
        document_id : str
            The document the detection belongs to.
        detection_id : str
            The detection to reject.
        actor : str
            Who is performing the action.
        reason : str, optional
            Why the detection is being rejected.

        Returns
        -------
        ReviewItem
            The updated review item reflecting the new state.
        """
        action = self._build_action(
            action_type=ReviewActionType.REJECT,
            document_id=document_id,
            detection_id=detection_id,
            actor=actor,
            reason=reason,
        )
        return self._execute_action(action, document_id)

    def edit_detection(
        self,
        document_id: str,
        detection_id: str,
        actor: str = "unknown",
        reason: Optional[str] = None,
        **updates: Any,
    ) -> ReviewItem:
        """
        Edit a detection's attributes (e.g. entity text, type, offsets).

        Parameters
        ----------
        document_id : str
            The document the detection belongs to.
        detection_id : str
            The detection to edit.
        actor : str
            Who is performing the action.
        reason : str, optional
            Why the detection is being edited.
        **updates
            The fields to update and their new values.  Allowed keys:
            ``entity``, ``entity_type``, ``confidence``, ``reason``,
            ``start_offset``, ``end_offset``, ``page``, ``line``.

        Returns
        -------
        ReviewItem
            The updated review item reflecting the new state.
        """
        action = self._build_action(
            action_type=ReviewActionType.EDIT,
            document_id=document_id,
            detection_id=detection_id,
            actor=actor,
            reason=reason,
            new_values=updates,
        )
        return self._execute_action(action, document_id)

    def add_detection(
        self,
        document_id: str,
        entity: str,
        entity_type: str,
        actor: str = "unknown",
        reason: Optional[str] = None,
        confidence: float = 1.0,
        start_offset: int = 0,
        end_offset: int = 0,
        page: int = 0,
        line: int = 0,
        sources: Optional[List[str]] = None,
    ) -> ReviewItem:
        """
        Manually add a detection that the AI missed.

        This creates a new detection with review state ``MANUALLY_ADDED``.

        Parameters
        ----------
        document_id : str
            The document to add the detection to.
        entity : str
            The PII entity text.
        entity_type : str
            The PII type.
        actor : str
            Who is adding the detection.
        reason : str, optional
            Why this detection is being added.
        confidence : float
            Confidence score for the manually added detection.
        start_offset : int
            Start offset in the normalised text.
        end_offset : int
            End offset in the normalised text.
        page : int
            1-based page number (0 if unknown).
        line : int
            1-based line number (0 if unknown).
        sources : list of str, optional
            Source identifiers.

        Returns
        -------
        ReviewItem
            The newly created review item.
        """
        import uuid

        detection_id = str(uuid.uuid4())

        values = {
            "entity": entity,
            "entity_type": entity_type,
            "confidence": confidence,
            "start_offset": start_offset,
            "end_offset": end_offset,
            "page": page,
            "line": line,
            "sources": sources or ["manual"],
        }

        action = self._build_action(
            action_type=ReviewActionType.ADD,
            document_id=document_id,
            detection_id=detection_id,
            actor=actor,
            reason=reason,
            new_values=values,
        )

        # Validate, apply, record
        return self._execute_action(action, document_id)

    def delete_detection(
        self,
        document_id: str,
        detection_id: str,
        actor: str = "unknown",
        reason: Optional[str] = None,
    ) -> ReviewItem:
        """
        Delete a detection entirely from the review set.

        This removes the detection from the review store so it no longer
        appears in the review list.  An audit event is still recorded.

        Parameters
        ----------
        document_id : str
            The document the detection belongs to.
        detection_id : str
            The detection to delete.
        actor : str
            Who is performing the action.
        reason : str, optional
            Why the detection is being deleted.

        Returns
        -------
        ReviewItem
            A summary item showing the deleted state.
        """
        action = self._build_action(
            action_type=ReviewActionType.DELETE,
            document_id=document_id,
            detection_id=detection_id,
            actor=actor,
            reason=reason,
        )

        # Validate
        all_ids = self._get_all_detection_ids(document_id)
        self._validator.validate_action(action, document_id, all_ids)

        # Apply state change
        prev_state, new_state = self._update_service.apply_action(
            ReviewActionType.DELETE, document_id, detection_id,
        )

        # Record audit
        self._audit_service.record_action(
            action=action,
            document_id=document_id,
            detection_id=detection_id,
            previous_state=prev_state,
            new_state=new_state,
        )

        # Push to history
        self._history_service.push_action(action)

        # Remove from tracking
        self._update_service.remove_detection(document_id, detection_id)

        logger.info(
            "Detection deleted",
            extra={
                "document_id": document_id,
                "detection_id": detection_id,
                "actor": actor,
            },
        )

        return ReviewItem(
            detection_id=detection_id,
            document_id=document_id,
            entity="",
            entity_type="",
            confidence=0.0,
            reason="Deleted by reviewer",
            sources=[],
            start_offset=0,
            end_offset=0,
            review_state=ReviewState.REJECTED,
        )

    # ──────────────────────────────────────────────────────────────
    # Undo / Redo
    # ──────────────────────────────────────────────────────────────

    def undo(self, document_id: str, actor: str = "unknown") -> Optional[ReviewAction]:
        """
        Undo the most recent review action for a document.

        Returns the action that was undone, or ``None`` if nothing to undo.
        """
        action = self._history_service.undo(document_id)
        if action is None:
            return None

        # Restore the previous state
        if action.previous_state is not None:
            self._update_service.set_state_directly(
                document_id, action.detection_id, action.previous_state,
            )

        # Record audit for the undo
        undo_action = self._build_action(
            action_type=ReviewActionType.UNDO,
            document_id=document_id,
            detection_id=action.detection_id,
            actor=actor,
            reason=f"Undid {action.action_type.value} of {action.detection_id}",
            previous_state=action.new_state,
            new_state=action.previous_state,
        )
        self._audit_service.record_action(
            action=undo_action,
            document_id=document_id,
            detection_id=action.detection_id,
            previous_state=action.new_state,
            new_state=action.previous_state,
        )

        logger.info(
            "Undo completed",
            extra={
                "document_id": document_id,
                "detection_id": action.detection_id,
                "undone_action": action.action_type.value,
            },
        )

        return action

    def redo(self, document_id: str, actor: str = "unknown") -> Optional[ReviewAction]:
        """
        Redo the most recently undone action for a document.

        Returns the action that was redone, or ``None`` if nothing to redo.
        """
        action = self._history_service.redo(document_id)
        if action is None:
            return None

        # Re-apply the action's new state
        if action.new_state is not None:
            self._update_service.set_state_directly(
                document_id, action.detection_id, action.new_state,
            )

        # Record audit for the redo
        redo_action = self._build_action(
            action_type=ReviewActionType.REDO,
            document_id=document_id,
            detection_id=action.detection_id,
            actor=actor,
            reason=f"Redid {action.action_type.value} of {action.detection_id}",
            previous_state=action.previous_state,
            new_state=action.new_state,
        )
        self._audit_service.record_action(
            action=redo_action,
            document_id=document_id,
            detection_id=action.detection_id,
            previous_state=action.previous_state,
            new_state=action.new_state,
        )

        logger.info(
            "Redo completed",
            extra={
                "document_id": document_id,
                "detection_id": action.detection_id,
                "redone_action": action.action_type.value,
            },
        )

        return action

    # ──────────────────────────────────────────────────────────────
    # Queries
    # ──────────────────────────────────────────────────────────────

    def get_review_items(
        self,
        document_id: str,
        detections: List[Dict[str, Any]],
    ) -> List[ReviewItem]:
        """
        Build the current list of review items for a document.

        This takes the original detections (from the detection pipeline)
        and overlays the current review state from the store.

        Parameters
        ----------
        document_id : str
            The document to get review items for.
        detections : list of dict
            The original detections as returned by the detection pipeline.
            Each dict must have at least ``id``, ``entity``, ``entity_type``,
            ``confidence``, ``reason``, ``sources``, ``start_offset``,
            ``end_offset``, ``page``, ``line``.

        Returns
        -------
        list of ReviewItem
            All review items with their current review state.
        """
        all_states = review_store.get_all_states(document_id)
        items: List[ReviewItem] = []

        for det in detections:
            det_id = det.get("id", "")
            state = all_states.get(det_id, ReviewState.PENDING)

            items.append(ReviewItem(
                detection_id=det_id,
                document_id=document_id,
                entity=det.get("entity", ""),
                entity_type=det.get("entity_type", ""),
                confidence=det.get("confidence", 0.0),
                reason=det.get("reason", ""),
                sources=det.get("sources", []),
                start_offset=det.get("start_offset", 0),
                end_offset=det.get("end_offset", 0),
                page=det.get("page", 0),
                line=det.get("line", 0),
                review_state=state,
            ))

        return items

    def get_history(
        self,
        document_id: str,
        *,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get the audit history for a document.

        Parameters
        ----------
        document_id : str
            The document to get history for.
        limit : int, optional
            Maximum number of events to return.

        Returns
        -------
        list of dict
            Chronological list of audit events with human-readable fields.
        """
        events = self._audit_service.get_document_events(document_id, limit=limit)
        return [
            {
                "event_id": e.event_id,
                "action": e.action.action_type.value,
                "detection_id": e.detection_id,
                "actor": e.action.actor,
                "reason": e.action.reason,
                "previous_state": e.previous_review_state,
                "new_state": e.new_review_state,
                "timestamp": e.event_timestamp.isoformat(),
            }
            for e in events
        ]

    def can_undo(self, document_id: str) -> bool:
        """Check if there are any actions to undo for this document."""
        return self._history_service.can_undo(document_id)

    def can_redo(self, document_id: str) -> bool:
        """Check if there are any actions to redo for this document."""
        return self._history_service.can_redo(document_id)

    # ──────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────

    def _build_action(
        self,
        action_type: ReviewActionType,
        document_id: str,
        detection_id: str,
        actor: str = "unknown",
        reason: Optional[str] = None,
        new_values: Optional[Dict[str, Any]] = None,
        previous_state: Optional[ReviewState] = None,
        new_state: Optional[ReviewState] = None,
    ) -> ReviewAction:
        """
        Build a :class:`ReviewAction` with sensible defaults.

        The ``previous_state`` and ``new_state`` are filled in by
        ``_execute_action`` after the state transition occurs.
        """
        return ReviewAction(
            action_type=action_type,
            detection_id=detection_id,
            document_id=document_id,
            previous_state=previous_state,
            new_state=new_state or ReviewState.PENDING,
            new_values=new_values,
            actor=actor,
            reason=reason,
        )

    def _execute_action(
        self,
        action: ReviewAction,
        document_id: str,
    ) -> ReviewItem:
        """
        Execute a validated review action end-to-end.

        1. Validate
        2. Apply state transition
        3. Record audit
        4. Push to history
        5. Return the updated ReviewItem
        """
        # 1. Validate
        all_ids = self._get_all_detection_ids(document_id)
        self._validator.validate_action(action, document_id, all_ids)

        # 2. Apply state transition
        prev_state, new_state = self._update_service.apply_action(
            action.action_type, document_id, action.detection_id,
        )

        # Update the action with actual states for history
        action.previous_state = prev_state
        action.new_state = new_state

        # 3. Record audit
        self._audit_service.record_action(
            action=action,
            document_id=document_id,
            detection_id=action.detection_id,
            previous_state=prev_state,
            new_state=new_state,
        )

        # 4. Push to history
        self._history_service.push_action(action)

        # 5. Build and return the ReviewItem
        all_states = review_store.get_all_states(document_id)
        current_state = all_states.get(action.detection_id, new_state)

        # For edit actions, include the updated values
        item_kwargs: Dict[str, Any] = {
            "detection_id": action.detection_id,
            "document_id": document_id,
            "review_state": current_state,
        }

        if action.action_type == ReviewActionType.EDIT and action.new_values:
            item_kwargs.update({
                "entity": action.new_values.get("entity", ""),
                "entity_type": action.new_values.get("entity_type", ""),
                "confidence": action.new_values.get("confidence", 0.0),
                "reason": action.new_values.get("reason", ""),
                "start_offset": action.new_values.get("start_offset", 0),
                "end_offset": action.new_values.get("end_offset", 0),
                "page": action.new_values.get("page", 0),
                "line": action.new_values.get("line", 0),
            })
        elif action.action_type == ReviewActionType.ADD and action.new_values:
            item_kwargs.update({
                "entity": action.new_values.get("entity", ""),
                "entity_type": action.new_values.get("entity_type", ""),
                "confidence": action.new_values.get("confidence", 1.0),
                "reason": action.reason or "Manually added",
                "sources": action.new_values.get("sources", ["manual"]),
                "start_offset": action.new_values.get("start_offset", 0),
                "end_offset": action.new_values.get("end_offset", 0),
                "page": action.new_values.get("page", 0),
                "line": action.new_values.get("line", 0),
            })
        else:
            # For approve/reject, return the item based on stored data
            # (we don't have the original detection here; the caller
            # will typically call get_review_items to get full data)
            item_kwargs.update({
                "entity": "",
                "entity_type": "",
                "confidence": 0.0,
                "reason": f"Detection {action.action_type.value}d",
                "sources": [],
                "start_offset": 0,
                "end_offset": 0,
            })

        logger.info(
            "Review action executed",
            extra={
                "document_id": document_id,
                "detection_id": action.detection_id,
                "action": action.action_type.value,
                "previous_state": prev_state.value if prev_state else None,
                "new_state": new_state.value,
            },
        )

        return ReviewItem(**item_kwargs)

    def _get_all_detection_ids(self, document_id: str) -> List[str]:
        """
        Get all detection IDs currently tracked for a document.

        This includes both pipeline detections and manually added ones.
        """
        all_states = review_store.get_all_states(document_id)
        return list(all_states.keys())
