"""
Confidence Engine — normalises and calibrates detection confidence scores.

Each detector reports confidence on its own scale:
* **Regex**: always 0.99 (deterministic pattern match).
* **Rules**: always 0.75 (heuristic, may be wrong).
* **Gemini**: varies 0.60–0.95 (model-supplied, may be overconfident).

The engine does **not** inflate or reduce individual scores — it simply
ensures they are consistent, clamped to [0.0, 1.0], and that merged
detections carry the highest confidence from any contributing source.
"""

from __future__ import annotations

import logging
from typing import List

from app.core.config import settings
from app.domain.models.detection import Detection

logger = logging.getLogger(settings.APP_NAME)


class ConfidenceEngine:
    """
    Calibrate and normalise confidence values for a list of detections.

    Responsibilities
    ----------------
    1. Clamp confidence to [0.0, 1.0].
    2. Assign a human-readable status based on confidence level.
    3. Log confidence distribution for observability.
    """

    # Confidence thresholds for status assignment
    HIGH_THRESHOLD = 0.9
    MEDIUM_THRESHOLD = 0.7

    def calibrate(self, detections: List[Detection]) -> List[Detection]:
        """
        Run calibration over every detection in the list.

        Parameters
        ----------
        detections : List[Detection]
            Detections after merging and conflict resolution.

        Returns
        -------
        List[Detection]
            Same list with confidence values clamped and status set.
        """
        for det in detections:
            self._clamp(det)
            det.status = self._status_for(det.confidence)
            det.review_state = "unreviewed"

        high = sum(1 for d in detections if d.confidence >= self.HIGH_THRESHOLD)
        medium = sum(
            1
            for d in detections
            if self.MEDIUM_THRESHOLD <= d.confidence < self.HIGH_THRESHOLD
        )
        low = sum(1 for d in detections if d.confidence < self.MEDIUM_THRESHOLD)

        logger.debug(
            "Confidence calibration completed",
            extra={
                "total": len(detections),
                "high": high,
                "medium": medium,
                "low": low,
            },
        )
        return detections

    # ──────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _clamp(det: Detection) -> None:
        """Ensure confidence is within [0.0, 1.0]."""
        if det.confidence < 0.0:
            det.confidence = 0.0
        elif det.confidence > 1.0:
            det.confidence = 1.0

    @staticmethod
    def _status_for(confidence: float) -> str:
        """Map a confidence value to a human-readable processing status."""
        if confidence >= 0.9:
            return "high_confidence"
        elif confidence >= 0.7:
            return "medium_confidence"
        else:
            return "low_confidence"
