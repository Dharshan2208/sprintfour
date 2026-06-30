"""
Secure Export routes — Phase 6.

Every export goes through validation first.  If validation fails, the
response includes a detailed list of issues that must be resolved before
export.

Endpoints
---------
POST /api/v1/export/validate  —  Validate a document for export (without exporting)
POST /api/v1/export/run       —  Validate and export a document
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from app.api.schemas.responses import ApiResponse, MetaResponse
from app.core.config import settings
from app.core.exceptions import ExportValidationException
from app.domain.models.export import (
    ExportFormat,
    RedactionConfig,
    RedactionStrategy,
)
from app.services.export_service import ExportService
from app.services.validation_service import ValidationService

logger = logging.getLogger(settings.APP_NAME)

router = APIRouter(prefix="/export", tags=["Export"])

_validation_service = ValidationService()
_export_service = ExportService()


# ── Request Schemas ────────────────────────────────────────────────

class ValidateRequest(BaseModel):
    """Request body for POST /api/v1/export/validate."""
    document_id: str = Field(..., description="ID of the document to validate")
    detections: List[Dict[str, Any]] = Field(
        ...,
        description="All detections for the document. "
        "Each must have: id, entity, entity_type, start_offset, end_offset.",
    )
    review_states: Optional[Dict[str, str]] = Field(
        default=None,
        description="Override review states. If omitted, read from store.",
    )
    require_full_review: bool = Field(
        default=False,
        description="If True, any pending item blocks export.",
    )


class ExportRequest(BaseModel):
    """Request body for POST /api/v1/export/run."""
    document_id: str = Field(..., description="ID of the document to export")
    text: str = Field(..., description="The original (normalised) document text")
    detections: List[Dict[str, Any]] = Field(
        ...,
        description="All detections. Each must have: id, entity, entity_type, "
        "confidence, reason, sources, start_offset, end_offset, page, line.",
    )
    review_states: Optional[Dict[str, str]] = Field(
        default=None,
        description="Override review states. If omitted, read from store.",
    )
    format: ExportFormat = Field(
        default=ExportFormat.TXT,
        description="Output format: txt, pdf, or json",
    )
    redaction_strategy: RedactionStrategy = Field(
        default=RedactionStrategy.REPLACE,
        description="Default redaction strategy",
    )
    per_type_strategies: Optional[Dict[str, RedactionStrategy]] = Field(
        default=None,
        description="Per-entity-type strategy overrides",
    )
    review_history: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Review audit history to include in JSON report",
    )
    risk_report: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Risk assessment to include in JSON report",
    )
    exported_by: str = Field(default="unknown", description="Who requested the export")


# ── Routes ─────────────────────────────────────────────────────────

@router.post(
    "/validate",
    summary="Validate a document for export readiness",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def validate_export(
    request: Request,
    body: ValidateRequest,
) -> ApiResponse[Dict[str, Any]]:
    """
    Check whether a document is safe to export.

    This runs all validation checks without actually performing the
    export.  Use this to give users feedback on what needs to be
    resolved before export.
    """
    result = _validation_service.validate(
        document_id=body.document_id,
        detections=body.detections,
        review_states=body.review_states,
        require_full_review=body.require_full_review,
    )

    return ApiResponse(
        message="Document is safe for export" if result.is_valid
        else f"Document has {len(result.issues)} issue(s) to resolve",
        data={
            "document_id": body.document_id,
            "is_valid": result.is_valid,
            "issues": [
                {
                    "severity": issue.severity,
                    "code": issue.code,
                    "message": issue.message,
                    "detection_id": issue.detection_id,
                }
                for issue in result.issues
            ],
        },
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp="",
        ),
    )


@router.post(
    "/run",
    summary="Validate and export a document with PII redacted",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def run_export(
    request: Request,
    body: ExportRequest,
) -> ApiResponse[Dict[str, Any]]:
    """
    Validate and export a document.

    If validation fails, the response includes all issues and no export
    is performed (HTTP 200 with success=False data, not a 400 error,
    because the request itself is valid — the *document* is not ready).

    If validation passes, the export is performed and the result includes
    the redacted text, operations, and report.
    """
    # Build redaction config
    config = RedactionConfig(
        default_strategy=body.redaction_strategy,
        per_type=body.per_type_strategies or {},
    )

    try:
        result = _export_service.export(
            document_id=body.document_id,
            text=body.text,
            detections=body.detections,
            review_states=body.review_states,
            format=body.format,
            config=config,
            review_history=body.review_history,
            risk_report=body.risk_report,
            metadata={"exported_by": body.exported_by},
        )
    except ExportValidationException as exc:
        # Validation failed — return the issues
        validation_data = exc.data or {}
        return ApiResponse(
            message=str(exc.message),
            data={
                "document_id": body.document_id,
                "exported": False,
                "validation_result": validation_data.get("validation_result", {}),
            },
            meta=MetaResponse(
                request_id=getattr(request.state, "request_id", "N/A"),
                timestamp="",
            ),
        )

    # Build the response
    response_data: Dict[str, Any] = {
        "document_id": result.document_id,
        "export_format": result.export_format.value,
        "redaction_count": result.redaction_count,
        "export_duration_ms": result.export_duration_ms,
        "exported_at": result.exported_at.isoformat(),
    }

    # Include redacted text for TXT/PDF exports
    if body.format in (ExportFormat.TXT, ExportFormat.PDF):
        response_data["redacted_text"] = result.redacted_text

    # Always include the JSON report
    response_data["json_report"] = result.json_report

    # Include redaction operations summary
    response_data["redaction_operations"] = [
        {
            "detection_id": op.detection_id,
            "entity_type": op.entity_type,
            "strategy": op.strategy.value,
        }
        for op in result.redaction_operations
    ]

    return ApiResponse(
        message="Document exported successfully",
        data=response_data,
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp="",
        ),
    )
