"""
Abstract base class for all document text extractors.

Every file-format extractor (TXT, PDF, DOCX, …) must implement the
``BaseExtractor`` interface so that ``DocumentService`` can remain
completely format‑agnostic.

Extractor contract
------------------
1. **Input** – an absolute file path on disk and the original filename.
2. **Output** – a fully populated ``Document`` with structural decomposition
   (pages → paragraphs → lines) and correct character offsets.
3. **Purity** – extractors should be stateless.  All state lives in the
   returned ``Document``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.models.document import Document


class BaseExtractor(ABC):
    """
    Interface that every concrete extractor must implement.

    The single public method ``extract`` drives the entire extraction and
    returns a complete ``Document`` domain model.
    """

    # ── Human-readable label used in logging / error messages ──
    format_name: str = "unknown"

    @abstractmethod
    def extract(self, file_path: str, original_filename: str) -> Document:
        """
        Extract text and structural information from a document.

        Parameters
        ----------
        file_path : str
            Absolute path to the temporary file on disk.
        original_filename : str
            The original uploaded filename (used for metadata only).

        Returns
        -------
        Document
            Fully populated domain model with pages, paragraphs, lines,
            and correct absolute character offsets.

        Raises
        ------
        DocumentExtractionException
            If the file cannot be parsed (corrupt, encrypted, …).
        """
        ...
