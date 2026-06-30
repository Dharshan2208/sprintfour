"""
Risk Intelligence routes — Phase 5.

Endpoints
---------
POST /api/v1/risk/assess  —  Run a full risk assessment on a document
POST /api/v1/risk/summary  —  Get a lightweight risk summary (no full report)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from app.api.schemas.responses import ApiResponse, MetaResponse
from app.core.config import settings
from app.services.risk_service import RiskService

logger = logging.getLogger(settings.APP_NAME)

router = APIRouter(prefix="/risk", tags=["Risk"])

_risk_service = RiskService()


# ── Request Schemas ────────────────────────────────────────────────

class RiskAssessRequest(BaseModel):
    """Request body for POST /api/v1/risk/assess."""
    document_id: str = Field(..., description="ID of the document to assess")
    detections: List[Dict[str, Any]] = Field(
        ...,
        description="All detections for the document. "
        "Each must have: id, entity_type, entity, confidence.",
    )
    review_states: Optional[Dict[str, str]] = Field(
        default=None,
        description="Override review states. "
        "Map of detection_id -> review_state. If omitted, states are "
        "read from the internal review store.",
    )


class RiskSummaryRequest(BaseModel):
    """Request body for POST /api/v1/risk/summary."""
    document_id: str = Field(..., description="ID of the document")
    detections: List[Dict[str, Any]] = Field(
        ...,
        description="Same structure as assess request.",
    )


# ── Routes ─────────────────────────────────────────────────────────

@router.post(
    "/assess",
    summary="Run a full risk assessment on a document",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def assess_risk(
    request: Request,
    body: RiskAssessRequest,
) -> ApiResponse[Dict[str, Any]]:
    """
    Perform a comprehensive risk assessment for a document.

    Returns a :class:`RiskReport` with overall score, review progress,
    priority-ranked items, warnings, and recommendations.
    """
    report = _risk_service.assess_document(
        document_id=body.document_id,
        detections=body.detections,
        review_states=body.review_states,
    )

    return ApiResponse(
        message="Risk assessment completed",
        data={
            "document_id": report.document_id,
            "overall_score": report.overall_score,
            "export_ready": report.export_ready,
            "export_ready_threshold": report.export_ready_threshold,
            "review_progress": {
                "total_items": report.review_progress.total_items,
                "reviewed_count": report.review_progress.reviewed_count,
                "pending_count": report.review_progress.pending_count,
                "approval_rate": report.review_progress.approval_rate,
                "review_percentage": report.review_progress.review_percentage,
            },
            "priority_items": [
                {
                    "detection_id": item.detection_id,
                    "entity_type": item.entity_type,
                    "entity": item.entity,
                    "confidence": item.confidence,
                    "review_state": item.review_state,
                    "priority": item.priority.value,
                    "reason": item.reason,
                }
                for item in report.priority_items
            ],
            "critical_items": [
                {
                    "detection_id": item.detection_id,
                    "entity_type": item.entity_type,
                    "entity": item.entity,
                    "priority": item.priority.value,
                    "reason": item.reason,
                }
                for item in report.critical_items
            ],
            "warnings": report.warnings,
            "recommendations": report.recommendations,
            "analyzed_at": report.analyzed_at.isoformat(),
        },
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp="",
        ),
    )


@router.post(
    "/summary",
    summary="Get a lightweight risk summary for a document",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def risk_summary(
    request: Request,
    body: RiskSummaryRequest,
) -> ApiResponse[Dict[str, Any]]:
    """
    Get a lightweight risk summary without the full report.

    This is faster than a full assessment and is suitable for dashboard
    views or periodic polling.
    """
    report = _risk_service.assess_document(
        document_id=body.document_id,
        detections=body.detections,
    )

    return ApiResponse(
        message="Risk summary retrieved",
        data={
            "document_id": report.document_id,
            "overall_score": report.overall_score,
            "export_ready": report.export_ready,
            "review_progress": {
                "total_items": report.review_progress.total_items,
                "reviewed_count": report.review_progress.reviewed_count,
                "pending_count": report.review_progress.pending_count,
                "review_percentage": report.review_progress.review_percentage,
            },
            "critical_count": len(report.critical_items),
            "warnings": report.warnings,
        },
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp="",
        ),
    )
