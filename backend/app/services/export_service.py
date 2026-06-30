"""
Export Service — orchestrates validation, redaction, and formatting for export.

This is the **primary entry point** for all export operations.
It coordinates:

1. :class:`ValidationService` — checks if the document is safe to export.
2. :class:`RedactionEngine` — applies redaction strategies to the text.
3. :class:`DocumentRenderer` — formats the output in the requested format.

The service does NOT contain business logic for validation, redaction,
or formatting — it delegates to the appropriate single-responsibility
service/engine.

Flow
----
1. User requests export (with format, config, etc.)
2. ExportService validates the document
3. If validation fails, return validation errors (no export)
4. If validation passes, run redaction
5. Render the output in the requested format
6. Record export audit events
7. Return the ExportResult

Usage::

    service = ExportService()
    result = service.export(
        document_id="doc-123",
        text="Original document text...",
        detections=[...],
        review_states={"det-1": "approved"},
        format=ExportFormat.TXT,
        config=RedactionConfig(),
        metadata={"exported_by": "user-abc"},
    )
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.exceptions import ExportException, ExportValidationException
from app.domain.models.export import (
    ExportFormat,
    ExportResult,
    RedactionConfig,
)
from app.domain.models.review import (
    ReviewAction,
    ReviewActionType,
    ReviewState,
)
from app.export.document_renderer import DocumentRenderer
from app.export.redaction_engine import RedactionEngine
from app.services.audit_service import AuditService
from app.services.detection_update_service import DetectionUpdateService
from app.services.validation_service import ValidationService
from app.store.review_store import audit_store, review_store

logger = logging.getLogger(settings.APP_NAME)


class ExportService:
    """
    Orchestrates the full export lifecycle.

    Always validates first — export never happens without validation.
    """

    def __init__(
        self,
        validation_service: Optional[ValidationService] = None,
        redaction_engine: Optional[RedactionEngine] = None,
        document_renderer: Optional[DocumentRenderer] = None,
        detection_update_service: Optional[DetectionUpdateService] = None,
        audit_service: Optional[AuditService] = None,
    ):
        self._validation_service = validation_service or ValidationService()
        self._redaction_engine = redaction_engine or RedactionEngine()
        self._document_renderer = document_renderer or DocumentRenderer()
        self._detection_update_service = detection_update_service or DetectionUpdateService()
        self._audit_service = audit_service or AuditService()

    # ── Public API ──────────────────────────────────────────────────

    def export(
        self,
        document_id: str,
        text: str,
        detections: List[Dict[str, Any]],
        review_states: Optional[Dict[str, str]] = None,
        format: ExportFormat = ExportFormat.TXT,
        config: Optional[RedactionConfig] = None,
        review_history: Optional[List[Dict[str, Any]]] = None,
        risk_report: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExportResult:
        """
        Export a document with PII redacted.

        Parameters
        ----------
        document_id : str
            The document to export.
        text : str
            The original (normalised) document text.
        detections : list of dict
            All detections.  Each must have: ``id``, ``entity``,
            ``entity_type``, ``confidence``, ``reason``, ``sources``,
            ``start_offset``, ``end_offset``, ``page``, ``line``.
        review_states : dict, optional
            Map of ``detection_id → review_state``.  If omitted, read
            from review store.
        format : ExportFormat
            The desired output format (default: TXT).
        config : RedactionConfig, optional
            Redaction strategy configuration.
        review_history : list of dict, optional
            Audit history to include in JSON report.
        risk_report : dict, optional
            Risk assessment to include in JSON report.
        metadata : dict, optional
            Additional metadata (e.g. ``exported_by``).

        Returns
        -------
        ExportResult
            The formatted export result.

        Raises
        ------
        ExportValidationException
            If the document fails validation checks.
        ExportException
            If the export process fails unexpectedly.
        """
        start_time = time.time()

        # 1. Resolve review states
        if review_states is None:
            raw_states = review_store.get_all_states(document_id)
            review_states = {
                k: v.value if hasattr(v, "value") else str(v)
                for k, v in raw_states.items()
            }

        # 2. Validate
        validation_result = self._validation_service.validate(
            document_id=document_id,
            detections=detections,
            review_states=review_states,
        )

        if not validation_result.is_valid:
            logger.warning(
                "Export blocked by validation",
                extra={
                    "document_id": document_id,
                    "issue_count": len(validation_result.issues),
                },
            )
            raise ExportValidationException(
                message="Document is not safe for export. "
                f"Found {len(validation_result.issues)} issue(s).",
                data={
                    "validation_result": {
                        "is_valid": validation_result.is_valid,
                        "issues": [
                            {
                                "severity": issue.severity,
                                "code": issue.code,
                                "message": issue.message,
                                "detection_id": issue.detection_id,
                            }
                            for issue in validation_result.issues
                        ],
                    },
                },
            )

        # 3. Redact
        try:
            redacted_text, operations = self._redaction_engine.redact(
                text=text,
                detections=detections,
                review_states=review_states,
                config=config,
            )
        except Exception as exc:
            raise ExportException(
                message=f"Redaction failed: {exc}",
            ) from exc

        # 4. Render
        try:
            export_result = self._document_renderer.render(
                format=format,
                document_id=document_id,
                redacted_text=redacted_text,
                operations=operations,
                detections=detections,
                review_history=review_history,
                risk_report=risk_report,
                metadata={
                    **(metadata or {}),
                    "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
            )
        except Exception as exc:
            raise ExportException(
                message=f"Document rendering failed: {exc}",
            ) from exc

        # 5. Mark all redacted detections as EXPORTED
        self._mark_exported(document_id, operations)

        # 6. Set timing
        elapsed_ms = (time.time() - start_time) * 1000
        export_result.export_duration_ms = round(elapsed_ms, 2)

        logger.info(
            "Export completed",
            extra={
                "document_id": document_id,
                "format": format.value,
                "redaction_count": len(operations),
                "duration_ms": export_result.export_duration_ms,
            },
        )

        return export_result

    # ── Internal ────────────────────────────────────────────────────

    def _mark_exported(
        self,
        document_id: str,
        operations: List[Any],
    ) -> None:
        """
        Mark all redacted detections as EXPORTED.

        This updates the review state and records an audit event for
        each redacted detection.
        """
        from datetime import datetime, timezone

        for op in operations:
            detection_id = op.detection_id

            # Get the current state before export
            current_state = self._detection_update_service.get_state(
                document_id, detection_id,
            ) or ReviewState.APPROVED

            # Update state
            self._detection_update_service.set_state_directly(
                document_id=document_id,
                detection_id=detection_id,
                state=ReviewState.EXPORTED,
            )

            # Create a proper action for audit
            export_action = ReviewAction(
                action_type=ReviewActionType.APPROVE,
                detection_id=detection_id,
                document_id=document_id,
                previous_state=current_state,
                new_state=ReviewState.EXPORTED,
                actor="system",
                reason="Detection included in secure export",
                timestamp=datetime.now(timezone.utc),
            )

            # Record audit event for the export
            self._audit_service.record_action(
                action=export_action,
                document_id=document_id,
                detection_id=detection_id,
                previous_state=current_state,
                new_state=ReviewState.EXPORTED,
            )
