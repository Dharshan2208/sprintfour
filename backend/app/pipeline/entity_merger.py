"""
Entity Merger — deduplicates and merges overlapping detections.

When multiple detectors (regex, rule, Gemini) flag the same or
overlapping spans of text, the merger combines them into a single
``Detection`` that carries the best attributes from each source.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

from app.core.config import settings
from app.domain.models.detection import Detection

logger = logging.getLogger(settings.APP_NAME)


class EntityMerger:
    """
    Merge overlapping and duplicate detections into a single set.

    Strategy
    --------
    1. Sort all detections by ``(start_offset, end_offset)``.
    2. Group detections that overlap (share any character range).
    3. Within each group:
       a. If all have the same ``entity_type`` → keep the one with the
          highest confidence, merge the ``sources`` lists.
       b. If types differ → keep **all** of them; the ``ConflictResolver``
          will decide what to do next.
    4. Detections that do not overlap with any other are kept as‑is.
    """

    def merge(self, detections: List[Detection]) -> List[Detection]:
        """
        Deduplicate and merge a list of detections.

        Parameters
        ----------
        detections : List[Detection]
            Raw detections from all detectors in the pipeline.

        Returns
        -------
        List[Detection]
            Merged list with duplicates removed.
        """
        if not detections:
            return []

        # 1. Sort by start_offset, then end_offset (longer spans first)
        sorted_dets = sorted(detections, key=lambda d: (d.start_offset, -d.end_offset))

        # 2. Group overlapping detections
        groups: List[List[Detection]] = []
        current_group: List[Detection] = [sorted_dets[0]]

        for det in sorted_dets[1:]:
            last_in_group = current_group[-1]
            if self._overlaps(det, last_in_group):
                current_group.append(det)
            else:
                groups.append(current_group)
                current_group = [det]
        groups.append(current_group)

        # 3. Merge each group
        merged: List[Detection] = []
        for group in groups:
            merged.extend(self._merge_group(group))

        logger.debug(
            "Entity merger completed",
            extra={"input_count": len(detections), "output_count": len(merged)},
        )
        return merged

    # ──────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _overlaps(a: Detection, b: Detection) -> bool:
        """Return True if two detections share any character range."""
        return a.start_offset < b.end_offset and b.start_offset < a.end_offset

    @staticmethod
    def _merge_group(group: List[Detection]) -> List[Detection]:
        """
        Merge a group of overlapping detections.

        - Same type → single merged detection.
        - Different type → keep all (conflict resolver handles it).
        """
        # Group by type within the overlap group
        by_type: Dict[str, List[Detection]] = {}
        for det in group:
            by_type.setdefault(det.entity_type, []).append(det)

        result: List[Detection] = []
        for type_key, same_type_dets in by_type.items():
            if len(same_type_dets) == 1:
                result.append(same_type_dets[0])
            else:
                result.append(EntityMerger._merge_same_type(same_type_dets))
        return result

    @staticmethod
    def _merge_same_type(detections: List[Detection]) -> Detection:
        """
        Merge multiple detections of the same entity type.

        Takes the highest‑confidence detection as the base and
        aggregates source lists.
        """
        best = max(detections, key=lambda d: d.confidence)

        all_sources: List[str] = []
        seen_sources: set = set()
        for det in detections:
            for src in det.sources:
                if src not in seen_sources:
                    all_sources.append(src)
                    seen_sources.add(src)

        return Detection(
            id=best.id,
            entity=best.entity,
            entity_type=best.entity_type,
            confidence=best.confidence,
            reason=best.reason,
            sources=all_sources,
            start_offset=best.start_offset,
            end_offset=best.end_offset,
            page=best.page,
            line=best.line,
            status=best.status,
            review_state=best.review_state,
        )
