"""
Extractor for plain-text (``.txt``) files.

Since TXT has no native page concept the entire file is treated as a
single page.  Paragraphs are delimited by one or more blank lines.
"""

from __future__ import annotations

import os
from typing import List

from app.core.exceptions import DocumentExtractionException
from app.domain.models.document import Document, DocumentMetadata, Line, Page, Paragraph
from app.extractors.base_extractor import BaseExtractor


class TxtExtractor(BaseExtractor):
    """Extract text from plain-text files."""

    format_name = "txt"

    # Encodings to try in order when reading the file.
    _ENCODINGS = ("utf-8", "latin-1", "cp1252")

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────

    def extract(self, file_path: str, original_filename: str) -> Document:
        raw_text = self._read_file(file_path)
        lines = raw_text.splitlines(keepends=False)

        page = self._build_page(lines)

        # The raw_text uses the original line endings for correctness.
        raw_text_with_newlines = "\n".join(lines)

        return Document(
            metadata=DocumentMetadata(
                filename=original_filename,
                file_size=os.path.getsize(file_path),
                mime_type="text/plain",
                extension="txt",
            ),
            pages=[page],
            raw_text=raw_text_with_newlines,
            page_count=1,
            character_count=len(raw_text_with_newlines),
        )

    # ──────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _read_file(file_path: str) -> str:
        """Read the file trying several common encodings."""
        for enc in TxtExtractor._ENCODINGS:
            try:
                with open(file_path, encoding=enc, errors="strict") as fh:
                    return fh.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise DocumentExtractionException(
            message="Could not decode TXT file with any supported encoding "
            f"(tried {', '.join(TxtExtractor._ENCODINGS)})."
        )

    def _build_page(self, lines: List[str]) -> Page:
        """Convert a flat list of text lines into a Page with paragraphs."""
        paragraphs: List[Paragraph] = []
        current_para_lines: List[str] = []
        para_counter = 0
        abs_offset = 0

        # ── We'll build a list of all lines including a virtual newline
        #    after each so offsets are correct. ──
        all_text_lines: List[str] = []
        for line in lines:
            all_text_lines.append(line)
            # We normalise line endings to \n internally.
            all_text_lines.append("\n")

        # Reset and parse paragraph structure
        line_counter = 0
        para_lines_acc: List[Line] = []
        para_start_offset = 0

        # Split on blank lines
        for i, raw_line in enumerate(lines):
            stripped = raw_line.strip()
            line_start = self._compute_abs_offset(lines, i)

            if stripped == "" and para_lines_acc:
                # End of current paragraph
                paragraph = self._finalise_paragraph(
                    para_lines_acc, para_counter + 1, para_start_offset, lines
                )
                paragraphs.append(paragraph)
                para_counter += 1
                para_lines_acc = []
                para_start_offset = 0
                continue

            if stripped == "":
                # Leading/trailing blank lines — skip
                continue

            # Non-empty line
            line_end = line_start + len(raw_line)
            if not para_lines_acc:
                para_start_offset = line_start
            para_lines_acc.append(
                Line(
                    text=raw_line,
                    line_number=len(para_lines_acc) + 1,
                    start_offset=line_start,
                    end_offset=line_end,
                )
            )

        # Flush last paragraph if any
        if para_lines_acc:
            paragraph = self._finalise_paragraph(
                para_lines_acc, para_counter + 1, para_start_offset, lines
            )
            paragraphs.append(paragraph)

        # ── Build the full page text with \n separators ──
        page_text = "\n\n".join(p.text for p in paragraphs)

        return Page(
            page_number=1,
            paragraphs=paragraphs,
            start_offset=0,
            end_offset=len(page_text),
            text=page_text,
        )

    @staticmethod
    def _compute_abs_offset(lines: List[str], line_idx: int) -> int:
        """Compute the absolute offset of line ``line_idx`` in the full text."""
        offset = 0
        for j in range(line_idx):
            offset += len(lines[j]) + 1  # +1 for the newline
        return offset

    @staticmethod
    def _finalise_paragraph(
        para_lines: List[Line],
        para_number: int,
        start_offset: int,
        all_lines: List[str],
    ) -> Paragraph:
        """Wrap accumulated Lines into a Paragraph with correct offsets."""
        para_text = "\n".join(l.text for l in para_lines)
        end_offset = start_offset + len(para_text) + (len(para_lines) - 1)  # newlines
        return Paragraph(
            text=para_text,
            paragraph_number=para_number,
            lines=para_lines,
            start_offset=start_offset,
            end_offset=end_offset,
        )
