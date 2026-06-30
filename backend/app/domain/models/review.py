"""
Domain models for the Human Review Engine (Phase 4).

These models track the lifecycle of a PII detection through human review.
Every user action (approve, reject, edit, add, delete) produces an
immutable :class:`AuditEvent` that is never modified or deleted.
The current review state of a detection is a *projection* — it is computed
by applying the sequence of actions to the original detection data.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────
# ReviewState
# ──────────────────────────────────────────────────────────────────────

class ReviewState(str, Enum):
    """
    The possible states of a detection in the human review lifecycle.

    These replace the simpler ``review_state`` field on the Detection
    model.  The mapping from legacy values is::

        unreviewed  → PENDING
        accepted    → APPROVED
        rejected    → REJECTED
        corrected   → MODIFIED

    New states introduced by Phase 4:

    * ``MANUALLY_ADDED`` — the human reviewer added a detection that the
      AI missed (the 'add' action).
    * ``SYSTEM_GENERATED`` — the detection came from the AI pipeline and
      is waiting for its first review action.
    * ``EXPORTED`` — the detection was included in an export (set
      automatically when export succeeds).
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    MANUALLY_ADDED = "manually_added"
    SYSTEM_GENERATED = "system_generated"
    EXPORTED = "exported"


# ──────────────────────────────────────────────────────────────────────
# ReviewAction — what a reviewer did
# ──────────────────────────────────────────────────────────────────────

class ReviewActionType(str, Enum):
    """
    The kind of action a human reviewer can perform.
    """

    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"
    ADD = "add"
    DELETE = "delete"
    UNDO = "undo"
    REDO = "redo"


class ReviewAction(BaseModel):
    """
    A single action performed by a human reviewer.

    This model captures *what* changed so that:
    1. The :class:`HistoryService` can undo/redo it.
    2. The :class:`AuditService` can record it permanently.

    Parameters
    ----------
    action_type : ReviewActionType
        What kind of action was performed.
    detection_id : str
        The detection this action applies to (or a new UUID for 'add').
    document_id : str
        The document being reviewed.
    previous_state : Optional[ReviewState]
        The review state *before* this action (None for 'add').
        Used by HistoryService to restore the old state on undo.
    new_state : ReviewState
        The review state *after* this action.
    previous_values : Optional[Dict[str, Any]]
        Previous field values for edit actions (e.g. {"entity": "old value"}).
    new_values : Optional[Dict[str, Any]]
        New field values for edit/add actions.
    actor : str
        Who performed the action (e.g. "user-123" or "admin").
    reason : Optional[str]
        Why the action was taken (free text from the reviewer).
    timestamp : datetime
        When the action occurred.
    """

    action_type: ReviewActionType
    detection_id: str
    document_id: str
    previous_state: Optional[ReviewState] = None
    new_state: ReviewState
    previous_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    actor: str = "unknown"
    reason: Optional[str] = None
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


# ──────────────────────────────────────────────────────────────────────
# AuditEvent — immutable, append-only record
# ──────────────────────────────────────────────────────────────────────

class AuditEvent(BaseModel):
    """
    An immutable append-only record of a review action.

    Unlike :class:`ReviewAction`, an ``AuditEvent`` is **never** modified
    or deleted.  Even undo/redo operations create *new* audit events
    recording the undo/redo itself.

    The ``event_id`` is a unique, monotonically-increasing-ish identifier
    (UUID-based).  In production this would also include a database
    sequence number for ordering guarantees.
    """

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this audit event",
    )
    action: ReviewAction = Field(..., description="The review action that triggered this event")
    event_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the audit event was recorded",
    )
    document_id: str = Field(..., description="The document this event relates to")
    detection_id: str = Field(..., description="The detection this event relates to")
    previous_review_state: Optional[str] = Field(
        None, description="Review state before the action (None for new detections)",
    )
    new_review_state: str = Field(..., description="Review state after the action")


# ──────────────────────────────────────────────────────────────────────
# ReviewItem — detection in the context of review
# ──────────────────────────────────────────────────────────────────────

class ReviewItem(BaseModel):
    """
    A detection presented for human review.

    This wraps a detection together with its current review state.
    The ``ReviewService`` computes these from the original detection
    data and the sequence of prior actions.
    """

    detection_id: str = Field(..., description="Links back to the Detection.id")
    document_id: str = Field(..., description="The document this item belongs to")
    entity: str = Field(..., description="The detected PII entity text")
    entity_type: str = Field(..., description="PII type (e.g. PERSON, EMAIL, …)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Normalised confidence score")
    reason: str = Field(..., description="Why this was flagged")
    sources: List[str] = Field(default_factory=list, description="Detecting stages")
    start_offset: int = Field(..., ge=0, description="Start offset in normalised text")
    end_offset: int = Field(..., ge=0, description="End offset in normalised text")
    page: int = Field(default=0, ge=0, description="1-based page number")
    line: int = Field(default=0, ge=0, description="1-based line number")
    review_state: ReviewState = Field(
        default=ReviewState.PENDING,
        description="Current state in the human review lifecycle",
    )
    original_detection_id: Optional[str] = Field(
        default=None,
        description="If this item was created by editing another detection, "
        "the ID of the original detection (for traceability)",
    )

    class Config:
        frozen = True  # Review items are snapshots; mutations create new items


# ──────────────────────────────────────────────────────────────────────
# DocumentSnapshot — point-in-time state of review for a document
# ──────────────────────────────────────────────────────────────────────

class DocumentSnapshot(BaseModel):
    """
    A point-in-time snapshot of a document's review state.

    This is used by the :class:`HistoryService` to restore previous
    states during undo/redo, and by the export system to record which
    state the document was in when exported.
    """

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this snapshot",
    )
    document_id: str = Field(..., description="The document this snapshot captures")
    items: List[ReviewItem] = Field(..., description="All review items at this point in time")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this snapshot was taken",
    )
    description: Optional[str] = Field(
        default=None,
        description="Why this snapshot was taken (e.g. 'before edit', 'before export')",
    )
