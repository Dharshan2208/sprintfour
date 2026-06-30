"""
Document upload and processing routes.

POST /api/v1/documents/upload  →  upload a document, extract text, return metadata
"""

from __future__ import annotations

import logging
from typing import Dict, Any

from fastapi import APIRouter, UploadFile, File, Request, status

from app.api.schemas.responses import ApiResponse, MetaResponse
from app.core.config import settings
from app.core.exceptions import UnsupportedFileException
from app.services.document_service import DocumentService
from app.store.document_store import document_store

logger = logging.getLogger(settings.APP_NAME)

router = APIRouter(prefix="/documents", tags=["Documents"])

# Service instance (would be injected via DI in a production setup)
_document_service = DocumentService()


@router.post(
    "/upload",
    summary="Upload and process a document",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def upload_document(
    request: Request,
    file: UploadFile = File(..., description="Document file (TXT, PDF, or DOCX)"),
) -> ApiResponse[Dict[str, Any]]:
    """
    Upload a document file for text extraction and normalisation.

    Supported formats: ``.txt``, ``.pdf``, ``.docx``.

    Returns a ``document_id`` that can be used with the detection endpoint,
    along with basic metadata and a short text preview.
    """
    # ── Input validation ──
    if not file.filename:
        raise UnsupportedFileException(message="No filename provided in the upload.")

    # FastAPI provides ``file.content_type`` from the ``Content-Type`` header.
    # It may be ``None`` if the client didn't send it.
    mime_type = file.content_type or "application/octet-stream"

    # Read the file bytes into memory.
    # For production with very large files, stream to disk instead.
    file_bytes = await file.read()

    # ── Process ──
    normalized_doc = _document_service.process_upload(
        file_bytes=file_bytes,
        original_filename=file.filename,
        mime_type=mime_type,
    )

    # ── Store for later retrieval (detection, export, etc.) ──
    document_store.save(normalized_doc)

    # ── Build response ──
    text_preview = normalized_doc.text[:200]
    if len(normalized_doc.text) > 200:
        text_preview += "…"

    response_data = {
        "document_id": normalized_doc.document_id,
        "metadata": {
            "filename": normalized_doc.metadata.filename,
            "file_size": normalized_doc.metadata.file_size,
            "mime_type": normalized_doc.metadata.mime_type,
            "extension": normalized_doc.metadata.extension,
        },
        "page_count": normalized_doc.original_document.page_count,
        "character_count": normalized_doc.original_document.character_count,
        "text_preview": text_preview,
        "processing_status": "ready",
    }

    return ApiResponse(
        message="Document uploaded and processed successfully",
        data=response_data,
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp="",  # Will be populated by middleware in future
        ),
    )
