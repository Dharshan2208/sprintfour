"""
Domain models for PII detection results.

Every detector (regex, rule, Gemini) returns ``Detection`` instances.
The ``DetectionResult`` aggregates them into a single response after
merging, conflict resolution, and confidence calibration.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Detection(BaseModel):
    """
    A single PII entity detected in the document.

    This is the **universal output format** for every detector in the
    pipeline.  Whether the detection came from a regex, a heuristic
    rule, or Gemini, it is represented identically.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this detection instance",
    )
    entity: str = Field(..., description="The detected PII entity text (exact substring)")
    entity_type: str = Field(..., description="PII type (e.g. PERSON, EMAIL, PHONE, …)")
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Normalised confidence score (0.0 = uncertain, 1.0 = certain)",
    )
    reason: str = Field(..., description="Human-readable explanation of why this was flagged")
    sources: List[str] = Field(
        default_factory=list,
        description="List of detecting stages, e.g. ['regex', 'gemini']",
    )
    start_offset: int = Field(..., ge=0, description="Start character offset in the normalised text (inclusive)")
    end_offset: int = Field(..., ge=0, description="End character offset in the normalised text (exclusive)")
    page: int = Field(default=0, ge=0, description="1‑based page number (0 if unknown)")
    line: int = Field(default=0, ge=0, description="1‑based line number within the page (0 if unknown)")
    status: str = Field(
        default="pending_review",
        description="Automated status: pending_review | confirmed | rejected | modified",
    )
    review_state: str = Field(
        default="unreviewed",
        description="Human review state: unreviewed | accepted | rejected | corrected",
    )


class DetectionSummary(BaseModel):
    """
    Aggregated statistics about the detections found in a document.
    """

    total_count: int = Field(..., ge=0, description="Total number of unique detections")
    per_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of detections grouped by entity_type",
    )
    per_source: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of detections grouped by source",
    )
    high_confidence_count: int = Field(
        default=0, ge=0,
        description="Detections with confidence >= 0.9",
    )
    medium_confidence_count: int = Field(
        default=0, ge=0,
        description="Detections with 0.7 <= confidence < 0.9",
    )
    low_confidence_count: int = Field(
        default=0, ge=0,
        description="Detections with confidence < 0.7",
    )

    class Config:
        frozen = True


class DetectionResult(BaseModel):
    """
    The complete output of the detection pipeline for a single document.
    """

    document_id: str = Field(..., description="The processed document's unique ID")
    detections: List[Detection] = Field(
        default_factory=list,
        description="All unique detections after merging and conflict resolution",
    )
    summary: DetectionSummary = Field(..., description="Aggregated statistics")
    processing_time_ms: float = Field(
        ..., ge=0,
        description="Total wall-clock time for the full detection pipeline in milliseconds",
    )
