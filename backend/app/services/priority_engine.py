"""
Priority Engine — determines the review priority of each detection.

Priority is computed from three factors:

1. **Entity sensitivity** — government IDs and financial data are more
   sensitive than URLs or organisation names.
2. **Review state** — unreviewed items are higher priority than reviewed
   ones.
3. **Confidence** — higher-confidence detections are more likely to be
   correct, so they should be reviewed sooner.

The output is a :class:`PriorityLevel` for each detection, which the UI
uses to sort the review list.

Configuration
-------------
* :data:`ENTITY_SENSITIVITY` in the risk models defines the base
  sensitivity weight for each entity type.
* Confidence thresholds and review state penalties are defined below.
"""

from __future__ import annotations

from typing import List

from app.domain.models.risk import (
    ENTITY_SENSITIVITY,
    PriorityItem,
    PriorityLevel,
)


class PriorityEngine:
    """
    Assigns a review priority to each detection.

    Usage::

        engine = PriorityEngine()
        priorities = engine.assign_priorities(detections, review_states)
    """

    # ── Configuration ───────────────────────────────────────────────

    # Sensitivity threshold for HIGH priority
    HIGH_SENSITIVITY_THRESHOLD: float = 0.85
    # Confidence threshold for CRITICAL priority
    HIGH_CONFIDENCE_THRESHOLD: float = 0.8

    # ── Public API ──────────────────────────────────────────────────

    def assign_priorities(
        self,
        detections: List[dict],
        review_states: dict,
    ) -> List[PriorityItem]:
        """
        Assign a priority level to each detection.

        Parameters
        ----------
        detections : list of dict
            Detections from the pipeline or review items.  Each entry
            must have ``id``, ``entity_type``, ``entity``, and
            ``confidence``.
        review_states : dict
            Mapping of ``detection_id → review_state string``.

        Returns
        -------
        list of PriorityItem
            Sorted by priority (CRITICAL first, LOW last).
        """
        items: List[PriorityItem] = []

        for det in detections:
            det_id = det.get("id", "")
            entity_type = det.get("entity_type", "CUSTOM")
            entity = det.get("entity", "")
            confidence = det.get("confidence", 0.0)
            review_state = review_states.get(det_id, "pending")

            priority, reason = self._compute_priority(
                entity_type, confidence, review_state,
            )

            items.append(PriorityItem(
                detection_id=det_id,
                entity_type=entity_type,
                entity=entity,
                confidence=confidence,
                review_state=review_state,
                priority=priority,
                reason=reason,
            ))

        # Sort: CRITICAL → HIGH → MEDIUM → LOW
        priority_order = {
            PriorityLevel.CRITICAL: 0,
            PriorityLevel.HIGH: 1,
            PriorityLevel.MEDIUM: 2,
            PriorityLevel.LOW: 3,
        }
        items.sort(key=lambda x: (priority_order.get(x.priority, 99), -x.confidence))

        return items

    # ── Internal Logic ──────────────────────────────────────────────

    def _compute_priority(
        self,
        entity_type: str,
        confidence: float,
        review_state: str,
    ) -> tuple:
        """
        Compute the priority level for a single detection.

        Priority decision tree::

            Is it CRITICAL?
              - sensitivity >= 0.85 AND unreviewed AND confidence >= 0.8
            Is it HIGH?
              - sensitivity >= 0.85 AND unreviewed
              - OR confidence >= 0.8 AND unreviewed
            Is it MEDIUM?
              - reviewed but with issues (modified, manually_added)
              - OR low sensitivity unreviewed
            Is it LOW?
              - approved, rejected, or exported
        """
        sensitivity = ENTITY_SENSITIVITY.get(entity_type.upper(), 0.5)
        is_reviewed = review_state in ("approved", "rejected", "exported")
        is_unreviewed = review_state in ("pending", "system_generated")

        # ── CRITICAL ──
        if (
            is_unreviewed
            and sensitivity >= self.HIGH_SENSITIVITY_THRESHOLD
            and confidence >= self.HIGH_CONFIDENCE_THRESHOLD
        ):
            return (
                PriorityLevel.CRITICAL,
                f"High-sensitivity {entity_type} with high confidence "
                f"({confidence:.0%}) — review immediately",
            )

        # ── HIGH ──
        if is_unreviewed and sensitivity >= self.HIGH_SENSITIVITY_THRESHOLD:
            return (
                PriorityLevel.HIGH,
                f"Sensitive entity type '{entity_type}' requires review",
            )
        if is_unreviewed and confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            return (
                PriorityLevel.HIGH,
                f"High-confidence ({confidence:.0%}) detection requires review",
            )

        # ── MEDIUM ──
        if review_state in ("modified", "manually_added"):
            return (
                PriorityLevel.MEDIUM,
                f"Detection was {review_state.replace('_', ' ')} — verify correctness",
            )
        if is_unreviewed:
            return (
                PriorityLevel.MEDIUM,
                f"Pending review (sensitivity: {sensitivity:.0%})",
            )

        # ── LOW ──
        if is_reviewed:
            return (
                PriorityLevel.LOW,
                f"Already {review_state}",
            )

        # Fallback
        return (PriorityLevel.MEDIUM, "Pending review")
