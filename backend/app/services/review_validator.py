"""
Review Validator — validates review actions before execution.

Every review action (approve, reject, edit, add, delete) must pass
validation before being applied.  This service encapsulates all
validation rules in one place so that:

1. The :class:`ReviewService` stays thin.
2. Rules can be unit-tested independently.
3. New rules can be added without touching the service.

Validation Rules
----------------
* Cannot approve an already-approved detection.
* Cannot reject an already-rejected detection.
* Cannot modify (edit/reject/approve) a deleted detection.
* Cannot edit a detection that does not exist.
* Manual additions must have non-empty entity text.
* Manual additions must have valid offsets (start < end).
* Cannot act on a detection from a different document.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.core.config import settings
from app.core.exceptions import InvalidReviewTransitionException
from app.domain.models.review import ReviewAction, ReviewActionType, ReviewState
from app.store.review_store import review_store

logger = logging.getLogger(settings.APP_NAME)


class ReviewValidator:
    """
    Validates review actions before they are executed.

    Usage::

        validator = ReviewValidator()
        validator.validate_action(
            action=review_action,
            document_id="doc-123",
            all_detection_ids=["det-1", "det-2"],
        )
    """

    # ── Public API ──────────────────────────────────────────────────

    def validate_action(
        self,
        action: ReviewAction,
        document_id: str,
        all_detection_ids: Optional[List[str]] = None,
    ) -> None:
        """
        Validate a review action.

        Parameters
        ----------
        action : ReviewAction
            The action to validate.
        document_id : str
            The document the action applies to.
        all_detection_ids : list of str, optional
            All known detection IDs for the document.  Used to check
            existence for edit/delete/approve/reject.

        Raises
        ------
        InvalidReviewTransitionException
            If the action is not valid.
        """
        # ── Document match ──
        if action.document_id != document_id:
            raise InvalidReviewTransitionException(
                message=(
                    f"Detection '{action.detection_id}' does not belong to "
                    f"document '{document_id}'."
                ),
            )

        # ── Route to type-specific validator ──
        if action.action_type == ReviewActionType.ADD:
            self._validate_add(action)
        else:
            self._validate_existing(action, all_detection_ids)

    # ── Internal Validators ─────────────────────────────────────────

    def _validate_existing(
        self,
        action: ReviewAction,
        all_detection_ids: Optional[List[str]],
    ) -> None:
        """
        Validate actions that target an existing detection
        (approve, reject, edit, delete).
        """
        # 1. Does the detection exist?
        if all_detection_ids and action.detection_id not in all_detection_ids:
            raise InvalidReviewTransitionException(
                message=(
                    f"Detection '{action.detection_id}' does not exist "
                    f"in document '{action.document_id}'."
                ),
            )

        # 2. Get the current state
        current_state = review_store.get_state(
            action.document_id, action.detection_id,
        )

        # 3. If not tracked yet, treat as PENDING
        if current_state is None:
            current_state = ReviewState.PENDING

        # 4. Check transition validity
        self._check_transition(action.action_type, current_state, action.detection_id)

        # 5. For edit actions, validate that values are provided
        if action.action_type == ReviewActionType.EDIT:
            self._validate_edit_values(action)

    def _validate_add(self, action: ReviewAction) -> None:
        """
        Validate a manual addition action.

        Rules
        -----
        * Must provide entity text.
        * Must provide valid offsets (start < end).
        * Must provide an entity type.
        """
        values = action.new_values or {}

        entity = values.get("entity", "")
        entity_type = values.get("entity_type", "")
        start_offset = values.get("start_offset")
        end_offset = values.get("end_offset")

        if not entity or not entity.strip():
            raise InvalidReviewTransitionException(
                message="Manual addition requires non-empty entity text.",
            )

        if not entity_type or not entity_type.strip():
            raise InvalidReviewTransitionException(
                message="Manual addition requires an entity type.",
            )

        if start_offset is not None and end_offset is not None:
            if not isinstance(start_offset, int) or not isinstance(end_offset, int):
                raise InvalidReviewTransitionException(
                    message="Offsets must be integers.",
                )
            if start_offset < 0 or end_offset < 0:
                raise InvalidReviewTransitionException(
                    message="Offsets must be non-negative.",
                )
            if start_offset >= end_offset:
                raise InvalidReviewTransitionException(
                    message="Start offset must be less than end offset.",
                )

    def _validate_edit_values(self, action: ReviewAction) -> None:
        """
        Validate that an edit action provides at least one value to change.
        """
        values = action.new_values or {}
        if not values:
            raise InvalidReviewTransitionException(
                message="Edit action must provide at least one value to change.",
            )

        # If entity is being changed, it must not be empty
        if "entity" in values and not values["entity"].strip():
            raise InvalidReviewTransitionException(
                message="Entity text cannot be empty.",
            )

        # If offsets are being changed, they must be valid
        start = values.get("start_offset")
        end = values.get("end_offset")
        if start is not None and end is not None:
            if start >= end:
                raise InvalidReviewTransitionException(
                    message="Start offset must be less than end offset.",
                )

    @staticmethod
    def _check_transition(
        action_type: ReviewActionType,
        current_state: ReviewState,
        detection_id: str,
    ) -> None:
        """
        Check whether the requested action is valid given the current
        review state.

        Valid transitions::

            PENDING     → approve/reject/edit/delete
            APPROVED    → reject/edit/delete
            REJECTED    → approve/edit/delete
            MODIFIED    → approve/reject/delete
            MANUALLY_ADDED → approve/reject/edit/delete
            SYSTEM_GENERATED → approve/reject/edit/delete
            EXPORTED    → ❌ (no transitions allowed once exported)
        """
        if current_state == ReviewState.EXPORTED:
            raise InvalidReviewTransitionException(
                message=(
                    f"Cannot '{action_type.value}' detection '{detection_id}': "
                    "it has already been exported."
                ),
            )

        if current_state == ReviewState.APPROVED and action_type == ReviewActionType.APPROVE:
            raise InvalidReviewTransitionException(
                message=f"Detection '{detection_id}' is already approved.",
            )

        if current_state == ReviewState.REJECTED and action_type == ReviewActionType.REJECT:
            raise InvalidReviewTransitionException(
                message=f"Detection '{detection_id}' is already rejected.",
            )

        # All other transitions are currently allowed.
        # This is intentionally permissive — the reviewer should be able
        # to correct mistakes (e.g. reject what was previously approved).
        # In a stricter workflow, additional restrictions could be added.
