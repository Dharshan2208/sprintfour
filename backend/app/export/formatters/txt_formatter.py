"""
TXT Export Formatter — produces a plain-text redacted document.

The TXT output format is simply the redacted text prefixed with a
metadata header.  For a pure redacted document without metadata, the
``redacted_text`` from the :class:`RedactionEngine` can be used directly.
"""

from __future__ import annotations

from typing import Any, Dict


class TxtExportFormatter:
    """
    Formats redacted text as a plain-text document.

    Usage::

        formatter = TxtExportFormatter()
        output = formatter.format(
            redacted_text="My Aadhaar is [AADHAAR].",
            json_report={...},
        )
    """

    def format(
        self,
        redacted_text: str,
        json_report: Dict[str, Any],
    ) -> str:
        """
        Format the redacted text for TXT export.

        Parameters
        ----------
        redacted_text : str
            The redacted document text.
        json_report : dict
            The structured report (may be used for a header).

        Returns
        -------
        str
            The formatted TXT output.
        """
        return redacted_text
