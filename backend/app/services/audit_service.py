"""
Audit Service — append-only record of every review action.

Responsibilities
----------------
* Create and persist :class:`AuditEvent` records for every review action.
* Provide query methods for audit trail retrieval.
* **Never** allow modification or deletion of recorded events.

The audit service is the system of record for *what happened*.
It is separate from :class:`HistoryService` because history (undo/redo)
is temporary and session-scoped, while audit is permanent and
document-scoped.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.exceptions import AuditException
from app.domain.models.review import (
    AuditEvent,
    ReviewAction,
    ReviewActionType,
    ReviewState,
)
from app.store.review_store import audit_store

logger = logging.getLogger(settings.APP_NAME)


class AuditService:
    """
    Records and retrieves immutable audit events for human review actions.

    Usage::

        audit = AuditService()
        event = audit.record_action(
            action=review_action,
            document_id="doc-123",
            detection_id="det-456",
            previous_state=None,
            new_state=ReviewState.APPROVED,
        )
        history = audit.get_document_events("doc-123")
    """

    # ── Public API ──────────────────────────────────────────────────

    def record_action(
        self,
        action: ReviewAction,
        document_id: str,
        detection_id: str,
        previous_state: Optional[ReviewState],
        new_state: ReviewState,
    ) -> AuditEvent:
        """
        Create and persist an audit event for a review action.

        Parameters
        ----------
        action : ReviewAction
            The review action that was performed.
        document_id : str
            The document the action applies to.
        detection_id : str
            The detection the action applies to.
        previous_state : Optional[ReviewState]
            The review state before the action (``None`` for new detections).
        new_state : ReviewState
            The review state after the action.

        Returns
        -------
        AuditEvent
            The persisted audit event.

        Raises
        ------
        AuditException
            If the event could not be recorded.
        """
        event = AuditEvent(
            action=action,
            document_id=document_id,
            detection_id=detection_id,
            previous_review_state=previous_state.value if previous_state else None,
            new_review_state=new_state.value,
        )

        try:
            audit_store.append(event)
        except Exception as exc:
            raise AuditException(
                message=f"Failed to record audit event: {exc}",
            ) from exc

        logger.info(
            "Audit event recorded",
            extra={
                "event_id": event.event_id,
                "document_id": document_id,
                "detection_id": detection_id,
                "action": action.action_type.value,
                "new_state": new_state.value,
            },
        )

        return event

    # ── Query Methods ───────────────────────────────────────────────

    def get_document_events(
        self, document_id: str, *, limit: Optional[int] = None,
    ) -> List[AuditEvent]:
        """
        Return all audit events for a document, oldest first.

        Parameters
        ----------
        document_id : str
            The document to retrieve events for.
        limit : int, optional
            Maximum number of events to return (most recent if limited).
        """
        return audit_store.get_by_document(document_id, limit=limit)

    def get_detection_events(
        self, document_id: str, detection_id: str,
    ) -> List[AuditEvent]:
        """
        Return all audit events for a specific detection.
        """
        return audit_store.get_by_detection(document_id, detection_id)

    def get_event_by_id(self, event_id: str) -> Optional[AuditEvent]:
        """
        Retrieve a single audit event by its ID.
        """
        return audit_store.get_by_event_id(event_id)

    def get_detection_review_history(
        self, document_id: str, detection_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Return a human-readable history of review state changes for a
        specific detection.

        Each entry contains: action type, actor, timestamp, reason,
        previous state, new state.

        This is useful for the UI to display a timeline for a single item.
        """
        events = self.get_detection_events(document_id, detection_id)
        return [
            {
                "action": e.action.action_type.value,
                "actor": e.action.actor,
                "timestamp": e.event_timestamp.isoformat(),
                "reason": e.action.reason,
                "previous_state": e.previous_review_state,
                "new_state": e.new_review_state,
            }
            for e in events
        ]

    @property
    def total_events(self) -> int:
        """Total number of audit events across all documents."""
        return audit_store.count()
