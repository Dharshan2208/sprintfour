"""
Document Renderer — produces the final rendered output for export.

The renderer takes the redacted text and metadata, and produces the
content for the requested output format.  It delegates format-specific
rendering to the appropriate formatter.

This layer exists so that the :class:`ExportService` does not need to
know about format-specific details.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.domain.models.export import (
    ExportFormat,
    ExportResult,
    RedactionOperation,
)
from app.export.formatters.txt_formatter import TxtExportFormatter
from app.export.formatters.json_formatter import JsonExportFormatter

logger = logging.getLogger(settings.APP_NAME)

# Registry of available formatters
_FORMATTERS = {
    ExportFormat.TXT: TxtExportFormatter,
    ExportFormat.JSON: JsonExportFormatter,
}


class DocumentRenderer:
    """
    Renders a redacted document in the requested output format.

    Usage::

        renderer = DocumentRenderer()
        result = renderer.render(
            format=ExportFormat.TXT,
            document_id="doc-123",
            redacted_text="...",
            operations=[...],
            detections=[...],
            review_history=[...],
            risk_report=risk_report,
        )
    """

    def render(
        self,
        format: ExportFormat,
        document_id: str,
        redacted_text: str,
        operations: List[RedactionOperation],
        detections: List[Dict[str, Any]],
        review_history: Optional[List[Dict[str, Any]]] = None,
        risk_report: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExportResult:
        """
        Render the document in the requested format.

        Parameters
        ----------
        format : ExportFormat
            The desired output format.
        document_id : str
            The document being exported.
        redacted_text : str
            The text with redactions applied.
        operations : list of RedactionOperation
            Every redaction operation that was applied.
        detections : list of dict
            All detections (for the JSON report).
        review_history : list of dict, optional
            Audit history (for the JSON report).
        risk_report : dict, optional
            Risk assessment (for the JSON report).
        metadata : dict, optional
            Additional metadata to include in the report.

        Returns
        -------
        ExportResult
            The formatted export result.
        """
        formatter_cls = _FORMATTERS.get(format)
        if formatter_cls is None:
            raise ValueError(f"Unsupported export format: {format}")

        formatter = formatter_cls()

        # Build report data for JSON (always included)
        json_report = self._build_json_report(
            document_id=document_id,
            redacted_text=redacted_text,
            operations=operations,
            detections=detections,
            review_history=review_history or [],
            risk_report=risk_report,
            metadata=metadata or {},
        )

        # Format the output
        formatted_output = formatter.format(
            redacted_text=redacted_text,
            json_report=json_report,
        )

        return ExportResult(
            document_id=document_id,
            export_format=format,
            redacted_text=formatted_output if format == ExportFormat.TXT else redacted_text,
            json_report=json_report,
            redaction_operations=operations,
            redaction_count=len(operations),
        )

    # ── Internal ────────────────────────────────────────────────────

    @staticmethod
    def _build_json_report(
        document_id: str,
        redacted_text: str,
        operations: List[RedactionOperation],
        detections: List[Dict[str, Any]],
        review_history: List[Dict[str, Any]],
        risk_report: Optional[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build the structured JSON report included with every export."""
        return {
            "document_id": document_id,
            "export_metadata": {
                "exported_at": metadata.get("exported_at", ""),
                "exported_by": metadata.get("exported_by", "unknown"),
                "total_detections": len(detections),
                "total_redactions": len(operations),
                "has_risk_report": risk_report is not None,
                "has_review_history": len(review_history) > 0,
            },
            "redacted_text": redacted_text,
            "redaction_operations": [
                {
                    "detection_id": op.detection_id,
                    "entity_type": op.entity_type,
                    "original_text": op.original_text,
                    "replacement_text": op.replacement_text,
                    "start_offset": op.start_offset,
                    "end_offset": op.end_offset,
                    "strategy": op.strategy.value,
                }
                for op in operations
            ],
            "detections": detections,
            "review_history": review_history,
            "risk_report": risk_report,
        }
