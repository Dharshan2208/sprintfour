"""
Abstract base class for LLM / AI providers.

``DetectionService`` communicates **only** with this interface.  The
concrete implementation (Gemini, OpenAI, Anthropic, …) is injected at
runtime, keeping the detection logic completely vendor‑agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel


class ProviderMessage(BaseModel):
    """
    A single message in a chat conversation.
    """
    role: str  # "user" | "model" | "system"
    content: str


class BaseProvider(ABC):
    """
    Interface for text‑generation AI providers.

    The single public method ``generate`` takes a list of messages and
    optional generation parameters, and returns the model's text output.
    """

    provider_name: str = "base"

    @abstractmethod
    def generate(
        self,
        messages: List[ProviderMessage],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Send messages to the AI model and return the generated text.

        Parameters
        ----------
        messages : List[ProviderMessage]
            Conversation history.  For simple PII detection this will
            be a single ``user`` message containing the prompt + text.
        max_tokens : int, optional
            Maximum tokens in the response.
        temperature : float, optional
            Sampling temperature (0.0 = deterministic).

        Returns
        -------
        str
            The raw generated text.  No post‑processing is applied.

        Raises
        ------
        GeminiException
            For any provider‑specific failure (network, auth, rate
            limit, malformed response).
        """
        ...
