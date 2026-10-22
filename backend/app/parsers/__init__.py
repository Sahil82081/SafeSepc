"""SafeSpec Document Parsers Package."""

from backend.app.parsers.pdf_parser import read_pdf_page, search_pdf

__all__ = [
    "read_pdf_page",
    "search_pdf",
]
