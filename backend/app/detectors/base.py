"""
Abstract base class for every PII detector in the pipeline.

Every detector — whether it uses regex, heuristics, or an LLM —
must implement the ``detect()`` method and return a ``list[Detection]``.
This uniform interface lets the ``DetectionPipeline`` treat all
detectors identically.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from app.domain.models.detection import Detection


class BaseDetector(ABC):
    """
    Interface that every concrete PII detector must implement.

    Attributes
    ----------
    name : str
        Short identifier used in logging and as a ``source`` value
        in the returned ``Detection`` objects (e.g. ``"regex"``,
        ``"rule"``, ``"gemini"``).
    """

    name: str = "base"

    @abstractmethod
    def detect(self, text: str) -> List[Detection]:
        """
        Scan ``text`` and return all PII entities found.

        Parameters
        ----------
        text : str
            Normalised document text (the output of ``TextNormalizer``).

        Returns
        -------
        List[Detection]
            Every PII entity found.  Returns an empty list when nothing
            is detected — never ``None``.
        """
        ...
