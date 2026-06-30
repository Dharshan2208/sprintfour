"""
Detection Service — orchestrates PII detection for a previously
uploaded document.

Routes call ``DetectionService.run_detection(document_id)`` and
receive a ``DetectionResult``.  The service is a thin wrapper around
the ``DetectionPipeline`` that handles document retrieval.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.core.config import settings
from app.core.exceptions import DetectionException, ResourceNotFoundException
from app.domain.models.detection import DetectionResult
from app.pipeline.detection_pipeline import DetectionPipeline
from app.store.document_store import document_store

logger = logging.getLogger(settings.APP_NAME)


class DetectionService:
    """
    Perform PII detection on an uploaded document.

    Usage::

        service = DetectionService()
        result = service.run_detection("doc-uuid-here")
    """

    def __init__(self, pipeline: Optional[DetectionPipeline] = None):
        self._pipeline = pipeline or DetectionPipeline()

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────

    def run_detection(self, document_id: str) -> DetectionResult:
        """
        Run the full detection pipeline on the document identified by
        ``document_id``.

        Parameters
        ----------
        document_id : str
            The document ID returned by the upload endpoint.

        Returns
        -------
        DetectionResult
            All detections, summary, and timing.

        Raises
        ------
        ResourceNotFoundException
            If the document ID is unknown.
        DetectionException
            If the pipeline encounters an unexpected error.
        """
        # 1. Retrieve the document
        normalized_doc = document_store.get(document_id)
        if normalized_doc is None:
            raise ResourceNotFoundException(
                message=f"Document '{document_id}' not found. "
                "Please upload the document first."
            )

        logger.info(
            "Detection started",
            extra={"document_id": document_id},
        )

        # 2. Run the pipeline
        try:
            result = self._pipeline.run(
                text=normalized_doc.text,
                document_id=document_id,
            )
        except Exception as exc:
            raise DetectionException(
                message=f"Detection pipeline failed: {exc}"
            ) from exc

        logger.info(
            "Detection completed",
            extra={
                "document_id": document_id,
                "total_detections": result.summary.total_count,
                "processing_time_ms": result.processing_time_ms,
            },
        )

        return result
