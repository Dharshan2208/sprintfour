"""
Redaction Engine — applies redaction strategies to document text.

The engine takes the original document text, a list of detections with
their review states, and a :class:`RedactionConfig`, and produces:

1. The redacted text (with PII replaced according to the strategy).
2. A list of :class:`RedactionOperation` records (for audit).

Redaction Strategies
--------------------
* ``REPLACE`` — replaces the entity text with ``[ENTITY_TYPE]``.
* ``MASK`` — shows first and last character with ``*`` in between.
* ``HASH`` — replaces with a SHA-256 hash of the entity.
* ``REMOVE`` — removes the entity text entirely.

Design Decision
---------------
Redactions are applied **right-to-left** through the text so that
earlier offset positions are not invalidated by later replacements.
This avoids the common "shifting offsets" bug.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.exceptions import RedactionException
from app.domain.models.export import (
    RedactionConfig,
    RedactionOperation,
    RedactionStrategy,
)

logger = logging.getLogger(settings.APP_NAME)


class RedactionEngine:
    """
    Applies configurable redaction strategies to document text.

    Usage::

        engine = RedactionEngine()
        redacted_text, operations = engine.redact(
            text="My Aadhaar is 1234-5678-9012.",
            detections=[...],
            review_states={"det-1": "approved"},
            config=RedactionConfig(),
        )
    """

    # ── Public API ──────────────────────────────────────────────────

    def redact(
        self,
        text: str,
        detections: List[dict],
        review_states: Dict[str, str],
        config: Optional[RedactionConfig] = None,
    ) -> Tuple[str, List[RedactionOperation]]:
        """
        Redact PII entities from the document text.

        Parameters
        ----------
        text : str
            The original (normalised) document text.
        detections : list of dict
            All detections.  Each must have: ``id``, ``entity``,
            ``entity_type``, ``start_offset``, ``end_offset``.
        review_states : dict
            Map of ``detection_id → review_state``.  Only detections
            with state ``approved``, ``modified``, or ``manually_added``
            are redacted.
        config : RedactionConfig, optional
            Redaction strategy configuration.  Uses defaults if omitted.

        Returns
        -------
        tuple of (str, list of RedactionOperation)
            The redacted text and a list of every operation applied.

        Raises
        ------
        RedactionException
            If redaction fails (e.g. invalid offsets).
        """
        if config is None:
            config = RedactionConfig()

        # 1. Filter to only approved/reviewed detections
        redactable_states = {"approved", "modified", "manually_added"}
        to_redact = [
            det for det in detections
            if review_states.get(det.get("id", ""), "") in redactable_states
        ]

        if not to_redact:
            logger.info("No detections to redact")
            return text, []

        # 2. Sort by end_offset descending (right-to-left) to avoid
        #    offset shifting when we replace text.
        to_redact.sort(key=lambda d: d.get("end_offset", 0), reverse=True)

        # 3. Apply redactions
        redacted = text
        operations: List[RedactionOperation] = []

        for det in to_redact:
            det_id = det.get("id", "")
            entity = det.get("entity", "")
            entity_type = det.get("entity_type", "UNKNOWN")
            start = det.get("start_offset", 0)
            end = det.get("end_offset", 0)

            # Validate offsets
            if start < 0 or end > len(redacted) or start >= end:
                logger.warning(
                    "Invalid offsets for detection, skipping",
                    extra={
                        "detection_id": det_id,
                        "start": start,
                        "end": end,
                        "text_length": len(redacted),
                    },
                )
                continue

            # Verify the text at the offsets matches
            actual_text = redacted[start:end]
            if actual_text != entity:
                logger.warning(
                    "Text mismatch at offsets, skipping",
                    extra={
                        "detection_id": det_id,
                        "expected": entity,
                        "actual": actual_text,
                    },
                )
                continue

            # Determine the strategy for this entity type
            strategy = config.per_type.get(
                entity_type.upper(),
                config.default_strategy,
            )

            # Generate replacement
            replacement = self._apply_strategy(entity, entity_type, strategy)

            # Perform replacement
            redacted = redacted[:start] + replacement + redacted[end:]

            # Record the operation (with updated offsets for the report)
            operations.append(RedactionOperation(
                detection_id=det_id,
                entity_type=entity_type,
                original_text=entity,
                replacement_text=replacement,
                start_offset=start,
                end_offset=start + len(replacement),
                strategy=strategy,
            ))

        logger.info(
            "Redaction complete",
            extra={
                "total_redacted": len(operations),
                "original_length": len(text),
                "final_length": len(redacted),
            },
        )

        return redacted, operations

    # ── Strategy Implementations ────────────────────────────────────

    @staticmethod
    def _apply_strategy(
        entity: str,
        entity_type: str,
        strategy: RedactionStrategy,
    ) -> str:
        """
        Apply a single redaction strategy to an entity.

        Parameters
        ----------
        entity : str
            The original entity text.
        entity_type : str
            The PII type (e.g. PERSON, EMAIL).
        strategy : RedactionStrategy
            The strategy to apply.

        Returns
        -------
        str
            The replacement text.
        """
        if strategy == RedactionStrategy.REPLACE:
            return f"[{entity_type.upper()}]"

        elif strategy == RedactionStrategy.MASK:
            return RedactionEngine._mask_entity(entity)

        elif strategy == RedactionStrategy.HASH:
            return hashlib.sha256(entity.encode("utf-8")).hexdigest()[:16]

        elif strategy == RedactionStrategy.REMOVE:
            return ""

        # Fallback
        return f"[{entity_type.upper()}]"

    @staticmethod
    def _mask_entity(entity: str) -> str:
        """
        Mask an entity, showing first and last character.

        Rules:
        - 1 character → show as ``*``
        - 2 characters → ``f*l``
        - 3+ characters → ``f**l``

        Examples::

            "John"      → "J**n"
            "a@b.com"   → "a*****m"
            "AB123456"  → "A*****6"
        """
        if not entity:
            return ""
        if len(entity) == 1:
            return "*"
        if len(entity) == 2:
            return f"{entity[0]}*{entity[1]}"

        return entity[0] + ("*" * (len(entity) - 2)) + entity[-1]
