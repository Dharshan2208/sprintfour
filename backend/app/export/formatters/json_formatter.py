"""
JSON Export Formatter — produces a structured JSON report of the export.

The JSON report includes:
* Document ID and export metadata
* The redacted text
* Every redaction operation with offsets
* All original detections
* The review audit history
* The risk assessment report
"""

from __future__ import annotations

from typing import Any, Dict


class JsonExportFormatter:
    """
    Formats the export as a structured JSON document.

    Usage::

        formatter = JsonExportFormatter()
        output = formatter.format(
            redacted_text="...",
            json_report={...},
        )
    """

    def format(
        self,
        redacted_text: str,  # noqa: ARG002 — kept for interface consistency
        json_report: Dict[str, Any],
    ) -> str:
        """
        Format the export as a JSON string.

        Parameters
        ----------
        redacted_text : str
            The redacted document text (included in json_report under
            ``redacted_text``).
        json_report : dict
            The structured report to serialize.

        Returns
        -------
        str
            The formatted JSON string.
        """
        import json

        return json.dumps(json_report, indent=2, default=str)
