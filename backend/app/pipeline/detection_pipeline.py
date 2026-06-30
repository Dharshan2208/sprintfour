"""
Detection Pipeline — orchestrates the full PII detection flow.

Flow
----
1. Regex  ── fast, deterministic patterns
2. Rule   ── heuristic label-value and honorific patterns
3. Gemini ── AI-powered detection for ambiguous / unstructured PII
4. Merge  ── deduplicate overlapping detections
5. Resolve ── resolve type conflicts
6. Calibrate ── normalise confidence scores
7. Summarise ── build aggregate statistics
"""

from __future__ import annotations

import logging
import time
from typing import List

from app.core.config import settings
from app.detectors.gemini_detector import GeminiDetector
from app.detectors.regex_detector import RegexDetector
from app.detectors.rule_detector import RuleDetector
from app.domain.models.detection import Detection, DetectionResult, DetectionSummary
from app.pipeline.confidence_engine import ConfidenceEngine
from app.pipeline.conflict_resolver import ConflictResolver
from app.pipeline.entity_merger import EntityMerger
from app.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(settings.APP_NAME)


class DetectionPipeline:
    """
    Run the full detection pipeline on a piece of normalised text.

    Usage::

        pipeline = DetectionPipeline()
        result = pipeline.run("some text", doc_id="abc-123")
    """

    def __init__(
        self,
        regex_detector: RegexDetector | None = None,
        rule_detector: RuleDetector | None = None,
        gemini_detector: GeminiDetector | None = None,
        merger: EntityMerger | None = None,
        resolver: ConflictResolver | None = None,
        confidence_engine: ConfidenceEngine | None = None,
    ):
        # Default to production instances; override for testing.
        self._regex = regex_detector or RegexDetector()
        self._rule = rule_detector or RuleDetector()
        self._gemini = gemini_detector or GeminiDetector(provider=GeminiProvider())
        self._merger = merger or EntityMerger()
        self._resolver = resolver or ConflictResolver()
        self._confidence = confidence_engine or ConfidenceEngine()

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────

    def run(self, text: str, document_id: str) -> DetectionResult:
        """
        Execute the full detection pipeline.

        Parameters
        ----------
        text : str
            Normalised document text.
        document_id : str
            The document's unique ID (for the result).

        Returns
        -------
        DetectionResult
            All detections, summary, and processing time.
        """
        start = time.perf_counter()

        # ── Stage 1: Regex ──────────────────────────────────────
        logger.info("Detection pipeline: regex stage started")
        regex_results = self._regex.detect(text)
        logger.info(
            "Regex stage finished",
            extra={"match_count": len(regex_results)},
        )

        # ── Stage 2: Rule ───────────────────────────────────────
        logger.info("Detection pipeline: rule stage started")
        rule_results = self._rule.detect(text)
        logger.info(
            "Rule stage finished",
            extra={"match_count": len(rule_results)},
        )

        # ── Stage 3: Gemini ─────────────────────────────────────
        logger.info("Detection pipeline: Gemini stage started")
        gemini_results = self._gemini.detect(text)
        logger.info(
            "Gemini stage finished",
            extra={"match_count": len(gemini_results)},
        )

        # ── Stage 4: Merge ──────────────────────────────────────
        all_detections: List[Detection] = []
        all_detections.extend(regex_results)
        all_detections.extend(rule_results)
        all_detections.extend(gemini_results)

        logger.info(
            "Merge started",
            extra={"input_count": len(all_detections)},
        )
        merged = self._merger.merge(all_detections)
        logger.info(
            "Merge finished",
            extra={"output_count": len(merged)},
        )

        # ── Stage 5: Conflict resolution ────────────────────────
        resolved = self._resolver.resolve(merged)

        # ── Stage 6: Confidence calibration ─────────────────────
        calibrated = self._confidence.calibrate(resolved)

        # ── Stage 7: Summary ────────────────────────────────────
        elapsed_ms = (time.perf_counter() - start) * 1000
        summary = self._build_summary(calibrated)

        logger.info(
            "Detection pipeline finished",
            extra={
                "total_detections": summary.total_count,
                "processing_time_ms": round(elapsed_ms, 2),
            },
        )

        return DetectionResult(
            document_id=document_id,
            detections=calibrated,
            summary=summary,
            processing_time_ms=round(elapsed_ms, 2),
        )

    # ──────────────────────────────────────────────────────────────
    # Summary builder
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _build_summary(detections: List[Detection]) -> DetectionSummary:
        """Aggregate statistics from the final detection list."""
        per_type: dict = {}
        per_source: dict = {}
        high = medium = low = 0

        for det in detections:
            # Per-type count
            per_type[det.entity_type] = per_type.get(det.entity_type, 0) + 1

            # Per-source count (a detection may have multiple sources;
            # we count each source independently)
            for src in det.sources:
                per_source[src] = per_source.get(src, 0) + 1

            # Confidence buckets
            if det.confidence >= 0.9:
                high += 1
            elif det.confidence >= 0.7:
                medium += 1
            else:
                low += 1

        return DetectionSummary(
            total_count=len(detections),
            per_type=per_type,
            per_source=per_source,
            high_confidence_count=high,
            medium_confidence_count=medium,
            low_confidence_count=low,
        )
