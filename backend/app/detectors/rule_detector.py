"""
Heuristic rule-based PII detector.

Catches patterns that structured regex cannot reliably handle, such as
person names following honorifics and labelled information fields.
"""

from __future__ import annotations

import logging
import re
from typing import List, Match, Optional

from app.core.config import settings
from app.detectors.base import BaseDetector
from app.detectors.entity_types import EntityType
from app.domain.models.detection import Detection

logger = logging.getLogger(settings.APP_NAME)


class RuleDetector(BaseDetector):
    """
    Heuristic PII detection using contextual rules.

    Two categories of rule:

    1. **Honorific-based** – ``Dr. Rajesh Kumar`` → ``PERSON``
    2. **Label-value** — ``Date of Birth: 15/08/1947`` → ``DATE_OF_BIRTH``
    """

    name = "rule"

    # ── Honorifics / Titles ───────────────────────────────────────
    # A capitalized word following one of these is likely a person name.
    _HONORIFICS_PATTERN = re.compile(
        r"(?:\b(?:"
        r"Mr|Mrs|Ms|Miss|Dr|Prof|Prof\.|Shri|Smt|Sir|Madam|Er|Eng|Col|Capt|Maj|Gen|Sri|Smt|Kum"
        r")\.?[ \t]+)([A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)*)",
    )

    # ── Label → PII mappings ──────────────────────────────────────
    # These patterns look for a known label followed by a value.
    # The label itself is not flagged; the value is.
    _LABEL_RULES: List[tuple[re.Pattern, str]] = [
        # Date of Birth
        (
            re.compile(
                r"(?i)(?:date\s*of\s*birth|dob|birth\s*date|born\s*on)"
                r"\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
            ),
            EntityType.DATE_OF_BIRTH,
        ),
        # Phone / Mobile / Contact
        (
            re.compile(
                r"(?i)(?:phone|mobile|contact|telephone|cell|whatsapp)"
                r"\s*[:\-]?\s*(\+?\d[\d\s\-()]{7,18}\d)"
            ),
            EntityType.PHONE,
        ),
        # Email
        (
            re.compile(
                r"(?i)(?:email|e-mail|mail|email id|e-mail id)"
                r"\s*[:\-]?\s*([\w.+-]+@[\w-]+(?:\.[\w-]+)+)"
            ),
            EntityType.EMAIL,
        ),
        # PAN
        (
            re.compile(
                r"(?i)(?:pan|pan\s*(?:no|number|card|#))\s*[:\-]?\s*"
                r"([A-Z]{5}[0-9]{4}[A-Z])"
            ),
            EntityType.PAN,
        ),
        # Aadhaar
        (
            re.compile(
                r"(?i)(?:aadhaar|aadhar|uid|aadhaar\s*(?:no|number|#))"
                r"\s*[:\-]?\s*(\d{4}\s?\d{4}\s?\d{4})"
            ),
            EntityType.AADHAAR,
        ),
        # Passport
        (
            re.compile(
                r"(?i)(?:passport|passport\s*(?:no|number|#))"
                r"\s*[:\-]?\s*([A-Z][0-9]{7})"
            ),
            EntityType.PASSPORT,
        ),
        # Bank Account
        (
            re.compile(
                r"(?i)(?:account\s*(?:no|number|#|\.)|a/c\s*(?:no|#)|bank\s*account)"
                r"\s*[:\-]?\s*(\d{9,18})"
            ),
            EntityType.BANK_ACCOUNT,
        ),
        # IFSC
        (
            re.compile(
                r"(?i)(?:ifsc|ifsc\s*(?:code|#))"
                r"\s*[:\-]?\s*([A-Z]{4}0[A-Z0-9]{6})"
            ),
            EntityType.IFSC,
        ),
    ]

    # ── Salary / Financial figures (common in HR documents) ───────
    _SALARY_PATTERN = re.compile(
        r"(?i)(?:salary|ctc|income|stipend|pay\s*scale)"
        r"\s*[:\-]?\s*(₹|Rs\.?|INR)?\s*([\d,]+(?:\.\d{1,2})?)"
    )

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────

    def detect(self, text: str) -> List[Detection]:
        results: List[Detection] = []

        # 1. Honorific → Person name
        for match in self._HONORIFICS_PATTERN.finditer(text):
            name = match.group(1).strip()
            # Sanity check: the name shouldn't be ridiculously long
            if len(name) < 100:
                results.append(
                    Detection(
                        entity=name,
                        entity_type=EntityType.PERSON,
                        confidence=0.75,
                        reason=f"Name following honorific '{match.group(0).split()[0]}'",
                        sources=["rule"],
                        start_offset=match.start(1),
                        end_offset=match.end(1),
                    )
                )

        # 2. Label → Value patterns
        for label_pattern, entity_type in self._LABEL_RULES:
            for match in label_pattern.finditer(text):
                value = match.group(1).strip()
                results.append(
                    Detection(
                        entity=value,
                        entity_type=entity_type,
                        confidence=0.75,
                        reason=f"Value following label '{match.group(0).split(':')[0].strip()}'",
                        sources=["rule"],
                        start_offset=match.start(1),
                        end_offset=match.end(1),
                    )
                )

        # Note: Salary detection is intentionally excluded from the
        # primary pipeline because salary is not PII in all jurisdictions.
        # It can be enabled via configuration in a future iteration.

        logger.info(
            "Rule detection completed",
            extra={"match_count": len(results)},
        )
        return results
