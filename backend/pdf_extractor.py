"""
PDF text extraction module using PyMuPDF.

This module provides functionality to extract text content from PDF files
and format it in a transcript-compatible structure for downstream processing.
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# Average reading speed for time estimation
WORDS_PER_MINUTE = 250
MIN_SECONDS_PER_PAGE = 10


def extract_text_from_pdf(pdf_path: Path) -> Dict[str, Any]:
    """
    Extract text from a PDF file and return in transcript-compatible format.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary containing:
        - text: Full extracted text from all pages
        - segments: List of page-based segments with timing estimates
        - engine: Metadata about extraction method
        - metadata: Additional PDF metadata (page count, etc.)

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If PDF cannot be opened or is invalid
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise ValueError(f"Failed to open PDF: {e}")

    all_text = []
    segments = []
    cumulative_time = 0.0

    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()

            if not page_text.strip():
                # Empty page, skip but record it
                logger.debug(f"Page {page_num + 1} is empty")
                continue

            # Calculate estimated reading time for this page
            word_count = len(page_text.split())
            reading_time = max(
                (word_count / WORDS_PER_MINUTE) * 60,
                MIN_SECONDS_PER_PAGE
            )

            # Create segment for this page
            segment = {
                "id": page_num,
                "start": cumulative_time,
                "end": cumulative_time + reading_time,
                "text": page_text.strip(),
                "page": page_num + 1,  # 1-indexed for user display
            }

            segments.append(segment)
            all_text.append(page_text)
            cumulative_time += reading_time

        full_text = "\n\n".join(all_text)

        # Extract PDF metadata
        metadata = {
            "page_count": len(doc),
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
        }

        result = {
            "text": full_text,
            "segments": segments,
            "engine": {
                "provider": "pymupdf",
                "version": fitz.version[0],
            },
            "metadata": metadata,
        }

        logger.info(
            f"Extracted {len(segments)} pages from PDF, "
            f"total {len(full_text)} characters"
        )

        return result

    finally:
        doc.close()


def validate_pdf(pdf_path: Path) -> bool:
    """
    Validate that a file is a valid PDF and can be opened.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        True if valid, False otherwise
    """
    try:
        doc = fitz.open(pdf_path)
        doc.close()
        return True
    except Exception as e:
        logger.warning(f"PDF validation failed for {pdf_path}: {e}")
        return False
