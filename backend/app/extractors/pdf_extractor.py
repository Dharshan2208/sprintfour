"""
Extractor for PDF files using PyMuPDF (fitz).

PyMuPDF is preferred over ``pypdf`` / ``pdfminer.six`` because of its
speed (C-backed rendering) and robust text extraction that handles
non-standard font encodings better than pure-Python alternatives.
"""

from __future__ import annotations

import os
from typing import List, Optional

from app.core.exceptions import DocumentExtractionException
from app.domain.models.document import Document, DocumentMetadata, Line, Page, Paragraph
from app.extractors.base_extractor import BaseExtractor


class PdfExtractor(BaseExtractor):
    """Extract text from PDF documents."""

    format_name = "pdf"

    def extract(self, file_path: str, original_filename: str) -> Document:
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise DocumentExtractionException(
                message="PDF extraction requires PyMuPDF (fitz). "
                "Install it with: pip install PyMuPDF"
            ) from exc

        doc: Optional[fitz.Document] = None
        try:
            doc = fitz.open(file_path)
        except Exception as exc:
            raise DocumentExtractionException(
                message=f"Failed to open PDF file: {exc}"
            ) from exc

        try:
            pages: List[Page] = []
            raw_text_parts: List[str] = []
            global_offset = 0

            for page_num in range(len(doc)):
                page_obj = doc[page_num]
                page_text = page_obj.get_text("text")

                # ── Split page text into paragraphs ──
                # PyMuPDF's "text" mode separates text blocks with \f (form-feed)
                # and paragraphs within blocks with double newlines.
                blocks = page_text.split("\f")

                paragraphs: List[Paragraph] = []
                para_counter = 0

                for block_text in blocks:
                    block_text = block_text.strip()
                    if not block_text:
                        continue

                    # Within a block, split by double newline for paragraphs
                    para_texts = block_text.split("\n\n")
                    for para_text in para_texts:
                        para_text = para_text.strip()
                        if not para_text:
                            continue

                        # Split paragraph into lines
                        para_lines = para_text.split("\n")
                        lines: List[Line] = []
                        para_start = global_offset

                        for line_idx, line_text in enumerate(para_lines):
                            line_start = global_offset
                            global_offset += len(line_text)
                            lines.append(
                                Line(
                                    text=line_text,
                                    line_number=line_idx + 1,
                                    start_offset=line_start,
                                    end_offset=global_offset,
                                )
                            )
                            # Add back the newline we split on
                            global_offset += 1  # \n

                        # The last newline was added one too many; remove it
                        if lines:
                            global_offset -= 1

                        para_end = global_offset
                        para_full_text = "\n".join(l.text for l in lines)

                        para_counter += 1
                        paragraphs.append(
                            Paragraph(
                                text=para_full_text,
                                paragraph_number=para_counter,
                                lines=lines,
                                start_offset=para_start,
                                end_offset=para_end,
                            )
                        )

                        # Add inter-paragraph spacing
                        global_offset += 2  # \n\n

                # ── Build page text ──
                page_start = raw_text_parts[-1] if raw_text_parts else ""
                page_full_text = "\n\n".join(p.text for p in paragraphs)
                page_end = global_offset

                pages.append(
                    Page(
                        page_number=page_num + 1,
                        paragraphs=paragraphs,
                        start_offset=len("".join(raw_text_parts)),
                        end_offset=page_end,
                        text=page_full_text,
                    )
                )
                raw_text_parts.append(page_full_text)

            raw_text = "\n\n".join(raw_text_parts)

            return Document(
                metadata=DocumentMetadata(
                    filename=original_filename,
                    file_size=os.path.getsize(file_path),
                    mime_type="application/pdf",
                    extension="pdf",
                ),
                pages=pages,
                raw_text=raw_text,
                page_count=len(pages),
                character_count=len(raw_text),
            )

        except DocumentExtractionException:
            raise
        except Exception as exc:
            raise DocumentExtractionException(
                message=f"Failed to extract text from PDF: {exc}"
            ) from exc
        finally:
            if doc is not None:
                doc.close()
