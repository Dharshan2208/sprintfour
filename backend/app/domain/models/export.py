"""
Domain models for the Validation & Secure Export Engine (Phase 6).

These models represent:
* The **validation result** — whether a document is safe to export.
* The **redaction configuration** — how each entity type should be redacted.
* The **export result** — the final output of the export process.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────
# Redaction Strategy
# ──────────────────────────────────────────────────────────────────────

class RedactionStrategy(str, Enum):
    """
    How a PII entity should be redacted in the exported document.

    ``REPLACE``
        Replace the entity text with a label like ``[PERSON]`` or
        ``[EMAIL]``.  This is the default strategy.

    ``MASK``
        Show the first and last character, mask the middle with ``*``.
        E.g. ``j*****@example.com`` or ``R*****n``.

    ``HASH``
        Replace with a SHA-256 hash of the entity text.  This allows
        deterministic matching across documents without revealing the
        original value.

    ``REMOVE``
        Remove the entity text entirely (replace with empty string).
    """

    REPLACE = "replace"
    MASK = "mask"
    HASH = "hash"
    REMOVE = "remove"


# ──────────────────────────────────────────────────────────────────────
# Redaction Config — per-entity-type redaction rules
# ──────────────────────────────────────────────────────────────────────

class RedactionConfig(BaseModel):
    """
    Configuration for how each entity type should be redacted.

    The ``default_strategy`` applies to entity types not explicitly
    configured in ``per_type``.

    Example::

        config = RedactionConfig(
            default_strategy=RedactionStrategy.REPLACE,
            per_type={
                "AADHAAR": RedactionStrategy.MASK,
                "CREDIT_CARD": RedactionStrategy.MASK,
                "URL": RedactionStrategy.REMOVE,
            },
        )
    """

    default_strategy: RedactionStrategy = Field(
        default=RedactionStrategy.REPLACE,
        description="Default redaction strategy for all entity types",
    )
    per_type: Dict[str, RedactionStrategy] = Field(
        default_factory=dict,
        description="Per-entity-type strategy overrides",
    )


# ──────────────────────────────────────────────────────────────────────
# Redaction Operation — a single redaction applied to the text
# ──────────────────────────────────────────────────────────────────────

class RedactionOperation(BaseModel):
    """
    A single redaction that was applied to the document text.

    This is recorded so the export result can include a full audit of
    what was redacted, where, and how.
    """

    detection_id: str = Field(..., description="The detection that triggered this redaction")
    entity_type: str = Field(..., description="PII type of the redacted entity")
    original_text: str = Field(..., description="The original entity text that was redacted")
    replacement_text: str = Field(..., description="What it was replaced with")
    start_offset: int = Field(..., ge=0, description="Start offset in the exported text")
    end_offset: int = Field(..., ge=0, description="End offset in the exported text")
    strategy: RedactionStrategy = Field(..., description="The strategy used")


# ──────────────────────────────────────────────────────────────────────
# Validation Result
# ──────────────────────────────────────────────────────────────────────

class ValidationIssue(BaseModel):
    """
    A single issue found during export validation.

    ``severity`` can be ``"error"`` (blocks export) or ``"warning"``
    (advisory, does not block).
    """

    severity: str = Field(..., pattern=r"^(error|warning)$")
    code: str = Field(..., description="Machine-readable issue code")
    message: str = Field(..., description="Human-readable description of the issue")
    detection_id: Optional[str] = Field(default=None, description="Related detection, if applicable")


class ValidationResult(BaseModel):
    """
    The result of export validation.

    A document is safe to export when ``is_valid`` is ``True`` and
    ``issues`` is empty.

    When ``is_valid`` is ``False``, the ``issues`` list contains all
    reasons the document cannot be exported.  The frontend should
    display these to the user and prevent export.
    """

    is_valid: bool = Field(..., description="Whether the document passed all validation checks")
    issues: List[ValidationIssue] = Field(
        default_factory=list,
        description="All issues found during validation",
    )
    document_id: str = Field(..., description="The validated document")
    validated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When validation was performed",
    )


# ──────────────────────────────────────────────────────────────────────
# Export Result
# ──────────────────────────────────────────────────────────────────────

class ExportFormat(str, Enum):
    """Supported export output formats."""
    TXT = "txt"
    PDF = "pdf"
    JSON = "json"


class ExportResult(BaseModel):
    """
    The complete result of a document export.

    Contains the redacted text (for TXT/PDF exports), a JSON report
    (always included), a list of every redaction operation applied,
    and metadata about the export.
    """

    document_id: str = Field(..., description="The exported document's ID")
    export_format: ExportFormat = Field(..., description="The output format")
    redacted_text: str = Field(
        default="",
        description="The redacted document text (empty for JSON-only export)",
    )
    json_report: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured JSON report with metadata, detections, and audit trail",
    )
    redaction_operations: List[RedactionOperation] = Field(
        default_factory=list,
        description="Every redaction that was applied",
    )
    redaction_count: int = Field(default=0, ge=0, description="Number of redactions applied")
    exported_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the export was performed",
    )
    export_duration_ms: float = Field(
        default=0.0, ge=0.0,
        description="Wall-clock time for the export operation",
    )
