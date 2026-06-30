"""
Detection routes — trigger PII detection on uploaded documents.

POST /api/v1/detection/run  →  run the full detection pipeline on a document
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from app.api.schemas.responses import ApiResponse, MetaResponse
from app.core.config import settings
from app.services.detection_service import DetectionService

logger = logging.getLogger(settings.APP_NAME)

router = APIRouter(prefix="/detection", tags=["Detection"])

_detection_service = DetectionService()


# ── Request schema ────────────────────────────────────────────────

class RunDetectionRequest(BaseModel):
    """Request body for POST /api/v1/detection/run."""
    document_id: str = Field(..., description="ID of the uploaded document to scan")


# ── Routes ────────────────────────────────────────────────────────

@router.post(
    "/run",
    summary="Run PII detection on a document",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def run_detection(
    request: Request,
    body: RunDetectionRequest,
) -> ApiResponse[Dict[str, Any]]:
    """
    Execute the full PII detection pipeline on a previously uploaded
    document.

    The document must first be uploaded via ``POST /api/v1/documents/upload``.
    """
    # ── Run detection ──
    result = _detection_service.run_detection(document_id=body.document_id)

    # ── Build response ──
    response_data = {
        "document_id": result.document_id,
        "processing_time_ms": result.processing_time_ms,
        "summary": result.summary.model_dump(),
        "detections": [
            {
                "id": d.id,
                "entity": d.entity,
                "entity_type": d.entity_type,
                "confidence": d.confidence,
                "reason": d.reason,
                "sources": d.sources,
                "start_offset": d.start_offset,
                "end_offset": d.end_offset,
                "page": d.page,
                "line": d.line,
                "status": d.status,
                "review_state": "system_generated",
            }
            for d in result.detections
        ],
    }

    return ApiResponse(
        message="Detection completed successfully",
        data=response_data,
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp="",
        ),
    )
