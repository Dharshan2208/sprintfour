"""
Risk Service — evaluates how safe a document is for export.

The service computes a risk score based on:

1. **Review state** — unreviewed detections increase risk.
2. **Entity sensitivity** — government IDs and financial data carry
   more weight than URLs or organisation names.
3. **Confidence** — high-confidence unverified detections increase risk
   more than low-confidence ones (because a high-confidence false
   positive is more likely to be wrong, and a high-confidence true
   positive is more important to verify).
4. **Review progress** — the proportion of items that have been reviewed.

The output is a :class:`RiskReport` with:
* An ``overall_score`` (0.0 = safe, 1.0 = high risk).
* Per-item priority assignments.
* Human-readable warnings and recommendations.
* A boolean ``export_ready`` flag.

Usage::

    service = RiskService()
    report = service.assess_document(
        document_id="doc-123",
        detections=[...],
        review_states={"det-1": "approved", ...},
    )
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.core.config import settings
from app.core.exceptions import RiskAnalysisException
from app.domain.models.risk import (
    ENTITY_SENSITIVITY,
    PriorityItem,
    PriorityLevel,
    ReviewProgress,
    RiskReport,
)
from app.services.priority_engine import PriorityEngine
from app.store.review_store import review_store

logger = logging.getLogger(settings.APP_NAME)


class RiskService:
    """
    Assesses the risk level of a document based on review state and
    entity sensitivity.

    The risk score is computed as a weighted combination of:
    - Unreviewed ratio (how many items haven't been reviewed)
    - Sensitivity-weighted unreviewed density
    - Confidence-weighted unreviewed density
    """

    def __init__(
        self,
        priority_engine: Optional[PriorityEngine] = None,
        export_ready_threshold: float = 0.3,
    ):
        self._priority_engine = priority_engine or PriorityEngine()
        self._export_ready_threshold = export_ready_threshold

    # ── Public API ──────────────────────────────────────────────────

    def assess_document(
        self,
        document_id: str,
        detections: List[dict],
        review_states: Optional[Dict[str, str]] = None,
    ) -> RiskReport:
        """
        Perform a full risk assessment for a document.

        Parameters
        ----------
        document_id : str
            The document to assess.
        detections : list of dict
            All detections for the document (from the pipeline or
            review items).  Each must have ``id``, ``entity_type``,
            ``entity``, ``confidence``.
        review_states : dict, optional
            Override review states.  If not provided, states are read
            from the :class:`InMemoryReviewStore`.

        Returns
        -------
        RiskReport
            The complete risk assessment.

        Raises
        ------
        RiskAnalysisException
            If the assessment fails.
        """
        try:
            # 1. Resolve review states
            if review_states is None:
                raw_states = review_store.get_all_states(document_id)
                # Convert to string values
                review_states = {
                    k: v.value if hasattr(v, "value") else str(v)
                    for k, v in raw_states.items()
                }

            # 2. Compute review progress
            progress = self._compute_review_progress(detections, review_states)

            # 3. Assign priorities
            priority_items = self._priority_engine.assign_priorities(
                detections, review_states,
            )

            # 4. Compute overall risk score
            overall_score = self._compute_risk_score(
                detections, review_states, progress,
            )

            # 5. Separate critical items
            critical_items = [
                item for item in priority_items
                if item.priority == PriorityLevel.CRITICAL
            ]

            # 6. Generate warnings and recommendations
            warnings = self._generate_warnings(
                progress, critical_items, overall_score,
            )
            recommendations = self._generate_recommendations(
                warnings, progress, critical_items,
            )

            # 7. Build report
            report = RiskReport(
                document_id=document_id,
                overall_score=round(overall_score, 4),
                review_progress=progress,
                priority_items=priority_items,
                critical_items=critical_items,
                warnings=warnings,
                recommendations=recommendations,
                export_ready=overall_score < self._export_ready_threshold,
                export_ready_threshold=self._export_ready_threshold,
            )

            logger.info(
                "Risk assessment completed",
                extra={
                    "document_id": document_id,
                    "overall_score": overall_score,
                    "export_ready": report.export_ready,
                    "total_items": progress.total_items,
                    "reviewed_count": progress.reviewed_count,
                },
            )

            return report

        except Exception as exc:
            raise RiskAnalysisException(
                message=f"Risk assessment failed: {exc}",
            ) from exc

    # ── Internal: Risk Score Computation ────────────────────────────

    def _compute_risk_score(
        self,
        detections: List[dict],
        review_states: Dict[str, str],
        progress: ReviewProgress,
    ) -> float:
        """
        Compute the overall risk score.

        Formula::

            unreviewed_ratio       = pending / total
            sensitivity_risk       = avg(sensitivity) of unreviewed
            confidence_risk        = avg(confidence) of unreviewed
            overall_score          = 0.5 * unreviewed_ratio
                                   + 0.3 * sensitivity_risk
                                   + 0.2 * confidence_risk

        If there are no detections, the score is 0.0 (safe by default).
        """
        if not detections or progress.total_items == 0:
            return 0.0

        # Collect unreviewed items
        unreviewed_states = {"pending", "system_generated"}
        unreviewed = [
            det for det in detections
            if review_states.get(det.get("id", ""), "pending") in unreviewed_states
        ]

        if not unreviewed:
            return 0.0  # All reviewed → safe

        # Sensitivity risk: average sensitivity of unreviewed items
        sensitivity_sum = sum(
            ENTITY_SENSITIVITY.get(det.get("entity_type", "CUSTOM").upper(), 0.5)
            for det in unreviewed
        )
        sensitivity_risk = sensitivity_sum / len(unreviewed)

        # Confidence risk: average confidence of unreviewed items
        confidence_sum = sum(
            det.get("confidence", 0.5) for det in unreviewed
        )
        confidence_risk = confidence_sum / len(unreviewed)

        # Weighted combination
        score = (
            0.5 * (progress.pending_count / progress.total_items)
            + 0.3 * sensitivity_risk
            + 0.2 * confidence_risk
        )

        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))

    # ── Internal: Review Progress ───────────────────────────────────

    @staticmethod
    def _compute_review_progress(
        detections: List[dict],
        review_states: Dict[str, str],
    ) -> ReviewProgress:
        """
        Compute review completion metrics.

        "Reviewed" means the state is one of: approved, rejected, modified.
        """
        total = len(detections)
        reviewed_states = {"approved", "rejected", "modified", "exported"}
        reviewed = sum(
            1 for det in detections
            if review_states.get(det.get("id", ""), "pending") in reviewed_states
        )
        pending = total - reviewed

        # Approved count for approval rate
        approved = sum(
            1 for det in detections
            if review_states.get(det.get("id", ""), "pending") == "approved"
        )

        approval_rate = approved / reviewed if reviewed > 0 else 0.0
        review_percentage = (reviewed / total * 100.0) if total > 0 else 100.0

        return ReviewProgress(
            total_items=total,
            reviewed_count=reviewed,
            pending_count=pending,
            approval_rate=round(approval_rate, 4),
            review_percentage=round(review_percentage, 2),
        )

    # ── Internal: Warnings & Recommendations ────────────────────────

    @staticmethod
    def _generate_warnings(
        progress: ReviewProgress,
        critical_items: List[PriorityItem],
        overall_score: float,
    ) -> List[str]:
        """Generate human-readable warnings based on the risk state."""
        warnings: List[str] = []

        if progress.pending_count > 0:
            warnings.append(
                f"{progress.pending_count} of {progress.total_items} detections "
                "have not been reviewed yet."
            )

        if critical_items:
            warnings.append(
                f"{len(critical_items)} critical item(s) require immediate review "
                f"before the document can be safely exported."
            )

        if overall_score > 0.7:
            warnings.append(
                "Overall risk score is very high. "
                "Review all critical and high-priority items before export."
            )

        if progress.approval_rate < 0.5 and progress.reviewed_count > 0:
            warnings.append(
                "More than half of reviewed items were rejected. "
                "The detection pipeline may have a high false-positive rate."
            )

        return warnings

    @staticmethod
    def _generate_recommendations(
        warnings: List[str],
        progress: ReviewProgress,
        critical_items: List[PriorityItem],
    ) -> List[str]:
        """Generate actionable recommendations to reduce risk."""
        recommendations: List[str] = []

        if progress.pending_count > 0:
            recommendations.append(
                f"Review the remaining {progress.pending_count} pending "
                "detection(s) to reduce risk."
            )

        if critical_items:
            recommendations.append(
                "Focus on critical items first: "
                + ", ".join(
                    f"{item.entity_type} ('{item.entity}')"
                    for item in critical_items[:5]
                )
                + ("..." if len(critical_items) > 5 else "")
            )

        if progress.review_percentage < 100.0:
            recommendations.append(
                "Aim for 100% review coverage before export."
            )

        if recommendations:
            recommendations.append(
                "Run a risk re-assessment after completing reviews to "
                "confirm the document is safe for export."
            )

        return recommendations
