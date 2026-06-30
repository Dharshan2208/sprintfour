"""
Document ingestion service.

Orchestrates the end‑to‑end flow:
  upload → validate → store → extract → normalize → return

Routes should call ``DocumentService.process_upload()`` and nothing else.
"""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
from typing import Dict, Type

from app.core.config import settings
from app.core.exceptions import (
    UnsupportedFileException,
    DocumentExtractionException,
    NormalizationException,
)
from app.domain.models.document import Document, NormalizedDocument
from app.extractors.base_extractor import BaseExtractor
from app.extractors.txt_extractor import TxtExtractor
from app.extractors.pdf_extractor import PdfExtractor
from app.extractors.docx_extractor import DocxExtractor
from app.normalizer.normalizer import TextNormalizer

logger = logging.getLogger(settings.APP_NAME)

# ── Supported MIME types (used during validation) ──
_SUPPORTED_MIME_TYPES: Dict[str, str] = {
    "text/plain": "txt",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

# ── Extension → Extractor mapping (used during routing) ──
_EXTENSIONS_MAP: Dict[str, Type[BaseExtractor]] = {
    "txt": TxtExtractor,
    "pdf": PdfExtractor,
    "docx": DocxExtractor,
}

# ── Default maximum file size (50 MB) ──
_DEFAULT_MAX_FILE_SIZE = 50 * 1024 * 1024


class DocumentService:
    """
    Coordinates the full document ingestion lifecycle.

    Usage::

        service = DocumentService()
        result = service.process_upload(file_bytes, "report.pdf", "application/pdf")
        # result is a NormalizedDocument ready for detection.
    """

    def __init__(
        self,
        max_file_size: int = _DEFAULT_MAX_FILE_SIZE,
        normalizer: TextNormalizer | None = None,
    ):
        self._max_file_size = max_file_size
        self._normalizer = normalizer or TextNormalizer()

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def process_upload(
        self,
        file_bytes: bytes,
        original_filename: str,
        mime_type: str,
    ) -> NormalizedDocument:
        """
        Validate, extract, and normalise an uploaded document.

        Parameters
        ----------
        file_bytes : bytes
            Raw file content from the upload.
        original_filename : str
            The original filename (used for metadata and extension
            detection if MIME is ambiguous).
        mime_type : str
            The MIME type declared by the client or inferred by FastAPI.

        Returns
        -------
        NormalizedDocument
            Fully processed document, ready for PII detection.

        Raises
        ------
        UnsupportedFileException
            If the file type is not supported.
        DocumentExtractionException
            If the file cannot be parsed.
        NormalizationException
            If normalisation fails unexpectedly.
        """
        # 1. Validate
        ext = self._validate(file_bytes, original_filename, mime_type)

        # 2. Store temporarily
        file_path = self._store_temp(file_bytes, ext)

        try:
            # 3. Extract
            logger.info("Extraction started", extra={"file_ext": ext})
            extractor = self._get_extractor(ext)
            document: Document = extractor.extract(file_path, original_filename)
            logger.info(
                "Extraction completed",
                extra={
                    "page_count": document.page_count,
                    "char_count": document.character_count,
                    "document_id": document.document_id,
                },
            )

            # 4. Normalise
            logger.info("Normalisation started", extra={"document_id": document.document_id})
            try:
                normalized = self._normalizer.normalize(document)
            except Exception as exc:
                raise NormalizationException(
                    message=f"Normalisation failed: {exc}"
                ) from exc

            logger.info(
                "Normalisation completed",
                extra={
                    "document_id": normalized.document_id,
                    "normalized_length": len(normalized.text),
                },
            )

            return normalized

        except (UnsupportedFileException, DocumentExtractionException):
            raise
        except NormalizationException:
            raise
        except Exception as exc:
            raise DocumentExtractionException(
                message=f"Unexpected error during document processing: {exc}"
            ) from exc
        finally:
            # 5. Clean up temp file
            self._cleanup_temp(file_path)

    # ──────────────────────────────────────────────────────────────────
    # Validation
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _validate(
        file_bytes: bytes,
        original_filename: str,
        mime_type: str,
    ) -> str:
        """
        Validate file size, MIME type, and extension.

        Returns the normalised extension (lowercase, no dot).
        """
        # Size check
        if len(file_bytes) > _DEFAULT_MAX_FILE_SIZE:
            raise UnsupportedFileException(
                message=f"File exceeds maximum size of {_DEFAULT_MAX_FILE_SIZE // (1024*1024)} MB."
            )

        # Extension from filename
        if "." not in original_filename:
            raise UnsupportedFileException(
                message="File has no extension. Supported: txt, pdf, docx."
            )

        ext = original_filename.rsplit(".", 1)[-1].lower()

        # MIME-type check (if we recognise it)
        if mime_type in _SUPPORTED_MIME_TYPES:
            expected_ext = _SUPPORTED_MIME_TYPES[mime_type]
            if ext != expected_ext:
                raise UnsupportedFileException(
                    message=f"MIME type '{mime_type}' does not match extension '.{ext}'."
                )

        # Extension check
        if ext not in _EXTENSIONS_MAP:
            raise UnsupportedFileException(
                message=f"Unsupported file extension '.{ext}'. Supported: {', '.join(_EXTENSIONS_MAP)}."
            )

        return ext

    # ──────────────────────────────────────────────────────────────────
    # Temporary storage
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _store_temp(file_bytes: bytes, ext: str) -> str:
        """
        Write uploaded bytes to a temporary file with a secure UUID name.

        Returns the absolute path to the temp file.
        """
        secure_name = f"{uuid.uuid4().hex}.{ext}"
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, secure_name)

        with open(file_path, "wb") as fh:
            fh.write(file_bytes)

        logger.debug("Temp file created", extra={"path": file_path})
        return file_path

    # ──────────────────────────────────────────────────────────────────
    # Cleanup
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _cleanup_temp(file_path: str) -> None:
        """Remove a temporary file if it exists."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug("Temp file removed", extra={"path": file_path})
        except OSError as exc:
            logger.warning("Failed to remove temp file", extra={"path": file_path, "error": str(exc)})

    # ──────────────────────────────────────────────────────────────────
    # Extractor routing
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_extractor(ext: str) -> BaseExtractor:
        """Return the extractor instance for the given extension."""
        cls = _EXTENSIONS_MAP.get(ext)
        if cls is None:
            raise UnsupportedFileException(
                message=f"No extractor registered for extension '.{ext}'."
            )
        return cls()
