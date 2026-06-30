"""
Google Gemini provider implementation.

Wraps the ``google-generativeai`` SDK behind the ``BaseProvider``
interface so that the rest of the system never depends on the SDK
directly.

Features
--------
* Retry with exponential backoff (configurable via settings).
* Timeout handling.
* Clear exception wrapping — never lets raw SDK exceptions propagate.
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional

from app.core.config import settings
from app.core.exceptions import GeminiException
from app.providers.base_provider import BaseProvider, ProviderMessage

logger = logging.getLogger(settings.APP_NAME)


class GeminiProvider(BaseProvider):
    """
    Concrete provider for Google Gemini models.

    Uses the model name from ``settings.GEMINI_MODEL`` (defaults to
    ``gemini-2.0-flash-001``).

    The provider initialises lazily — the client is not created until
    the first call to ``generate()``.  This allows the application to
    start even when ``GEMINI_API_KEY`` is not yet configured; calls
    will fail with a clear ``GeminiException`` at runtime.
    """

    provider_name = "gemini"

    def __init__(self) -> None:
        self._model_name = settings.GEMINI_MODEL
        self._max_retries = settings.GEMINI_MAX_RETRIES
        self._timeout = settings.GEMINI_TIMEOUT_SECONDS
        self._max_tokens = settings.GEMINI_MAX_TOKENS
        self._client = None  # Lazy initialisation

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────

    def generate(
        self,
        messages: List[ProviderMessage],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Send a prompt to Gemini and return the generated text.

        Implements retry with exponential backoff for transient failures.
        The client is initialised on the first call (lazy init).
        """
        if self._client is None:
            self._client = self._init_client()

        last_exception: Optional[Exception] = None
        model = self._client.GenerativeModel(self._model_name)

        # Convert our ProviderMessage list to the SDK's expected format
        contents = self._to_sdk_content(messages)

        for attempt in range(1, self._max_retries + 1):
            try:
                response = model.generate_content(
                    contents,
                    generation_config=self._gen_config(max_tokens, temperature),
                    request_options={"timeout": self._timeout},
                )

                # Gemini may block responses for safety reasons
                if not response.candidates:
                    raise GeminiException(
                        message="Gemini blocked the response (safety filter). "
                        "Consider adjusting the prompt or safety settings."
                    )

                raw = response.text.strip()
                if not raw:
                    raise GeminiException(
                        message="Gemini returned an empty response."
                    )

                logger.debug(
                    "Gemini generation succeeded",
                    extra={"attempt": attempt, "response_length": len(raw)},
                )
                return raw

            except GeminiException:
                raise  # Don't retry semantic errors
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "Gemini attempt failed",
                    extra={"attempt": attempt, "error": str(exc)},
                )
                if attempt < self._max_retries:
                    sleep_time = 2 ** attempt  # exponential backoff
                    time.sleep(sleep_time)

        raise GeminiException(
            message=f"Gemini API failed after {self._max_retries} retries. "
            f"Last error: {last_exception}"
        )

    # ──────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _init_client():
        """Initialise the Google AI client."""
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise GeminiException(
                message="google-generativeai package is not installed. "
                "Install it with: pip install google-generativeai"
            ) from exc

        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise GeminiException(
                message="GEMINI_API_KEY is not configured. "
                "Set it in .env or environment variables."
            )

        genai.configure(api_key=api_key)
        return genai

    def _to_sdk_content(self, messages: List[ProviderMessage]) -> list:
        """Convert our generic messages to the Gemini SDK format."""
        contents = []
        for msg in messages:
            role = "model" if msg.role == "model" else "user"
            contents.append({"role": role, "parts": [{"text": msg.content}]})
        return contents

    def _gen_config(
        self,
        max_tokens: Optional[int],
        temperature: Optional[float],
    ) -> dict:
        """Build the generation config dict."""
        config: dict = {
            "max_output_tokens": max_tokens or self._max_tokens,
            "temperature": temperature or 0.1,  # low temp for deterministic output
        }
        return config
