"""
History Service — manages undo/redo for human review actions.

Architecture
------------
Each document has two stacks:
* **undo_stack** — actions that can be undone (most recent on top).
* **redo_stack** — actions that were undone and can be re-applied.

When a new review action is performed, it is pushed onto the undo_stack
and the redo_stack is cleared (standard undo/redo behavior — any new
action after an undo invalidates the redo history).

Each stack entry is a :class:`ReviewAction` that includes the
``previous_state`` and ``new_state`` so the system can reverse the
action without re-executing the business logic.

Limitations
-----------
* History is stored **in-memory** and is lost on server restart.
* For production, history should be stored in Redis (or a database)
  with a TTL for session-based expiry.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.exceptions import HistoryException
from app.domain.models.review import ReviewAction, ReviewActionType, ReviewState

logger = logging.getLogger(settings.APP_NAME)


class HistoryService:
    """
    Tracks undo/redo state for review actions per document.

    Usage::

        history = HistoryService()
        history.push_action(action)
        undone_action = history.undo("doc-123")  # returns action or None
        redone_action = history.redo("doc-123")   # returns action or None
    """

    def __init__(self) -> None:
        # Stack entries: (document_id) -> [ReviewAction, ...]
        self._undo_stacks: Dict[str, List[ReviewAction]] = {}
        self._redo_stacks: Dict[str, List[ReviewAction]] = {}

    # ── Public API ──────────────────────────────────────────────────

    def push_action(self, action: ReviewAction) -> None:
        """
        Record a completed action in the undo history.

        Calling this clears the redo stack for the document because the
        new action invalidates any previously undone state.

        Parameters
        ----------
        action : ReviewAction
            The action that was performed.  Must have ``previous_state``
            and ``new_state`` populated.
        """
        doc_id = action.document_id
        self._undo_stacks.setdefault(doc_id, []).append(action)
        # Clear redo on new action (standard undo/redo behavior)
        self._redo_stacks.pop(doc_id, None)

        logger.debug(
            "Action pushed to history",
            extra={
                "document_id": doc_id,
                "detection_id": action.detection_id,
                "action": action.action_type.value,
            },
        )

    def undo(self, document_id: str) -> Optional[ReviewAction]:
        """
        Undo the most recent action for a document.

        Returns the action that was undone, or ``None`` if there is
        nothing to undo.  The action is moved from the undo stack to
        the redo stack.

        The caller (typically :class:`ReviewService`) is responsible
        for applying the reverse state change using the action's
        ``previous_state``.
        """
        stack = self._undo_stacks.get(document_id)
        if not stack:
            logger.info("Nothing to undo", extra={"document_id": document_id})
            return None

        action = stack.pop()
        # Push onto redo stack
        self._redo_stacks.setdefault(document_id, []).append(action)

        logger.info(
            "Undo performed",
            extra={
                "document_id": document_id,
                "detection_id": action.detection_id,
                "action": action.action_type.value,
            },
        )

        return action

    def redo(self, document_id: str) -> Optional[ReviewAction]:
        """
        Redo the most recently undone action for a document.

        Returns the action that was redone, or ``None`` if there is
        nothing to redo.  The action is moved from the redo stack back
        to the undo stack.
        """
        stack = self._redo_stacks.get(document_id)
        if not stack:
            logger.info("Nothing to redo", extra={"document_id": document_id})
            return None

        action = stack.pop()
        # Push back onto undo stack
        self._undo_stacks.setdefault(document_id, []).append(action)

        logger.info(
            "Redo performed",
            extra={
                "document_id": document_id,
                "detection_id": action.detection_id,
                "action": action.action_type.value,
            },
        )

        return action

    def can_undo(self, document_id: str) -> bool:
        """Return ``True`` if there is an action to undo for this document."""
        return bool(self._undo_stacks.get(document_id))

    def can_redo(self, document_id: str) -> bool:
        """Return ``True`` if there is an action to redo for this document."""
        return bool(self._redo_stacks.get(document_id))

    def get_undo_count(self, document_id: str) -> int:
        """Number of undoable actions for this document."""
        return len(self._undo_stacks.get(document_id, []))

    def get_redo_count(self, document_id: str) -> int:
        """Number of redoable actions for this document."""
        return len(self._redo_stacks.get(document_id, []))

    def clear_document(self, document_id: str) -> None:
        """Clear all history for a document (e.g. when review is reset)."""
        self._undo_stacks.pop(document_id, None)
        self._redo_stacks.pop(document_id, None)

    def peek_undo(self, document_id: str) -> Optional[ReviewAction]:
        """
        Return the most recent undoable action without removing it.
        Useful for the UI to show "Undo: {action description}".
        """
        stack = self._undo_stacks.get(document_id)
        if not stack:
            return None
        return stack[-1]

    def peek_redo(self, document_id: str) -> Optional[ReviewAction]:
        """
        Return the most recent redoable action without removing it.
        """
        stack = self._redo_stacks.get(document_id)
        if not stack:
            return None
        return stack[-1]

    def clear_all(self) -> None:
        """Clear all history (useful for testing)."""
        self._undo_stacks.clear()
        self._redo_stacks.clear()
