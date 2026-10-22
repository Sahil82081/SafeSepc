"""PDF Parser using PyMuPDF (pymupdf).

Provides robust extraction and search of automotive requirement PDFs.
Methods never crash; on exceptions, they return structured dicts with the error field set.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import pymupdf


def read_pdf_page(pdf_path: str, page_number: int) -> Dict[str, Any]:
    """Extract text and metadata from a specific page in a PDF (1-indexed).

    Args:
        pdf_path: Filesystem path to the target PDF document.
        page_number: 1-indexed page number to extract.

    Returns:
        Dict with text, page_number, total_pages, and error (None on success).
    """
    path = Path(pdf_path)
    if not path.exists():
        return {
            "text": "",
            "page_number": page_number,
            "total_pages": 0,
            "error": f"PDF file not found at: {pdf_path}",
        }

    try:
        doc = pymupdf.open(str(path))
        total = len(doc)
        if page_number < 1 or page_number > total:
            doc.close()
            return {
                "text": "",
                "page_number": page_number,
                "total_pages": total,
                "error": f"Invalid page number {page_number}. Document contains {total} pages.",
            }

        page = doc.load_page(page_number - 1)
        text = page.get_text("text")
        doc.close()

        return {
            "text": text.strip(),
            "page_number": page_number,
            "total_pages": total,
            "error": None,
        }
    except Exception as exc:
        return {
            "text": "",
            "page_number": page_number,
            "total_pages": 0,
            "error": f"Error parsing PDF page: {str(exc)}",
        }


def search_pdf(pdf_path: str, query: str) -> Dict[str, Any]:
    """Search for terms or keywords across all pages of a PDF document.

    Args:
        pdf_path: Filesystem path to the PDF document.
        query: Search string or keyword to locate.

    Returns:
        Dict with list of matches (page, snippet, rects), count, and error.
    """
    path = Path(pdf_path)
    if not path.exists():
        return {
            "matches": [],
            "count": 0,
            "error": f"PDF file not found at: {pdf_path}",
        }

    if not query.strip():
        return {
            "matches": [],
            "count": 0,
            "error": "Query string cannot be empty.",
        }

    try:
        doc = pymupdf.open(str(path))
        matches: List[Dict[str, Any]] = []

        for p_idx in range(len(doc)):
            page = doc.load_page(p_idx)
            rects = page.search_for(query)
            if rects:
                page_text = page.get_text("text")
                # Create short context snippet around query
                lower_text = page_text.lower()
                q_pos = lower_text.find(query.lower())
                start = max(0, q_pos - 60)
                end = min(len(page_text), q_pos + len(query) + 60)
                snippet = page_text[start:end].replace("\n", " ").strip()

                matches.append({
                    "page": p_idx + 1,
                    "occurrences": len(rects),
                    "snippet": f"...{snippet}..." if start > 0 else f"{snippet}...",
                })

        doc.close()
        return {
            "matches": matches,
            "count": sum(m["occurrences"] for m in matches),
            "error": None,
        }
    except Exception as exc:
        return {
            "matches": [],
            "count": 0,
            "error": f"Error searching PDF document: {str(exc)}",
        }
