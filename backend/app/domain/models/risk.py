"""
Domain models for the Risk Intelligence Engine (Phase 5).

The risk engine evaluates how *safe* a document is for export based on:
* The current review state of every detection.
* The sensitivity of each entity type (AADHAAR, PAN, CREDIT_CARD, etc.
  are more sensitive than, say, URL).
* The confidence of each detection.
* The proportion of detections that have been reviewed.

Output is a :class:`RiskReport` with an overall score, per-item
breakdown, warnings, and recommendations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────
# Priority Levels
# ──────────────────────────────────────────────────────────────────────

class PriorityLevel(str, Enum):
    """
    How urgently a detection needs human review.

    ``CRITICAL`` — High-sensitivity, unreviewed, high-confidence.
    ``HIGH``     — High-sensitivity or unreviewed high-confidence.
    ``MEDIUM``   — Medium priority (reviewed but needs attention).
    ``LOW``      — Already reviewed or low-sensitivity.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ──────────────────────────────────────────────────────────────────────
# PriorityItem — a detection with its priority assessment
# ──────────────────────────────────────────────────────────────────────

class PriorityItem(BaseModel):
    """
    A single detection with its assigned priority for review.

    The ``priority`` field tells the UI which detections to show first.
    The ``reason`` explains *why* this priority was assigned.
    """

    detection_id: str
    entity_type: str
    entity: str
    confidence: float
    review_state: str
    priority: PriorityLevel
    reason: str


# ──────────────────────────────────────────────────────────────────────
# ReviewProgress — how much review work has been completed
# ──────────────────────────────────────────────────────────────────────

class ReviewProgress(BaseModel):
    """
    Summary of review completion for a document.
    """

    total_items: int = Field(..., ge=0, description="Total number of detections")
    reviewed_count: int = Field(..., ge=0, description="Items that have been reviewed (approved/rejected/modified)")
    pending_count: int = Field(..., ge=0, description="Items still pending review")
    approval_rate: float = Field(
        ..., ge=0.0, le=1.0,
        description="Fraction of reviewed items that were approved (approved / reviewed)",
    )
    review_percentage: float = Field(
        ..., ge=0.0, le=100.0,
        description="Percentage of items that have been reviewed",
    )


# ──────────────────────────────────────────────────────────────────────
# Risk Factors — configurable weights for risk calculation
# ──────────────────────────────────────────────────────────────────────

ENTITY_SENSITIVITY: Dict[str, float] = {
    # High-sensitivity government IDs and financial data
    "AADHAAR": 1.0,
    "PAN": 1.0,
    "PASSPORT": 1.0,
    "CREDIT_CARD": 1.0,
    "BANK_ACCOUNT": 1.0,
    "VOTER_ID": 1.0,
    "DRIVING_LICENSE": 0.9,
    "CIN": 0.9,
    "GST": 0.9,
    "IFSC": 0.9,
    "UPI_ID": 0.8,
    # Personal identifiable information
    "PHONE": 0.85,
    "EMAIL": 0.8,
    "DATE_OF_BIRTH": 0.85,
    "AGE": 0.6,
    "GENDER": 0.4,
    # Contextual / less sensitive
    "PERSON": 0.75,
    "ADDRESS": 0.8,
    "ORGANIZATION": 0.5,
    "IP_ADDRESS": 0.7,
    "MAC_ADDRESS": 0.7,
    "URL": 0.3,
    "CUSTOM": 0.5,
}


# ──────────────────────────────────────────────────────────────────────
# RiskReport — the main output of the risk engine
# ──────────────────────────────────────────────────────────────────────

class RiskReport(BaseModel):
    """
    Complete risk assessment for a document.

    The ``overall_score`` is a value between 0.0 (safe) and 1.0 (high
    risk).  A score of 0.0 means all detections have been reviewed and
    approved or resolved.  A high score means many unreviewed or
    high-sensitivity items remain.

    The ``export_ready`` flag is a boolean convenience: ``True`` if
    ``overall_score`` is below the configurable threshold (default: 0.3).
    """

    document_id: str = Field(..., description="The document being assessed")
    overall_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Overall risk score (0 = safe, 1 = high risk)",
    )
    review_progress: ReviewProgress = Field(..., description="Review completion summary")
    priority_items: List[PriorityItem] = Field(
        default_factory=list,
        description="All items sorted by priority (critical first)",
    )
    critical_items: List[PriorityItem] = Field(
        default_factory=list,
        description="Only CRITICAL-priority items",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Human-readable warnings about the document's risk state",
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Suggested actions to reduce risk",
    )
    export_ready: bool = Field(
        default=False,
        description="Whether the document is safe to export",
    )
    export_ready_threshold: float = Field(
        default=0.3,
        description="Score threshold below which export_ready is True",
    )
    analyzed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this report was generated",
    )

    class Config:
        frozen = True
