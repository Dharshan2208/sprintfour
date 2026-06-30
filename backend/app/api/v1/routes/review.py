"""
Human Review routes — Phase 4.

Every review action goes through the :class:`ReviewService` which
handles validation, state transitions, audit logging, and history
management.  Routes remain thin — they parse the request, call the
service, and format the response.

Endpoints
---------
POST /api/v1/review/items          — List all review items for a document
POST /api/v1/review/approve        — Approve a detection
POST /api/v1/review/reject         — Reject a detection
POST /api/v1/review/edit           — Edit a detection
POST /api/v1/review/add            — Manually add a detection
POST /api/v1/review/delete         — Delete a detection
POST /api/v1/review/undo           — Undo the last action
POST /api/v1/review/redo           — Redo the last undone action
GET  /api/v1/review/history/{document_id} — Get audit history
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from app.api.schemas.responses import ApiResponse, MetaResponse
from typing import List
from app.core.config import settings
from app.services.review_service import ReviewService

logger = logging.getLogger(settings.APP_NAME)

router = APIRouter(prefix="/review", tags=["Review"])

_review_service = ReviewService()


# ── Request Schemas ────────────────────────────────────────────────

class ReviewActionRequest(BaseModel):
    """Base fields for actions targeting an existing detection."""
    document_id: str = Field(..., description="ID of the document being reviewed")
    detection_id: str = Field(..., description="ID of the detection to act on")
    actor: str = Field(default="unknown", description="Who is performing the action")
    reason: Optional[str] = Field(default=None, description="Why this action is being taken")


class ApproveRequest(ReviewActionRequest):
    """Request body for POST /api/v1/review/approve."""
    pass


class RejectRequest(ReviewActionRequest):
    """Request body for POST /api/v1/review/reject."""
    pass


class EditRequest(ReviewActionRequest):
    """Request body for POST /api/v1/review/edit."""
    entity: Optional[str] = Field(default=None, description="New entity text")
    entity_type: Optional[str] = Field(default=None, description="New PII type")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="New confidence score")
    reason_text: Optional[str] = Field(default=None, description="New reason text")
    start_offset: Optional[int] = Field(default=None, ge=0, description="New start offset")
    end_offset: Optional[int] = Field(default=None, ge=0, description="New end offset")
    page: Optional[int] = Field(default=None, ge=0, description="New page number")
    line: Optional[int] = Field(default=None, ge=0, description="New line number")


class AddRequest(BaseModel):
    """Request body for POST /api/v1/review/add."""
    document_id: str = Field(..., description="ID of the document")
    entity: str = Field(..., description="The PII entity text that was missed")
    entity_type: str = Field(..., description="PII type (e.g. PERSON, EMAIL)")
    actor: str = Field(default="unknown", description="Who is adding the detection")
    reason: Optional[str] = Field(default=None, description="Why this is being added")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    start_offset: int = Field(default=0, ge=0, description="Start offset in normalised text")
    end_offset: int = Field(default=0, ge=0, description="End offset in normalised text")
    page: int = Field(default=0, ge=0, description="1-based page number")
    line: int = Field(default=0, ge=0, description="1-based line number")


class DeleteRequest(ReviewActionRequest):
    """Request body for POST /api/v1/review/delete."""
    pass


class UndoRedoRequest(BaseModel):
    """Request body for POST /api/v1/review/undo and redo."""
    document_id: str = Field(..., description="ID of the document")
    actor: str = Field(default="unknown", description="Who is performing the action")


class ReviewItemsRequest(BaseModel):
    """Request body for POST /api/v1/review/items."""
    document_id: str = Field(..., description="ID of the document")
    detections: List[Dict[str, Any]] = Field(
        ...,
        description="Original detections from the detection pipeline. "
        "Each item must have: id, entity, entity_type, confidence, reason, "
        "sources, start_offset, end_offset, page, line.",
    )


# ── Routes ─────────────────────────────────────────────────────────

@router.post(
    "/items",
    summary="List all review items for a document with their current review state",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def get_review_items(
    request: Request,
    body: ReviewItemsRequest,
) -> ApiResponse[Dict[str, Any]]:
    """
    Get all review items for a document with the current review state
    overlaid on top of the original detection data.

    The client should send the original detections (from the detection
    pipeline) and this endpoint will return them annotated with the
    current review state.
    """
    items = _review_service.get_review_items(
        document_id=body.document_id,
        detections=body.detections,
    )

    return ApiResponse(
        message="Review items retrieved",
        data={
            "document_id": body.document_id,
            "total_items": len(items),
            "items": [
                {
                    "detection_id": item.detection_id,
                    "entity": item.entity,
                    "entity_type": item.entity_type,
                    "confidence": item.confidence,
                    "reason": item.reason,
                    "sources": item.sources,
                    "start_offset": item.start_offset,
                    "end_offset": item.end_offset,
                    "page": item.page,
                    "line": item.line,
                    "review_state": item.review_state.value,
                }
                for item in items
            ],
        },
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp="",
        ),
    )


@router.post(
    "/approve",
    summary="Approve a detection as correctly identified PII",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def approve_detection(
    request: Request,
    body: ApproveRequest,
) -> ApiResponse[Dict[str, Any]]:
    """Mark a detection as correctly identified PII."""
    item = _review_service.approve_detection(
        document_id=body.document_id,
        detection_id=body.detection_id,
        actor=body.actor,
        reason=body.reason,
    )

    return ApiResponse(
        message="Detection approved",
        data=_item_to_dict(item),
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp="",
        ),
    )


@router.post(
    "/reject",
    summary="Reject a detection as a false positive",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def reject_detection(
    request: Request,
    body: RejectRequest,
) -> ApiResponse[Dict[str, Any]]:
    """Mark a detection as a false positive."""
    item = _review_service.reject_detection(
        document_id=body.document_id,
        detection_id=body.detection_id,
        actor=body.actor,
        reason=body.reason,
    )

    return ApiResponse(
        message="Detection rejected",
        data=_item_to_dict(item),
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp="",
        ),
    )


@router.post(
    "/edit",
    summary="Edit a detection's attributes",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def edit_detection(
    request: Request,
    body: EditRequest,
) -> ApiResponse[Dict[str, Any]]:
    """Edit one or more attributes of a detection."""
    # Collect only the fields that were provided
    updates: Dict[str, Any] = {}
    for field in ("entity", "entity_type", "confidence", "reason_text",
                   "start_offset", "end_offset", "page", "line"):
        value = getattr(body, field, None)
        if value is not None:
            key = "reason" if field == "reason_text" else field
            updates[key] = value

    item = _review_service.edit_detection(
        document_id=body.document_id,
        detection_id=body.detection_id,
        actor=body.actor,
        reason=body.reason,
        **updates,
    )

    return ApiResponse(
        message="Detection edited",
        data=_item_to_dict(item),
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp="",
        ),
    )


@router.post(
    "/add",
    summary="Manually add a missed PII detection",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
)
async def add_detection(
    request: Request,
    body: AddRequest,
) -> ApiResponse[Dict[str, Any]]:
    """Add a PII detection that the AI pipeline missed."""
    item = _review_service.add_detection(
        document_id=body.document_id,
        entity=body.entity,
        entity_type=body.entity_type,
        actor=body.actor,
        reason=body.reason,
        confidence=body.confidence,
        start_offset=body.start_offset,
        end_offset=body.end_offset,
        page=body.page,
        line=body.line,
    )

    return ApiResponse(
        message="Detection added manually",
        data=_item_to_dict(item),
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp="",
        ),
    )


@router.post(
    "/delete",
    summary="Delete a detection from the review set",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def delete_detection(
    request: Request,
    body: DeleteRequest,
) -> ApiResponse[Dict[str, Any]]:
    """Remove a detection from the review set entirely."""
    item = _review_service.delete_detection(
        document_id=body.document_id,
        detection_id=body.detection_id,
        actor=body.actor,
        reason=body.reason,
    )

    return ApiResponse(
        message="Detection deleted",
        data=_item_to_dict(item),
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp="",
        ),
    )


@router.post(
    "/undo",
    summary="Undo the most recent review action",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def undo_action(
    request: Request,
    body: UndoRedoRequest,
) -> ApiResponse[Dict[str, Any]]:
    """Undo the most recent review action for a document."""
    action = _review_service.undo(
        document_id=body.document_id,
        actor=body.actor,
    )

    if action is None:
        return ApiResponse(
            message="Nothing to undo",
            data={"document_id": body.document_id, "undone": False},
            meta=MetaResponse(
                request_id=getattr(request.state, "request_id", "N/A"),
                timestamp="",
            ),
        )

    return ApiResponse(
        message=f"Undid {action.action_type.value} of {action.detection_id}",
        data={
            "document_id": body.document_id,
            "undone_action": action.action_type.value,
            "detection_id": action.detection_id,
        },
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp="",
        ),
    )


@router.post(
    "/redo",
    summary="Redo the most recently undone action",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def redo_action(
    request: Request,
    body: UndoRedoRequest,
) -> ApiResponse[Dict[str, Any]]:
    """Redo the most recently undone review action for a document."""
    action = _review_service.redo(
        document_id=body.document_id,
        actor=body.actor,
    )

    if action is None:
        return ApiResponse(
            message="Nothing to redo",
            data={"document_id": body.document_id, "redone": False},
            meta=MetaResponse(
                request_id=getattr(request.state, "request_id", "N/A"),
                timestamp="",
            ),
        )

    return ApiResponse(
        message=f"Redid {action.action_type.value} of {action.detection_id}",
        data={
            "document_id": body.document_id,
            "redone_action": action.action_type.value,
            "detection_id": action.detection_id,
        },
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp="",
        ),
    )


@router.get(
    "/history/{document_id}",
    summary="Get the full audit history for a document's review",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def get_review_history(
    request: Request,
    document_id: str,
    limit: Optional[int] = None,
) -> ApiResponse[Dict[str, Any]]:
    """Get the complete audit trail of review actions for a document."""
    history = _review_service.get_history(
        document_id=document_id,
        limit=limit,
    )

    return ApiResponse(
        message="Review history retrieved",
        data={
            "document_id": document_id,
            "total_events": len(history),
            "events": history,
        },
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp="",
        ),
    )


# ── Batch endpoints (for quick correction workflow) ────────────────

class BatchActionRequest(BaseModel):
    """Request body for batch approve/reject."""
    document_id: str = Field(..., description="ID of the document")
    detection_ids: List[str] = Field(..., description="List of detection IDs to act on")
    actor: str = Field(default="unknown", description="Who is performing the action")
    reason: Optional[str] = Field(default=None, description="Why this action is being taken")


@router.post(
    "/batch-approve",
    summary="Approve multiple detections at once",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def batch_approve_detections(
    request: Request,
    body: BatchActionRequest,
) -> ApiResponse[Dict[str, Any]]:
    """Approve multiple detections in a single request."""
    items = _review_service.batch_approve(
        document_id=body.document_id,
        detection_ids=body.detection_ids,
        actor=body.actor,
        reason=body.reason,
    )

    return ApiResponse(
        message=f"{len(items)} detections approved",
        data={
            "document_id": body.document_id,
            "processed_count": len(items),
            "items": [_item_to_dict(item) for item in items],
        },
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp="",
        ),
    )


@router.post(
    "/batch-reject",
    summary="Reject multiple detections at once (false positives)",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def batch_reject_detections(
    request: Request,
    body: BatchActionRequest,
) -> ApiResponse[Dict[str, Any]]:
    """Reject multiple detections as false positives in a single request."""
    items = _review_service.batch_reject(
        document_id=body.document_id,
        detection_ids=body.detection_ids,
        actor=body.actor,
        reason=body.reason,
    )

    return ApiResponse(
        message=f"{len(items)} detections rejected",
        data={
            "document_id": body.document_id,
            "processed_count": len(items),
            "items": [_item_to_dict(item) for item in items],
        },
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp="",
        ),
    )


# ── Helpers ─────────────────────────────────────────────────────────

def _item_to_dict(item: Any) -> Dict[str, Any]:
    """Convert a ReviewItem to a serialisable dict."""
    return {
        "detection_id": item.detection_id,
        "entity": item.entity,
        "entity_type": item.entity_type,
        "confidence": item.confidence,
        "reason": item.reason,
        "sources": item.sources,
        "start_offset": item.start_offset,
        "end_offset": item.end_offset,
        "page": item.page,
        "line": item.line,
        "review_state": item.review_state.value if hasattr(item, "review_state") else "pending",
    }
