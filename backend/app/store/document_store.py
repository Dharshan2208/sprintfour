"""
Lightweight in-memory document store.

Holds ``NormalizedDocument`` instances by ``document_id`` so the
detection route can retrieve them.

**This is a development-only implementation.**  In production the store
would be backed by PostgreSQL / S3 / Redis.  The interface is kept
intentionally simple so migration is straightforward.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from app.core.config import settings
from app.domain.models.document import NormalizedDocument

logger = logging.getLogger(settings.APP_NAME)


class InMemoryDocumentStore:
    """
    Thread‑safe (within a single process) in-memory document store.

    Usage::

        store = InMemoryDocumentStore()
        store.save(normalized_doc)
        doc = store.get(document_id)
    """

    def __init__(self) -> None:
        self._store: Dict[str, NormalizedDocument] = {}

    def save(self, document: NormalizedDocument) -> None:
        """Store a normalised document keyed by its ``document_id``."""
        self._store[document.document_id] = document
        logger.debug(
            "Document stored",
            extra={"document_id": document.document_id},
        )

    def get(self, document_id: str) -> Optional[NormalizedDocument]:
        """
        Retrieve a document by its ID.

        Returns ``None`` if the document ID is unknown.
        """
        doc = self._store.get(document_id)
        if doc is None:
            logger.warning("Document not found in store", extra={"document_id": document_id})
        return doc

    def delete(self, document_id: str) -> None:
        """Remove a document from the store."""
        self._store.pop(document_id, None)
        logger.debug("Document removed from store", extra={"document_id": document_id})

    def clear(self) -> None:
        """Remove all documents (useful for testing)."""
        self._store.clear()

    @property
    def count(self) -> int:
        """Number of documents currently held in memory."""
        return len(self._store)


# Singleton instance — shared across the application.
# In a DI‑enabled system this would be injected.
document_store = InMemoryDocumentStore()
