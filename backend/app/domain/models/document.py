"""
Internal domain models for a processed document.

These models represent the document after extraction and normalisation but
BEFORE detection.  They live in the **domain layer** and must NOT be confused
with API schemas (which live in ``app.api.schemas``).

Structure
---------
Document
 ├── metadata (DocumentMetadata)
 ├── pages[] (Page)
 │    ├── paragraphs[] (Paragraph)
 │    │    └── lines[] (Line)
 │    └── text (full-page concatenation)
 └── raw_text (concatenation of every page)

NormalizedDocument
 ├── text (normalised version of raw_text)
 └── offset_maps[]  (original ↔ normalised translation table)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────
# Document Metadata
# ──────────────────────────────────────────────────────────────────────

class DocumentMetadata(BaseModel):
    """
    File-level metadata describing the original uploaded document.

    This is extracted / inferred at upload time and does NOT change
    throughout the lifecycle of the document.
    """

    filename: str = Field(..., description="Original uploaded filename")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    mime_type: str = Field(..., description="Detected or declared MIME type")
    extension: str = Field(..., description="File extension (lowercase, no dot)")
    upload_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the file was uploaded",
    )
    processing_status: str = Field(
        default="pending",
        description="Current processing status: pending | extracting | normalizing | ready | error",
    )

    class Config:
        frozen = True  # metadata is immutable after creation


# ──────────────────────────────────────────────────────────────────────
# Line / Paragraph / Page — the structural hierarchy
# ──────────────────────────────────────────────────────────────────────

class Line(BaseModel):
    """
    A single line of extracted text.

    One line maps to one physical line in the source document (for TXT),
    one paragraph-run in PDF, or one paragraph in DOCX.
    """

    text: str = Field(..., description="Raw extracted text of this line")
    line_number: int = Field(..., ge=1, description="Line number within the parent paragraph (1‑based)")
    start_offset: int = Field(..., ge=0, description="Absolute character offset in the full raw text (inclusive)")
    end_offset: int = Field(..., ge=0, description="Absolute character offset in the full raw text (exclusive)")


class Paragraph(BaseModel):
    """
    A paragraph made of one or more consecutive lines.

    In most documents a paragraph is a block of text separated by blank
    lines.  In PDFs it may be reconstructed from fragmented runs.
    """

    text: str = Field(..., description="Concatenated text of all lines in this paragraph")
    paragraph_number: int = Field(..., ge=1, description="Paragraph number within the parent page (1‑based)")
    lines: List[Line] = Field(default_factory=list, description="Ordered lines that make up this paragraph")
    start_offset: int = Field(..., ge=0, description="Absolute start offset in the full raw text (inclusive)")
    end_offset: int = Field(..., ge=0, description="Absolute end offset in the full raw text (exclusive)")


class Page(BaseModel):
    """
    A single page of the original document.

    Page numbers are 1‑based.  The ``text`` field is the concatenation of
    every paragraph on the page and is a substring of the document's
    ``raw_text``.
    """

    page_number: int = Field(..., ge=1, description="1‑based page number")
    paragraphs: List[Paragraph] = Field(default_factory=list, description="Ordered paragraphs on this page")
    start_offset: int = Field(..., ge=0, description="Absolute start offset in the full raw text (inclusive)")
    end_offset: int = Field(..., ge=0, description="Absolute end offset in the full raw text (exclusive)")
    text: str = Field(default="", description="Full concatenated text of this page")


# ──────────────────────────────────────────────────────────────────────
# Document — the top-level extraction result
# ──────────────────────────────────────────────────────────────────────

class Document(BaseModel):
    """
    A fully extracted document, including its structural decomposition.

    This is the **output** of the extraction phase and is consumed by the
    normalizer (and later by the detection pipeline).
    """

    document_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this document instance",
    )
    metadata: DocumentMetadata = Field(..., description="File-level metadata")
    pages: List[Page] = Field(default_factory=list, description="Ordered pages of the document")
    raw_text: str = Field(default="", description="Full raw text concatenated from all pages")
    page_count: int = Field(..., ge=0, description="Number of pages in the document")
    character_count: int = Field(..., ge=0, description="Total number of characters in raw_text")


# ──────────────────────────────────────────────────────────────────────
# Offset Mapping — bridges normalised ↔ original positions
# ──────────────────────────────────────────────────────────────────────

class OffsetMapping(BaseModel):
    """
    Maps a range in the **normalised** text back to the corresponding
    range in the **original** (raw) text.

    Because normalisation may collapse multiple whitespace characters,
    normalise Unicode forms, or strip invisible characters, the mapping
    is not always 1:1 — a single normalised character may correspond to
    one or many original characters.
    """

    normalized_start: int = Field(..., ge=0, description="Start offset in the normalised text (inclusive)")
    normalized_end: int = Field(..., ge=0, description="End offset in the normalised text (exclusive)")
    original_start: int = Field(..., ge=0, description="Start offset in the original raw text (inclusive)")
    original_end: int = Field(..., ge=0, description="End offset in the original raw text (exclusive)")


# ──────────────────────────────────────────────────────────────────────
# NormalizedDocument — ready for detection
# ──────────────────────────────────────────────────────────────────────

class NormalizedDocument(BaseModel):
    """
    A document that has been normalised for PII detection.

    The ``text`` field contains cleaned, normalised text suitable for
    regex scanning and LLM consumption.  The ``offset_maps`` table lets
    consumers translate every detection position back to the original
    extracted text (and from there back to the original file).

    The original ``Document`` is retained so that structural look‑ups
    (e.g. "which page / paragraph contains this PII?") remain possible.
    """

    document_id: str = Field(..., description="Matches the original Document.document_id")
    text: str = Field(..., description="Normalised, whitespace‑cleaned full text")
    offset_maps: List[OffsetMapping] = Field(
        default_factory=list,
        description="Ordered list mapping normalised offsets → original offsets",
    )
    metadata: DocumentMetadata = Field(..., description="Carried over from the original Document")
    original_document: Document = Field(..., description="Reference to the pre‑normalisation Document")
