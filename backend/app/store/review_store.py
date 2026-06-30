"""
In-memory stores for the Human Review Engine (Phase 4).

Two stores live here:

1. :class:`InMemoryReviewStore` — holds the current review state for
   each detection per document.  This is the *projected* state computed
   from the sequence of actions.

2. :class:`InMemoryAuditStore` — an append-only log of every
   :class:`AuditEvent`.  Events are never modified or deleted.

**These are development-only implementations.**  In production the
review state and audit log would live in PostgreSQL (with transactional
guarantees) and the audit log would additionally be written to an
append-only medium (e.g. AWS CloudWatch Logs, a Kafka topic, or a
dedicated audit database).

The interface is kept simple so migration is straightforward — replace
the internal dict with a database session.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.core.config import settings
from app.domain.models.review import AuditEvent, ReviewState

logger = logging.getLogger(settings.APP_NAME)


class InMemoryReviewStore:
    """
    Tracks the current review state of every detection, keyed by
    ``(document_id, detection_id)``.

    This store only keeps the **current** projected state.  For history
    (undo/redo) the :class:`InMemoryAuditStore` is used together with
    the :class:`~app.services.history_service.HistoryService`.
    """

    def __init__(self) -> None:
        # Nested dict: _state[document_id][detection_id] = ReviewState
        self._state: Dict[str, Dict[str, ReviewState]] = {}

    # ── Public API ──────────────────────────────────────────────────

    def get_state(self, document_id: str, detection_id: str) -> Optional[ReviewState]:
        """
        Return the current review state for a detection, or ``None``
        if the detection is not tracked.
        """
        doc_states = self._state.get(document_id)
        if doc_states is None:
            return None
        return doc_states.get(detection_id)

    def set_state(
        self, document_id: str, detection_id: str, state: ReviewState,
    ) -> None:
        """Set (or update) the review state for a detection."""
        self._state.setdefault(document_id, {})[detection_id] = state
        logger.debug(
            "Review state updated",
            extra={
                "document_id": document_id,
                "detection_id": detection_id,
                "state": state.value,
            },
        )

    def get_all_states(self, document_id: str) -> Dict[str, ReviewState]:
        """
        Return all detection states for a given document.

        Returns an empty dict if the document has no tracked detections.
        """
        return self._state.get(document_id, {}).copy()

    def remove_state(self, document_id: str, detection_id: str) -> None:
        """
        Remove the state tracking for a detection (e.g. when a
        detection is deleted by the reviewer).
        """
        doc_states = self._state.get(document_id)
        if doc_states is not None:
            doc_states.pop(detection_id, None)

    def clear_document(self, document_id: str) -> None:
        """Remove all state tracking for a document."""
        self._state.pop(document_id, None)

    def clear_all(self) -> None:
        """Remove all review state (useful for testing)."""
        self._state.clear()

    @property
    def document_count(self) -> int:
        return len(self._state)


class InMemoryAuditStore:
    """
    Append-only log of :class:`AuditEvent` instances.

    Events are stored in insertion order and indexed by
    ``(document_id, detection_id)`` for efficient lookups.

    Rules
    -----
    * ``append()`` MUST be the only mutation method.
    * ``clear_all()`` exists ONLY for testing.
    * No update or delete methods are provided.
    """

    def __init__(self) -> None:
        self._events: List[AuditEvent] = []
        # Index: _by_document[document_id] = list of event_ids
        self._by_document: Dict[str, List[str]] = {}

    # ── Public API ──────────────────────────────────────────────────

    def append(self, event: AuditEvent) -> None:
        """
        Record an audit event.

        This is the **only** write method.  Once appended, an event
        cannot be modified or removed.
        """
        self._events.append(event)
        self._by_document.setdefault(event.document_id, []).append(event.event_id)
        logger.debug(
            "Audit event recorded",
            extra={
                "event_id": event.event_id,
                "document_id": event.document_id,
                "detection_id": event.detection_id,
                "action": event.action.action_type.value,
            },
        )

    def get_by_event_id(self, event_id: str) -> Optional[AuditEvent]:
        """Retrieve a single audit event by its ID."""
        for event in self._events:
            if event.event_id == event_id:
                return event
        return None

    def get_by_document(
        self, document_id: str, *, limit: Optional[int] = None,
    ) -> List[AuditEvent]:
        """
        Return all audit events for a document, in chronological order
        (oldest first).

        Parameters
        ----------
        document_id : str
            The document to retrieve events for.
        limit : int, optional
            Maximum number of events to return (newest-first if limited).
        """
        event_ids = self._by_document.get(document_id, [])
        # Walk the full list in reverse to collect the limit
        events: List[AuditEvent] = []
        for event in reversed(self._events):
            if event.event_id in event_ids:
                events.append(event)
                if limit is not None and len(events) >= limit:
                    break
        # Return in chronological order
        events.reverse()
        return events

    def get_by_detection(
        self, document_id: str, detection_id: str,
    ) -> List[AuditEvent]:
        """Return all audit events for a specific detection in a document."""
        result: List[AuditEvent] = []
        for event in self._events:
            if event.document_id == document_id and event.detection_id == detection_id:
                result.append(event)
        return result

    def count(self) -> int:
        """Total number of audit events recorded."""
        return len(self._events)

    def clear_all(self) -> None:
        """
        Remove all events.

        **For testing only.**  Never call this in production.
        """
        self._events.clear()
        self._by_document.clear()


# ── Singleton instances ─────────────────────────────────────────────

review_store = InMemoryReviewStore()
audit_store = InMemoryAuditStore()
