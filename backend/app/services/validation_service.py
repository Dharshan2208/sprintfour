"""
Validation Service — determines whether a document is safe to export.

Validation checks
-----------------
1. **Critical unreviewed items** — any detection with review state
   ``pending`` or ``system_generated`` and a sensitivity >= 0.85
   blocks export.
2. **Pending items** — if ``require_full_review`` is True, any pending
   item blocks export.
3. **Invalid offsets** — detections with start_offset >= end_offset
   or out-of-range offsets block export.
4. **Empty required fields** — detections missing entity or entity_type
   block export.
5. **Deleted with no review** — detections review state ``rejected``
   with no audit history are flagged as warnings.

Usage::

    service = ValidationService()
    result = service.validate(
        document_id="doc-123",
        detections=[...],
        review_states={"det-1": "approved"},
        require_full_review=False,
    )
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.domain.models.export import ValidationIssue, ValidationResult
from app.domain.models.risk import ENTITY_SENSITIVITY
from app.store.review_store import audit_store, review_store

logger = logging.getLogger(settings.APP_NAME)


class ValidationService:
    """
    Validates whether a document is safe to export based on review
    state and data integrity.
    """

    # ── Configuration ───────────────────────────────────────────────
    # Entity types with sensitivity >= this threshold are "critical"
    CRITICAL_SENSITIVITY_THRESHOLD: float = 0.85

    # ── Public API ──────────────────────────────────────────────────

    def validate(
        self,
        document_id: str,
        detections: List[Dict[str, Any]],
        review_states: Optional[Dict[str, str]] = None,
        require_full_review: bool = False,
    ) -> ValidationResult:
        """
        Run all validation checks against a document.

        Parameters
        ----------
        document_id : str
            The document to validate.
        detections : list of dict
            All detections for the document.  Each must have ``id``,
            ``entity``, ``entity_type``, ``start_offset``, ``end_offset``.
        review_states : dict, optional
            Override review states.  If omitted, read from review store.
        require_full_review : bool
            If ``True``, any unreviewed detection blocks export.
            Default ``False`` (only critical unreviewed items block).

        Returns
        -------
        ValidationResult
            The validation result with all issues found.
        """
        issues: List[ValidationIssue] = []

        # 1. Resolve review states
        if review_states is None:
            raw_states = review_store.get_all_states(document_id)
            review_states = {
                k: v.value if hasattr(v, "value") else str(v)
                for k, v in raw_states.items()
            }

        # 2. Run checks
        self._check_critical_unreviewed(detections, review_states, issues)
        self._check_pending(detections, review_states, issues, require_full_review)
        self._check_invalid_offsets(detections, issues)
        self._check_empty_fields(detections, issues)
        self._check_deleted_no_review(detections, review_states, issues)

        # 3. Build result
        result = ValidationResult(
            is_valid=len([i for i in issues if i.severity == "error"]) == 0,
            issues=issues,
            document_id=document_id,
        )

        logger.info(
            "Export validation completed",
            extra={
                "document_id": document_id,
                "is_valid": result.is_valid,
                "total_issues": len(issues),
                "require_full_review": require_full_review,
            },
        )

        return result

    # ── Internal Checks ─────────────────────────────────────────────

    @staticmethod
    def _check_critical_unreviewed(
        detections: List[Dict[str, Any]],
        review_states: Dict[str, str],
        issues: List[ValidationIssue],
    ) -> None:
        """
        Check for unreviewed detections with high-sensitivity entity types.

        These are the most dangerous items to export — they represent
        high-value PII that hasn't been verified.
        """
        unreviewed_states = {"pending", "system_generated"}

        for det in detections:
            det_id = det.get("id", "")
            state = review_states.get(det_id, "pending")

            if state not in unreviewed_states:
                continue

            entity_type = det.get("entity_type", "CUSTOM").upper()
            sensitivity = ENTITY_SENSITIVITY.get(entity_type, 0.5)

            if sensitivity >= 0.85:
                issues.append(ValidationIssue(
                    severity="error",
                    code="CRITICAL_UNREVIEWED",
                    message=(
                        f"Critical {entity_type} detection is unreviewed: "
                        f"'{det.get('entity', '')}'"
                    ),
                    detection_id=det_id,
                ))

    @staticmethod
    def _check_pending(
        detections: List[Dict[str, Any]],
        review_states: Dict[str, str],
        issues: List[ValidationIssue],
        require_full_review: bool,
    ) -> None:
        """
        Check for pending detections when full review is required.
        """
        if not require_full_review:
            return

        pending_states = {"pending", "system_generated"}

        for det in detections:
            det_id = det.get("id", "")
            state = review_states.get(det_id, "pending")

            if state in pending_states:
                issues.append(ValidationIssue(
                    severity="error",
                    code="PENDING_REVIEW",
                    message=(
                        f"Detection '{det.get('entity_type', '')}' has not "
                        "been reviewed"
                    ),
                    detection_id=det_id,
                ))

    @staticmethod
    def _check_invalid_offsets(
        detections: List[Dict[str, Any]],
        issues: List[ValidationIssue],
    ) -> None:
        """
        Check for detections with invalid character offsets.
        """
        for det in detections:
            det_id = det.get("id", "")
            start = det.get("start_offset", 0)
            end = det.get("end_offset", 0)

            if start < 0 or end < 0:
                issues.append(ValidationIssue(
                    severity="error",
                    code="NEGATIVE_OFFSET",
                    message=f"Detection has negative offset (start={start}, end={end})",
                    detection_id=det_id,
                ))
            elif start >= end:
                issues.append(ValidationIssue(
                    severity="error",
                    code="INVALID_OFFSET_RANGE",
                    message=f"Detection has start_offset >= end_offset ({start} >= {end})",
                    detection_id=det_id,
                ))

    @staticmethod
    def _check_empty_fields(
        detections: List[Dict[str, Any]],
        issues: List[ValidationIssue],
    ) -> None:
        """
        Check for detections missing required fields.
        """
        for det in detections:
            det_id = det.get("id", "")
            entity = det.get("entity", "")
            entity_type = det.get("entity_type", "")

            if not entity or not entity.strip():
                issues.append(ValidationIssue(
                    severity="error",
                    code="EMPTY_ENTITY",
                    message="Detection has empty entity text",
                    detection_id=det_id,
                ))

            if not entity_type or not entity_type.strip():
                issues.append(ValidationIssue(
                    severity="error",
                    code="EMPTY_ENTITY_TYPE",
                    message="Detection has empty entity type",
                    detection_id=det_id,
                ))

    @staticmethod
    def _check_deleted_no_review(
        detections: List[Dict[str, Any]],
        review_states: Dict[str, str],
        issues: List[ValidationIssue],
    ) -> None:
        """
        Flag detections that were rejected/deleted without any review history.

        These may indicate accidental deletion.
        """
        deleted_states = {"rejected"}

        for det in detections:
            det_id = det.get("id", "")
            state = review_states.get(det_id, "")

            if state in deleted_states:
                # Check if there's any audit history for this detection
                detection_events = audit_store.get_by_detection(
                    det.get("document_id", ""), det_id,
                )
                if not detection_events:
                    issues.append(ValidationIssue(
                        severity="warning",
                        code="DELETED_WITHOUT_REVIEW",
                        message=(
                            f"Detection '{det.get('entity_type', '')}' was "
                            "rejected/deleted without any review history"
                        ),
                        detection_id=det_id,
                    ))
