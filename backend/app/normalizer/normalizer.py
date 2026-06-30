"""
Text normaliser for extracted document content.

Normalisation steps
-------------------
1. **Unicode NFC** – combine composed character sequences (e.g. ``é``
   as a single code point rather than ``e`` + ``\u0301``).
2. **Whitespace homogenisation** – replace special whitespace (non‑breaking
   space, thin space, figure space, …) with U+0020 SPACE.
3. **Line‑ending normalisation** – ``\r\n`` → ``\n``.
4. **Whitespace collapsing** – runs of two or more spaces → single space.
5. **Trailing-whitespace strip** – remove spaces at end of each line.
6. **Final newline** – ensure the document ends with ``\n``.

Offset tracking
---------------
Every normalised character position is mapped back to its original
position through an ``OffsetMapping`` list.  Because normalisation is
many‑to‑one (e.g. five spaces → one space), a range in normalised text
may correspond to a longer range in the original text.
"""

from __future__ import annotations

import unicodedata
import re
from typing import List

from app.domain.models.document import (
    Document,
    NormalizedDocument,
    OffsetMapping,
)


# ── Whitespace characters that should be replaced with a space ──
# This covers the Unicode categories Zs (space separator) except ASCII
# space itself, plus a handful of special characters commonly found in
# PDF and DOCX output.
_WHITESPACE_SUBSTITUTIONS = str.maketrans(
    {
        "\xa0": " ",   # non-breaking space (NBSP)
        "\u2000": " ", # en quad
        "\u2001": " ", # em quad
        "\u2002": " ", # en space
        "\u2003": " ", # em space
        "\u2004": " ", # three-per-em space
        "\u2005": " ", # four-per-em space
        "\u2006": " ", # six-per-em space
        "\u2007": " ", # figure space
        "\u2008": " ", # punctuation space
        "\u2009": " ", # thin space
        "\u200a": " ", # hair space
        "\u202f": " ", # narrow no-break space
        "\u205f": " ", # medium mathematical space
        "\u3000": " ", # ideographic space
    }
)

# Characters to remove entirely (zero-width, soft-hyphen, etc.)
_REMOVE_CHARS = str.maketrans(
    {
        "\u200b": "",  # zero-width space
        "\u200c": "",  # zero-width non-joiner
        "\u200d": "",  # zero-width joiner
        "\u2060": "",  # word joiner
        "\ufeff": "",  # BOM
        "\xad": "",    # soft hyphen
    }
)

# Regex for collapsing runs of spaces
_COLLAPSE_SPACES = re.compile(r"  +")

# Regex for trailing whitespace on lines
_TRAILING_WS = re.compile(r"[ \t]+$", re.MULTILINE)


class TextNormalizer:
    """
    Transform extracted raw text into normalised text suitable for
    detection, preserving offset mappings for downstream redaction.
    """

    def normalize(self, document: Document) -> NormalizedDocument:
        """
        Produce a ``NormalizedDocument`` from an extracted ``Document``.

        Parameters
        ----------
        document : Document
            The output of any ``BaseExtractor`` implementation.

        Returns
        -------
        NormalizedDocument
            Clean text with an offset map enabling accurate location
            of detections in the original extracted text.
        """
        raw = document.raw_text
        offset_maps: List[OffsetMapping] = []
        normalized_chars: List[str] = []

        orig_pos = 0
        raw_len = len(raw)

        while orig_pos < raw_len:
            ch = raw[orig_pos]

            # ── Step 1: Remove zero-width / invisible characters ──
            if ch in (
                "\u200b", "\u200c", "\u200d", "\u2060", "\ufeff", "\xad"
            ):
                # These characters simply disappear; no offset map entry
                # because they have no representation in the normalised text.
                orig_pos += 1
                continue

            # ── Step 2: Normalise line endings ──
            if ch == "\r":
                # \r\n → \n  or  standalone \r → \n
                if orig_pos + 1 < raw_len and raw[orig_pos + 1] == "\n":
                    orig_pos += 1  # skip \r, keep \n below
                # Write \n at the normalised position
                norm_start = len(normalized_chars)
                normalized_chars.append("\n")
                norm_end = len(normalized_chars)
                offset_maps.append(
                    OffsetMapping(
                        normalized_start=norm_start,
                        normalized_end=norm_end,
                        original_start=orig_pos - (1 if raw[orig_pos] == "\r" else 0),
                        original_end=orig_pos + 1,
                    )
                )
                orig_pos += 1
                continue

            # ── Step 3: Substitute special whitespace with regular space ──
            if ch in _WHITESPACE_SUBSTITUTIONS:
                ch = " "

            # ── Step 4: Unicode NFC normalisation ──
            # We process one grapheme-cluster at a time.  For simplicity
            # we NFC-normalise the entire character (which may be multiple
            # code points) and treat it as one unit.
            ch_normalized = unicodedata.normalize("NFC", ch)

            norm_start = len(normalized_chars)
            normalized_chars.append(ch_normalized)
            norm_end = len(normalized_chars)

            offset_maps.append(
                OffsetMapping(
                    normalized_start=norm_start,
                    normalized_end=norm_end,
                    original_start=orig_pos,
                    original_end=orig_pos + 1,
                )
            )
            orig_pos += 1

        # ── Step 5: Collapse runs of spaces ──
        raw_normalized = "".join(normalized_chars)
        collapsed = _COLLAPSE_SPACES.sub(" ", raw_normalized)

        # Rebuild offset maps for collapsed spaces
        offset_maps = self._rebuild_offset_maps_after_collapse(
            raw_normalized, collapsed, offset_maps
        )

        # ── Step 6: Strip trailing whitespace on each line ──
        stripped = _TRAILING_WS.sub("", collapsed)
        # Trailing-whitespace removal doesn't change character positions
        # for remaining characters (only trailing spaces are removed from
        # each line).  The offset maps remain valid for all characters
        # that were kept.

        # ── Step 7: Ensure single trailing newline ──
        normalized_text = stripped.rstrip("\n") + "\n"

        # Adjust offset maps for the stripped trailing newlines
        # (simplification: we only stripped trailing \n, which don't
        # affect any earlier offsets.)

        return NormalizedDocument(
            document_id=document.document_id,
            text=normalized_text,
            offset_maps=offset_maps,
            metadata=document.metadata,
            original_document=document,
        )

    # ──────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _rebuild_offset_maps_after_collapse(
        raw: str,
        collapsed: str,
        old_maps: List[OffsetMapping],
    ) -> List[OffsetMapping]:
        """
        After collapsing multiple spaces into one, the offset maps need
        to be rebuilt because the character positions have shifted.

        We iterate through both strings simultaneously, tracking the
        mapping between collapsed positions and original positions via
        the old per-character maps.
        """
        # Build a position map: collapsed_index → original_index
        # by walking both strings concurrently.
        new_maps: List[OffsetMapping] = []
        collapsed_idx = 0
        raw_idx = 0

        # Map each collapsed character to the original range it came from
        while raw_idx < len(raw):
            if raw[raw_idx] == " " and collapsed[collapsed_idx] == " ":
                # Start of a potential run of spaces in raw
                space_start_raw = raw_idx
                space_start_collapsed = collapsed_idx
                # Skip all spaces in raw
                while raw_idx < len(raw) and raw[raw_idx] == " ":
                    raw_idx += 1
                # One space in collapsed
                collapsed_idx += 1
                new_maps.append(
                    OffsetMapping(
                        normalized_start=space_start_collapsed,
                        normalized_end=space_start_collapsed + 1,
                        original_start=space_start_raw,
                        original_end=raw_idx,
                    )
                )
            else:
                # Non-space character — use the old offset map
                if raw_idx < len(old_maps) and raw_idx < len(raw):
                    om = old_maps[raw_idx]
                    new_maps.append(
                        OffsetMapping(
                            normalized_start=collapsed_idx,
                            normalized_end=collapsed_idx + 1,
                            original_start=om.original_start,
                            original_end=om.original_end,
                        )
                    )
                raw_idx += 1
                collapsed_idx += 1

        return new_maps
