"""
Gemini-powered PII detector.

Uses the ``GeminiProvider`` to analyse document text and identify
sensitive entities that regex and rule detectors cannot reliably catch
(e.g. person names, organisation names, addresses).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.exceptions import GeminiException
from app.detectors.base import BaseDetector
from app.detectors.entity_types import EntityType
from app.domain.models.detection import Detection
from app.providers.base_provider import ProviderMessage
from app.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(settings.APP_NAME)

# ── Number of times to retry when the model returns invalid JSON ──
_MAX_PARSE_RETRIES = 2

# ── Maximum characters sent to Gemini per call ───────────────────
# Gemini 2.0 Flash has a large context window, but we limit input
# to keep latency predictable.  For documents longer than this, the
# text is truncated (a future enhancement could split into chunks).
_MAX_INPUT_CHARS = 50_000


class GeminiDetector(BaseDetector):
    """
    AI-powered PII detector backed by a Gemini model.

    Usage::

        detector = GeminiDetector(provider=GeminiProvider())
        results = detector.detect("Dr. Rajesh Kumar lives in Mumbai.")
    """

    name = "gemini"

    def __init__(self, provider: Optional[GeminiProvider] = None):
        self._provider = provider or GeminiProvider()

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────

    def detect(self, text: str) -> List[Detection]:
        if not text.strip():
            return []

        # Truncate if necessary
        input_text = text[: _MAX_INPUT_CHARS]
        if len(text) > _MAX_INPUT_CHARS:
            logger.warning(
                "Text truncated for Gemini detection",
                extra={
                    "original_length": len(text),
                    "truncated_length": _MAX_INPUT_CHARS,
                },
            )

        # ── Build the prompt ──────────────────────────────────
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(input_text)

        # ── Call Gemini ───────────────────────────────────────
        try:
            raw_response = self._provider.generate(
                messages=[
                    ProviderMessage(role="user", content=system_prompt + "\n\n" + user_prompt),
                ],
                temperature=0.1,  # Low temperature for deterministic output
            )
        except GeminiException as exc:
            logger.warning(
                "Gemini detection failed, returning empty results",
                extra={"error": str(exc)},
            )
            return []

        # ── Parse & validate ──────────────────────────────────
        detections = self._parse_response(raw_response, input_text)

        logger.info(
            "Gemini detection completed",
            extra={"match_count": len(detections)},
        )
        return detections

    # ──────────────────────────────────────────────────────────────
    # Prompt construction
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _build_system_prompt() -> str:
        return (
            "You are a PII (Personally Identifiable Information) detection system. "
            "Your task is to identify all PII entities in the provided text.\n\n"
            "RULES:\n"
            "1. Return ONLY valid JSON — no markdown, no code fences, no explanations.\n"
            "2. Every entity must be an EXACT substring of the input text.\n"
            "3. If uncertain, assign a lower confidence score (0.0–1.0).\n"
            "4. Do NOT invent or hallucinate entities.\n"
            "5. Include the surrounding context (±30 characters) for each detection.\n\n"
            "SUPPORTED ENTITY TYPES:\n"
            "- PERSON: Individual names\n"
            "- EMAIL: Email addresses\n"
            "- PHONE: Phone numbers\n"
            "- ADDRESS: Physical or postal addresses\n"
            "- ORGANIZATION: Company, institution, or organisation names\n"
            "- DATE_OF_BIRTH: Birth dates (not generic dates)\n"
            "- AADHAAR: Indian Aadhaar numbers\n"
            "- PAN: Indian PAN card numbers\n"
            "- PASSPORT: Passport numbers\n"
            "- BANK_ACCOUNT: Bank account numbers\n"
            "- CREDIT_CARD: Credit/debit card numbers\n"
            "- IFSC: Bank IFSC codes\n"
            "- UPI_ID: UPI payment IDs\n"
            "- URL: Web URLs\n"
            "- IP_ADDRESS: IPv4 or IPv6 addresses\n"
            "- AGE: Age values\n"
            "- GENDER: Gender information\n\n"
            "OUTPUT FORMAT (JSON array):\n"
            "[\n"
            '  {\n'
            '    "entity": "<exact substring>",\n'
            '    "type": "<ENTITY_TYPE>",\n'
            '    "confidence": <0.0–1.0>,\n'
            '    "reason": "<why this is PII>",\n'
            '    "start_offset": <integer>,\n'
            '    "end_offset": <integer>,\n'
            '    "surrounding_context": "<±30 chars around the entity>"\n'
            "  }\n"
            "]\n\n"
            "Return an empty array [] if no PII is found."
        )

    @staticmethod
    def _build_user_prompt(text: str) -> str:
        return f"TEXT:\n```\n{text}\n```\n\nAnalyse the above text and return all PII entities as a JSON array."

    # ──────────────────────────────────────────────────────────────
    # Response parsing
    # ──────────────────────────────────────────────────────────────

    def _parse_response(self, raw: str, original_text: str) -> List[Detection]:
        """Parse Gemini's JSON response and validate every detection."""
        clean = self._clean_json(raw)
        if not clean:
            logger.warning("Gemini returned empty response after cleaning")
            return []

        # Attempt to parse as JSON
        for attempt in range(_MAX_PARSE_RETRIES):
            try:
                parsed = json.loads(clean)
                if isinstance(parsed, dict):
                    # Sometimes the model wraps the array in an object
                    parsed = parsed.get("detections", parsed.get("entities", []))
                if not isinstance(parsed, list):
                    logger.warning(
                        "Gemini response is not a list",
                        extra={"type": type(parsed).__name__},
                    )
                    return []
                break
            except (json.JSONDecodeError, TypeError) as exc:
                logger.warning(
                    "Failed to parse Gemini JSON",
                    extra={"attempt": attempt + 1, "error": str(exc)},
                )
                if attempt < _MAX_PARSE_RETRIES - 1:
                    # Try to extract JSON from the response
                    clean = self._extract_json_snippet(raw)
                else:
                    return []

        # Validate each detection
        detections: List[Detection] = []
        for item in parsed:
            detection = self._validate_item(item, original_text)
            if detection is not None:
                detections.append(detection)

        return detections

    # ──────────────────────────────────────────────────────────────
    # Validation helpers
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _validate_item(item: Any, original_text: str) -> Optional[Detection]:
        """Validate a single parsed JSON object and return a Detection or None."""
        if not isinstance(item, dict):
            return None

        entity: Optional[str] = item.get("entity")
        entity_type: Optional[str] = item.get("type")
        confidence: Optional[float] = item.get("confidence")
        reason: Optional[str] = item.get("reason")
        start: Optional[int] = item.get("start_offset")
        end: Optional[int] = item.get("end_offset")

        # Required fields check
        if not all([entity, entity_type, reason is not None, start is not None, end is not None]):
            return None

        # Entity must be an exact substring
        if entity not in original_text:
            logger.debug(
                "Gemini hallucinated entity, dropping",
                extra={"entity": entity},
            )
            return None

        # Confidence must be valid
        if not isinstance(confidence, (int, float)):
            confidence = 0.7  # default
        confidence = max(0.0, min(1.0, float(confidence)))

        # Offsets must be valid — verify they point to the same substring
        text_len = len(original_text)
        if start < 0 or end > text_len or start >= end:
            # Try to find the entity in the text
            found = original_text.find(entity)
            if found != -1:
                start = found
                end = found + len(entity)
            else:
                return None

        # Verify the offsets match the entity string
        if original_text[start:end] != entity:
            # Off mismatch — try a correction
            found = original_text.find(entity)
            if found != -1:
                start = found
                end = found + len(entity)
            else:
                return None

        # Validate entity_type is in our supported list
        valid_types = {e.value for e in EntityType}
        if entity_type.upper() not in valid_types:
            logger.debug(
                "Unknown entity type from Gemini, dropping",
                extra={"type": entity_type},
            )
            return None

        return Detection(
            entity=entity,
            entity_type=entity_type.upper(),
            confidence=confidence,
            reason=reason or "Detected by Gemini AI",
            sources=["gemini"],
            start_offset=start,
            end_offset=end,
        )

    # ──────────────────────────────────────────────────────────────
    # Text cleaning utilities
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _clean_json(raw: str) -> str:
        """Strip markdown fences and leading/trailing whitespace."""
        raw = raw.strip()
        # Remove markdown code blocks
        if raw.startswith("```"):
            # Find the first newline after the opening ```
            first_nl = raw.find("\n")
            if first_nl != -1:
                raw = raw[first_nl + 1 :]
            # Remove trailing ```
            if raw.endswith("```"):
                raw = raw[:-3].rstrip()
            elif "```" in raw:
                raw = raw[: raw.rfind("```")].rstrip()
        return raw.strip()

    @staticmethod
    def _extract_json_snippet(text: str) -> str:
        """Try to extract a JSON array or object from arbitrary text."""
        # Find the first [ or {
        start = -1
        for i, ch in enumerate(text):
            if ch in ("[", "{"):
                start = i
                break
        if start == -1:
            return ""

        # Find matching closing bracket (naive — works for simple cases)
        bracket_map = {"[": "]", "{": "}"}
        opening = text[start]
        closing = bracket_map[opening]
        depth = 0
        end = -1
        for i in range(start, len(text)):
            if text[i] == opening:
                depth += 1
            elif text[i] == closing:
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        if end != -1:
            return text[start:end]
        return text[start:]
