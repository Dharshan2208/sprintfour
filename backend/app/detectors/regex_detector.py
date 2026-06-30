"""
Deterministic PII detection using compiled regular expressions.

Every pattern is hand‑crafted for a specific entity type.  Patterns
are kept simple and precise — we prefer false negatives (missed PII
that Gemini might catch) over false positives (annoying the reviewer).
"""

from __future__ import annotations

import logging
import re
from typing import List, Tuple

from app.core.config import settings
from app.detectors.base import BaseDetector
from app.detectors.entity_types import EntityType
from app.domain.models.detection import Detection

logger = logging.getLogger(settings.APP_NAME)

# Type alias for a pattern definition
_RegexPattern = Tuple[re.Pattern, str, str]


class RegexDetector(BaseDetector):
    """
    Scans text with a battery of compiled regex patterns.

    Usage::

        detector = RegexDetector()
        results = detector.detect("Contact me at john@example.com")
    """

    name = "regex"

    # ── Pattern list ──────────────────────────────────────────────
    # Each entry: (compiled_regex, entity_type_string, reason_prefix)
    # Order does not affect correctness, but more-specific patterns
    # should come before less-specific ones for readability.
    _PATTERNS: List[_RegexPattern] = [
        # ── Email ──────────────────────────────────────────────
        (
            re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
            EntityType.EMAIL,
            "Matched standard email format",
        ),
        # ── URL ────────────────────────────────────────────────
        (
            re.compile(r"https?://(?:www\.)?[^\s<>\"']+?(?:\.(?:com|org|net|gov|in|io|edu|co|app|dev))[^\s<>\"']*"),
            EntityType.URL,
            "Matched HTTP/HTTPS URL",
        ),
        # ── IPv4 ───────────────────────────────────────────────
        (
            re.compile(
                r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
                r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
            ),
            EntityType.IP_ADDRESS,
            "Matched IPv4 address",
        ),
        # ── IPv6 (simplified – covers common forms) ────────────
        (
            re.compile(
                r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"
                r"|\b(?:[0-9a-fA-F]{1,4}:){1,7}:"
                r"|\b(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}\b"
            ),
            EntityType.IP_ADDRESS,
            "Matched IPv6 address",
        ),
        # ── Indian PAN ─────────────────────────────────────────
        (
            re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
            EntityType.PAN,
            "Matched PAN card format",
        ),
        # ── Aadhaar (12-digit, optional spaces/hyphens) ────────
        # The negative lookahead ``(?![-\s]?\d)`` prevents matching
        # the first 12 digits of a credit card (e.g. "4111-1111-1111-1111").
        (
            re.compile(r"\b[2-9]\d{3}[-\s]?\d{4}[-\s]?\d{4}(?![-\s]?\d)\b"),
            EntityType.AADHAAR,
            "Matched Aadhaar number format",
        ),
        # ── IFSC (11 chars: 4 letters + 0 + 6 alphanum) ───────
        (
            re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
            EntityType.IFSC,
            "Matched IFSC code format",
        ),
        # ── UPI ID ─────────────────────────────────────────────
        # UPI handles have the form ``user@provider`` where the
        # provider is a short alphanumeric string (no dots), which
        # distinguishes them from email addresses.
        (
            re.compile(r"[\w.-]+@[A-Za-z]\w{2,10}"),
            EntityType.UPI_ID,
            "Matched UPI ID format",
        ),
        # ── Credit Card (major networks, with optional separators) ─
        (
            re.compile(
                r"\b(?:"
                r"4[0-9]{3}[- ]?[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}"   # Visa (16-digit with optional dashes/spaces)
                r"|4[0-9]{12}(?:[0-9]{3})?"                            # Visa (contiguous 13/16-digit)
                r"|5[1-5][0-9]{14}"                                     # MasterCard
                r"|3[47][0-9]{13}"                                      # Amex
                r"|6(?:011|5[0-9]{2})[0-9]{12}"                        # Discover
                r"|(?:2131|1800|35\d{3})\d{11}"                         # JCB
                r")\b"
            ),
            EntityType.CREDIT_CARD,
            "Matched credit card number pattern",
        ),
        # ── Bank Account (11-18 digits, heuristic) ─────────────
        # Minimum 11 digits to avoid matching 10-digit phone numbers.
        # Indian bank accounts are typically 11-16 digits.
        (
            re.compile(r"\b\d{11,18}\b"),
            EntityType.BANK_ACCOUNT,
            "Matched numeric sequence matching bank account length",
        ),
        # ── Indian Passport ────────────────────────────────────
        (
            re.compile(r"\b[A-Z][0-9]{7}\b"),
            EntityType.PASSPORT,
            "Matched passport number format (1 letter + 7 digits)",
        ),
        # ── Indian Voter ID (EPIC) ─────────────────────────────
        (
            re.compile(r"\b[A-Z]{3}[0-9]{7}\b"),
            EntityType.VOTER_ID,
            "Matched EPIC/Voter ID format",
        ),
        # ── Indian Driving License ─────────────────────────────
        (
            re.compile(r"\b[A-Z]{2}-?\d{2}-?\d{4,7}\b"),
            EntityType.DRIVING_LICENSE,
            "Matched Driving License format",
        ),
        # ── Indian Phone (mobile, landline with STD) ───────────
        (
            re.compile(r"\b(?:\+?91[-\s]?)?[6-9]\d{9}\b"),
            EntityType.PHONE,
            "Matched Indian mobile number",
        ),
        # ── International Phone (requires leading +) ───────────
        (
            re.compile(r"\b\+\d{1,3}[-\s]?\(?\d{2,4}\)?[-\s]?\d{3,4}[-\s]?\d{4}\b"),
            EntityType.PHONE,
            "Matched international phone number",
        ),
        # ── MAC Address ────────────────────────────────────────
        (
            re.compile(r"\b(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\b"),
            EntityType.MAC_ADDRESS,
            "Matched MAC address format",
        ),
    ]

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────

    def detect(self, text: str) -> List[Detection]:
        results: List[Detection] = []

        for pattern, entity_type, reason_prefix in self._PATTERNS:
            try:
                for match in pattern.finditer(text):
                    detection = self._build_detection(match, entity_type, reason_prefix)
                    results.append(detection)
            except Exception as exc:
                # Log and skip a misbehaving pattern (shouldn't happen
                # with compiled regex, but defensive coding).
                logger.warning(
                    "Regex pattern failed",
                    extra={
                        "entity_type": entity_type,
                        "error": str(exc),
                    },
                )
                continue

        logger.info(
            "Regex detection completed",
            extra={"match_count": len(results)},
        )
        return results

    # ──────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _build_detection(
        match: re.Match,
        entity_type: str,
        reason_prefix: str,
    ) -> Detection:
        return Detection(
            entity=match.group(),
            entity_type=entity_type,
            confidence=0.99,
            reason=f"{reason_prefix}: '{match.group()[:50]}'",
            sources=["regex"],
            start_offset=match.start(),
            end_offset=match.end(),
        )
