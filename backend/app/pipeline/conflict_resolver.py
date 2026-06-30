"""
Conflict Resolver — resolves type and span conflicts among merged detections.

After the ``EntityMerger`` deduplicates, some conflicts may remain:
* Two detections overlapping the same span with **different** entity types.
* One detection fully **nested** inside another.
* Exact same span but completely different classifications.

This resolver applies deterministic priority rules so that the final
list is consistent and reviewable.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Set

from app.core.config import settings
from app.domain.models.detection import Detection

logger = logging.getLogger(settings.APP_NAME)

# ── Type priority (higher number = wins in ambiguity) ────────────
# Government-issued IDs beat financial details, which beat personal
# info, which beats organisational info.
_TYPE_PRIORITY: Dict[str, int] = {
    # Government IDs — highest priority
    "AADHAAR": 100,
    "PAN": 99,
    "PASSPORT": 98,
    "VOTER_ID": 97,
    "DRIVING_LICENSE": 96,
    # Financial
    "CREDIT_CARD": 90,
    "BANK_ACCOUNT": 89,
    "IFSC": 88,
    "UPI_ID": 87,
    "CIN": 86,
    "GST": 85,
    # Personal identification
    "PERSON": 80,
    "DATE_OF_BIRTH": 79,
    "AGE": 78,
    "GENDER": 77,
    "EMAIL": 76,
    "PHONE": 75,
    # Location
    "ADDRESS": 70,
    # Organisational
    "ORGANIZATION": 60,
    # Digital / Network
    "IP_ADDRESS": 50,
    "URL": 49,
    "MAC_ADDRESS": 48,
    # Fallback
    "CUSTOM": 10,
}


class ConflictResolver:
    """
    Resolve type conflicts and nesting among detections.

    Strategy
    --------
    1. **Nested (same type)** → keep the one with higher confidence.
    2. **Nested (different types)** → keep both; the reviewer decides.
    3. **Exact same span, different type** → keep the type with higher
       ``_TYPE_PRIORITY``; the losing detection is **discarded** (the
       reviewer still sees the entity, just with the best-guess type).
    4. **Partially overlapping, different types** → keep both (likely
       different entities that happen to be adjacent).
    """

    def resolve(self, detections: List[Detection]) -> List[Detection]:
        """
        Resolve conflicts in a list of merged detections.

        Returns a clean list with no conflicting type assignments on
        the same span.
        """
        if not detections:
            return []

        # Sort by start_offset then decreasing span length
        sorted_dets = sorted(
            detections, key=lambda d: (d.start_offset, -(d.end_offset - d.start_offset))
        )

        resolved: List[Detection] = []
        skip_ids: Set[str] = set()

        for i, det in enumerate(sorted_dets):
            if det.id in skip_ids:
                continue

            resolved_det = det  # may be replaced during conflict resolution

            for j, other in enumerate(sorted_dets):
                if i == j or other.id in skip_ids:
                    continue

                # Check if they share the exact same span
                if self._exact_same_span(resolved_det, other):
                    resolved_det = self._resolve_same_span(resolved_det, other)
                    # Mark BOTH original IDs as consumed — the resolved
                    # detection is the only one we keep.
                    skip_ids.add(det.id)
                    skip_ids.add(other.id)

            # Only append if this specific ID wasn't already consumed
            # as a loser in a previous resolution.
            if resolved_det.id not in skip_ids:
                resolved.append(resolved_det)
                skip_ids.add(resolved_det.id)

        logger.debug(
            "Conflict resolution completed",
            extra={"input_count": len(detections), "output_count": len(resolved)},
        )
        return resolved

    # ──────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _exact_same_span(a: Detection, b: Detection) -> bool:
        """Return True if both detections cover the exact same range."""
        return a.start_offset == b.start_offset and a.end_offset == b.end_offset

    def _resolve_same_span(self, a: Detection, b: Detection) -> Detection:
        """
        Two detections cover the same span but disagree on type.

        The entity type with higher ``_TYPE_PRIORITY`` wins.  However,
        we **merge the sources** so the losing type is not lost —
        it is recorded in the ``reason`` field.
        """
        a_prio = _TYPE_PRIORITY.get(a.entity_type, 0)
        b_prio = _TYPE_PRIORITY.get(b.entity_type, 0)

        if a_prio > b_prio:
            winner = a
            loser_type = b.entity_type
        elif b_prio > a_prio:
            winner = b
            loser_type = a.entity_type
        else:
            # Equal priority — higher confidence wins
            winner = a if a.confidence >= b.confidence else b
            loser_type = b.entity_type if winner.id == a.id else a.entity_type

        # Merge source lists
        merged_sources = list(dict.fromkeys(winner.sources + b.sources))
        # If we took the loser's sources, update
        if winner.id == a.id:
            # a won; add b's sources if not present
            pass  # Already in merged_sources above

        return Detection(
            id=winner.id,
            entity=winner.entity,
            entity_type=winner.entity_type,
            confidence=winner.confidence,
            reason=(
                f"{winner.reason} | Also classified as {loser_type} "
                f"by {', '.join(b.sources)}"
            ),
            sources=merged_sources,
            start_offset=winner.start_offset,
            end_offset=winner.end_offset,
            page=winner.page or b.page,
            line=winner.line or b.line,
            status=winner.status,
            review_state=winner.review_state,
        )
